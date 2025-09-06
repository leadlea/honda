"""
Role-Based Access Control (RBAC) system for the veteran talent matching platform.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from functools import wraps
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger()


class Role(Enum):
    """User roles in the system."""

    VETERAN = "veteran"
    ADMIN = "admin"
    EXTERNAL_RECRUITER = "external_recruiter"


class Permission(Enum):
    """System permissions."""

    # Profile permissions
    VIEW_OWN_PROFILE = "view_own_profile"
    EDIT_OWN_PROFILE = "edit_own_profile"
    VIEW_ANY_PROFILE = "view_any_profile"
    EDIT_ANY_PROFILE = "edit_any_profile"
    DELETE_ANY_PROFILE = "delete_any_profile"

    # Public profile permissions
    VIEW_PUBLIC_PROFILES = "view_public_profiles"
    SEARCH_PUBLIC_PROFILES = "search_public_profiles"
    CONTACT_VETERANS = "contact_veterans"

    # Questionnaire permissions
    TAKE_QUESTIONNAIRE = "take_questionnaire"
    VIEW_QUESTIONNAIRE_RESULTS = "view_questionnaire_results"
    MANAGE_QUESTIONNAIRES = "manage_questionnaires"

    # Opportunity permissions
    VIEW_OPPORTUNITIES = "view_opportunities"
    CREATE_OPPORTUNITIES = "create_opportunities"
    EDIT_OPPORTUNITIES = "edit_opportunities"
    DELETE_OPPORTUNITIES = "delete_opportunities"

    # Application permissions
    APPLY_TO_OPPORTUNITIES = "apply_to_opportunities"
    VIEW_OWN_APPLICATIONS = "view_own_applications"
    VIEW_ALL_APPLICATIONS = "view_all_applications"
    MANAGE_APPLICATIONS = "manage_applications"

    # Recommendation permissions
    READ_RECOMMENDATIONS = "read_recommendations"
    GENERATE_RECOMMENDATIONS = "generate_recommendations"
    READ_ALL_PROFILES = "read_all_profiles"
    ANALYZE_MATCHES = "analyze_matches"
    ADMIN_ACCESS = "admin_access"

    # User management permissions
    CREATE_USERS = "create_users"
    VIEW_USERS = "view_users"
    EDIT_USERS = "edit_users"
    DELETE_USERS = "delete_users"
    MANAGE_USER_ROLES = "manage_user_roles"

    # System administration
    VIEW_AUDIT_LOGS = "view_audit_logs"
    MANAGE_SYSTEM_SETTINGS = "manage_system_settings"
    ACCESS_ADMIN_PANEL = "access_admin_panel"


@dataclass
class AccessContext:
    """Context information for access control decisions."""

    user_id: str
    role: str
    resource_owner_id: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    additional_context: Dict[str, Any] = None

    def __post_init__(self):
        if self.additional_context is None:
            self.additional_context = {}


class RBACManager:
    """Role-Based Access Control manager."""

    def __init__(self):
        self._role_permissions = self._initialize_role_permissions()

    def _initialize_role_permissions(self) -> Dict[Role, Set[Permission]]:
        """Initialize role-permission mappings."""
        return {
            Role.VETERAN: {
                # Profile permissions
                Permission.VIEW_OWN_PROFILE,
                Permission.EDIT_OWN_PROFILE,
                # Questionnaire permissions
                Permission.TAKE_QUESTIONNAIRE,
                Permission.VIEW_QUESTIONNAIRE_RESULTS,
                # Opportunity permissions
                Permission.VIEW_OPPORTUNITIES,
                Permission.APPLY_TO_OPPORTUNITIES,
                # Application permissions
                Permission.VIEW_OWN_APPLICATIONS,
                # Recommendation permissions
                Permission.READ_RECOMMENDATIONS,
                Permission.GENERATE_RECOMMENDATIONS,
            },
            Role.ADMIN: {
                # All veteran permissions
                *{perm for perm in Permission},  # Admins have all permissions
            },
            Role.EXTERNAL_RECRUITER: {
                # Public profile permissions
                Permission.VIEW_PUBLIC_PROFILES,
                Permission.SEARCH_PUBLIC_PROFILES,
                Permission.CONTACT_VETERANS,
                # Opportunity permissions (for external opportunities)
                Permission.VIEW_OPPORTUNITIES,
                Permission.CREATE_OPPORTUNITIES,
                Permission.EDIT_OPPORTUNITIES,
                # Application permissions (limited)
                Permission.VIEW_ALL_APPLICATIONS,
                Permission.MANAGE_APPLICATIONS,
            },
        }

    def has_permission(
        self,
        user_role: str,
        permission: Permission,
        context: Optional[AccessContext] = None,
    ) -> bool:
        """
        Check if a user role has a specific permission.

        Args:
            user_role: User's role string
            permission: Permission to check
            context: Additional context for access control decisions

        Returns:
            bool: True if user has permission, False otherwise
        """
        try:
            role = Role(user_role)
        except ValueError:
            logger.warning(f"Invalid role: {user_role}")
            return False

        # Check basic role permissions
        if permission in self._role_permissions.get(role, set()):
            # Apply context-specific rules
            return self._apply_context_rules(role, permission, context)

        return False

    def _apply_context_rules(
        self, role: Role, permission: Permission, context: Optional[AccessContext]
    ) -> bool:
        """
        Apply context-specific access control rules.

        Args:
            role: User's role
            permission: Permission being checked
            context: Access context

        Returns:
            bool: True if access is allowed, False otherwise
        """
        if context is None:
            return True

        # Rule: Users can only access their own resources (unless admin)
        if role != Role.ADMIN and context.resource_owner_id:
            if permission in [
                Permission.VIEW_OWN_PROFILE,
                Permission.EDIT_OWN_PROFILE,
                Permission.VIEW_OWN_APPLICATIONS,
                Permission.VIEW_QUESTIONNAIRE_RESULTS,
            ]:
                return context.user_id == context.resource_owner_id

        # Rule: External recruiters can only view public profiles
        if role == Role.EXTERNAL_RECRUITER:
            if permission in [
                Permission.VIEW_PUBLIC_PROFILES,
                Permission.SEARCH_PUBLIC_PROFILES,
            ]:
                # Additional check: profile must be marked as public
                is_public = context.additional_context.get("is_public", False)
                return is_public

        # Rule: Veterans can only apply to active opportunities
        if role == Role.VETERAN and permission == Permission.APPLY_TO_OPPORTUNITIES:
            is_active = context.additional_context.get("opportunity_active", True)
            return is_active

        return True

    def get_user_permissions(self, user_role: str) -> Set[Permission]:
        """
        Get all permissions for a user role.

        Args:
            user_role: User's role string

        Returns:
            Set of permissions for the role
        """
        try:
            role = Role(user_role)
            return self._role_permissions.get(role, set())
        except ValueError:
            logger.warning(f"Invalid role: {user_role}")
            return set()

    def can_access_resource(
        self,
        user_role: str,
        user_id: str,
        resource_type: str,
        resource_owner_id: str,
        action: str,
        **kwargs,
    ) -> bool:
        """
        Check if user can access a specific resource.

        Args:
            user_role: User's role
            user_id: User's ID
            resource_type: Type of resource (profile, application, etc.)
            resource_owner_id: ID of resource owner
            action: Action being performed (view, edit, delete)
            **kwargs: Additional context

        Returns:
            bool: True if access is allowed, False otherwise
        """
        # Map resource actions to permissions
        permission_map = {
            ("profile", "view"): Permission.VIEW_OWN_PROFILE,
            ("profile", "edit"): Permission.EDIT_OWN_PROFILE,
            ("application", "view"): Permission.VIEW_OWN_APPLICATIONS,
            ("questionnaire", "view"): Permission.VIEW_QUESTIONNAIRE_RESULTS,
        }

        # Get the appropriate permission
        permission = permission_map.get((resource_type, action))
        if not permission:
            logger.warning(f"Unknown resource action: {resource_type}.{action}")
            return False

        # Create access context
        context = AccessContext(
            user_id=user_id,
            role=user_role,
            resource_owner_id=resource_owner_id,
            resource_type=resource_type,
            additional_context=kwargs,
        )

        return self.has_permission(user_role, permission, context)


# Global RBAC manager instance
rbac_manager = RBACManager()


def require_permission(permission: Permission, resource_owner_field: str = None):
    """
    Decorator to require specific permission for a function.

    Args:
        permission: Required permission
        resource_owner_field: Field name in event that contains resource owner ID
    """

    def decorator(func):
        @wraps(func)
        def wrapper(event, context):
            # Extract user information from event
            user = event.get("user")
            if not user:
                return {
                    "statusCode": 401,
                    "headers": {"Content-Type": "application/json"},
                    "body": '{"error": "Authentication required"}',
                }

            user_role = user.get("role")
            user_id = user.get("user_id")

            # Create access context
            access_context = AccessContext(user_id=user_id, role=user_role)

            # If resource owner field is specified, extract it
            if resource_owner_field:
                resource_owner_id = event.get(resource_owner_field)
                access_context.resource_owner_id = resource_owner_id

            # Check permission
            if not rbac_manager.has_permission(user_role, permission, access_context):
                # Log security event
                log_access_denied(user_id, user_role, permission.value, access_context)

                return {
                    "statusCode": 403,
                    "headers": {"Content-Type": "application/json"},
                    "body": '{"error": "Insufficient permissions"}',
                }

            # Log successful access
            log_access_granted(user_id, user_role, permission.value, access_context)

            return func(event, context)

        return wrapper

    return decorator


def require_role(*allowed_roles: str):
    """
    Decorator to require specific roles.

    Args:
        allowed_roles: Variable number of allowed role strings
    """

    def decorator(func):
        @wraps(func)
        def wrapper(event, context):
            user = event.get("user")
            if not user:
                return {
                    "statusCode": 401,
                    "headers": {"Content-Type": "application/json"},
                    "body": '{"error": "Authentication required"}',
                }

            user_role = user.get("role")
            user_id = user.get("user_id")

            if user_role not in allowed_roles:
                # Log security event
                log_access_denied(
                    user_id, user_role, f"role_check:{','.join(allowed_roles)}"
                )

                return {
                    "statusCode": 403,
                    "headers": {"Content-Type": "application/json"},
                    "body": '{"error": "Insufficient permissions"}',
                }

            return func(event, context)

        return wrapper

    return decorator


def check_resource_access(
    user_role: str,
    user_id: str,
    resource_type: str,
    resource_owner_id: str,
    action: str,
    **kwargs,
) -> bool:
    """
    Check if user can access a specific resource.

    Args:
        user_role: User's role
        user_id: User's ID
        resource_type: Type of resource
        resource_owner_id: ID of resource owner
        action: Action being performed
        **kwargs: Additional context

    Returns:
        bool: True if access is allowed, False otherwise
    """
    return rbac_manager.can_access_resource(
        user_role, user_id, resource_type, resource_owner_id, action, **kwargs
    )


def log_access_granted(
    user_id: str, user_role: str, permission: str, context: AccessContext = None
):
    """Log successful access grant."""
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": "access_granted",
        "user_id": user_id,
        "user_role": user_role,
        "permission": permission,
        "context": context.__dict__ if context else {},
    }
    logger.info(f"ACCESS_GRANTED: {log_entry}")


def log_access_denied(
    user_id: str, user_role: str, permission: str, context: AccessContext = None
):
    """Log access denial."""
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": "access_denied",
        "user_id": user_id,
        "user_role": user_role,
        "permission": permission,
        "context": context.__dict__ if context else {},
    }
    logger.warning(f"ACCESS_DENIED: {log_entry}")


def get_user_permissions(user_role: str) -> List[str]:
    """
    Get list of permission strings for a user role.

    Args:
        user_role: User's role string

    Returns:
        List of permission strings
    """
    permissions = rbac_manager.get_user_permissions(user_role)
    return [perm.value for perm in permissions]


def validate_role(role: str) -> bool:
    """
    Validate if a role string is valid.

    Args:
        role: Role string to validate

    Returns:
        bool: True if valid, False otherwise
    """
    try:
        Role(role)
        return True
    except ValueError:
        return False


def get_available_roles() -> List[str]:
    """
    Get list of all available roles.

    Returns:
        List of role strings
    """
    return [role.value for role in Role]
