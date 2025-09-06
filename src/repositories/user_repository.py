"""
User repository for DynamoDB operations.
"""

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from botocore.exceptions import ClientError

from ..models.user import SecurityAuditLog, User
from .base_repository import BaseRepository

logger = logging.getLogger(__name__)


class UserRepository(BaseRepository):
    """Repository for user data operations."""

    def __init__(self):
        table_name = f"{os.environ.get('DYNAMODB_TABLE_PREFIX', 'honda-veteran-talent-matching-dev')}-users"
        super().__init__(table_name)

    def create_user(self, user: User) -> bool:
        """
        Create a new user in DynamoDB.

        Args:
            user: User object to create

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Check if user already exists
            if self.get_user_by_id(user.user_id):
                logger.warning(f"User already exists: {user.user_id}")
                return False

            # Check if email already exists
            if self.get_user_by_email(user.email):
                logger.warning(f"Email already exists: {user.email}")
                return False

            # Create user
            item = user.to_dynamodb_item()
            self.put_item(item)

            logger.info(f"User created successfully: {user.user_id}")
            return True

        except ClientError as e:
            logger.error(f"Error creating user: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error creating user: {str(e)}")
            return False

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """
        Get user by user ID.

        Args:
            user_id: User ID to search for

        Returns:
            User object if found, None otherwise
        """
        try:
            item = self.get_item({"user_id": user_id})

            if item:
                return User.from_dynamodb_item(item)

            return None

        except ClientError as e:
            logger.error(f"Error getting user by ID: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting user by ID: {str(e)}")
            return None

    def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email address.

        Args:
            email: Email address to search for

        Returns:
            User object if found, None otherwise
        """
        try:
            items = self.query(
                key_condition_expression="email = :email",
                expression_attribute_values={":email": email},
                index_name="EmailIndex",
            )

            if items:
                return User.from_dynamodb_item(items[0])

            return None

        except ClientError as e:
            logger.error(f"Error getting user by email: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting user by email: {str(e)}")
            return None

    def update_user(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update user information.

        Args:
            user_id: User ID to update
            updates: Dictionary of fields to update

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Build update expression
            update_expression = "SET updated_at = :updated_at"
            expression_values = {":updated_at": datetime.now(timezone.utc).isoformat()}

            # Add fields to update
            for field, value in updates.items():
                if field not in [
                    "user_id",
                    "created_at",
                ]:  # Don't allow updating these fields
                    update_expression += f", {field} = :{field}"
                    expression_values[f":{field}"] = value

            # Update user
            self.update_item(
                key={"user_id": user_id},
                update_expression=update_expression,
                expression_attribute_values=expression_values,
            )

            logger.info(f"User updated successfully: {user_id}")
            return True

        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                logger.warning(f"User not found for update: {user_id}")
            else:
                logger.error(f"Error updating user: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error updating user: {str(e)}")
            return False

    def deactivate_user(self, user_id: str) -> bool:
        """
        Deactivate a user (soft delete).

        Args:
            user_id: User ID to deactivate

        Returns:
            bool: True if successful, False otherwise
        """
        return self.update_user(user_id, {"is_active": False})

    def activate_user(self, user_id: str) -> bool:
        """
        Activate a user.

        Args:
            user_id: User ID to activate

        Returns:
            bool: True if successful, False otherwise
        """
        return self.update_user(user_id, {"is_active": True})

    def list_users_by_role(self, role: str, active_only: bool = True) -> List[User]:
        """
        List users by role.

        Args:
            role: Role to filter by
            active_only: Whether to include only active users

        Returns:
            List of User objects
        """
        try:
            # Scan table (in production, consider using GSI for better performance)
            filter_expression = "#role = :role"
            expression_values = {":role": role}
            expression_names = {"#role": "role"}

            if active_only:
                filter_expression += " AND is_active = :active"
                expression_values[":active"] = True

            items = self.scan(
                filter_expression=filter_expression,
                expression_attribute_values=expression_values,
                expression_attribute_names=expression_names,
            )

            users = []
            for item in items:
                try:
                    users.append(User.from_dynamodb_item(item))
                except Exception as e:
                    logger.warning(f"Error parsing user data: {str(e)}")
                    continue

            return users

        except ClientError as e:
            logger.error(f"Error listing users by role: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error listing users by role: {str(e)}")
            return []

    def list_users_by_department(
        self, department: str, active_only: bool = True
    ) -> List[User]:
        """
        List users by department.

        Args:
            department: Department to filter by
            active_only: Whether to include only active users

        Returns:
            List of User objects
        """
        try:
            filter_expression = "department = :department"
            expression_values = {":department": department}

            if active_only:
                filter_expression += " AND is_active = :active"
                expression_values[":active"] = True

            items = self.scan(
                filter_expression=filter_expression,
                expression_attribute_values=expression_values,
            )

            users = []
            for item in items:
                try:
                    users.append(User.from_dynamodb_item(item))
                except Exception as e:
                    logger.warning(f"Error parsing user data: {str(e)}")
                    continue

            return users

        except ClientError as e:
            logger.error(f"Error listing users by department: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error listing users by department: {str(e)}")
            return []

    def get_user_count_by_role(self) -> Dict[str, int]:
        """
        Get count of users by role.

        Returns:
            Dictionary with role counts
        """
        try:
            items = self.scan(
                filter_expression="is_active = :active",
                expression_attribute_values={":active": True},
            )

            role_counts = {}
            for item in items:
                role = item.get("role", "unknown")
                role_counts[role] = role_counts.get(role, 0) + 1

            return role_counts

        except ClientError as e:
            logger.error(f"Error getting user count by role: {str(e)}")
            return {}
        except Exception as e:
            logger.error(f"Unexpected error getting user count by role: {str(e)}")
            return {}

    def search_users(self, search_term: str, role: Optional[str] = None) -> List[User]:
        """
        Search users by name or email.

        Args:
            search_term: Term to search for in name or email
            role: Optional role filter

        Returns:
            List of matching User objects
        """
        try:
            # Build filter expression
            filter_expression = "is_active = :active AND (contains(#name, :search) OR contains(email, :search))"
            expression_values = {":active": True, ":search": search_term.lower()}
            expression_names = {"#name": "name"}

            if role:
                filter_expression += " AND #role = :role"
                expression_values[":role"] = role
                expression_names["#role"] = "role"

            items = self.scan(
                filter_expression=filter_expression,
                expression_attribute_values=expression_values,
                expression_attribute_names=expression_names,
            )

            users = []
            for item in items:
                try:
                    user = User.from_dynamodb_item(item)
                    # Additional filtering for case-insensitive search
                    if (
                        search_term.lower() in user.name.lower()
                        or search_term.lower() in user.email.lower()
                    ):
                        users.append(user)
                except Exception as e:
                    logger.warning(f"Error parsing user data: {str(e)}")
                    continue

            return users

        except ClientError as e:
            logger.error(f"Error searching users: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error searching users: {str(e)}")
            return []


class AuditLogRepository:
    """Repository for security audit logs."""

    def __init__(self):
        # In a production system, this would use a separate table or logging service
        self.table_name = f"{os.environ.get('DYNAMODB_TABLE_PREFIX')}-audit-logs"

    def log_security_event(self, audit_log: SecurityAuditLog) -> bool:
        """
        Log a security event.

        Args:
            audit_log: SecurityAuditLog object

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # For now, just log to CloudWatch
            logger.info(f"SECURITY_AUDIT: {audit_log.to_dict()}")

            # In production, you would store this in a dedicated audit table
            # or send to a centralized logging service like CloudTrail or Splunk

            return True

        except Exception as e:
            logger.error(f"Error logging security event: {str(e)}")
            return False

    def create_login_log(
        self,
        user_id: str,
        ip_address: str = None,
        user_agent: str = None,
        success: bool = True,
    ) -> bool:
        """
        Create a login audit log.

        Args:
            user_id: User ID
            ip_address: Client IP address
            user_agent: Client user agent
            success: Whether login was successful

        Returns:
            bool: True if successful, False otherwise
        """
        event_type = "login_success" if success else "login_failure"

        audit_log = SecurityAuditLog(
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type=event_type,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"success": success},
        )

        return self.log_security_event(audit_log)

    def create_logout_log(self, user_id: str, ip_address: str = None) -> bool:
        """
        Create a logout audit log.

        Args:
            user_id: User ID
            ip_address: Client IP address

        Returns:
            bool: True if successful, False otherwise
        """
        audit_log = SecurityAuditLog(
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type="logout",
            user_id=user_id,
            ip_address=ip_address,
        )

        return self.log_security_event(audit_log)

    def create_profile_access_log(
        self, user_id: str, accessed_profile_id: str, action: str = "view"
    ) -> bool:
        """
        Create a profile access audit log.

        Args:
            user_id: User ID performing the action
            accessed_profile_id: Profile being accessed
            action: Type of action (view, update, etc.)

        Returns:
            bool: True if successful, False otherwise
        """
        audit_log = SecurityAuditLog(
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type="profile_access",
            user_id=user_id,
            resource=f"profile:{accessed_profile_id}",
            details={"action": action, "accessed_profile_id": accessed_profile_id},
        )

        return self.log_security_event(audit_log)
