"""
User data models and validation for the veteran talent matching system.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class UserRole(Enum):
    """User roles in the system."""

    VETERAN = "veteran"
    ADMIN = "admin"
    EXTERNAL_RECRUITER = "external_recruiter"


@dataclass
class User:
    """
    User model representing a user in the system.
    """

    user_id: str
    employee_id: str
    email: str
    name: str
    department: str
    role: str
    is_active: bool = True
    join_date: Optional[str] = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def __post_init__(self):
        """Validate user data after initialization."""
        self.validate()

    def validate(self) -> None:
        """Validate user data."""
        if not self.user_id:
            raise ValueError("User ID is required")

        if not self.employee_id:
            raise ValueError("Employee ID is required")

        if not self.email or not self._is_valid_email(self.email):
            raise ValueError("Valid email is required")

        if not self.name or len(self.name.strip()) < 2:
            raise ValueError("Name must be at least 2 characters")

        if not self.department:
            raise ValueError("Department is required")

        if self.role not in [role.value for role in UserRole]:
            raise ValueError(
                f"Invalid role. Must be one of: {[role.value for role in UserRole]}"
            )

    def _is_valid_email(self, email: str) -> bool:
        """Validate email format."""
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return re.match(pattern, email) is not None

    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary."""
        return {
            "user_id": self.user_id,
            "employee_id": self.employee_id,
            "email": self.email,
            "name": self.name,
            "department": self.department,
            "role": self.role,
            "is_active": self.is_active,
            "join_date": self.join_date,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def to_dynamodb_item(self) -> Dict[str, Any]:
        """Convert to DynamoDB item format."""
        return {
            "user_id": self.user_id,
            "employee_id": self.employee_id,
            "email": self.email,
            "name": self.name,
            "department": self.department,
            "role": self.role,
            "is_active": self.is_active,
            "join_date": self.join_date or "",
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "User":
        """Create user from dictionary."""
        return cls(
            user_id=data["user_id"],
            employee_id=data["employee_id"],
            email=data["email"],
            name=data["name"],
            department=data["department"],
            role=data["role"],
            is_active=data.get("is_active", True),
            join_date=data.get("join_date"),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            updated_at=data.get("updated_at", datetime.now(timezone.utc).isoformat()),
        )

    @classmethod
    def from_dynamodb_item(cls, item: Dict[str, Any]) -> "User":
        """Create user from DynamoDB item."""
        return cls(
            user_id=item["user_id"],
            employee_id=item["employee_id"],
            email=item["email"],
            name=item["name"],
            department=item["department"],
            role=item["role"],
            is_active=item.get("is_active", True),
            join_date=item.get("join_date") if item.get("join_date") else None,
            created_at=item.get("created_at", datetime.now(timezone.utc).isoformat()),
            updated_at=item.get("updated_at", datetime.now(timezone.utc).isoformat()),
        )

    def is_veteran(self) -> bool:
        """Check if user is a veteran."""
        return self.role == UserRole.VETERAN.value

    def is_admin(self) -> bool:
        """Check if user is an admin."""
        return self.role == UserRole.ADMIN.value

    def is_external_recruiter(self) -> bool:
        """Check if user is an external recruiter."""
        return self.role == UserRole.EXTERNAL_RECRUITER.value

    def can_access_profile(self, profile_user_id: str) -> bool:
        """Check if user can access a specific profile."""
        # Users can access their own profile
        if self.user_id == profile_user_id:
            return True

        # Admins can access any profile
        if self.is_admin():
            return True

        # External recruiters need additional checks for public profiles
        return False

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.now(timezone.utc).isoformat()


@dataclass
class UserRegistrationRequest:
    """
    Data model for user registration requests.
    """

    email: str
    password: str
    name: str
    employee_id: str
    department: str
    role: str = UserRole.VETERAN.value

    def validate(self) -> List[str]:
        """Validate registration request and return list of errors."""
        errors = []

        if not self.email or not self._is_valid_email(self.email):
            errors.append("Valid email is required")

        if not self.password:
            errors.append("Password is required")
        elif len(self.password) < 8:
            errors.append("Password must be at least 8 characters")

        if not self.name or len(self.name.strip()) < 2:
            errors.append("Name must be at least 2 characters")

        if not self.employee_id:
            errors.append("Employee ID is required")

        if not self.department:
            errors.append("Department is required")

        if self.role not in [role.value for role in UserRole]:
            errors.append(
                f"Invalid role. Must be one of: {[role.value for role in UserRole]}"
            )

        return errors

    def _is_valid_email(self, email: str) -> bool:
        """Validate email format."""
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return re.match(pattern, email) is not None

    def is_valid(self) -> bool:
        """Check if registration request is valid."""
        return len(self.validate()) == 0


@dataclass
class UserLoginRequest:
    """
    Data model for user login requests.
    """

    email: str
    password: str

    def validate(self) -> List[str]:
        """Validate login request and return list of errors."""
        errors = []

        if not self.email:
            errors.append("Email is required")

        if not self.password:
            errors.append("Password is required")

        return errors

    def is_valid(self) -> bool:
        """Check if login request is valid."""
        return len(self.validate()) == 0


@dataclass
class UserUpdateRequest:
    """
    Data model for user profile update requests.
    """

    name: Optional[str] = None
    department: Optional[str] = None

    def validate(self) -> List[str]:
        """Validate update request and return list of errors."""
        errors = []

        if self.name is not None and len(self.name.strip()) < 2:
            errors.append("Name must be at least 2 characters")

        return errors

    def is_valid(self) -> bool:
        """Check if update request is valid."""
        return len(self.validate()) == 0

    def has_updates(self) -> bool:
        """Check if request contains any updates."""
        return self.name is not None or self.department is not None


@dataclass
class AuthTokens:
    """
    Data model for authentication tokens.
    """

    access_token: str
    id_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "Bearer"

    def to_dict(self) -> Dict[str, Any]:
        """Convert tokens to dictionary."""
        return {
            "access_token": self.access_token,
            "id_token": self.id_token,
            "refresh_token": self.refresh_token,
            "expires_in": self.expires_in,
            "token_type": self.token_type,
        }


@dataclass
class UserSession:
    """
    Data model for user session information.
    """

    user: User
    tokens: AuthTokens
    login_time: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary."""
        return {
            "user": self.user.to_dict(),
            "tokens": self.tokens.to_dict(),
            "login_time": self.login_time,
        }


@dataclass
class SecurityAuditLog:
    """
    Data model for security audit logs.
    """

    timestamp: str
    event_type: str
    user_id: str
    resource: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    source: str = "auth_system"
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert audit log to dictionary."""
        return {
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "user_id": self.user_id,
            "resource": self.resource,
            "details": self.details,
            "source": self.source,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
        }
