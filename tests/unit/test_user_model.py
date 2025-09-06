"""
Unit tests for user models.
"""

from datetime import datetime, timezone

import pytest

from src.models.user import (
    AuthTokens,
    SecurityAuditLog,
    User,
    UserLoginRequest,
    UserRegistrationRequest,
    UserRole,
    UserSession,
    UserUpdateRequest,
)


class TestUser:
    """Test cases for User model."""

    def test_user_creation_valid(self):
        """Test creating a valid user."""
        user = User(
            user_id="test-user-id",
            employee_id="EMP001",
            email="test@example.com",
            name="Test User",
            department="Engineering",
            role="veteran",
        )

        assert user.user_id == "test-user-id"
        assert user.employee_id == "EMP001"
        assert user.email == "test@example.com"
        assert user.name == "Test User"
        assert user.department == "Engineering"
        assert user.role == "veteran"
        assert user.is_active is True

    def test_user_creation_invalid_email(self):
        """Test creating user with invalid email."""
        with pytest.raises(ValueError, match="Valid email is required"):
            User(
                user_id="test-user-id",
                employee_id="EMP001",
                email="invalid-email",
                name="Test User",
                department="Engineering",
                role="veteran",
            )

    def test_user_creation_invalid_role(self):
        """Test creating user with invalid role."""
        with pytest.raises(ValueError, match="Invalid role"):
            User(
                user_id="test-user-id",
                employee_id="EMP001",
                email="test@example.com",
                name="Test User",
                department="Engineering",
                role="invalid_role",
            )

    def test_user_creation_missing_required_fields(self):
        """Test creating user with missing required fields."""
        with pytest.raises(ValueError, match="User ID is required"):
            User(
                user_id="",
                employee_id="EMP001",
                email="test@example.com",
                name="Test User",
                department="Engineering",
                role="veteran",
            )

    def test_user_to_dict(self):
        """Test converting user to dictionary."""
        user = User(
            user_id="test-user-id",
            employee_id="EMP001",
            email="test@example.com",
            name="Test User",
            department="Engineering",
            role="veteran",
        )

        user_dict = user.to_dict()

        assert user_dict["user_id"] == "test-user-id"
        assert user_dict["employee_id"] == "EMP001"
        assert user_dict["email"] == "test@example.com"
        assert user_dict["name"] == "Test User"
        assert user_dict["department"] == "Engineering"
        assert user_dict["role"] == "veteran"
        assert user_dict["is_active"] is True

    def test_user_from_dict(self):
        """Test creating user from dictionary."""
        user_data = {
            "user_id": "test-user-id",
            "employee_id": "EMP001",
            "email": "test@example.com",
            "name": "Test User",
            "department": "Engineering",
            "role": "veteran",
            "is_active": True,
        }

        user = User.from_dict(user_data)

        assert user.user_id == "test-user-id"
        assert user.employee_id == "EMP001"
        assert user.email == "test@example.com"
        assert user.name == "Test User"
        assert user.department == "Engineering"
        assert user.role == "veteran"
        assert user.is_active is True

    def test_user_role_checks(self):
        """Test user role checking methods."""
        veteran = User(
            user_id="veteran-id",
            employee_id="EMP001",
            email="veteran@example.com",
            name="Veteran User",
            department="Engineering",
            role="veteran",
        )

        admin = User(
            user_id="admin-id",
            employee_id="EMP002",
            email="admin@example.com",
            name="Admin User",
            department="IT",
            role="admin",
        )

        recruiter = User(
            user_id="recruiter-id",
            employee_id="EMP003",
            email="recruiter@example.com",
            name="Recruiter User",
            department="HR",
            role="external_recruiter",
        )

        assert veteran.is_veteran() is True
        assert veteran.is_admin() is False
        assert veteran.is_external_recruiter() is False

        assert admin.is_veteran() is False
        assert admin.is_admin() is True
        assert admin.is_external_recruiter() is False

        assert recruiter.is_veteran() is False
        assert recruiter.is_admin() is False
        assert recruiter.is_external_recruiter() is True

    def test_user_can_access_profile(self):
        """Test user profile access permissions."""
        user = User(
            user_id="test-user-id",
            employee_id="EMP001",
            email="test@example.com",
            name="Test User",
            department="Engineering",
            role="veteran",
        )

        admin = User(
            user_id="admin-id",
            employee_id="EMP002",
            email="admin@example.com",
            name="Admin User",
            department="IT",
            role="admin",
        )

        # User can access own profile
        assert user.can_access_profile("test-user-id") is True

        # User cannot access other's profile
        assert user.can_access_profile("other-user-id") is False

        # Admin can access any profile
        assert admin.can_access_profile("test-user-id") is True
        assert admin.can_access_profile("other-user-id") is True

    def test_user_update_timestamp(self):
        """Test updating user timestamp."""
        user = User(
            user_id="test-user-id",
            employee_id="EMP001",
            email="test@example.com",
            name="Test User",
            department="Engineering",
            role="veteran",
        )

        original_timestamp = user.updated_at
        user.update_timestamp()

        assert user.updated_at != original_timestamp


