"""
Unit tests for RBAC (Role-Based Access Control) system.
"""

from unittest.mock import patch


from src.utils.rbac import (
    AccessContext,
    Permission,
    RBACManager,
    check_resource_access,
    get_available_roles,
    get_user_permissions,
    require_permission,
    require_role,
    validate_role,
)


class TestRBACManager:
    """Test cases for RBACManager."""

    def setup_method(self):
        """Set up test environment."""
        self.rbac = RBACManager()

    def test_veteran_permissions(self):
        """Test veteran role permissions."""
        # Veterans should have basic permissions
        assert self.rbac.has_permission("veteran", Permission.VIEW_OWN_PROFILE)
        assert self.rbac.has_permission("veteran", Permission.EDIT_OWN_PROFILE)
        assert self.rbac.has_permission("veteran", Permission.TAKE_QUESTIONNAIRE)
        assert self.rbac.has_permission("veteran", Permission.VIEW_OPPORTUNITIES)
        assert self.rbac.has_permission("veteran", Permission.APPLY_TO_OPPORTUNITIES)

        # Veterans should NOT have admin permissions
        assert not self.rbac.has_permission("veteran", Permission.VIEW_ANY_PROFILE)
        assert not self.rbac.has_permission("veteran", Permission.CREATE_USERS)
        assert not self.rbac.has_permission("veteran", Permission.VIEW_AUDIT_LOGS)

    def test_admin_permissions(self):
        """Test admin role permissions."""
        # Admins should have all permissions
        for permission in Permission:
            assert self.rbac.has_permission("admin", permission)

    def test_external_recruiter_permissions(self):
        """Test external recruiter role permissions."""
        # External recruiters should have limited permissions
        assert self.rbac.has_permission(
            "external_recruiter", Permission.VIEW_PUBLIC_PROFILES
        )
        assert self.rbac.has_permission(
            "external_recruiter", Permission.SEARCH_PUBLIC_PROFILES
        )
        assert self.rbac.has_permission(
            "external_recruiter", Permission.CONTACT_VETERANS
        )
        assert self.rbac.has_permission(
            "external_recruiter", Permission.CREATE_OPPORTUNITIES
        )

        # External recruiters should NOT have internal permissions
        assert not self.rbac.has_permission(
            "external_recruiter", Permission.VIEW_OWN_PROFILE
        )
        assert not self.rbac.has_permission(
            "external_recruiter", Permission.TAKE_QUESTIONNAIRE
        )
        assert not self.rbac.has_permission(
            "external_recruiter", Permission.CREATE_USERS
        )

    def test_invalid_role(self):
        """Test handling of invalid roles."""
        assert not self.rbac.has_permission("invalid_role", Permission.VIEW_OWN_PROFILE)

    def test_context_based_access_own_resource(self):
        """Test context-based access control for own resources."""
        context = AccessContext(
            user_id="user123", role="veteran", resource_owner_id="user123"
        )

        # User should be able to access their own profile
        assert self.rbac.has_permission("veteran", Permission.VIEW_OWN_PROFILE, context)
        assert self.rbac.has_permission("veteran", Permission.EDIT_OWN_PROFILE, context)

    def test_context_based_access_other_resource(self):
        """Test context-based access control for other user's resources."""
        context = AccessContext(
            user_id="user123", role="veteran", resource_owner_id="user456"
        )

        # Veteran should NOT be able to access other user's profile
        assert not self.rbac.has_permission(
            "veteran", Permission.VIEW_OWN_PROFILE, context
        )
        assert not self.rbac.has_permission(
            "veteran", Permission.EDIT_OWN_PROFILE, context
        )

    def test_admin_context_access(self):
        """Test admin access with context."""
        context = AccessContext(
            user_id="admin123", role="admin", resource_owner_id="user456"
        )

        # Admin should be able to access any resource
        assert self.rbac.has_permission("admin", Permission.VIEW_OWN_PROFILE, context)
        assert self.rbac.has_permission("admin", Permission.EDIT_OWN_PROFILE, context)

    def test_external_recruiter_public_profile_access(self):
        """Test external recruiter access to public profiles."""
        # Public profile
        public_context = AccessContext(
            user_id="recruiter123",
            role="external_recruiter",
            additional_context={"is_public": True},
        )

        assert self.rbac.has_permission(
            "external_recruiter", Permission.VIEW_PUBLIC_PROFILES, public_context
        )

        # Private profile
        private_context = AccessContext(
            user_id="recruiter123",
            role="external_recruiter",
            additional_context={"is_public": False},
        )

        assert not self.rbac.has_permission(
            "external_recruiter", Permission.VIEW_PUBLIC_PROFILES, private_context
        )

    def test_veteran_opportunity_application(self):
        """Test veteran application to opportunities."""
        # Active opportunity
        active_context = AccessContext(
            user_id="veteran123",
            role="veteran",
            additional_context={"opportunity_active": True},
        )

        assert self.rbac.has_permission(
            "veteran", Permission.APPLY_TO_OPPORTUNITIES, active_context
        )

        # Inactive opportunity
        inactive_context = AccessContext(
            user_id="veteran123",
            role="veteran",
            additional_context={"opportunity_active": False},
        )

        assert not self.rbac.has_permission(
            "veteran", Permission.APPLY_TO_OPPORTUNITIES, inactive_context
        )

    def test_get_user_permissions(self):
        """Test getting user permissions."""
        veteran_permissions = self.rbac.get_user_permissions("veteran")
        admin_permissions = self.rbac.get_user_permissions("admin")
        recruiter_permissions = self.rbac.get_user_permissions("external_recruiter")

        # Veteran should have fewer permissions than admin
        assert len(veteran_permissions) < len(admin_permissions)

        # Admin should have all permissions
        assert len(admin_permissions) == len(Permission)

        # External recruiter should have specific permissions
        assert Permission.VIEW_PUBLIC_PROFILES in recruiter_permissions
        assert Permission.TAKE_QUESTIONNAIRE not in recruiter_permissions

    def test_can_access_resource(self):
        """Test resource access checking."""
        # User accessing own profile
        assert self.rbac.can_access_resource(
            user_role="veteran",
            user_id="user123",
            resource_type="profile",
            resource_owner_id="user123",
            action="view",
        )

        # User accessing other's profile
        assert not self.rbac.can_access_resource(
            user_role="veteran",
            user_id="user123",
            resource_type="profile",
            resource_owner_id="user456",
            action="view",
        )

        # Admin accessing any profile
        assert self.rbac.can_access_resource(
            user_role="admin",
            user_id="admin123",
            resource_type="profile",
            resource_owner_id="user456",
            action="view",
        )


