"""
Security configuration and constants for the application.
Centralizes security settings and policies.
"""

import os
from enum import Enum
from typing import Any, Dict, List


class SecurityLevel(Enum):
    """Security levels for different data types."""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class DataClassification:
    """Data classification and handling requirements."""

    # PII fields that require encryption
    PII_FIELDS = {
        "email",
        "phone",
        "address",
        "ssn",
        "employee_id",
        "full_name",
        "birth_date",
        "personal_phone",
        "home_address",
        "emergency_contact",
        "medical_info",
    }

    # Sensitive business fields
    SENSITIVE_FIELDS = {
        "salary",
        "performance_rating",
        "compensation",
        "review_notes",
        "disciplinary_actions",
        "internal_notes",
        "manager_feedback",
    }

    # Fields that can be shown publicly (with anonymization)
    PUBLIC_SAFE_FIELDS = {
        "skills",
        "experience",
        "certifications",
        "business_title",
        "department",
        "years_of_service",
        "specializations",
        "interests",
    }

    # Fields that require audit logging
    AUDIT_REQUIRED_FIELDS = {
        "role",
        "permissions",
        "access_level",
        "privacy_settings",
        "profile_visibility",
        "contact_preferences",
    }


class EncryptionConfig:
    """Encryption configuration settings."""

    # KMS key configuration
    KMS_KEY_ID = os.environ.get("KMS_KEY_ID", "alias/honda-veteran-bank-key")

    # Encryption algorithms
    SYMMETRIC_ALGORITHM = "AES-256-GCM"
    HASH_ALGORITHM = "SHA-256"

    # Key derivation settings
    PBKDF2_ITERATIONS = 100000
    SALT_LENGTH = 32

    # Environment-specific settings
    ENCRYPTION_PASSWORD = os.environ.get("ENCRYPTION_PASSWORD", "dev-encryption-key")
    ENCRYPTION_SALT = os.environ.get("ENCRYPTION_SALT", "dev-salt-value")
    PII_HASH_SALT = os.environ.get("PII_HASH_SALT", "dev-pii-salt")


class SecurityHeaders:
    """Security headers configuration."""

    # Content Security Policy
    CSP_POLICY = {
        "default-src": ["'self'"],
        "script-src": ["'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net"],
        "style-src": ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com"],
        "font-src": ["'self'", "https://fonts.gstatic.com"],
        "img-src": ["'self'", "data:", "https:"],
        "connect-src": ["'self'", "https://*.amazonaws.com"],
        "frame-ancestors": ["'none'"],
        "base-uri": ["'self'"],
        "form-action": ["'self'"],
    }

    # Allowed origins for CORS
    ALLOWED_ORIGINS = [
        "https://honda-veteran-bank.com",
        "https://www.honda-veteran-bank.com",
        "https://dev.honda-veteran-bank.com",
        "http://localhost:3000",  # Development
        "http://localhost:3001",  # Development
    ]

    # Security headers
    SECURITY_HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=(), payment=(), usb=(), magnetometer=(), gyroscope=()",
        "Cache-Control": "no-store, no-cache, must-revalidate, private",
        "Pragma": "no-cache",
        "Expires": "0",
    }


class RateLimitConfig:
    """Rate limiting configuration."""

    # Default rate limits (requests per hour)
    DEFAULT_RATE_LIMIT = 1000

    # Endpoint-specific rate limits
    ENDPOINT_LIMITS = {
        "/auth/login": 10,  # 10 login attempts per hour
        "/auth/register": 5,  # 5 registrations per hour
        "/auth/refresh": 100,  # 100 token refreshes per hour
        "/public/search": 200,  # 200 searches per hour
        "/contact": 20,  # 20 contact requests per hour
    }

    # Rate limit window (seconds)
    RATE_LIMIT_WINDOW = 3600  # 1 hour


class AuditConfig:
    """Security audit configuration."""

    # Events that require audit logging
    AUDIT_EVENTS = {
        "user_login",
        "user_logout",
        "user_registration",
        "profile_update",
        "privacy_change",
        "role_change",
        "data_access",
        "data_export",
        "admin_action",
        "security_violation",
        "rate_limit_exceeded",
    }

    # High-risk events that require immediate alerting
    HIGH_RISK_EVENTS = {
        "multiple_failed_logins",
        "privilege_escalation",
        "data_breach_attempt",
        "unauthorized_access",
        "suspicious_activity",
    }

    # Audit log retention (days)
    AUDIT_RETENTION_DAYS = 2555  # 7 years for compliance


