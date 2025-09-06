"""
Unit tests for application status service
"""
from unittest.mock import Mock, patch

import pytest

from src.models.application import Application
from src.models.opportunity import Opportunity
from src.models.user import User
from src.services.application_status_service import (
    ApplicationStatusService,
    StatusUpdate,
)


class TestApplicationStatusService:
    """Test cases for ApplicationStatusService"""

    def setup_method(self):
        """Set up test fixtures"""
        self.service = ApplicationStatusService()

        # Mock repositories
        self.service.application_repo = Mock()
        self.service.user_repo = Mock()
        self.service.opportunity_repo = Mock()

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

    def test_update_status_with_workflow_success(self):
        """Test successful status update with workflow validation"""
        # Setup
        self.service.application_repo.get_application.return_value = (
            self.sample_application
        )
        self.service.application_repo.update_application_status.return_value = True

        # Execute
        result = self.service.update_status_with_workflow(
            "app123", "under_review", "admin123", "Reviewing application"
        )

        # Assert
        assert result["success"] is True
        assert result["old_status"] == "submitted"
        assert result["new_status"] == "under_review"
        assert result["updated_by"] == "admin123"

        # Verify repository calls
        self.service.application_repo.get_application.assert_called_once_with("app123")
        self.service.application_repo.update_application_status.assert_called_once_with(
            "app123", "under_review", "admin123", "Reviewing application"
        )

    def test_update_status_with_workflow_invalid_transition(self):
        """Test status update with invalid transition"""
        # Setup - try to go from submitted directly to accepted (should go through under_review)
        self.service.application_repo.get_application.return_value = (
            self.sample_application
        )

        # Execute
        result = self.service.update_status_with_workflow(
            "app123", "accepted", "admin123", "Accepting application"
        )

        # Assert
        assert result["success"] is False
        assert "Invalid status transition" in result["error"]

        # Verify no update was attempted
        self.service.application_repo.update_application_status.assert_not_called()

    def test_update_status_with_workflow_application_not_found(self):
        """Test status update for non-existent application"""
        # Setup
        self.service.application_repo.get_application.return_value = None

        # Execute
        result = self.service.update_status_with_workflow(
            "nonexistent", "under_review", "admin123", "Notes"
        )

        # Assert
        assert result["success"] is False
        assert result["error"] == "Application not found"

    def test_get_application_history_success(self):
        """Test getting application history successfully"""
        # Setup
        self.service.application_repo.get_application.return_value = (
            self.sample_application
        )
        self.service.opportunity_repo.get_opportunity.return_value = (
            self.sample_opportunity
        )
        self.service.user_repo.get_user.return_value = self.sample_user

        # Execute
        result = self.service.get_application_history("app123")

        # Assert
        assert result["success"] is True
        assert "application" in result
        assert "opportunity" in result
        assert "applicant" in result
        assert "history" in result
        assert len(result["history"]) >= 1  # At least the submission event

        # Verify the submission event is included
        submission_event = next(
            (
                event
                for event in result["history"]
                if event["event_type"] == "application_submitted"
            ),
            None,
        )
        assert submission_event is not None
        assert submission_event["status"] == "submitted"

    def test_get_application_history_not_found(self):
        """Test getting history for non-existent application"""
        # Setup
        self.service.application_repo.get_application.return_value = None

        # Execute
        result = self.service.get_application_history("nonexistent")

        # Assert
        assert result["success"] is False
        assert result["error"] == "Application not found"

    def test_send_communication_message_success(self):
        """Test sending communication message successfully"""
        # Setup
        self.service.application_repo.get_application.return_value = (
            self.sample_application
        )

        # Execute
        result = self.service.send_communication_message(
            "app123",
            "user123",
            "Hello, I have a question about this position",
            "general",
        )

        # Assert
        assert result["success"] is True
        assert "message_id" in result
        assert "sent_at" in result

    def test_send_communication_message_application_not_found(self):
        """Test sending message for non-existent application"""
        # Setup
        self.service.application_repo.get_application.return_value = None

        # Execute
        result = self.service.send_communication_message(
            "nonexistent", "user123", "Hello", "general"
        )

        # Assert
        assert result["success"] is False
        assert result["error"] == "Application not found"

    def test_get_application_communications_success(self):
        """Test getting application communications successfully"""
        # Setup
        self.service.application_repo.get_application.return_value = (
            self.sample_application
        )
        self.service.user_repo.get_user.return_value = self.sample_user

        # Execute
        result = self.service.get_application_communications("app123", "user123")

        # Assert
        assert result["success"] is True
        assert "communications" in result
        assert "total" in result
        assert isinstance(result["communications"], list)

    def test_get_application_communications_access_denied(self):
        """Test getting communications with insufficient access"""
        # Setup
        self.service.application_repo.get_application.return_value = (
            self.sample_application
        )
        other_user = User(
            user_id="other123",
            employee_id="EMP456",
            email="other@example.com",
            name="Other User",
            department="Marketing",
            role="veteran",
        )
        self.service.user_repo.get_user.return_value = other_user

        # Execute
        result = self.service.get_application_communications("app123", "other123")

        # Assert
        assert result["success"] is False
        assert result["error"] == "Access denied"

    def test_get_application_communications_admin_access(self):
        """Test getting communications with admin access"""
        # Setup
        self.service.application_repo.get_application.return_value = (
            self.sample_application
        )
        admin_user = User(
            user_id="admin123",
            employee_id="ADMIN123",
            email="admin@example.com",
            name="Admin User",
            department="IT",
            role="admin",
        )
        self.service.user_repo.get_user.return_value = admin_user

        # Execute
        result = self.service.get_application_communications("app123", "admin123")

        # Assert
        assert result["success"] is True
        assert "communications" in result

    def test_is_valid_status_transition(self):
        """Test status transition validation"""
        # Valid transitions
        assert (
            self.service._is_valid_status_transition("submitted", "under_review")
            is True
        )
        assert self.service._is_valid_status_transition("submitted", "rejected") is True
        assert (
            self.service._is_valid_status_transition("under_review", "accepted") is True
        )
        assert (
            self.service._is_valid_status_transition(
                "under_review", "interview_scheduled"
            )
            is True
        )

        # Invalid transitions
        assert (
            self.service._is_valid_status_transition("submitted", "accepted") is False
        )
        assert (
            self.service._is_valid_status_transition("accepted", "under_review")
            is False
        )
        assert self.service._is_valid_status_transition("rejected", "accepted") is False
        assert (
            self.service._is_valid_status_transition("withdrawn", "under_review")
            is False
        )

    @patch("src.services.application_status_service.logger")
    def test_log_status_change(self, mock_logger):
        """Test status change logging"""
        # Setup
        status_update = StatusUpdate(
            application_id="app123",
            old_status="submitted",
            new_status="under_review",
            updated_by="admin123",
            notes="Reviewing application",
        )

        # Execute
        self.service._log_status_change(status_update)

        # Assert
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert "Status change:" in call_args
        assert "app123" in call_args

    @patch("src.services.application_status_service.logger")
    def test_notify_status_change(self, mock_logger):
        """Test status change notification"""
        # Setup
        self.service.user_repo.get_user.return_value = self.sample_user
        self.service.opportunity_repo.get_opportunity.return_value = (
            self.sample_opportunity
        )

        # Execute
        self.service._notify_status_change(
            self.sample_application,
            "submitted",
            "under_review",
            "admin123",
            "Reviewing",
        )

        # Assert
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert "Status change notification:" in call_args

    @patch("src.services.application_status_service.logger")
    def test_notify_new_message(self, mock_logger):
        """Test new message notification"""
        # Setup
        self.service.user_repo.get_user.return_value = self.sample_user
        self.service.opportunity_repo.get_opportunity.return_value = (
            self.sample_opportunity
        )

        # Execute
        self.service._notify_new_message(
            self.sample_application, "user123", "admin123", "Hello", "general"
        )

        # Assert
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert "New message notification:" in call_args


if __name__ == "__main__":
    pytest.main([__file__])
