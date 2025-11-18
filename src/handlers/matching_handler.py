"""
Lambda handler for AI matching and recommendation operations.
Handles profile-opportunity matching, recommendation generation, and match analysis.
"""

import asyncio
import json
import logging
from typing import Any, Dict

from ..services.matching_engine import MatchingCriteria, get_matching_engine
from ..services.recommendation_service import (
    RecommendationFeedback,
    get_recommendation_service,
)
from ..utils.auth_utils import extract_user_from_event
from ..utils.rbac import Permission, require_permission

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for matching operations.

    Args:
        event: Lambda event containing HTTP request data
        context: Lambda context object

    Returns:
        HTTP response dictionary
    """
    try:
        # Extract HTTP method and path
        http_method = event.get("httpMethod", "")
        path = event.get("path", "")

        # Route to appropriate handler
        if http_method == "POST" and "/generate" in path:
            return handle_generate_recommendations(event, context)
        elif http_method == "POST" and "/refresh" in path:
            return handle_refresh_recommendations(event, context)
        elif http_method == "GET" and "/recommendations/" in path:
            return handle_get_recommendations(event, context)
        elif http_method == "GET" and "/match-analysis/" in path:
            return handle_get_match_analysis(event, context)
        elif http_method == "POST" and path.endswith("/match-analysis"):
            return handle_analyze_match(event, context)
        elif http_method == "POST" and path.endswith("/batch-recommendations"):
            return handle_batch_generate_recommendations(event, context)
        elif http_method == "POST" and "/feedback" in path:
            return handle_recommendation_feedback(event, context)
        elif http_method == "GET" and "/statistics" in path:
            return handle_get_recommendation_statistics(event, context)
        elif http_method == "GET" and "/history" in path:
            return handle_get_recommendation_history(event, context)
        elif http_method == "GET" and "/insights" in path:
            return handle_get_recommendation_insights(event, context)
        else:
            return {
                "statusCode": 404,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps(
                    {"error": "Endpoint not found", "path": path, "method": http_method}
                ),
            }

    except Exception as e:
        logger.error(f"Unhandled error in matching handler: {e}")
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"error": "Internal server error", "message": str(e)}),
        }


def handle_get_recommendations(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle GET /recommendations/{user_id} - Get recommendations for a user.
    """
    try:
        # Get user data from API Gateway authorizer context
        user_data = extract_user_from_event(event)
        if not user_data:
            return {
                "statusCode": 401,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps({"error": "Authentication required"}),
            }

        # Check permissions
        if not require_permission(user_data, Permission.READ_RECOMMENDATIONS):
            return {
                "statusCode": 403,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps({"error": "Insufficient permissions"}),
            }

        # Extract user ID from path
        path_params = event.get("pathParameters", {})
        user_id = path_params.get("user_id")

        if not user_id:
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps({"error": "user_id is required"}),
            }

        # Check if user can access this user's recommendations
        requesting_user_id = user_data.get("user_id")
        if user_id != requesting_user_id and not require_permission(
            user_data, Permission.READ_ALL_PROFILES
        ):
            return {
                "statusCode": 403,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps(
                    {"error": "Cannot access other user recommendations"}
                ),
            }

        # Get query parameters
        query_params = event.get("queryStringParameters") or {}
        status = query_params.get("status")
        limit = int(query_params.get("limit", 20))

        # Get matching engine and fetch recommendations
        matching_engine = get_matching_engine()

        if status:
            recommendations = (
                matching_engine.recommendation_repo.get_user_recommendations_by_status(
                    user_id, status, limit
                )
            )
        else:
            recommendations = (
                matching_engine.recommendation_repo.get_user_recommendations(
                    user_id, limit
                )
            )

        # Convert to response format
        recommendations_data = []
        for rec in recommendations:
            recommendations_data.append(
                {
                    "recommendation_id": rec.recommendation_id,
                    "opportunity_id": rec.opportunity_id,
                    "match_score": rec.match_score,
                    "match_reasons": rec.match_reasons,
                    "status": rec.status,
                    "generated_at": rec.generated_at,
                    "viewed_at": rec.viewed_at,
                    "applied_at": rec.applied_at,
                }
            )

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps(
                {
                    "recommendations": recommendations_data,
                    "count": len(recommendations_data),
                }
            ),
        }

    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps(
                {"error": "Failed to get recommendations", "message": str(e)}
            ),
        }


