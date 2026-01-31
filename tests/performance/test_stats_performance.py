"""
Performance tests for statistics handler.
Tests response time and parallel execution efficiency.
"""

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from unittest.mock import Mock, patch

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
        """Test that parallel fetching is faster than sequential."""
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
        # With moto, this should be very fast (< 1 second)
        assert parallel_time < 1.0, f"Parallel execution took {parallel_time:.4f}s, expected < 1.0s"

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

        # For moto, it should be much faster (< 1 second)
        assert response_time < 1.0, f"Response took {response_time:.4f}s, expected < 1.0s with moto"

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

        # Total time should be reasonable (not num_requests * single_request_time)
        # With parallel execution, should be much faster
        assert total_time < 5.0, f"Concurrent requests took {total_time:.4f}s, expected < 5.0s"

    def test_large_dataset_performance(self):
        """Test performance with larger datasets."""
        dynamodb = boto3.resource("dynamodb", region_name="us-west-2")

        # Add more data
        q_table = dynamodb.Table("test-questionnaires")
        for i in range(10, 100):  # Add 90 more questionnaires
            q_table.put_item(
                Item={
                    "questionnaire_id": f"q-{i}",
                    "user_id": "user-123",
                    "status": "completed",
                }
            )

        # Measure response time with larger dataset
        start_time = time.time()
        stats = fetch_statistics_parallel("user-123")
        response_time = time.time() - start_time

        print(f"\nLarge dataset response time: {response_time:.4f} seconds")
        print(f"Questionnaires count: {stats['completed_questionnaires']}")

        # Should still be fast
        assert response_time < 2.0, f"Large dataset query took {response_time:.4f}s, expected < 2.0s"

        # Verify correct count
        assert stats["completed_questionnaires"] == 100

    def test_parallel_vs_sequential_comparison(self):
        """Compare parallel vs sequential execution times."""
        from src.handlers.stats_handler import (
            count_applications,
            count_completed_questionnaires,
            count_recommendations,
            get_profile_views,
        )

        user_id = "user-123"

        # Measure sequential execution
        start_time = time.time()
        q_count = count_completed_questionnaires(user_id)
        r_count = count_recommendations(user_id)
        a_count = count_applications(user_id)
        p_views = get_profile_views(user_id)
        sequential_time = time.time() - start_time

        # Measure parallel execution
        start_time = time.time()
        stats = fetch_statistics_parallel(user_id)
        parallel_time = time.time() - start_time

        print(f"\nSequential execution time: {sequential_time:.4f} seconds")
        print(f"Parallel execution time: {parallel_time:.4f} seconds")
        
        if sequential_time > 0:
            speedup = sequential_time / parallel_time
            print(f"Speedup: {speedup:.2f}x")

        # Results should be the same
        assert stats["completed_questionnaires"] == q_count
        assert stats["received_recommendations"] == r_count
        assert stats["submitted_applications"] == a_count
        assert stats["profile_views"] == p_views

        # Parallel should be at least as fast (or faster) than sequential
        # Note: With moto, the difference might be minimal due to mocking
        assert parallel_time <= sequential_time * 1.5, \
            f"Parallel ({parallel_time:.4f}s) should not be significantly slower than sequential ({sequential_time:.4f}s)"


if __name__ == "__main__":
    # Run performance tests
    pytest.main([__file__, "-v", "-s"])
