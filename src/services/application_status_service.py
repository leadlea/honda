"""
Application Status Management Service
Handles status updates, communication mediation, and application history
"""
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict

from ..models.application import Application
from ..repositories.application_repository import ApplicationRepository
from ..repositories.opportunity_repository import OpportunityRepository
from ..repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


@dataclass
class StatusUpdate:
    """Represents an application status update"""

    application_id: str
    old_status: str
    new_status: str
    updated_by: str
    notes: str = ""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class CommunicationMessage:
    """Represents a communication message between parties"""

    message_id: str
    application_id: str
    sender_id: str
    recipient_id: str
    message: str
    message_type: str = (
        "general"  # 'general', 'status_update', 'interview_request', 'feedback'
    )
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    is_read: bool = False


class ApplicationStatusService:
    """Service for managing application status and communication"""

    def __init__(self):
        self.application_repo = ApplicationRepository()
        self.user_repo = UserRepository()
        self.opportunity_repo = OpportunityRepository()

    def update_status_with_workflow(
        self, application_id: str, new_status: str, updated_by: str, notes: str = ""
    ) -> Dict[str, Any]:
        """
        Update application status with workflow validation
        Requirements: 3.3, 3.4
        """
        try:
            # Get current application
            application = self.application_repo.get_application(application_id)
            if not application:
                return {"success": False, "error": "Application not found"}

            old_status = application.status

            # Validate status transition
            if not self._is_valid_status_transition(old_status, new_status):
                return {
                    "success": False,
                    "error": f"Invalid status transition from {old_status} to {new_status}",
                }

            # Update application status
            success = self.application_repo.update_application_status(
                application_id, new_status, updated_by, notes
            )

            if not success:
                return {"success": False, "error": "Failed to update status"}

            # Create status update record
            status_update = StatusUpdate(
                application_id=application_id,
                old_status=old_status,
                new_status=new_status,
                updated_by=updated_by,
                notes=notes,
            )

            # Log status change
            self._log_status_change(status_update)

            # Send notifications
            self._notify_status_change(
                application, old_status, new_status, updated_by, notes
            )

            return {
                "success": True,
                "old_status": old_status,
                "new_status": new_status,
                "updated_by": updated_by,
                "timestamp": status_update.timestamp,
            }

        except Exception as e:
            logger.error(f"Error updating application status: {e}")
            return {"success": False, "error": "Internal server error"}

    def get_application_history(self, application_id: str) -> Dict[str, Any]:
        """
        Get complete history of an application including status changes
        Requirements: 3.3
        """
        try:
            application = self.application_repo.get_application(application_id)
            if not application:
                return {"success": False, "error": "Application not found"}

            # Get opportunity details
            opportunity = self.opportunity_repo.get_opportunity(
                application.opportunity_id
            )

            # Get applicant details
            applicant = self.user_repo.get_user(application.user_id)

            # Build history timeline
            history = []

            # Initial submission
            history.append(
                {
                    "event_type": "application_submitted",
                    "timestamp": application.submitted_at,
                    "status": "submitted",
                    "description": f'Application submitted for {opportunity.title if opportunity else "Unknown Position"}',
                    "actor": applicant.name if applicant else "Unknown User",
                }
            )

            # Status updates (in a real implementation, these would be stored separately)
            if application.reviewed_at:
                history.append(
                    {
                        "event_type": "status_updated",
                        "timestamp": application.reviewed_at,
                        "status": application.status,
                        "description": f"Status updated to {application.status}",
                        "actor": "Reviewer",
                        "notes": application.reviewer_notes,
                    }
                )

            # Sort by timestamp
            history.sort(key=lambda x: x["timestamp"])

            return {
                "success": True,
                "application": application.to_dynamodb_item(),
                "opportunity": opportunity.to_dynamodb_item() if opportunity else None,
                "applicant": {
                    "name": applicant.name,
                    "email": applicant.email,
                    "department": applicant.department,
                }
                if applicant
                else None,
                "history": history,
            }

        except Exception as e:
            logger.error(f"Error getting application history: {e}")
            return {"success": False, "error": "Internal server error"}

    def send_communication_message(
        self,
        application_id: str,
        sender_id: str,
        message: str,
        message_type: str = "general",
    ) -> Dict[str, Any]:
        """
        Send a communication message between applicant and recruiter
        Requirements: 3.3, 3.4
        """
        try:
            # Get application to determine participants
            application = self.application_repo.get_application(application_id)
            if not application:
                return {"success": False, "error": "Application not found"}

            # Determine recipient
            if sender_id == application.user_id:
                # Applicant sending to recruiter/admin
                recipient_id = application.reviewer_id or "admin"
            else:
                # Recruiter/admin sending to applicant
                recipient_id = application.user_id

            # Create message (in a real implementation, this would be stored in a separate table)
            message_data = {
                "application_id": application_id,
                "sender_id": sender_id,
                "recipient_id": recipient_id,
                "message": message,
                "message_type": message_type,
                "timestamp": datetime.utcnow().isoformat(),
                "is_read": False,
            }

            # Log communication
            logger.info(f"Communication message: {json.dumps(message_data)}")

            # Send notification to recipient
            self._notify_new_message(
                application, sender_id, recipient_id, message, message_type
            )

            return {
                "success": True,
                "message_id": f"msg_{application_id}_{datetime.utcnow().timestamp()}",
                "sent_at": message_data["timestamp"],
            }

        except Exception as e:
            logger.error(f"Error sending communication message: {e}")
            return {"success": False, "error": "Internal server error"}

    def get_application_communications(
        self, application_id: str, user_id: str
    ) -> Dict[str, Any]:
        """
        Get all communications for an application (filtered by user permissions)
        Requirements: 3.3
        """
        try:
            # Get application to verify access
            application = self.application_repo.get_application(application_id)
            if not application:
                return {"success": False, "error": "Application not found"}

            # Check if user has access to this application's communications
            user = self.user_repo.get_user(user_id)
            if not user:
                return {"success": False, "error": "User not found"}

            # Verify access (applicant, reviewer, or admin)
            has_access = (
                user_id == application.user_id
                or user_id == application.reviewer_id  # Applicant
                or user.role == "admin"  # Reviewer  # Admin
            )

            if not has_access:
                return {"success": False, "error": "Access denied"}

            # In a real implementation, this would query a communications table
            # For now, return a placeholder structure
            communications = [
                {
                    "message_id": f"msg_{application_id}_1",
                    "sender_name": "System",
                    "message": "Application submitted successfully",
                    "message_type": "status_update",
                    "timestamp": application.submitted_at,
                    "is_read": True,
                }
            ]

            if application.reviewer_notes:
                communications.append(
                    {
                        "message_id": f"msg_{application_id}_2",
                        "sender_name": "Reviewer",
                        "message": application.reviewer_notes,
                        "message_type": "feedback",
                        "timestamp": application.reviewed_at or application.updated_at,
                        "is_read": False,
                    }
                )

            return {
                "success": True,
                "communications": communications,
                "total": len(communications),
            }

        except Exception as e:
            logger.error(f"Error getting application communications: {e}")
            return {"success": False, "error": "Internal server error"}

    def _is_valid_status_transition(self, old_status: str, new_status: str) -> bool:
        """
        Validate if a status transition is allowed
        """
        # Define valid status transitions
        valid_transitions = {
            "submitted": ["under_review", "rejected", "withdrawn"],
            "under_review": ["interview_scheduled", "accepted", "rejected"],
            "interview_scheduled": ["accepted", "rejected", "under_review"],
            "accepted": [],  # Final state
            "rejected": [],  # Final state
            "withdrawn": [],  # Final state
        }

        return new_status in valid_transitions.get(old_status, [])

    def _log_status_change(self, status_update: StatusUpdate) -> None:
        """
        Log status change for audit purposes
        """
        log_data = {
            "event_type": "application_status_change",
            "application_id": status_update.application_id,
            "old_status": status_update.old_status,
            "new_status": status_update.new_status,
            "updated_by": status_update.updated_by,
            "notes": status_update.notes,
            "timestamp": status_update.timestamp,
        }

        logger.info(f"Status change: {json.dumps(log_data)}")

    def _notify_status_change(
        self,
        application: Application,
        old_status: str,
        new_status: str,
        updated_by: str,
        notes: str,
    ) -> None:
        """
        Send notifications for status changes
        Requirements: 3.4
        """
        try:
            # Get applicant details
            applicant = self.user_repo.get_user(application.user_id)

            # Get opportunity details
            opportunity = self.opportunity_repo.get_opportunity(
                application.opportunity_id
            )

            notification_data = {
                "event_type": "application_status_updated",
                "application_id": application.application_id,
                "applicant": {
                    "name": applicant.name if applicant else "Unknown",
                    "email": applicant.email if applicant else "unknown@example.com",
                },
                "opportunity": {
                    "title": opportunity.title if opportunity else "Unknown Position",
                    "company": opportunity.company
                    if opportunity
                    else "Unknown Company",
                },
                "status_change": {
                    "old_status": old_status,
                    "new_status": new_status,
                    "updated_by": updated_by,
                    "notes": notes,
                },
                "timestamp": datetime.utcnow().isoformat(),
            }

            # Log notification (in a real implementation, send email/SMS/push notification)
            logger.info(f"Status change notification: {json.dumps(notification_data)}")

        except Exception as e:
            logger.error(f"Error sending status change notification: {e}")

    def _notify_new_message(
        self,
        application: Application,
        sender_id: str,
        recipient_id: str,
        message: str,
        message_type: str,
    ) -> None:
        """
        Send notification for new communication message
        Requirements: 3.4
        """
        try:
            # Get sender and recipient details
            sender = self.user_repo.get_user(sender_id)
            recipient = self.user_repo.get_user(recipient_id)

            # Get opportunity details
            opportunity = self.opportunity_repo.get_opportunity(
                application.opportunity_id
            )

            notification_data = {
                "event_type": "new_application_message",
                "application_id": application.application_id,
                "sender": {
                    "name": sender.name if sender else "Unknown",
                    "email": sender.email if sender else "unknown@example.com",
                },
                "recipient": {
                    "name": recipient.name if recipient else "Unknown",
                    "email": recipient.email if recipient else "unknown@example.com",
                },
                "opportunity": {
                    "title": opportunity.title if opportunity else "Unknown Position"
                },
                "message": {"content": message, "type": message_type},
                "timestamp": datetime.utcnow().isoformat(),
            }

            # Log notification (in a real implementation, send email/SMS/push notification)
            logger.info(f"New message notification: {json.dumps(notification_data)}")

        except Exception as e:
            logger.error(f"Error sending new message notification: {e}")