class TestUserRegistrationRequest:
    """Test cases for UserRegistrationRequest model."""

    def test_valid_registration_request(self):
        """Test valid registration request."""
        request = UserRegistrationRequest(
            email="test@example.com",
            password="TestPass123!",
            name="Test User",
            employee_id="EMP001",
            department="Engineering",
        )

        assert request.is_valid() is True
        assert len(request.validate()) == 0

    def test_invalid_email_registration(self):
        """Test registration request with invalid email."""
        request = UserRegistrationRequest(
            email="invalid-email",
            password="TestPass123!",
            name="Test User",
            employee_id="EMP001",
            department="Engineering",
        )

        assert request.is_valid() is False
        errors = request.validate()
        assert any("Valid email is required" in error for error in errors)

    def test_short_password_registration(self):
        """Test registration request with short password."""
        request = UserRegistrationRequest(
            email="test@example.com",
            password="short",
            name="Test User",
            employee_id="EMP001",
            department="Engineering",
        )

        assert request.is_valid() is False
        errors = request.validate()
        assert any("at least 8 characters" in error for error in errors)

    def test_missing_fields_registration(self):
        """Test registration request with missing fields."""
        request = UserRegistrationRequest(
            email="test@example.com",
            password="TestPass123!",
            name="",
            employee_id="",
            department="",
        )

        assert request.is_valid() is False
        errors = request.validate()
        assert len(errors) >= 3  # name, employee_id, department


class TestUserLoginRequest:
    """Test cases for UserLoginRequest model."""

    def test_valid_login_request(self):
        """Test valid login request."""
        request = UserLoginRequest(email="test@example.com", password="TestPass123!")

        assert request.is_valid() is True
        assert len(request.validate()) == 0

    def test_missing_email_login(self):
        """Test login request with missing email."""
        request = UserLoginRequest(email="", password="TestPass123!")

        assert request.is_valid() is False
        errors = request.validate()
        assert "Email is required" in errors

    def test_missing_password_login(self):
        """Test login request with missing password."""
        request = UserLoginRequest(email="test@example.com", password="")

        assert request.is_valid() is False
        errors = request.validate()
        assert "Password is required" in errors


class TestUserUpdateRequest:
    """Test cases for UserUpdateRequest model."""

    def test_valid_update_request(self):
        """Test valid update request."""
        request = UserUpdateRequest(
            name="Updated Name", department="Updated Department"
        )

        assert request.is_valid() is True
        assert request.has_updates() is True
        assert len(request.validate()) == 0

    def test_empty_update_request(self):
        """Test empty update request."""
        request = UserUpdateRequest()

        assert request.is_valid() is True
        assert request.has_updates() is False

    def test_invalid_name_update(self):
        """Test update request with invalid name."""
        request = UserUpdateRequest(name="A")  # Too short

        assert request.is_valid() is False
        errors = request.validate()
        assert any("at least 2 characters" in error for error in errors)


