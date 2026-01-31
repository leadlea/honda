"""
Unit tests for statistics handler.
Tests count functions, error cases, and parallel execution.
"""

import json
import os
from decimal import Decimal
from unittest.mock import MagicMock, Mock, patch

import boto3
import pytest
from botocore.exceptions import ClientError
from moto import mock_aws

# Set environment variables for testing
os.environ["DYNAMODB_TABLE_PREFIX"] = "test"
os.environ["REGION"] = "us-west-2"

from src.handlers.stats_handler import (
    count_applications,
    count_completed_questionnaires,
    count_recommendations,
    create_response,
    extract_user_id_from_claims,
    fetch_statistics_parallel,
    get_profile_views,
    get_user_statistics,
)


@mock_aws
class TestStatsHandler:
    """Test cases for statistics handler."""

    def setup_method(self, method):
        """Set up test environment with mock DynamoDB tables."""
        dynamodb = boto3.resource("dynamodb", region_name="us-west-2")

        # Create Questionnaires table with UserIdIndex
        dynamodb.create_table(
            TableName="test-questionnaires",
            KeySchema=[{"AttributeName": "questionnaire_id", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "questionnaire_id", "AttributeType": "S"},
                {"AttributeName": "user_id", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "UserIdIndex",
                    "KeySchema": [{"AttributeName": "user_id", "KeyType": "HASH"}],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        # Create Recommendations table
        dynamodb.create_table(
            TableName="test-recommendations",
            KeySchema=[
                {"AttributeName": "user_id", "KeyType": "HASH"},
                {"AttributeName": "opportunity_id", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "user_id", "AttributeType": "S"},
                {"AttributeName": "opportunity_id", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        # Create Applications table with UserIdIndex
        dynamodb.create_table(
            TableName="test-applications",
            KeySchema=[{"AttributeName": "application_id", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "application_id", "AttributeType": "S"},
                {"AttributeName": "user_id", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "UserIdIndex",
                    "KeySchema": [{"AttributeName": "user_id", "KeyType": "HASH"}],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        # Create VeteranProfiles table
        dynamodb.create_table(
            TableName="test-veteran-profiles",
            KeySchema=[{"AttributeName": "user_id", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "user_id", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

    def test_extract_user_id_from_claims_success(self):
        """Test successful extraction of user ID from Cognito claims."""
        event = {
            "requestContext": {
                "authorizer": {
                    "claims": {
                        "sub": "test-user-123",
                        "email": "test@example.com",
                    }
                }
            }
        }

        user_id = extract_user_id_from_claims(event)
        assert user_id == "test-user-123"

    def test_extract_user_id_from_claims_missing(self):
        """Test extraction when claims are missing."""
        event = {"requestContext": {}}

        user_id = extract_user_id_from_claims(event)
        assert user_id is None

    def test_extract_user_id_from_claims_error(self):
        """Test extraction with malformed event."""
        event = {}

        user_id = extract_user_id_from_claims(event)
        assert user_id is None

    def test_count_completed_questionnaires_with_data(self):
        """Test counting completed questionnaires when data exists."""
        dynamodb = boto3.resource("dynamodb", region_name="us-west-2")
        table = dynamodb.Table("test-questionnaires")

        # Add test data
        table.put_item(
            Item={
                "questionnaire_id": "q1",
                "user_id": "user-123",
                "status": "completed",
            }
        )
        table.put_item(
            Item={
                "questionnaire_id": "q2",
                "user_id": "user-123",
                "status": "completed",
            }
        )
        table.put_item(
            Item={
                "questionnaire_id": "q3",
                "user_id": "user-123",
                "status": "in_progress",
            }
        )
        table.put_item(
            Item={
                "questionnaire_id": "q4",
                "user_id": "other-user",
                "status": "completed",
            }
        )

        count = count_completed_questionnaires("user-123")
        assert count == 2

    def test_count_completed_questionnaires_no_data(self):
        """Test counting completed questionnaires when no data exists."""
        count = count_completed_questionnaires("user-123")
        assert count == 0

    def test_count_recommendations_with_data(self):
        """Test counting recommendations when data exists."""
        dynamodb = boto3.resource("dynamodb", region_name="us-west-2")
        table = dynamodb.Table("test-recommendations")

        # Add test data
        table.put_item(
            Item={
                "user_id": "user-123",
                "opportunity_id": "opp-1",
                "score": Decimal("0.85"),
            }
        )
        table.put_item(
            Item={
                "user_id": "user-123",
                "opportunity_id": "opp-2",
                "score": Decimal("0.75"),
            }
        )
        table.put_item(
            Item={
                "user_id": "other-user",
                "opportunity_id": "opp-3",
                "score": Decimal("0.90"),
            }
        )

        count = count_recommendations("user-123")
        assert count == 2

    def test_count_recommendations_no_data(self):
        """Test counting recommendations when no data exists."""
        count = count_recommendations("user-123")
        assert count == 0

    def test_count_applications_with_data(self):
        """Test counting applications when data exists."""
        dynamodb = boto3.resource("dynamodb", region_name="us-west-2")
        table = dynamodb.Table("test-applications")

        # Add test data
        table.put_item(
            Item={
                "application_id": "app-1",
                "user_id": "user-123",
                "opportunity_id": "opp-1",
            }
        )
        table.put_item(
            Item={
                "application_id": "app-2",
                "user_id": "user-123",
                "opportunity_id": "opp-2",
            }
        )
        table.put_item(
            Item={
                "application_id": "app-3",
                "user_id": "other-user",
                "opportunity_id": "opp-3",
            }
        )

        count = count_applications("user-123")
        assert count == 2

    def test_count_applications_no_data(self):
        """Test counting applications when no data exists."""
        count = count_applications("user-123")
        assert count == 0

    def test_get_profile_views_with_data(self):
        """Test getting profile views when data exists."""
        dynamodb = boto3.resource("dynamodb", region_name="us-west-2")
        table = dynamodb.Table("test-veteran-profiles")

        # Add test data
        table.put_item(
            Item={
                "user_id": "user-123",
                "profile_views": 42,
            }
        )

        # Verify data was stored
        response = table.get_item(Key={"user_id": "user-123"})
        assert "Item" in response, "Item not found in table"
        assert response["Item"]["profile_views"] == 42, f"Expected 42, got {response['Item'].get('profile_views')}"

        views = get_profile_views("user-123")
        assert views == 42

    def test_get_profile_views_with_decimal(self):
        """Test getting profile views when stored as Decimal."""
        dynamodb = boto3.resource("dynamodb", region_name="us-west-2")
        table = dynamodb.Table("test-veteran-profiles")

        # Add test data with Decimal
        table.put_item(
            Item={
                "user_id": "user-123",
                "profile_views": Decimal("25"),
            }
        )

        views = get_profile_views("user-123")
        assert views == 25

    def test_get_profile_views_no_data(self):
        """Test getting profile views when profile doesn't exist."""
        views = get_profile_views("user-123")
        assert views == 0

    def test_get_profile_views_no_views_field(self):
        """Test getting profile views when profile_views field is missing."""
        dynamodb = boto3.resource("dynamodb", region_name="us-west-2")
        table = dynamodb.Table("test-veteran-profiles")

        # Add profile without profile_views field
        table.put_item(
            Item={
                "user_id": "user-123",
                "name": "Test User",
            }
        )

        views = get_profile_views("user-123")
        assert views == 0

    def test_count_completed_questionnaires_client_error(self):
        """Test error handling for DynamoDB ClientError."""
        with patch("src.handlers.stats_handler.ddb") as mock_ddb:
            mock_table = Mock()
            mock_ddb.Table.return_value = mock_table
            mock_table.query.side_effect = ClientError(
                {"Error": {"Code": "ResourceNotFoundException", "Message": "Table not found"}},
                "Query",
            )

            count = count_completed_questionnaires("user-123")
            assert count == 0

    def test_count_recommendations_client_error(self):
        """Test error handling for recommendations ClientError."""
        with patch("src.handlers.stats_handler.ddb") as mock_ddb:
            mock_table = Mock()
            mock_ddb.Table.return_value = mock_table
            mock_table.query.side_effect = ClientError(
                {"Error": {"Code": "ResourceNotFoundException", "Message": "Table not found"}},
                "Query",
            )

            count = count_recommendations("user-123")
            assert count == 0

    def test_count_applications_client_error(self):
        """Test error handling for applications ClientError."""
        with patch("src.handlers.stats_handler.ddb") as mock_ddb:
            mock_table = Mock()
            mock_ddb.Table.return_value = mock_table
            mock_table.query.side_effect = ClientError(
                {"Error": {"Code": "ResourceNotFoundException", "Message": "Table not found"}},
                "Query",
            )

            count = count_applications("user-123")
            assert count == 0

    def test_get_profile_views_client_error(self):
        """Test error handling for profile views ClientError."""
        with patch("src.handlers.stats_handler.ddb") as mock_ddb:
            mock_table = Mock()
            mock_ddb.Table.return_value = mock_table
            mock_table.get_item.side_effect = ClientError(
                {"Error": {"Code": "ResourceNotFoundException", "Message": "Table not found"}},
                "GetItem",
            )

            views = get_profile_views("user-123")
            assert views == 0

    def test_count_completed_questionnaires_generic_error(self):
        """Test error handling for generic exceptions."""
        with patch("src.handlers.stats_handler.ddb") as mock_ddb:
            mock_table = Mock()
            mock_ddb.Table.return_value = mock_table
            mock_table.query.side_effect = Exception("Unexpected error")

            count = count_completed_questionnaires("user-123")
            assert count == 0

    def test_fetch_statistics_parallel_success(self):
        """Test parallel fetching of all statistics."""
        dynamodb = boto3.resource("dynamodb", region_name="us-west-2")

        # Add test data to all tables
        q_table = dynamodb.Table("test-questionnaires")
        q_table.put_item(
            Item={"questionnaire_id": "q1", "user_id": "user-123", "status": "completed"}
        )

        r_table = dynamodb.Table("test-recommendations")
        r_table.put_item(
            Item={"user_id": "user-123", "opportunity_id": "opp-1", "score": Decimal("0.85")}
        )
        r_table.put_item(
            Item={"user_id": "user-123", "opportunity_id": "opp-2", "score": Decimal("0.75")}
        )

        a_table = dynamodb.Table("test-applications")
        a_table.put_item(
            Item={"application_id": "app-1", "user_id": "user-123", "opportunity_id": "opp-1"}
        )
        a_table.put_item(
            Item={"application_id": "app-2", "user_id": "user-123", "opportunity_id": "opp-2"}
        )
        a_table.put_item(
            Item={"application_id": "app-3", "user_id": "user-123", "opportunity_id": "opp-3"}
        )

        p_table = dynamodb.Table("test-veteran-profiles")
        p_table.put_item(Item={"user_id": "user-123", "profile_views": 15})

        stats = fetch_statistics_parallel("user-123")

        assert stats["completed_questionnaires"] == 1
        assert stats["received_recommendations"] == 2
        assert stats["submitted_applications"] == 3
        assert stats["profile_views"] == 15

    def test_fetch_statistics_parallel_no_data(self):
        """Test parallel fetching when no data exists."""
        stats = fetch_statistics_parallel("user-123")

        assert stats["completed_questionnaires"] == 0
        assert stats["received_recommendations"] == 0
        assert stats["submitted_applications"] == 0
        assert stats["profile_views"] == 0

    def test_fetch_statistics_parallel_partial_failure(self):
        """Test parallel fetching with partial failures."""
        with patch("src.handlers.stats_handler.count_completed_questionnaires") as mock_q, \
             patch("src.handlers.stats_handler.count_recommendations") as mock_r, \
             patch("src.handlers.stats_handler.count_applications") as mock_a, \
             patch("src.handlers.stats_handler.get_profile_views") as mock_v:
            
            # Simulate partial failure
            mock_q.return_value = 5
            mock_r.side_effect = Exception("Database error")
            mock_a.return_value = 3
            mock_v.return_value = 10

            stats = fetch_statistics_parallel("user-123")

            # Should have default value for failed stat
            assert stats["completed_questionnaires"] == 5
            assert stats["received_recommendations"] == 0  # Failed, default to 0
            assert stats["submitted_applications"] == 3
            assert stats["profile_views"] == 10

    def test_create_response(self):
        """Test response creation with proper headers."""
        body = {"message": "success", "data": {"count": 42}}
        response = create_response(200, body)

        assert response["statusCode"] == 200
        assert "headers" in response
        assert response["headers"]["Content-Type"] == "application/json"
        assert response["headers"]["Access-Control-Allow-Origin"] == "*"
        assert "body" in response

        parsed_body = json.loads(response["body"])
        assert parsed_body["message"] == "success"
        assert parsed_body["data"]["count"] == 42

    def test_get_user_statistics_success(self):
        """Test successful retrieval of user statistics."""
        dynamodb = boto3.resource("dynamodb", region_name="us-west-2")

        # Add test data
        q_table = dynamodb.Table("test-questionnaires")
        q_table.put_item(
            Item={"questionnaire_id": "q1", "user_id": "user-123", "status": "completed"}
        )

        event = {
            "requestContext": {
                "authorizer": {
                    "claims": {"sub": "user-123"}
                }
            },
            "pathParameters": {"userId": "user-123"},
        }

        response = get_user_statistics(event, {})

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["user_id"] == "user-123"
        assert "statistics" in body
        assert body["statistics"]["completed_questionnaires"] == 1
        assert "last_updated" in body

    def test_get_user_statistics_no_auth(self):
        """Test statistics retrieval without authentication."""
        event = {
            "requestContext": {},
            "pathParameters": {"userId": "user-123"},
        }

        response = get_user_statistics(event, {})

        assert response["statusCode"] == 401
        body = json.loads(response["body"])
        assert "error" in body

    def test_get_user_statistics_missing_user_id(self):
        """Test statistics retrieval without user ID in path."""
        event = {
            "requestContext": {
                "authorizer": {
                    "claims": {"sub": "user-123"}
                }
            },
            "pathParameters": {},
        }

        response = get_user_statistics(event, {})

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "error" in body

    def test_get_user_statistics_unauthorized_access(self):
        """Test statistics retrieval for different user (authorization check)."""
        event = {
            "requestContext": {
                "authorizer": {
                    "claims": {"sub": "user-123"}
                }
            },
            "pathParameters": {"userId": "other-user"},
        }

        response = get_user_statistics(event, {})

        assert response["statusCode"] == 403
        body = json.loads(response["body"])
        assert "error" in body
        assert "Access denied" in body["error"]

    def test_get_user_statistics_internal_error(self):
        """Test statistics retrieval with internal error."""
        with patch("src.handlers.stats_handler.extract_user_id_from_claims") as mock_extract:
            mock_extract.side_effect = Exception("Unexpected error")

            event = {
                "requestContext": {
                    "authorizer": {
                        "claims": {"sub": "user-123"}
                    }
                },
                "pathParameters": {"userId": "user-123"},
            }

            response = get_user_statistics(event, {})

            assert response["statusCode"] == 500
            body = json.loads(response["body"])
            assert "error" in body
