"""
Statistics Handler Lambda function.
Retrieves user statistics data from DynamoDB tables.
"""

import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
REGION = os.environ.get("AWS_REGION") or os.environ.get("REGION") or "ap-northeast-1"
PREFIX = os.environ.get("DYNAMODB_TABLE_PREFIX", "honda-veteran-talent-matching-dev")

# DynamoDB resource
ddb = boto3.resource("dynamodb", region_name=REGION)


def extract_user_id_from_claims(event: Dict[str, Any]) -> Optional[str]:
    """
    Extract user ID from Cognito authorizer claims.
    """
    try:
        request_context = event.get("requestContext", {})
        authorizer = request_context.get("authorizer", {})
        claims = authorizer.get("claims", {})
        return claims.get("sub")
    except Exception as e:
        logger.error(f"Error extracting user from claims: {str(e)}")
        return None


def get_user_statistics(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Get user statistics data.
    Retrieves completed questionnaires, recommendations, applications, and profile views.
    """
    try:
        # Extract user ID from Cognito claims
        user_id = extract_user_id_from_claims(event)
        if not user_id:
            logger.error("No user ID found in Cognito claims")
            return create_response(401, {"error": "Authentication required"})

        # Extract target user ID from path
        path_parameters = event.get("pathParameters") or {}
        target_user_id = path_parameters.get("userId")

        if not target_user_id:
            return create_response(400, {"error": "User ID required"})

        # Authorization check: users can only access their own statistics
        if user_id != target_user_id:
            logger.warning(
                f"User {user_id} attempted to access statistics for user {target_user_id}"
            )
            return create_response(403, {"error": "Access denied"})

        logger.info(f"Fetching statistics for user: {target_user_id}")

        # Fetch statistics in parallel for better performance
        statistics = fetch_statistics_parallel(target_user_id)

        response_data = {
            "user_id": target_user_id,
            "statistics": statistics,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

        logger.info(f"Successfully retrieved statistics for user {target_user_id}")
        return create_response(200, response_data)

    except Exception as e:
        logger.error(f"Error getting user statistics: {str(e)}", exc_info=True)
        return create_response(500, {"error": "Internal server error"})


def fetch_statistics_parallel(user_id: str) -> Dict[str, int]:
    """
    Fetch all statistics data in parallel using ThreadPoolExecutor.
    """
    statistics = {
        "completed_questionnaires": 0,
        "received_recommendations": 0,
        "submitted_applications": 0,
        "profile_views": 0,
    }

    # Use ThreadPoolExecutor for parallel data fetching
    with ThreadPoolExecutor(max_workers=4) as executor:
        # Submit all tasks
        future_to_stat = {
            executor.submit(count_completed_questionnaires, user_id): "completed_questionnaires",
            executor.submit(count_recommendations, user_id): "received_recommendations",
            executor.submit(count_applications, user_id): "submitted_applications",
            executor.submit(get_profile_views, user_id): "profile_views",
        }

        # Collect results as they complete
        for future in as_completed(future_to_stat):
            stat_name = future_to_stat[future]
            try:
                result = future.result()
                statistics[stat_name] = result
                logger.info(f"Retrieved {stat_name}: {result}")
            except Exception as e:
                logger.error(f"Error fetching {stat_name}: {str(e)}")
                # Keep default value of 0 on error

    return statistics


def count_completed_questionnaires(user_id: str) -> int:
    """
    Count completed questionnaires for a user.
    Uses UserIdIndex GSI to query by user_id and filters by status='completed'.
    """
    try:
        table = ddb.Table(f"{PREFIX}-questionnaires")
        
        response = table.query(
            IndexName="UserIdIndex",
            KeyConditionExpression=Key("user_id").eq(user_id),
            FilterExpression="attribute_exists(#status) AND #status = :status",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={":status": "completed"},
        )

        count = len(response.get("Items", []))
        logger.info(f"Completed questionnaires for user {user_id}: {count}")
        return count

    except ClientError as e:
        logger.error(
            f"DynamoDB error counting questionnaires for user {user_id}: {e.response['Error']['Code']} - {e.response['Error']['Message']}"
        )
        return 0
    except Exception as e:
        logger.error(f"Error counting questionnaires for user {user_id}: {str(e)}")
        return 0


def count_recommendations(user_id: str) -> int:
    """
    Count recommendations for a user.
    Recommendations table uses user_id as partition key.
    """
    try:
        table = ddb.Table(f"{PREFIX}-recommendations")
        
        response = table.query(
            KeyConditionExpression=Key("user_id").eq(user_id)
        )

        count = len(response.get("Items", []))
        logger.info(f"Recommendations for user {user_id}: {count}")
        return count

    except ClientError as e:
        logger.error(
            f"DynamoDB error counting recommendations for user {user_id}: {e.response['Error']['Code']} - {e.response['Error']['Message']}"
        )
        return 0
    except Exception as e:
        logger.error(f"Error counting recommendations for user {user_id}: {str(e)}")
        return 0


def count_applications(user_id: str) -> int:
    """
    Count applications submitted by a user.
    Uses UserIdIndex GSI to query by user_id.
    """
    try:
        table = ddb.Table(f"{PREFIX}-applications")
        
        response = table.query(
            IndexName="UserIdIndex",
            KeyConditionExpression=Key("user_id").eq(user_id)
        )

        count = len(response.get("Items", []))
        logger.info(f"Applications for user {user_id}: {count}")
        return count

    except ClientError as e:
        logger.error(
            f"DynamoDB error counting applications for user {user_id}: {e.response['Error']['Code']} - {e.response['Error']['Message']}"
        )
        return 0
    except Exception as e:
        logger.error(f"Error counting applications for user {user_id}: {str(e)}")
        return 0


def get_profile_views(user_id: str) -> int:
    """
    Get profile view count for a user.
    Retrieves the profile_views field from VeteranProfiles table.
    """
    try:
        table = ddb.Table(f"{PREFIX}-veteran-profiles")
        
        response = table.get_item(Key={"user_id": user_id})
        
        item = response.get("Item", {})
        profile_views = item.get("profile_views", 0)
        
        # Handle Decimal type from DynamoDB
        if isinstance(profile_views, (int, float)):
            profile_views = int(profile_views)
        else:
            profile_views = 0

        logger.info(f"Profile views for user {user_id}: {profile_views}")
        return profile_views

    except ClientError as e:
        logger.error(
            f"DynamoDB error getting profile views for user {user_id}: {e.response['Error']['Code']} - {e.response['Error']['Message']}"
        )
        return 0
    except Exception as e:
        logger.error(f"Error getting profile views for user {user_id}: {str(e)}")
        return 0


def create_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create standardized HTTP response with CORS headers.
    """
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Amz-User-Agent",
            "Access-Control-Allow-Methods": "GET,OPTIONS",
        },
        "body": json.dumps(body, default=str),
    }
