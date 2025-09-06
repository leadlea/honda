"""
Unit tests for ApplicationRepository
"""
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import boto3
import pytest
from moto import mock_dynamodb

from src.models.application import Application
from src.repositories.application_repository import ApplicationRepository


@mock_dynamodb
class TestApplicationRepository:
    """Test cases for ApplicationRepository"""

    def setup_method(self, method):
        """Set up test fixtures"""
        # Create mock DynamoDB table
        self.dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

        # Create table
        self.table = self.dynamodb.create_table(
            TableName="Applications",
            KeySchema=[{"AttributeName": "application_id", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "application_id", "AttributeType": "S"},
                {"AttributeName": "user_id", "AttributeType": "S"},
                {"AttributeName": "opportunity_id", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "UserApplicationsIndex",
                    "KeySchema": [
                        {"AttributeName": "user_id", "KeyType": "HASH"},
                        {"AttributeName": "application_id", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                    "ProvisionedThroughput": {
                        "ReadCapacityUnits": 5,
                        "WriteCapacityUnits": 5,
                    },
                },
                {
                    "IndexName": "OpportunityApplicationsIndex",
                    "KeySchema": [
                        {"AttributeName": "opportunity_id", "KeyType": "HASH"},
                        {"AttributeName": "application_id", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                    "ProvisionedThroughput": {
                        "ReadCapacityUnits": 5,
                        "WriteCapacityUnits": 5,
                    },
                },
            ],
            BillingMode="PROVISIONED",
            ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
        )

        # Initialize repository with mocked table
        self.repo = ApplicationRepository()
        self.repo.table = self.table

        # Sample application data
        self.sample_application = Application(
            application_id="app123",
            user_id="user123",
            opportunity_id="opp123",
            status="submitted",
            cover_letter="Test cover letter",
            additional_notes="5 years experience",
            submitted_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )

    def test_create_application_success(self):
        """Test successful application creation"""
        result = self.repo.create_application(self.sample_application)

        assert result is True

        # Verify application was stored
        response = self.table.get_item(Key={"application_id": "app123"})
        assert "Item" in response
        assert response["Item"]["user_id"] == "user123"
        assert response["Item"]["status"] == "submitted"

    def test_create_application_failure(self):
        """Test application creation failure"""
        # Mock table to raise exception
        with patch.object(
            self.repo.table, "put_item", side_effect=Exception("DynamoDB error")
        ):
            result = self.repo.create_application(self.sample_application)
            assert result is False

    def test_get_application_success(self):
        """Test successful application retrieval"""
        # First create the application
        self.repo.create_application(self.sample_application)

        # Then retrieve it
        result = self.repo.get_application("app123")

        assert result is not None
        assert result.application_id == "app123"
        assert result.user_id == "user123"
        assert result.status == "submitted"

    def test_get_application_not_found(self):
        """Test application retrieval when not found"""
        result = self.repo.get_application("nonexistent")
        assert result is None

    def test_get_application_exception(self):
        """Test application retrieval with exception"""
        with patch.object(
            self.repo.table, "get_item", side_effect=Exception("DynamoDB error")
        ):
            result = self.repo.get_application("app123")
            assert result is None

    def test_update_application_success(self):
        """Test successful application update"""
        # First create the application
        self.repo.create_application(self.sample_application)

        # Update the application
        self.sample_application.status = "under_review"
        self.sample_application.updated_at = "2024-01-02T00:00:00"

        result = self.repo.update_application(self.sample_application)
        assert result is True

        # Verify update
        updated_app = self.repo.get_application("app123")
        assert updated_app.status == "under_review"
        assert updated_app.updated_at == "2024-01-02T00:00:00"

    def test_update_application_failure(self):
        """Test application update failure"""
        with patch.object(
            self.repo.table, "put_item", side_effect=Exception("DynamoDB error")
        ):
            result = self.repo.update_application(self.sample_application)
            assert result is False

    def test_delete_application_success(self):
        """Test successful application deletion"""
        # First create the application
        self.repo.create_application(self.sample_application)

        # Delete it
        result = self.repo.delete_application("app123")
        assert result is True

        # Verify deletion
        deleted_app = self.repo.get_application("app123")
        assert deleted_app is None

    def test_delete_application_failure(self):
        """Test application deletion failure"""
        with patch.object(
            self.repo.table, "delete_item", side_effect=Exception("DynamoDB error")
        ):
            result = self.repo.delete_application("app123")
            assert result is False

    def test_get_user_applications_success(self):
        """Test successful retrieval of user applications"""
        # Create multiple applications for the user
        app1 = Application(
            application_id="app1",
            user_id="user123",
            opportunity_id="opp1",
            status="submitted",
        )
        app2 = Application(
            application_id="app2",
            user_id="user123",
            opportunity_id="opp2",
            status="under_review",
        )

        self.repo.create_application(app1)
        self.repo.create_application(app2)

        # Get user applications
        result = self.repo.get_user_applications("user123")

        assert len(result) == 2
        assert all(app.user_id == "user123" for app in result)

    def test_get_user_applications_with_status_filter(self):
        """Test retrieval of user applications with status filter"""
        # Create applications with different statuses
        app1 = Application(
            application_id="app1",
            user_id="user123",
            opportunity_id="opp1",
            status="submitted",
        )
        app2 = Application(
            application_id="app2",
            user_id="user123",
            opportunity_id="opp2",
            status="under_review",
        )

        self.repo.create_application(app1)
        self.repo.create_application(app2)

        # Get applications with specific status
        result = self.repo.get_user_applications("user123", status="submitted")

        assert len(result) == 1
        assert result[0].status == "submitted"

    def test_get_user_applications_exception(self):
        """Test user applications retrieval with exception"""
        with patch.object(
            self.repo.table, "query", side_effect=Exception("DynamoDB error")
        ):
            result = self.repo.get_user_applications("user123")
            assert result == []

    def test_get_opportunity_applications_success(self):
        """Test successful retrieval of opportunity applications"""
        # Create multiple applications for the opportunity
        app1 = Application(
            application_id="app1",
            user_id="user1",
            opportunity_id="opp123",
            status="submitted",
        )
        app2 = Application(
            application_id="app2",
            user_id="user2",
            opportunity_id="opp123",
            status="under_review",
        )

        self.repo.create_application(app1)
        self.repo.create_application(app2)

        # Get opportunity applications
        result = self.repo.get_opportunity_applications("opp123")

        assert len(result) == 2
        assert all(app.opportunity_id == "opp123" for app in result)

    def test_get_opportunity_applications_exception(self):
        """Test opportunity applications retrieval with exception"""
        with patch.object(
            self.repo.table, "query", side_effect=Exception("DynamoDB error")
        ):
            result = self.repo.get_opportunity_applications("opp123")
            assert result == []

    def test_application_exists_true(self):
        """Test application existence check when exists"""
        self.repo.create_application(self.sample_application)

        result = self.repo.application_exists("user123", "opp123")
        assert result is True

    def test_application_exists_false(self):
        """Test application existence check when doesn't exist"""
        result = self.repo.application_exists("user123", "opp123")
        assert result is False

    def test_application_exists_exception(self):
        """Test application existence check with exception"""
        with patch.object(
            self.repo.table, "query", side_effect=Exception("DynamoDB error")
        ):
            result = self.repo.application_exists("user123", "opp123")
            assert result is False