def handle_generate_recommendations(
    event: Dict[str, Any], context: Any
) -> Dict[str, Any]:
    """
    Handle POST /recommendations/{user_id}/generate - Generate new recommendations for a user.
    """
    try:
        # Verify authentication
        token = event.get("headers", {}).get("Authorization", "").replace("Bearer ", "")
        if not token:
            return {
                "statusCode": 401,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps({"error": "Authorization token required"}),
            }

        user_data = verify_jwt_token(token)
        if not user_data:
            return {
                "statusCode": 401,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps({"error": "Invalid or expired token"}),
            }

        # Check permissions
        if not require_permission(user_data, Permission.GENERATE_RECOMMENDATIONS):
            return {
                "statusCode": 403,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps({"error": "Insufficient permissions"}),
            }

        # Extract user ID from path
        path_params = event.get("pathParameters", {})
        user_id = path_params.get("user_id")

        if not user_id:
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps({"error": "user_id is required"}),
            }

        # Parse request body for criteria
        body = event.get("body", "{}")
        if isinstance(body, str):
            body = json.loads(body)

        # Build matching criteria
        criteria = None
        if body:
            criteria = MatchingCriteria(
                min_score_threshold=body.get("min_score_threshold", 0.3),
                max_recommendations_per_user=body.get("max_recommendations", 10),
                include_internal_only=body.get("include_internal_only", False),
                include_external_only=body.get("include_external_only", False),
                preferred_locations=body.get("preferred_locations"),
                required_skills=body.get("required_skills"),
                opportunity_types=body.get("opportunity_types"),
            )

        # Generate recommendations
        matching_engine = get_matching_engine()

        # Run async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            recommendations = loop.run_until_complete(
                matching_engine.refresh_recommendations_for_veteran(user_id, criteria)
            )
        finally:
            loop.close()

        # Convert to response format
        recommendations_data = []
        for rec in recommendations:
            recommendations_data.append(
                {
                    "recommendation_id": rec.recommendation_id,
                    "opportunity_id": rec.opportunity_id,
                    "match_score": rec.match_score,
                    "match_reasons": rec.match_reasons,
                    "status": rec.status,
                    "generated_at": rec.generated_at,
                }
            )

        return {
            "statusCode": 201,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps(
                {
                    "message": "Recommendations generated successfully",
                    "recommendations": recommendations_data,
                    "count": len(recommendations_data),
                }
            ),
        }

    except Exception as e:
        logger.error(f"Error generating recommendations: {e}")
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps(
                {"error": "Failed to generate recommendations", "message": str(e)}
            ),
        }


def handle_refresh_recommendations(
    event: Dict[str, Any], context: Any
) -> Dict[str, Any]:
    """
    Handle POST /recommendations/{user_id}/refresh - Refresh recommendations for a user.
    """
    # This is essentially the same as generate_recommendations
    return handle_generate_recommendations(event, context)


