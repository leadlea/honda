"""
Unit tests for authentication utilities.
"""

import os
from unittest.mock import Mock, patch

import jwt

# Set environment variables for testing
os.environ["COGNITO_USER_POOL_ID"] = "test-pool-id"
os.environ["COGNITO_CLIENT_ID"] = "test-client-id"
os.environ["REGION"] = "us-west-2"

from src.utils.auth_utils import (
    can_access_profile,
    create_audit_log,
    extract_user_from_event,
    is_admin,
    is_external_recruiter,
    is_veteran,
    log_security_event,
    require_auth,
    require_role,
    validate_password_strength,
    verify_jwt_token,
)


class TestAuthUtils:
    """Test cases for authentication utilities."""

    def test_extract_user_from_event_with_authorizer(self):
        """Test extracting user from event with API Gateway authorizer."""
        event = {
            "requestContext": {
                "authorizer": {
                    "claims": {
                        "username": "test-user-id",
                        "email": "test@example.com",
                        "name": "Test User",
                        "custom:role": "veteran",
                        "custom:department": "Engineering",
                        "custom:employee_id": "EMP001",
                    }
                }
            }
        }

        user = extract_user_from_event(event)

        assert user is not None
        assert user["user_id"] == "test-user-id"
        assert user["email"] == "test@example.com"
        assert user["name"] == "Test User"
        assert user["role"] == "veteran"
        assert user["department"] == "Engineering"
        assert user["employee_id"] == "EMP001"

    def test_extract_user_from_event_with_token(self):
        """Test extracting user from event with Authorization header."""
        event = {"headers": {"Authorization": "Bearer test-token"}}

        with patch("src.utils.auth_utils.verify_jwt_token") as mock_verify:
            mock_verify.return_value = {
                "username": "test-user-id",
                "email": "test@example.com",
                "name": "Test User",
                "custom:role": "veteran",
                "custom:department": "Engineering",
                "custom:employee_id": "EMP001",
            }

            user = extract_user_from_event(event)

            assert user is not None
            assert user["user_id"] == "test-user-id"
            assert user["email"] == "test@example.com"

    def test_extract_user_from_event_no_auth(self):
        """Test extracting user from event without authentication."""
        event = {"headers": {}}

        user = extract_user_from_event(event)

        assert user is None

    def test_require_auth_decorator_success(self):
        """Test require_auth decorator with valid authentication."""

        @require_auth()
        def test_handler(event, context):
            return {"statusCode": 200, "body": "success"}

        event = {
            "requestContext": {
                "authorizer": {
                    "claims": {
                        "username": "test-user-id",
                        "email": "test@example.com",
                        "custom:role": "veteran",
                    }
                }
            }
        }

        result = test_handler(event, {})

        assert result["statusCode"] == 200
        assert "user" in event
        assert event["user"]["user_id"] == "test-user-id"

    def test_require_auth_decorator_no_auth(self):
        """Test require_auth decorator without authentication."""

        @require_auth()
        def test_handler(event, context):
            return {"statusCode": 200, "body": "success"}

        event = {"headers": {}}

        result = test_handler(event, {})

        assert result["statusCode"] == 401
        assert "Authentication required" in result["body"]

    def test_require_role_decorator_success(self):
        """Test require_role decorator with correct role."""

        @require_role("admin", "veteran")
        def test_handler(event, context):
            return {"statusCode": 200, "body": "success"}

        event = {
            "requestContext": {
                "authorizer": {
                    "claims": {"username": "test-user-id", "custom:role": "veteran"}
                }
            }
        }

        result = test_handler(event, {})

        assert result["statusCode"] == 200

    def test_require_role_decorator_insufficient_permissions(self):
        """Test require_role decorator with insufficient permissions."""

        @require_role("admin")
        def test_handler(event, context):
            return {"statusCode": 200, "body": "success"}

        event = {
            "requestContext": {
                "authorizer": {
                    "claims": {"username": "test-user-id", "custom:role": "veteran"}
                }
            }
        }

        result = test_handler(event, {})

        assert result["statusCode"] == 403
        assert "Insufficient permissions" in result["body"]

    def test_is_admin_true(self):
        """Test is_admin function with admin user."""
        user = {"role": "admin"}
        assert is_admin(user) is True

    def test_is_admin_false(self):
        """Test is_admin function with non-admin user."""
        user = {"role": "veteran"}
        assert is_admin(user) is False

    def test_is_veteran_true(self):
        """Test is_veteran function with veteran user."""
        user = {"role": "veteran"}
        assert is_veteran(user) is True

    def test_is_veteran_false(self):
        """Test is_veteran function with non-veteran user."""
        user = {"role": "admin"}
        assert is_veteran(user) is False

    def test_is_external_recruiter_true(self):
        """Test is_external_recruiter function with external recruiter."""
        user = {"role": "external_recruiter"}
        assert is_external_recruiter(user) is True

    def test_is_external_recruiter_false(self):
        """Test is_external_recruiter function with non-external recruiter."""
        user = {"role": "veteran"}
        assert is_external_recruiter(user) is False

    def test_can_access_profile_own_profile(self):
        """Test can_access_profile with user's own profile."""
        user = {"user_id": "test-user-id", "role": "veteran"}
        assert can_access_profile(user, "test-user-id") is True

    def test_can_access_profile_admin(self):
        """Test can_access_profile with admin user."""
        user = {"user_id": "admin-id", "role": "admin"}
        assert can_access_profile(user, "other-user-id") is True

    def test_can_access_profile_unauthorized(self):
        """Test can_access_profile with unauthorized access."""
        user = {"user_id": "test-user-id", "role": "veteran"}
        assert can_access_profile(user, "other-user-id") is False

    def test_validate_password_strength_valid(self):
        """Test password validation with valid password."""
        result = validate_password_strength("TestPass123!")

        assert result["valid"] is True
        assert len(result["errors"]) == 0

    def test_validate_password_strength_too_short(self):
        """Test password validation with short password."""
        result = validate_password_strength("Test1!")

        assert result["valid"] is False
        assert any("at least 8 characters" in error for error in result["errors"])

    def test_validate_password_strength_no_uppercase(self):
        """Test password validation without uppercase letter."""
        result = validate_password_strength("testpass123!")

        assert result["valid"] is False
        assert any("uppercase letter" in error for error in result["errors"])

    def test_validate_password_strength_no_lowercase(self):
        """Test password validation without lowercase letter."""
        result = validate_password_strength("TESTPASS123!")

        assert result["valid"] is False
        assert any("lowercase letter" in error for error in result["errors"])

    def test_validate_password_strength_no_number(self):
        """Test password validation without number."""
        result = validate_password_strength("TestPass!")

        assert result["valid"] is False
        assert any("number" in error for error in result["errors"])

    def test_validate_password_strength_no_special_char(self):
        """Test password validation without special character."""
        result = validate_password_strength("TestPass123")

        assert result["valid"] is False
        assert any("special character" in error for error in result["errors"])

    @patch("src.utils.auth_utils.logger")
    def test_log_security_event(self, mock_logger):
        """Test security event logging."""
        log_security_event("login_attempt", "test-user-id", {"ip": "192.168.1.1"})

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert "SECURITY_EVENT" in call_args
        assert "login_attempt" in call_args
        assert "test-user-id" in call_args

    @patch("src.utils.auth_utils.logger")
    def test_create_audit_log(self, mock_logger):
        """Test audit log creation."""
        create_audit_log(
            "profile_update", "test-user-id", "profile:123", {"field": "name"}
        )

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert "AUDIT_LOG" in call_args
        assert "profile_update" in call_args
        assert "test-user-id" in call_args

    @patch("src.utils.auth_utils.requests.get")
    def test_verify_jwt_token_success(self, mock_get):
        """Test successful JWT token verification."""
        # Mock JWKS response
        mock_get.return_value.json.return_value = {
            "keys": [{"kid": "test-key-id", "kty": "RSA", "n": "test-n", "e": "AQAB"}]
        }
        mock_get.return_value.raise_for_status.return_value = None

        # Mock JWT decode
        with patch(
            "src.utils.auth_utils.jwt.get_unverified_header"
        ) as mock_header, patch(
            "src.utils.auth_utils.jwt.get_algorithm_by_name"
        ) as mock_get_alg, patch(
            "src.utils.auth_utils.jwt.decode"
        ) as mock_decode:
            mock_header.return_value = {"kid": "test-key-id"}
            mock_rsa_alg = Mock()
            mock_rsa_alg.from_jwk.return_value = "mock-key"
            mock_get_alg.return_value = mock_rsa_alg
            mock_decode.return_value = {
                "username": "test-user-id",
                "email": "test@example.com",
            }

            result = verify_jwt_token("test-token")

            assert result is not None
            assert result["username"] == "test-user-id"
            assert result["email"] == "test@example.com"

    @patch("src.utils.auth_utils.requests.get")
    def test_verify_jwt_token_invalid(self, mock_get):
        """Test JWT token verification with invalid token."""
        # Mock JWKS response
        mock_get.return_value.json.return_value = {
            "keys": [{"kid": "test-key-id", "kty": "RSA", "n": "test-n", "e": "AQAB"}]
        }
        mock_get.return_value.raise_for_status.return_value = None

        # Mock JWT decode to raise exception
        with patch(
            "src.utils.auth_utils.jwt.get_unverified_header"
        ) as mock_header, patch(
            "src.utils.auth_utils.jwt.get_algorithm_by_name"
        ) as mock_get_alg, patch(
            "src.utils.auth_utils.jwt.decode"
        ) as mock_decode:
            mock_header.return_value = {"kid": "test-key-id"}
            mock_rsa_alg = Mock()
            mock_rsa_alg.from_jwk.return_value = "mock-key"
            mock_get_alg.return_value = mock_rsa_alg
            mock_decode.side_effect = jwt.InvalidTokenError("Invalid token")

            result = verify_jwt_token("invalid-token")

            assert result is None
