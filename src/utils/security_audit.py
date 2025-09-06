"""
Security audit logging system for compliance and monitoring.
"""

import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

import boto3

logger = logging.getLogger()

# Initialize CloudWatch Logs client for centralized logging
try:
    cloudwatch_logs = boto3.client("logs")
except Exception:
    cloudwatch_logs = None
    logger.warning("CloudWatch Logs client not available")


class SecurityEventType(Enum):
    """Types of security events to audit."""

    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    PASSWORD_CHANGE = "password_change"
    PROFILE_ACCESS = "profile_access"
    PROFILE_UPDATE = "profile_update"
    PERMISSION_DENIED = "permission_denied"
    ROLE_CHANGE = "role_change"
    DATA_EXPORT = "data_export"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    ADMIN_ACTION = "admin_action"
    EXTERNAL_ACCESS = "external_access"


class RiskLevel(Enum):
    """Risk levels for security events."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SecurityEvent:
    """Security event data structure."""

    event_type: str
    user_id: str
    timestamp: str
    risk_level: str
    source_ip: Optional[str] = None
    user_agent: Optional[str] = None
    resource: Optional[str] = None
    action: Optional[str] = None
    result: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return asdict(self)


class SecurityAuditor:
    """Security audit logging manager."""

    def __init__(self):
        self.log_group_name = f"/aws/lambda/{os.environ.get('AWS_LAMBDA_FUNCTION_NAME', 'security-audit')}"
        self.log_stream_name = f"security-audit-{datetime.now().strftime('%Y-%m-%d')}"

    def log_event(self, event: SecurityEvent) -> bool:
        """
        Log a security event.

        Args:
            event: SecurityEvent to log

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Log to CloudWatch Logs (structured logging)
            log_entry = {
                "timestamp": event.timestamp,
                "level": "SECURITY_AUDIT",
                "event": event.to_dict(),
            }

            # Log locally (will go to CloudWatch Logs via Lambda)
            logger.info(f"SECURITY_AUDIT: {json.dumps(log_entry)}")

            # Optionally send to dedicated security log stream
            if cloudwatch_logs:
                self._send_to_cloudwatch(log_entry)

            # For high/critical risk events, send alerts
            if event.risk_level in [RiskLevel.HIGH.value, RiskLevel.CRITICAL.value]:
                self._send_security_alert(event)

            return True

        except Exception as e:
            logger.error(f"Failed to log security event: {str(e)}")
            return False

    def _send_to_cloudwatch(self, log_entry: Dict[str, Any]) -> None:
        """Send log entry to dedicated CloudWatch log stream."""
        try:
            # Create log group if it doesn't exist
            try:
                cloudwatch_logs.create_log_group(logGroupName=self.log_group_name)
            except cloudwatch_logs.exceptions.ResourceAlreadyExistsException:
                pass

            # Create log stream if it doesn't exist
            try:
                cloudwatch_logs.create_log_stream(
                    logGroupName=self.log_group_name, logStreamName=self.log_stream_name
                )
            except cloudwatch_logs.exceptions.ResourceAlreadyExistsException:
                pass

            # Send log event
            cloudwatch_logs.put_log_events(
                logGroupName=self.log_group_name,
                logStreamName=self.log_stream_name,
                logEvents=[
                    {
                        "timestamp": int(datetime.now().timestamp() * 1000),
                        "message": json.dumps(log_entry),
                    }
                ],
            )

        except Exception as e:
            logger.error(f"Failed to send to CloudWatch: {str(e)}")

    def _send_security_alert(self, event: SecurityEvent) -> None:
        """Send security alert for high-risk events."""
        try:
            # In a production system, this would integrate with:
            # - SNS for email/SMS alerts
            # - Slack/Teams for team notifications
            # - Security Information and Event Management (SIEM) systems

            alert_message = {
                "alert_type": "SECURITY_EVENT",
                "risk_level": event.risk_level,
                "event_type": event.event_type,
                "user_id": event.user_id,
                "timestamp": event.timestamp,
                "details": event.details or {},
            }

            logger.warning(f"SECURITY_ALERT: {json.dumps(alert_message)}")

        except Exception as e:
            logger.error(f"Failed to send security alert: {str(e)}")

    def log_login_attempt(
        self,
        user_id: str,
        success: bool,
        source_ip: str = None,
        user_agent: str = None,
        failure_reason: str = None,
    ) -> None:
        """Log user login attempt."""
        event_type = (
            SecurityEventType.LOGIN_SUCCESS
            if success
            else SecurityEventType.LOGIN_FAILURE
        )
        risk_level = RiskLevel.LOW if success else RiskLevel.MEDIUM

        details = {}
        if not success and failure_reason:
            details["failure_reason"] = failure_reason

        event = SecurityEvent(
            event_type=event_type.value,
            user_id=user_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            risk_level=risk_level.value,
            source_ip=source_ip,
            user_agent=user_agent,
            action="login",
            result="success" if success else "failure",
            details=details,
        )

        self.log_event(event)

    def log_logout(self, user_id: str, source_ip: str = None) -> None:
        """Log user logout."""
        event = SecurityEvent(
            event_type=SecurityEventType.LOGOUT.value,
            user_id=user_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            risk_level=RiskLevel.LOW.value,
            source_ip=source_ip,
            action="logout",
            result="success",
        )

        self.log_event(event)

    def log_profile_access(
        self,
        user_id: str,
        accessed_profile_id: str,
        action: str,
        success: bool = True,
        source_ip: str = None,
    ) -> None:
        """Log profile access attempt."""
        risk_level = RiskLevel.LOW

        # Higher risk if accessing someone else's profile
        if user_id != accessed_profile_id:
            risk_level = RiskLevel.MEDIUM

        event = SecurityEvent(
            event_type=SecurityEventType.PROFILE_ACCESS.value,
            user_id=user_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            risk_level=risk_level.value,
            source_ip=source_ip,
            resource=f"profile:{accessed_profile_id}",
            action=action,
            result="success" if success else "failure",
            details={"accessed_profile_id": accessed_profile_id},
        )

        self.log_event(event)

    def log_permission_denied(
        self,
        user_id: str,
        user_role: str,
        attempted_action: str,
        resource: str = None,
        source_ip: str = None,
    ) -> None:
        """Log permission denied event."""
        event = SecurityEvent(
            event_type=SecurityEventType.PERMISSION_DENIED.value,
            user_id=user_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            risk_level=RiskLevel.MEDIUM.value,
            source_ip=source_ip,
            resource=resource,
            action=attempted_action,
            result="denied",
            details={"user_role": user_role, "attempted_action": attempted_action},
        )

        self.log_event(event)

    def log_role_change(
        self,
        admin_user_id: str,
        target_user_id: str,
        old_role: str,
        new_role: str,
        source_ip: str = None,
    ) -> None:
        """Log user role change."""
        event = SecurityEvent(
            event_type=SecurityEventType.ROLE_CHANGE.value,
            user_id=admin_user_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            risk_level=RiskLevel.HIGH.value,
            source_ip=source_ip,
            resource=f"user:{target_user_id}",
            action="role_change",
            result="success",
            details={
                "target_user_id": target_user_id,
                "old_role": old_role,
                "new_role": new_role,
            },
        )

        self.log_event(event)

    def log_admin_action(
        self,
        admin_user_id: str,
        action: str,
        target_resource: str = None,
        details: Dict[str, Any] = None,
        source_ip: str = None,
    ) -> None:
        """Log administrative action."""
        event = SecurityEvent(
            event_type=SecurityEventType.ADMIN_ACTION.value,
            user_id=admin_user_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            risk_level=RiskLevel.HIGH.value,
            source_ip=source_ip,
            resource=target_resource,
            action=action,
            result="success",
            details=details or {},
        )

        self.log_event(event)

    def log_external_access(
        self,
        external_user_id: str,
        action: str,
        resource: str = None,
        source_ip: str = None,
        user_agent: str = None,
    ) -> None:
        """Log external recruiter access."""
        event = SecurityEvent(
            event_type=SecurityEventType.EXTERNAL_ACCESS.value,
            user_id=external_user_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            risk_level=RiskLevel.MEDIUM.value,
            source_ip=source_ip,
            user_agent=user_agent,
            resource=resource,
            action=action,
            result="success",
            details={"user_type": "external_recruiter"},
        )

        self.log_event(event)

    def log_suspicious_activity(
        self,
        user_id: str,
        activity_type: str,
        details: Dict[str, Any],
        source_ip: str = None,
    ) -> None:
        """Log suspicious activity."""
        event = SecurityEvent(
            event_type=SecurityEventType.SUSPICIOUS_ACTIVITY.value,
            user_id=user_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            risk_level=RiskLevel.CRITICAL.value,
            source_ip=source_ip,
            action=activity_type,
            result="detected",
            details=details,
        )

        self.log_event(event)

    def get_user_activity_summary(
        self, user_id: str, start_date: datetime = None, end_date: datetime = None
    ) -> Dict[str, Any]:
        """
        Get activity summary for a user (for compliance reporting).

        Args:
            user_id: User ID to get summary for
            start_date: Start date for summary
            end_date: End date for summary

        Returns:
            Dictionary with activity summary
        """
        # In a production system, this would query the audit logs
        # from CloudWatch Logs or a dedicated audit database

        summary = {
            "user_id": user_id,
            "period": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None,
            },
            "total_events": 0,
            "event_types": {},
            "risk_levels": {},
            "last_login": None,
            "failed_logins": 0,
            "profile_accesses": 0,
        }

        # This would be implemented with actual log querying
        logger.info(f"Activity summary requested for user: {user_id}")

        return summary


# Global security auditor instance
security_auditor = SecurityAuditor()


def audit_security_event(
    event_type: SecurityEventType,
    user_id: str,
    risk_level: RiskLevel = RiskLevel.LOW,
    **kwargs,
) -> None:
    """
    Convenience function to log security events.

    Args:
        event_type: Type of security event
        user_id: User ID associated with event
        risk_level: Risk level of the event
        **kwargs: Additional event details
    """
    event = SecurityEvent(
        event_type=event_type.value,
        user_id=user_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        risk_level=risk_level.value,
        **kwargs,
    )

    security_auditor.log_event(event)


def extract_request_info(event: Dict[str, Any]) -> Dict[str, str]:
    """
    Extract request information from Lambda event for audit logging.

    Args:
        event: Lambda event dictionary

    Returns:
        Dictionary with request information
    """
    headers = event.get("headers", {})
    request_context = event.get("requestContext", {})

    return {
        "source_ip": (
            headers.get("X-Forwarded-For", "").split(",")[0].strip()
            or request_context.get("identity", {}).get("sourceIp")
        ),
        "user_agent": headers.get("User-Agent"),
        "request_id": request_context.get("requestId"),
        "api_id": request_context.get("apiId"),
    }
