"""
Performance tests for statistics handler.
Tests response time and parallel execution efficiency.
"""

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import boto3
import pytest
from moto import mock_aws

# Set environment variables for testing
os.environ["DYNAMODB_TABLE_PREFIX"] = "test"
os.environ["REGION"] = "us-west-2"

from src.handlers.stats_handler import (
    fetch_statistics_parallel,
    get_user_statistics,
)


@mock_aws
class TestStatsPerformance:
    """Performance tests for statistics handler."""

    def setup_method(self, method):
        """Set up test environment with mock DynamoDB tables."""
        dynamodb = boto3.resource("dynamodb", region_name="us-west-2")

        # Create all required tables
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

        dynamodb.create_table(
            TableName="test-veteran-profiles",
            KeySchema=[{"AttributeName": "user_id", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "user_id", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        # Populate with test data
        self._populate_test_data(dynamodb)

    def _populate_test_data(self, dynamodb):
        """Populate tables with test data."""
        # Add questionnaires
        q_table = dynamodb.Table("test-questionnaires")
        for i in range(10):
            q_table.put_item(
                Item={
                    "questionnaire_id": f"q-{i}",
                    "user_id": "user-123",
                    "status": "completed",
                }
            )

        # Add recommendations
        r_table = dynamodb.Table("test-recommendations")
        for i in range(15):
            r_table.put_item(
                Item={
                    "user_id": "user-123",
                    "opportunity_id": f"opp-{i}",
                    "score": Decimal("0.85"),
                }
            )

        # Add applications
        a_table = dynamodb.Table("test-applications")
        for i in range(8):
            a_table.put_item(
                Item={
                    "application_id": f"app-{i}",
                    "user_id": "user-123",
                    "opportunity_id": f"opp-{i}",
                }
            )

        # Add profile
        p_table = dynamodb.Table("test-veteran-profiles")
        p_table.put_item(
            Item={
                "user_id": "user-123",
                "profile_views": 42,
            }
        )

    def test_parallel_fetch_performance(self):
        """Test that parallel fetching completes quickly."""
        user_id = "user-123"

        # Measure parallel execution time
        start_time = time.time()
        stats_parallel = fetch_statistics_parallel(user_id)
        parallel_time = time.time() - start_time

        print(f"\nParallel execution time: {parallel_time:.4f} seconds")
        print(f"Statistics retrieved: {stats_parallel}")

        # Verify results are correct
        assert stats_parallel["completed_questionnaires"] == 10
        assert stats_parallel["received_recommendations"] == 15
        assert stats_parallel["submitted_applications"] == 8
        assert stats_parallel["profile_views"] == 42

        # Parallel execution should complete reasonably fast
        assert parallel_time < 5.0, f"Parallel execution took {parallel_time:.4f}s, expected < 5.0s"

    def test_get_user_statistics_response_time(self):
        """Test that get_user_statistics responds within acceptable time."""
        event = {
            "requestContext": {
                "authorizer": {
                    "claims": {"sub": "user-123"}
                }
            },
            "pathParameters": {"userId": "user-123"},
        }

        # Measure response time
        start_time = time.time()
        response = get_user_statistics(event, {})
        response_time = time.time() - start_time

        print(f"\nAPI response time: {response_time:.4f} seconds")

        # Verify successful response
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["user_id"] == "user-123"
        assert "statistics" in body

        # Response should be within 5 seconds (requirement from design doc)
        assert response_time < 5.0, f"Response took {response_time:.4f}s, expected < 5.0s"

    def test_multiple_concurrent_requests(self):
        """Test handling multiple concurrent requests efficiently."""
        event_template = {
            "requestContext": {
                "authorizer": {
                    "claims": {"sub": "user-123"}
                }
            },
            "pathParameters": {"userId": "user-123"},
        }

        num_requests = 10

        # Measure time for concurrent requests
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(get_user_statistics, event_template, {})
                for _ in range(num_requests)
            ]
            results = [f.result() for f in futures]

        total_time = time.time() - start_time
        avg_time = total_time / num_requests

        print(f"\nConcurrent requests: {num_requests}")
        print(f"Total time: {total_time:.4f} seconds")
        print(f"Average time per request: {avg_time:.4f} seconds")

        # All requests should succeed
        assert all(r["statusCode"] == 200 for r in results)

        # Total time should be reasonable
        assert total_time < 10.0, f"Concurrent requests took {total_time:.4f}s, expected < 10.0s"