class TestRBACDecorators:
    """Test cases for RBAC decorators."""

    def test_require_permission_decorator_success(self):
        """Test require_permission decorator with valid permission."""

        @require_permission(Permission.VIEW_OWN_PROFILE)
        def test_handler(event, context):
            return {"statusCode": 200, "body": "success"}

        event = {"user": {"user_id": "user123", "role": "veteran"}}

        with patch(
            "src.utils.rbac.rbac_manager.has_permission", return_value=True
        ), patch("src.utils.rbac.log_access_granted") as mock_log:
            result = test_handler(event, {})

            assert result["statusCode"] == 200
            mock_log.assert_called_once()

    def test_require_permission_decorator_denied(self):
        """Test require_permission decorator with insufficient permission."""

        @require_permission(Permission.CREATE_USERS)
        def test_handler(event, context):
            return {"statusCode": 200, "body": "success"}

        event = {"user": {"user_id": "user123", "role": "veteran"}}

        with patch(
            "src.utils.rbac.rbac_manager.has_permission", return_value=False
        ), patch("src.utils.rbac.log_access_denied") as mock_log:
            result = test_handler(event, {})

            assert result["statusCode"] == 403
            assert "Insufficient permissions" in result["body"]
            mock_log.assert_called_once()

    def test_require_permission_decorator_no_auth(self):
        """Test require_permission decorator without authentication."""

        @require_permission(Permission.VIEW_OWN_PROFILE)
        def test_handler(event, context):
            return {"statusCode": 200, "body": "success"}

        event = {}  # No user in event

        result = test_handler(event, {})

        assert result["statusCode"] == 401
        assert "Authentication required" in result["body"]

    def test_require_role_decorator_success(self):
        """Test require_role decorator with valid role."""

        @require_role("admin", "veteran")
        def test_handler(event, context):
            return {"statusCode": 200, "body": "success"}

        event = {"user": {"user_id": "user123", "role": "veteran"}}

        result = test_handler(event, {})

        assert result["statusCode"] == 200

    def test_require_role_decorator_denied(self):
        """Test require_role decorator with invalid role."""

        @require_role("admin")
        def test_handler(event, context):
            return {"statusCode": 200, "body": "success"}

        event = {"user": {"user_id": "user123", "role": "veteran"}}

        with patch("src.utils.rbac.log_access_denied") as mock_log:
            result = test_handler(event, {})

            assert result["statusCode"] == 403
            assert "Insufficient permissions" in result["body"]
            mock_log.assert_called_once()


class TestRBACUtilities:
    """Test cases for RBAC utility functions."""

    def test_check_resource_access(self):
        """Test check_resource_access function."""
        with patch(
            "src.utils.rbac.rbac_manager.can_access_resource", return_value=True
        ):
            result = check_resource_access(
                user_role="veteran",
                user_id="user123",
                resource_type="profile",
                resource_owner_id="user123",
                action="view",
            )

            assert result is True

    def test_get_user_permissions_function(self):
        """Test get_user_permissions function."""
        permissions = get_user_permissions("veteran")

        assert isinstance(permissions, list)
        assert "view_own_profile" in permissions
        assert "create_users" not in permissions

    def test_validate_role_function(self):
        """Test validate_role function."""
        assert validate_role("veteran") is True
        assert validate_role("admin") is True
        assert validate_role("external_recruiter") is True
        assert validate_role("invalid_role") is False

    def test_get_available_roles_function(self):
        """Test get_available_roles function."""
        roles = get_available_roles()

        assert isinstance(roles, list)
        assert "veteran" in roles
        assert "admin" in roles
        assert "external_recruiter" in roles
        assert len(roles) == 3


class TestAccessContext:
    """Test cases for AccessContext."""

    def test_access_context_creation(self):
        """Test AccessContext creation."""
        context = AccessContext(
            user_id="user123",
            role="veteran",
            resource_owner_id="user456",
            resource_type="profile",
        )

        assert context.user_id == "user123"
        assert context.role == "veteran"
        assert context.resource_owner_id == "user456"
        assert context.resource_type == "profile"
        assert context.additional_context == {}

    def test_access_context_with_additional_context(self):
        """Test AccessContext with additional context."""
        context = AccessContext(
            user_id="user123",
            role="veteran",
            additional_context={"is_public": True, "department": "Engineering"},
        )

        assert context.additional_context["is_public"] is True
        assert context.additional_context["department"] == "Engineering"
