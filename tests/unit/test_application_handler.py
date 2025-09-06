"""
Unit tests for application handler
"""
import json
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.handlers.application_handler import ApplicationHandler
from src.models.application import Application
from src.models.opportunity import Opportunity
from src.models.user import User


class TestApplicationHandler:
    """Test cases for ApplicationHandler"""

    def setup_method(self):
        """Set up test fixtures"""
        self.handler = ApplicationHandler()

        # Mock repositories
        self.handler.application_repo = Mock()
        self.handler.opportunity_repo = Mock()
        self.handler.user_repo = Mock()

        # Sample data
        self.sample_user = User(
            user_id="user123",
            employee_id="EMP123",
            email="test@example.com",
            name="Test User",
            department="Engineering",
            role="veteran",
        )

        self.sample_opportunity = Opportunity(
            opportunity_id="opp123",
            title="Senior Developer",
            description="Great opportunity",
            company="Test Company",
            type="internal_transfer",
            source="internal",
            is_active=True,
        )

        self.sample_application = Application(
            application_id="app123",
            user_id="user123",
            opportunity_id="opp123",
            application_type="interest",
            status="submitted",
        )

    @patch("src.handlers.application_handler.extract_user_from_event")
    def test_submit_application_success(self, mock_extract_user):
        """Test successful application submission"""
        # Setup
        mock_extract_user.return_value = {"user_id": "user123", "role": "veteran"}
        self.handler.opportunity_repo.get_opportunity.return_value = (
            self.sample_opportunity
        )
        self.handler.application_repo.check_existing_application.return_value = None
        self.handler.application_repo.create_application.return_value = True

        event = {
            "body": json.dumps(
                {
                    "opportunity_id": "opp123",
                    "application_type": "interest",
                    "cover_letter": "I am interested in this position",
                }
            )
        }

        # Execute
        result = self.handler.submit_application(event, None)

        # Assert
        assert result["statusCode"] == 201
        response_body = json.loads(result["body"])
        assert response_body["message"] == "Application submitted successfully"
        assert "application_id" in response_body

        # Verify repository calls
        self.handler.opportunity_repo.get_opportunity.assert_called_once_with("opp123")
        self.handler.application_repo.check_existing_application.assert_called_once_with(
            "user123", "opp123"
        )
        self.handler.application_repo.create_application.assert_called_once()

    @patch("src.handlers.application_handler.extract_user_from_event")
    def test_submit_application_unauthorized(self, mock_extract_user):
        """Test application submission without authentication"""
        # Setup
        mock_extract_user.return_value = None

        event = {"body": json.dumps({"opportunity_id": "opp123"})}

        # Execute
        result = self.handler.submit_application(event, None)

        # Assert
        assert result["statusCode"] == 401
        response_body = json.loads(result["body"])
        assert response_body["error"] == "Unauthorized"

    @patch("src.handlers.application_handler.extract_user_from_event")
    def test_submit_application_missing_opportunity_id(self, mock_extract_user):
        """Test application submission without opportunity_id"""
        # Setup
        mock_extract_user.return_value = {"user_id": "user123", "role": "veteran"}

        event = {"body": json.dumps({})}

        # Execute
        result = self.handler.submit_application(event, None)

        # Assert
        assert result["statusCode"] == 400
        response_body = json.loads(result["body"])
        assert response_body["error"] == "opportunity_id is required"

    @patch("src.handlers.application_handler.extract_user_from_event")
    def test_submit_application_opportunity_not_found(self, mock_extract_user):
        """Test application submission for non-existent opportunity"""
        # Setup
        mock_extract_user.return_value = {"user_id": "user123", "role": "veteran"}
        self.handler.opportunity_repo.get_opportunity.return_value = None

        event = {"body": json.dumps({"opportunity_id": "nonexistent"})}

        # Execute
        result = self.handler.submit_application(event, None)

        # Assert
        assert result["statusCode"] == 404
        response_body = json.loads(result["body"])
        assert response_body["error"] == "Opportunity not found"

    @patch("src.handlers.application_handler.extract_user_from_event")
    def test_submit_application_inactive_opportunity(self, mock_extract_user):
        """Test application submission for inactive opportunity"""
        # Setup
        mock_extract_user.return_value = {"user_id": "user123", "role": "veteran"}
        inactive_opportunity = Opportunity(
            opportunity_id="opp123", title="Inactive Job", is_active=False
        )
        self.handler.opportunity_repo.get_opportunity.return_value = (
            inactive_opportunity
        )

        event = {"body": json.dumps({"opportunity_id": "opp123"})}

        # Execute
        result = self.handler.submit_application(event, None)

        # Assert
        assert result["statusCode"] == 400
        response_body = json.loads(result["body"])
        assert response_body["error"] == "Opportunity is no longer active"

    @patch("src.handlers.application_handler.extract_user_from_event")
    def test_submit_application_duplicate(self, mock_extract_user):
        """Test application submission when user has already applied"""
        # Setup
        mock_extract_user.return_value = {"user_id": "user123", "role": "veteran"}
        self.handler.opportunity_repo.get_opportunity.return_value = (
            self.sample_opportunity
        )
        self.handler.application_repo.check_existing_application.return_value = (
            self.sample_application
        )

        event = {"body": json.dumps({"opportunity_id": "opp123"})}

        # Execute
        result = self.handler.submit_application(event, None)

        # Assert
        assert result["statusCode"] == 409
        response_body = json.loads(result["body"])
        assert response_body["error"] == "You have already applied to this opportunity"
        assert response_body["existing_application_id"] == "app123"

    @patch("src.handlers.application_handler.extract_user_from_event")
    def test_get_user_applications_success(self, mock_extract_user):
        """Test getting user applications successfully"""
        # Setup
        mock_extract_user.return_value = {"user_id": "user123", "role": "veteran"}
        self.handler.application_repo.get_user_applications.return_value = [
            self.sample_application
        ]
        self.handler.opportunity_repo.get_opportunity.return_value = (
            self.sample_opportunity
        )

        event = {"queryStringParameters": {"limit": "10"}}

        # Execute
        result = self.handler.get_user_applications(event, None)

        # Assert
        assert result["statusCode"] == 200
        response_body = json.loads(result["body"])
        assert len(response_body["applications"]) == 1
        assert response_body["total"] == 1
        assert "opportunity" in response_body["applications"][0]

    @patch("src.handlers.application_handler.extract_user_from_event")
    def test_get_user_applications_with_status_filter(self, mock_extract_user):
        """Test getting user applications with status filter"""
        # Setup
        mock_extract_user.return_value = {"user_id": "user123", "role": "veteran"}
        self.handler.application_repo.get_user_applications_by_status.return_value = [
            self.sample_application
        ]
        self.handler.opportunity_repo.get_opportunity.return_value = (
            self.sample_opportunity
        )

        event = {"queryStringParameters": {"status": "submitted", "limit": "10"}}

        # Execute
        result = self.handler.get_user_applications(event, None)

        # Assert
        assert result["statusCode"] == 200
        self.handler.application_repo.get_user_applications_by_status.assert_called_once_with(
            "user123", "submitted", 10
        )

    @patch("src.handlers.application_handler.extract_user_from_event")
    def test_get_application_details_success(self, mock_extract_user):
        """Test getting application details successfully"""
        # Setup
        mock_extract_user.return_value = {"user_id": "user123", "role": "veteran"}
        self.handler.application_repo.get_application.return_value = (
            self.sample_application
        )
        self.handler.opportunity_repo.get_opportunity.return_value = (
            self.sample_opportunity
        )

        event = {"pathParameters": {"application_id": "app123"}}

        # Execute
        result = self.handler.get_application_details(event, None)

        # Assert
        assert result["statusCode"] == 200
        response_body = json.loads(result["body"])
        assert response_body["application_id"] == "app123"
        assert "opportunity" in response_body

    @patch("src.handlers.application_handler.extract_user_from_event")
    def test_get_application_details_not_found(self, mock_extract_user):
        """Test getting details for non-existent application"""
        # Setup
        mock_extract_user.return_value = {"user_id": "user123", "role": "veteran"}
        self.handler.application_repo.get_application.return_value = None

        event = {"pathParameters": {"application_id": "nonexistent"}}

        # Execute
        result = self.handler.get_application_details(event, None)

        # Assert
        assert result["statusCode"] == 404
        response_body = json.loads(result["body"])
        assert response_body["error"] == "Application not found"

    @patch("src.handlers.application_handler.rbac_manager")
    @patch("src.handlers.application_handler.extract_user_from_event")
    def test_get_application_details_access_denied(
        self, mock_extract_user, mock_rbac_manager
    ):
        """Test getting application details with insufficient permissions"""
        # Setup
        mock_extract_user.return_value = {"user_id": "other_user", "role": "veteran"}
        mock_rbac_manager.has_permission.return_value = False
        self.handler.application_repo.get_application.return_value = (
            self.sample_application
        )

        event = {"pathParameters": {"application_id": "app123"}}

        # Execute
        result = self.handler.get_application_details(event, None)

        # Assert
        assert result["statusCode"] == 403
        response_body = json.loads(result["body"])
        assert response_body["error"] == "Access denied"

    @patch("src.handlers.application_handler.extract_user_from_event")
    def test_withdraw_application_success(self, mock_extract_user):
        """Test successful application withdrawal"""
        # Setup
        mock_extract_user.return_value = {"user_id": "user123", "role": "veteran"}
        self.handler.application_repo.withdraw_application.return_value = True
        self.handler.application_repo.get_application.return_value = (
            self.sample_application
        )
        self.handler.opportunity_repo.get_opportunity.return_value = (
            self.sample_opportunity
        )

        event = {"pathParameters": {"application_id": "app123"}}

        # Execute
        result = self.handler.withdraw_application(event, None)

        # Assert
        assert result["statusCode"] == 200
        response_body = json.loads(result["body"])
        assert response_body["message"] == "Application withdrawn successfully"

        self.handler.application_repo.withdraw_application.assert_called_once_with(
            "app123", "user123"
        )

    @patch("src.handlers.application_handler.extract_user_from_event")
    def test_withdraw_application_failure(self, mock_extract_user):
        """Test application withdrawal failure"""
        # Setup
        mock_extract_user.return_value = {"user_id": "user123", "role": "veteran"}
        self.handler.application_repo.withdraw_application.side_effect = ValueError(
            "Cannot withdraw"
        )

        event = {"pathParameters": {"application_id": "app123"}}

        # Execute
        result = self.handler.withdraw_application(event, None)

        # Assert
        assert result["statusCode"] == 400
        response_body = json.loads(result["body"])
        assert response_body["error"] == "Cannot withdraw"

    @patch("src.handlers.application_handler.rbac_manager")
    @patch("src.handlers.application_handler.extract_user_from_event")
    def test_update_application_status_success(
        self, mock_extract_user, mock_rbac_manager
    ):
        """Test successful application status update"""
        # Setup
        mock_extract_user.return_value = {"user_id": "admin123", "role": "admin"}
        mock_rbac_manager.has_permission.return_value = True
        self.handler.application_repo.update_application_status.return_value = True
        self.handler.application_repo.get_application.return_value = (
            self.sample_application
        )
        self.handler.opportunity_repo.get_opportunity.return_value = (
            self.sample_opportunity
        )

        event = {
            "pathParameters": {"application_id": "app123"},
            "body": json.dumps(
                {"status": "under_review", "notes": "Reviewing application"}
            ),
        }

        # Execute
        result = self.handler.update_application_status(event, None)

        # Assert
        assert result["statusCode"] == 200
        response_body = json.loads(result["body"])
        assert response_body["message"] == "Application status updated successfully"
        assert response_body["status"] == "under_review"

        self.handler.application_repo.update_application_status.assert_called_once_with(
            "app123", "under_review", "admin123", "Reviewing application"
        )

    @patch("src.handlers.application_handler.rbac_manager")
    @patch("src.handlers.application_handler.extract_user_from_event")
    def test_update_application_status_insufficient_permissions(
        self, mock_extract_user, mock_rbac_manager
    ):
        """Test application status update with insufficient permissions"""
        # Setup
        mock_extract_user.return_value = {"user_id": "user123", "role": "veteran"}
        mock_rbac_manager.has_permission.return_value = False

        event = {
            "pathParameters": {"application_id": "app123"},
            "body": json.dumps({"status": "under_review"}),
        }

        # Execute
        result = self.handler.update_application_status(event, None)

        # Assert
        assert result["statusCode"] == 403
        response_body = json.loads(result["body"])
        assert response_body["error"] == "Insufficient permissions"

    @patch("src.handlers.application_handler.rbac_manager")
    @patch("src.handlers.application_handler.extract_user_from_event")
    def test_update_application_status_missing_status(
        self, mock_extract_user, mock_rbac_manager
    ):
        """Test application status update without status field"""
        # Setup
        mock_extract_user.return_value = {"user_id": "admin123", "role": "admin"}
        mock_rbac_manager.has_permission.return_value = True

        event = {
            "pathParameters": {"application_id": "app123"},
            "body": json.dumps({"notes": "Some notes"}),
        }

        # Execute
        result = self.handler.update_application_status(event, None)

        # Assert
        assert result["statusCode"] == 400
        response_body = json.loads(result["body"])
        assert response_body["error"] == "status is required"

    @patch("src.handlers.application_handler.rbac_manager")
    @patch("src.handlers.application_handler.extract_user_from_event")
    def test_get_applications_for_opportunity_success(
        self, mock_extract_user, mock_rbac_manager
    ):
        """Test getting applications for opportunity successfully"""
        # Setup
        mock_extract_user.return_value = {"user_id": "admin123", "role": "admin"}
        mock_rbac_manager.has_permission.return_value = True
        self.handler.application_repo.get_applications_for_opportunity.return_value = [
            self.sample_application
        ]
        self.handler.user_repo.get_user.return_value = self.sample_user

        event = {
            "pathParameters": {"opportunity_id": "opp123"},
            "queryStringParameters": {"limit": "10"},
        }

        # Execute
        result = self.handler.get_applications_for_opportunity(event, None)

        # Assert
        assert result["statusCode"] == 200
        response_body = json.loads(result["body"])
        assert len(response_body["applications"]) == 1
        assert response_body["total"] == 1
        assert "applicant" in response_body["applications"][0]

    @patch("src.handlers.application_handler.rbac_manager")
    @patch("src.handlers.application_handler.extract_user_from_event")
    def test_get_applications_for_opportunity_insufficient_permissions(
        self, mock_extract_user, mock_rbac_manager
    ):
        """Test getting applications for opportunity with insufficient permissions"""
        # Setup
        mock_extract_user.return_value = {"user_id": "user123", "role": "veteran"}
        mock_rbac_manager.has_permission.return_value = False

        event = {"pathParameters": {"opportunity_id": "opp123"}}

        # Execute
        result = self.handler.get_applications_for_opportunity(event, None)

        # Assert
        assert result["statusCode"] == 403
        response_body = json.loads(result["body"])
        assert response_body["error"] == "Insufficient permissions"

    def test_notify_stakeholders(self):
        """Test stakeholder notification functionality"""
        # Setup
        self.handler.user_repo.get_user.return_value = self.sample_user

        # Execute (should not raise exception)
        self.handler._notify_stakeholders(
            self.sample_application, self.sample_opportunity, "application_submitted"
        )

        # Assert
        self.handler.user_repo.get_user.assert_called_once_with("user123")

    def test_notify_stakeholders_user_not_found(self):
        """Test stakeholder notification when user not found"""
        # Setup
        self.handler.user_repo.get_user.return_value = None

        # Execute (should not raise exception)
        self.handler._notify_stakeholders(
            self.sample_application, self.sample_opportunity, "application_submitted"
        )

        # Assert
        self.handler.user_repo.get_user.assert_called_once_with("user123")

    # Additional tests for task 7.2 functionality

    @patch("src.handlers.application_handler.extract_user_from_event")
    def test_get_application_history_success(self, mock_extract_user):
        """Test getting application history successfully"""
        # Setup
        mock_extract_user.return_value = {"user_id": "user123", "role": "veteran"}
        self.handler.application_repo.get_application.return_value = (
            self.sample_application
        )

        event = {"pathParameters": {"application_id": "app123"}}

        # Mock the status service
        with patch(
            "src.handlers.application_handler.ApplicationStatusService"
        ) as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.get_application_history.return_value = {
                "success": True,
                "application": self.sample_application.to_dynamodb_item(),
                "history": [
                    {
                        "event_type": "application_submitted",
                        "timestamp": "2024-01-01T00:00:00",
                    }
                ],
            }

            # Execute
            result = self.handler.get_application_history(event, None)

            # Assert
            assert result["statusCode"] == 200
            mock_service.get_application_history.assert_called_once_with("app123")

    @patch("src.handlers.application_handler.extract_user_from_event")
    def test_send_application_message_success(self, mock_extract_user):
        """Test sending application message successfully"""
        # Setup
        mock_extract_user.return_value = {"user_id": "user123", "role": "veteran"}
        self.handler.application_repo.get_application.return_value = (
            self.sample_application
        )
        self.handler.user_repo.get_user.return_value = self.sample_user

        event = {
            "pathParameters": {"application_id": "app123"},
            "body": json.dumps(
                {
                    "message": "I have a question about this position",
                    "message_type": "general",
                }
            ),
        }

        # Mock the status service
        with patch(
            "src.handlers.application_handler.ApplicationStatusService"
        ) as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.send_communication_message.return_value = {
                "success": True,
                "message_id": "msg123",
                "sent_at": "2024-01-01T00:00:00",
            }

            # Execute
            result = self.handler.send_application_message(event, None)

            # Assert
            assert result["statusCode"] == 201
            response_body = json.loads(result["body"])
            assert response_body["message"] == "Message sent successfully"
            assert "message_id" in response_body

    @patch("src.handlers.application_handler.extract_user_from_event")
    def test_send_application_message_empty_message(self, mock_extract_user):
        """Test sending empty application message"""
        # Setup
        mock_extract_user.return_value = {"user_id": "user123", "role": "veteran"}

        event = {
            "pathParameters": {"application_id": "app123"},
            "body": json.dumps({"message": "", "message_type": "general"}),
        }

        # Execute
        result = self.handler.send_application_message(event, None)

        # Assert
        assert result["statusCode"] == 400
        response_body = json.loads(result["body"])
        assert response_body["error"] == "message is required"

    @patch("src.handlers.application_handler.extract_user_from_event")
    def test_get_application_communications_success(self, mock_extract_user):
        """Test getting application communications successfully"""
        # Setup
        mock_extract_user.return_value = {"user_id": "user123", "role": "veteran"}

        event = {"pathParameters": {"application_id": "app123"}}

        # Mock the status service
        with patch(
            "src.handlers.application_handler.ApplicationStatusService"
        ) as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.get_application_communications.return_value = {
                "success": True,
                "communications": [
                    {
                        "message_id": "msg1",
                        "sender_name": "System",
                        "message": "Application submitted",
                        "timestamp": "2024-01-01T00:00:00",
                    }
                ],
                "total": 1,
            }

            # Execute
            result = self.handler.get_application_communications(event, None)

            # Assert
            assert result["statusCode"] == 200
            mock_service.get_application_communications.assert_called_once_with(
                "app123", "user123"
            )

    @patch("src.handlers.application_handler.rbac_manager")
    @patch("src.handlers.application_handler.extract_user_from_event")
    def test_update_application_status_with_workflow_success(
        self, mock_extract_user, mock_rbac_manager
    ):
        """Test updating application status with workflow validation"""
        # Setup
        mock_extract_user.return_value = {"user_id": "admin123", "role": "admin"}
        mock_rbac_manager.has_permission.return_value = True

        event = {
            "pathParameters": {"application_id": "app123"},
            "body": json.dumps(
                {"status": "under_review", "notes": "Starting review process"}
            ),
        }

        # Mock the status service
        with patch(
            "src.handlers.application_handler.ApplicationStatusService"
        ) as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.update_status_with_workflow.return_value = {
                "success": True,
                "old_status": "submitted",
                "new_status": "under_review",
                "updated_by": "admin123",
                "timestamp": "2024-01-01T00:00:00",
            }

            # Execute
            result = self.handler.update_application_status_with_workflow(event, None)

            # Assert
            assert result["statusCode"] == 200
            response_body = json.loads(result["body"])
            assert response_body["message"] == "Application status updated successfully"
            assert response_body["old_status"] == "submitted"
            assert response_body["new_status"] == "under_review"

    @patch("src.handlers.application_handler.rbac_manager")
    @patch("src.handlers.application_handler.extract_user_from_event")
    def test_update_application_status_with_workflow_invalid_transition(
        self, mock_extract_user, mock_rbac_manager
    ):
        """Test updating application status with invalid workflow transition"""
        # Setup
        mock_extract_user.return_value = {"user_id": "admin123", "role": "admin"}
        mock_rbac_manager.has_permission.return_value = True

        event = {
            "pathParameters": {"application_id": "app123"},
            "body": json.dumps(
                {"status": "accepted", "notes": "Trying to skip review"}
            ),
        }

        # Mock the status service
        with patch(
            "src.handlers.application_handler.ApplicationStatusService"
        ) as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.update_status_with_workflow.return_value = {
                "success": False,
                "error": "Invalid status transition from submitted to accepted",
            }

            # Execute
            result = self.handler.update_application_status_with_workflow(event, None)

            # Assert
            assert result["statusCode"] == 400
            response_body = json.loads(result["body"])
            assert "Invalid status transition" in response_body["error"]


if __name__ == "__main__":
    pytest.main([__file__])