def handle_get_match_analysis(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle GET /match-analysis/{user_id}/{opportunity_id} - Get detailed match analysis.
    """
    try:
        # Verify authentication
        token = event.get("headers", {}).get("Authorization", "").replace("Bearer ", "")
        if not token:
            return {
                "statusCode": 401,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps({"error": "Authorization token required"}),
            }

        user_data = verify_jwt_token(token)
        if not user_data:
            return {
                "statusCode": 401,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps({"error": "Invalid or expired token"}),
            }

        # Check permissions
        if not require_permission(user_data, Permission.READ_RECOMMENDATIONS):
            return {
                "statusCode": 403,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps({"error": "Insufficient permissions"}),
            }

        # Extract parameters from path
        path_params = event.get("pathParameters", {})
        user_id = path_params.get("user_id")
        opportunity_id = path_params.get("opportunity_id")

        if not user_id or not opportunity_id:
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps(
                    {"error": "user_id and opportunity_id are required"}
                ),
            }

        # Get match explanation
        matching_engine = get_matching_engine()

        # Run async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            match_explanation = loop.run_until_complete(
                matching_engine.get_match_explanation(user_id, opportunity_id)
            )
        finally:
            loop.close()

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps(match_explanation),
        }

    except Exception as e:
        logger.error(f"Error getting match analysis: {e}")
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps(
                {"error": "Failed to get match analysis", "message": str(e)}
            ),
        }


def handle_analyze_match(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle POST /match-analysis - Analyze match between veteran and opportunity.
    """
    try:
        # Verify authentication
        token = event.get("headers", {}).get("Authorization", "").replace("Bearer ", "")
        if not token:
            return {
                "statusCode": 401,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps({"error": "Authorization token required"}),
            }

        user_data = verify_jwt_token(token)
        if not user_data:
            return {
                "statusCode": 401,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps({"error": "Invalid or expired token"}),
            }

        # Check permissions
        if not require_permission(user_data, Permission.ANALYZE_MATCHES):
            return {
                "statusCode": 403,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps({"error": "Insufficient permissions"}),
            }

        # Parse request body
        body = event.get("body", "{}")
        if isinstance(body, str):
            body = json.loads(body)

        user_id = body.get("user_id")
        opportunity_id = body.get("opportunity_id")

        if not user_id or not opportunity_id:
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps(
                    {"error": "user_id and opportunity_id are required"}
                ),
            }

        # Get veteran profile and opportunity
        matching_engine = get_matching_engine()
        veteran_profile = matching_engine.veteran_repo.get_profile(user_id)
        opportunity = matching_engine.opportunity_repo.get_opportunity(opportunity_id)

        if not veteran_profile:
            return {
                "statusCode": 404,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps({"error": "Veteran profile not found"}),
            }

        if not opportunity:
            return {
                "statusCode": 404,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps({"error": "Opportunity not found"}),
            }

        # Analyze match
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            match_result = loop.run_until_complete(
                matching_engine.analyze_match(veteran_profile, opportunity)
            )
        finally:
            loop.close()

        # Convert to response format
        response_data = {
            "veteran_id": match_result.veteran_id,
            "opportunity_id": match_result.opportunity_id,
            "overall_score": match_result.overall_score,
            "match_reasons": match_result.match_reasons,
            "recommendation_action": match_result.recommendation_action,
            "success_factors": match_result.success_factors,
            "risk_factors": match_result.risk_factors,
            "match_summary": match_result.match_summary,
        }

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps(response_data),
        }

    except Exception as e:
        logger.error(f"Error analyzing match: {e}")
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"error": "Failed to analyze match", "message": str(e)}),
        }


def handle_batch_generate_recommendations(
    event: Dict[str, Any], context: Any
) -> Dict[str, Any]:
    """
    Handle POST /batch-recommendations - Generate recommendations for multiple users.
    """
    try:
        # Verify authentication
        token = event.get("headers", {}).get("Authorization", "").replace("Bearer ", "")
        if not token:
            return {
                "statusCode": 401,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps({"error": "Authorization token required"}),
            }

        user_data = verify_jwt_token(token)
        if not user_data:
            return {
                "statusCode": 401,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps({"error": "Invalid or expired token"}),
            }

        # Check permissions (admin only for batch operations)
        if not require_permission(user_data, Permission.ADMIN_ACCESS):
            return {
                "statusCode": 403,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps(
                    {"error": "Admin access required for batch operations"}
                ),
            }

        # Parse request body
        body = event.get("body", "{}")
        if isinstance(body, str):
            body = json.loads(body)

        user_ids = body.get("user_ids", [])
        if not user_ids:
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps({"error": "user_ids list is required"}),
            }

        # Build matching criteria
        criteria = None
        if "criteria" in body:
            criteria_data = body["criteria"]
            criteria = MatchingCriteria(
                min_score_threshold=criteria_data.get("min_score_threshold", 0.3),
                max_recommendations_per_user=criteria_data.get(
                    "max_recommendations", 10
                ),
                include_internal_only=criteria_data.get("include_internal_only", False),
                include_external_only=criteria_data.get("include_external_only", False),
                preferred_locations=criteria_data.get("preferred_locations"),
                required_skills=criteria_data.get("required_skills"),
                opportunity_types=criteria_data.get("opportunity_types"),
            )

        # Generate batch recommendations
        matching_engine = get_matching_engine()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            batch_results = loop.run_until_complete(
                matching_engine.batch_generate_recommendations(user_ids, criteria)
            )
        finally:
            loop.close()

        # Save all recommendations
        all_recommendations = []
        for user_recommendations in batch_results.values():
            all_recommendations.extend(user_recommendations)

        if all_recommendations:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(
                    matching_engine.save_recommendations(all_recommendations)
                )
            finally:
                loop.close()

        # Prepare response
        results_summary = {}
        for user_id, recommendations in batch_results.items():
            results_summary[user_id] = {
                "count": len(recommendations),
                "average_score": sum(r.match_score for r in recommendations)
                / len(recommendations)
                if recommendations
                else 0,
            }

        return {
            "statusCode": 201,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps(
                {
                    "message": "Batch recommendations generated successfully",
                    "results": results_summary,
                    "total_recommendations": len(all_recommendations),
                }
            ),
        }

    except Exception as e:
        logger.error(f"Error in batch recommendation generation: {e}")
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps(
                {"error": "Failed to generate batch recommendations", "message": str(e)}
            ),
        }