class TestAuthTokens:
    """Test cases for AuthTokens model."""

    def test_auth_tokens_creation(self):
        """Test creating auth tokens."""
        tokens = AuthTokens(
            access_token="access-token",
            id_token="id-token",
            refresh_token="refresh-token",
            expires_in=3600,
        )

        assert tokens.access_token == "access-token"
        assert tokens.id_token == "id-token"
        assert tokens.refresh_token == "refresh-token"
        assert tokens.expires_in == 3600
        assert tokens.token_type == "Bearer"

    def test_auth_tokens_to_dict(self):
        """Test converting auth tokens to dictionary."""
        tokens = AuthTokens(
            access_token="access-token",
            id_token="id-token",
            refresh_token="refresh-token",
            expires_in=3600,
        )

        tokens_dict = tokens.to_dict()

        assert tokens_dict["access_token"] == "access-token"
        assert tokens_dict["id_token"] == "id-token"
        assert tokens_dict["refresh_token"] == "refresh-token"
        assert tokens_dict["expires_in"] == 3600
        assert tokens_dict["token_type"] == "Bearer"


class TestUserSession:
    """Test cases for UserSession model."""

    def test_user_session_creation(self):
        """Test creating user session."""
        user = User(
            user_id="test-user-id",
            employee_id="EMP001",
            email="test@example.com",
            name="Test User",
            department="Engineering",
            role="veteran",
        )

        tokens = AuthTokens(
            access_token="access-token",
            id_token="id-token",
            refresh_token="refresh-token",
            expires_in=3600,
        )

        session = UserSession(user=user, tokens=tokens)

        assert session.user == user
        assert session.tokens == tokens
        assert session.login_time is not None

    def test_user_session_to_dict(self):
        """Test converting user session to dictionary."""
        user = User(
            user_id="test-user-id",
            employee_id="EMP001",
            email="test@example.com",
            name="Test User",
            department="Engineering",
            role="veteran",
        )

        tokens = AuthTokens(
            access_token="access-token",
            id_token="id-token",
            refresh_token="refresh-token",
            expires_in=3600,
        )

        session = UserSession(user=user, tokens=tokens)
        session_dict = session.to_dict()

        assert "user" in session_dict
        assert "tokens" in session_dict
        assert "login_time" in session_dict
        assert session_dict["user"]["user_id"] == "test-user-id"


class TestSecurityAuditLog:
    """Test cases for SecurityAuditLog model."""

    def test_security_audit_log_creation(self):
        """Test creating security audit log."""
        log = SecurityAuditLog(
            timestamp="2023-01-01T00:00:00Z",
            event_type="login_attempt",
            user_id="test-user-id",
            resource="auth",
            details={"ip": "192.168.1.1"},
        )

        assert log.timestamp == "2023-01-01T00:00:00Z"
        assert log.event_type == "login_attempt"
        assert log.user_id == "test-user-id"
        assert log.resource == "auth"
        assert log.details == {"ip": "192.168.1.1"}
        assert log.source == "auth_system"

    def test_security_audit_log_to_dict(self):
        """Test converting security audit log to dictionary."""
        log = SecurityAuditLog(
            timestamp="2023-01-01T00:00:00Z",
            event_type="login_attempt",
            user_id="test-user-id",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        log_dict = log.to_dict()

        assert log_dict["timestamp"] == "2023-01-01T00:00:00Z"
        assert log_dict["event_type"] == "login_attempt"
        assert log_dict["user_id"] == "test-user-id"
        assert log_dict["ip_address"] == "192.168.1.1"
        assert log_dict["user_agent"] == "Mozilla/5.0"
        assert log_dict["source"] == "auth_system"