class ValidationConfig:
    """Input validation configuration."""

    # Maximum input lengths
    MAX_LENGTHS = {
        "email": 254,
        "name": 100,
        "title": 200,
        "description": 2000,
        "skill_name": 100,
        "company_name": 200,
        "phone": 20,
        "address": 500,
    }

    # Allowed characters patterns
    PATTERNS = {
        "email": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
        "phone": r"^\+?[\d\s\-\(\)]{10,20}$",
        "name": r"^[a-zA-Z\s\-\'\.]{1,100}$",
        "alphanumeric": r"^[a-zA-Z0-9\s]{1,200}$",
    }

    # Dangerous characters to sanitize
    DANGEROUS_CHARS = ["<", ">", '"', "'", "&", "\x00", "\n", "\r", "\t"]


class ComplianceConfig:
    """Compliance and regulatory configuration."""

    # Data retention policies (days)
    DATA_RETENTION = {
        "user_profiles": 2555,  # 7 years
        "audit_logs": 2555,  # 7 years
        "application_data": 1095,  # 3 years
        "session_data": 30,  # 30 days
        "temp_data": 1,  # 1 day
    }

    # GDPR compliance settings
    GDPR_SETTINGS = {
        "data_portability": True,
        "right_to_erasure": True,
        "consent_required": True,
        "purpose_limitation": True,
    }

    # Data processing purposes
    PROCESSING_PURPOSES = {
        "talent_matching": "Matching veterans with suitable opportunities",
        "profile_management": "Managing user profiles and preferences",
        "communication": "Facilitating communication between parties",
        "analytics": "Improving system performance and user experience",
        "compliance": "Meeting legal and regulatory requirements",
    }


def get_security_config() -> Dict[str, Any]:
    """Get complete security configuration."""
    return {
        "encryption": {
            "kms_key_id": EncryptionConfig.KMS_KEY_ID,
            "algorithm": EncryptionConfig.SYMMETRIC_ALGORITHM,
            "pbkdf2_iterations": EncryptionConfig.PBKDF2_ITERATIONS,
        },
        "headers": SecurityHeaders.SECURITY_HEADERS,
        "cors": {"allowed_origins": SecurityHeaders.ALLOWED_ORIGINS},
        "rate_limiting": {
            "default_limit": RateLimitConfig.DEFAULT_RATE_LIMIT,
            "endpoint_limits": RateLimitConfig.ENDPOINT_LIMITS,
            "window": RateLimitConfig.RATE_LIMIT_WINDOW,
        },
        "audit": {
            "events": AuditConfig.AUDIT_EVENTS,
            "high_risk_events": AuditConfig.HIGH_RISK_EVENTS,
            "retention_days": AuditConfig.AUDIT_RETENTION_DAYS,
        },
        "validation": {
            "max_lengths": ValidationConfig.MAX_LENGTHS,
            "patterns": ValidationConfig.PATTERNS,
            "dangerous_chars": ValidationConfig.DANGEROUS_CHARS,
        },
        "compliance": {
            "data_retention": ComplianceConfig.DATA_RETENTION,
            "gdpr_settings": ComplianceConfig.GDPR_SETTINGS,
            "processing_purposes": ComplianceConfig.PROCESSING_PURPOSES,
        },
        "data_classification": {
            "pii_fields": DataClassification.PII_FIELDS,
            "sensitive_fields": DataClassification.SENSITIVE_FIELDS,
            "public_safe_fields": DataClassification.PUBLIC_SAFE_FIELDS,
            "audit_required_fields": DataClassification.AUDIT_REQUIRED_FIELDS,
        },
    }


def is_production() -> bool:
    """Check if running in production environment."""
    return os.environ.get("ENVIRONMENT", "dev").lower() == "production"


def get_environment_config() -> Dict[str, Any]:
    """Get environment-specific security configuration."""
    env = os.environ.get("ENVIRONMENT", "dev").lower()

    if env == "production":
        return {
            "debug_mode": False,
            "detailed_errors": False,
            "rate_limit_strict": True,
            "audit_all_events": True,
            "encryption_required": True,
        }
    elif env == "staging":
        return {
            "debug_mode": False,
            "detailed_errors": True,
            "rate_limit_strict": True,
            "audit_all_events": True,
            "encryption_required": True,
        }
    else:  # development
        return {
            "debug_mode": True,
            "detailed_errors": True,
            "rate_limit_strict": False,
            "audit_all_events": False,
            "encryption_required": False,
        }