def handle_recommendation_feedback(
    event: Dict[str, Any], context: Any
) -> Dict[str, Any]:
    """
    Handle POST /recommendations/{user_id}/feedback - Record feedback for a recommendation.
    """
    try:
        # Verify authentication
        token = event.get("headers", {}).get("Authorization", "").replace("Bearer ", "")
        if not token:
            return {
                "statusCode": 401,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps({"error": "Authorization token required"}),
            }

        user_data = verify_jwt_token(token)
        if not user_data:
            return {
                "statusCode": 401,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps({"error": "Invalid or expired token"}),
            }

        # Check permissions
        if not require_permission(user_data, Permission.READ_RECOMMENDATIONS):
            return {
                "statusCode": 403,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps({"error": "Insufficient permissions"}),
            }

        # Extract user ID from path
        path_params = event.get("pathParameters", {})
        user_id = path_params.get("user_id")

        if not user_id:
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps({"error": "user_id is required"}),
            }

        # Check if user can provide feedback for this user's recommendations
        requesting_user_id = user_data.get("user_id")
        if user_id != requesting_user_id and not require_permission(
            user_data, Permission.READ_ALL_PROFILES
        ):
            return {
                "statusCode": 403,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps(
                    {"error": "Cannot provide feedback for other user recommendations"}
                ),
            }

        # Parse request body
        body = event.get("body", "{}")
        if isinstance(body, str):
            body = json.loads(body)

        recommendation_id = body.get("recommendation_id")
        feedback_type = body.get("feedback_type")
        feedback_score = body.get("feedback_score")
        feedback_comment = body.get("feedback_comment")

        if not recommendation_id or not feedback_type:
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps(
                    {"error": "recommendation_id and feedback_type are required"}
                ),
            }

        # Validate feedback type
        valid_feedback_types = ["positive", "negative", "applied", "dismissed"]
        if feedback_type not in valid_feedback_types:
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps(
                    {
                        "error": f'feedback_type must be one of: {", ".join(valid_feedback_types)}'
                    }
                ),
            }

        # Create feedback object
        feedback = RecommendationFeedback(
            recommendation_id=recommendation_id,
            user_id=user_id,
            feedback_type=feedback_type,
            feedback_score=feedback_score,
            feedback_comment=feedback_comment,
        )

        # Record feedback
        recommendation_service = get_recommendation_service()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            success = loop.run_until_complete(
                recommendation_service.record_recommendation_feedback(feedback)
            )
        finally:
            loop.close()

        if success:
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps(
                    {
                        "message": "Feedback recorded successfully",
                        "feedback": {
                            "recommendation_id": recommendation_id,
                            "feedback_type": feedback_type,
                            "feedback_score": feedback_score,
                        },
                    }
                ),
            }
        else:
            return {
                "statusCode": 500,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps({"error": "Failed to record feedback"}),
            }

    except Exception as e:
        logger.error(f"Error recording recommendation feedback: {e}")
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps(
                {"error": "Failed to record feedback", "message": str(e)}
            ),
        }


def handle_get_recommendation_statistics(
    event: Dict[str, Any], context: Any
) -> Dict[str, Any]:
    """
    Handle GET /recommendations/{user_id}/statistics - Get recommendation statistics for a user.
    """
    try:
        # Verify authentication
        token = event.get("headers", {}).get("Authorization", "").replace("Bearer ", "")
        if not token:
            return {
                "statusCode": 401,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps({"error": "Authorization token required"}),
            }

        user_data = verify_jwt_token(token)
        if not user_data:
            return {
                "statusCode": 401,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps({"error": "Invalid or expired token"}),
            }

        # Check permissions
        if not require_permission(user_data, Permission.READ_RECOMMENDATIONS):
            return {
                "statusCode": 403,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps({"error": "Insufficient permissions"}),
            }

        # Extract user ID from path
        path_params = event.get("pathParameters", {})
        user_id = path_params.get("user_id")

        if not user_id:
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps({"error": "user_id is required"}),
            }

        # Check if user can access this user's statistics
        requesting_user_id = user_data.get("user_id")
        if user_id != requesting_user_id and not require_permission(
            user_data, Permission.READ_ALL_PROFILES
        ):
            return {
                "statusCode": 403,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps({"error": "Cannot access other user statistics"}),
            }

        # Get query parameters
        query_params = event.get("queryStringParameters") or {}
        days = int(query_params.get("days", 30))

        # Get statistics
        recommendation_service = get_recommendation_service()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            stats = loop.run_until_complete(
                recommendation_service.get_recommendation_statistics(user_id, days)
            )
        finally:
            loop.close()

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps(
                {
                    "statistics": {
                        "total_recommendations": stats.total_recommendations,
                        "viewed_count": stats.viewed_count,
                        "applied_count": stats.applied_count,
                        "dismissed_count": stats.dismissed_count,
                        "average_match_score": stats.average_match_score,
                        "feedback_count": stats.feedback_count,
                        "average_feedback_score": stats.average_feedback_score,
                        "conversion_rate": stats.conversion_rate,
                        "engagement_rate": stats.engagement_rate,
                    },
                    "period_days": days,
                }
            ),
        }

    except Exception as e:
        logger.error(f"Error getting recommendation statistics: {e}")
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps(
                {"error": "Failed to get statistics", "message": str(e)}
            ),
        }


def handle_get_recommendation_history(
    event: Dict[str, Any], context: Any
) -> Dict[str, Any]:
    """
    Handle GET /recommendations/{user_id}/history - Get recommendation history for a user.
    """
    try:
        # Verify authentication
        token = event.get("headers", {}).get("Authorization", "").replace("Bearer ", "")
        if not token:
            return {
                "statusCode": 401,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps({"error": "Authorization token required"}),
            }

        user_data = verify_jwt_token(token)
        if not user_data:
            return {
                "statusCode": 401,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps({"error": "Invalid or expired token"}),
            }

        # Check permissions
        if not require_permission(user_data, Permission.READ_RECOMMENDATIONS):
            return {
                "statusCode": 403,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps({"error": "Insufficient permissions"}),
            }

        # Extract user ID from path
        path_params = event.get("pathParameters", {})
        user_id = path_params.get("user_id")

        if not user_id:
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps({"error": "user_id is required"}),
            }

        # Check if user can access this user's history
        requesting_user_id = user_data.get("user_id")
        if user_id != requesting_user_id and not require_permission(
            user_data, Permission.READ_ALL_PROFILES
        ):
            return {
                "statusCode": 403,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps({"error": "Cannot access other user history"}),
            }

        # Get query parameters
        query_params = event.get("queryStringParameters") or {}
        limit = int(query_params.get("limit", 50))
        status_filter = query_params.get("status")

        # Get history
        recommendation_service = get_recommendation_service()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            history = loop.run_until_complete(
                recommendation_service.get_recommendation_history(
                    user_id, limit, status_filter
                )
            )
        finally:
            loop.close()

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps(
                {
                    "history": history,
                    "count": len(history),
                    "limit": limit,
                    "status_filter": status_filter,
                }
            ),
        }

    except Exception as e:
        logger.error(f"Error getting recommendation history: {e}")
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"error": "Failed to get history", "message": str(e)}),
        }


def handle_get_recommendation_insights(
    event: Dict[str, Any], context: Any
) -> Dict[str, Any]:
    """
    Handle GET /recommendations/{user_id}/insights - Get recommendation insights for a user.
    """
    try:
        # Verify authentication
        token = event.get("headers", {}).get("Authorization", "").replace("Bearer ", "")
        if not token:
            return {
                "statusCode": 401,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps({"error": "Authorization token required"}),
            }

        user_data = verify_jwt_token(token)
        if not user_data:
            return {
                "statusCode": 401,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps({"error": "Invalid or expired token"}),
            }

        # Check permissions
        if not require_permission(user_data, Permission.READ_RECOMMENDATIONS):
            return {
                "statusCode": 403,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps({"error": "Insufficient permissions"}),
            }

        # Extract user ID from path
        path_params = event.get("pathParameters", {})
        user_id = path_params.get("user_id")

        if not user_id:
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps({"error": "user_id is required"}),
            }

        # Check if user can access this user's insights
        requesting_user_id = user_data.get("user_id")
        if user_id != requesting_user_id and not require_permission(
            user_data, Permission.READ_ALL_PROFILES
        ):
            return {
                "statusCode": 403,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps({"error": "Cannot access other user insights"}),
            }

        # Get insights
        recommendation_service = get_recommendation_service()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            insights = loop.run_until_complete(
                recommendation_service.get_recommendation_insights(user_id)
            )
        finally:
            loop.close()

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps(insights),
        }

    except Exception as e:
        logger.error(f"Error getting recommendation insights: {e}")
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"error": "Failed to get insights", "message": str(e)}),
        }
