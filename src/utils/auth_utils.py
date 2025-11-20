"""
Authentication utilities for JWT token validation and user management.
"""

import logging
import os
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Dict, List, Optional

import boto3
import requests

logger = logging.getLogger()

# Initialize AWS clients
cognito_client = boto3.client("cognito-idp")

# Environment variables
USER_POOL_ID = os.environ.get("COGNITO_USER_POOL_ID")
REGION = os.environ.get("REGION", "us-west-2")

# Cache for JWKS
_jwks_cache = None


def get_jwks() -> Dict[str, Any]:
    """
    Get JSON Web Key Set (JWKS) from Cognito.
    """
    global _jwks_cache

    if _jwks_cache is None:
        jwks_url = f"https://cognito-idp.{REGION}.amazonaws.com/{USER_POOL_ID}/.well-known/jwks.json"
        response = requests.get(jwks_url, timeout=10)
        response.raise_for_status()
        _jwks_cache = response.json()

    return _jwks_cache


def verify_jwt_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify JWT token signature and return decoded claims.
    Note: This function requires python-jose[cryptography] which may not be available.
    Prefer using extract_user_from_event() with API Gateway Cognito Authorizer instead.
    """
    try:
        # Lazy import to avoid cryptography dependency at module load time
        from jose import jwt as jose_jwt
        
        # Get JWKS
        jwks = get_jwks()

        # Decode header to get key ID
        unverified_header = jose_jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")

        if not kid:
            logger.error("No 'kid' found in token header")
            return None

        # Find the correct key
        key = None
        for jwk in jwks["keys"]:
            if jwk["kid"] == kid:
                key = jwk
                break

        if not key:
            logger.error(f"Unable to find key with kid: {kid}")
            return None

        # Verify and decode token using python-jose
        decoded_token = jose_jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=os.environ.get("COGNITO_CLIENT_ID"),
            issuer=f"https://cognito-idp.{REGION}.amazonaws.com/{USER_POOL_ID}",
        )

        # Normalize the token data for easier use
        return {
            "user_id": decoded_token.get("username") or decoded_token.get("sub"),
            "email": decoded_token.get("email"),
            "name": decoded_token.get("name"),
            "role": decoded_token.get("custom:role"),
            "department": decoded_token.get("custom:department"),
            "employee_id": decoded_token.get("custom:employee_id"),
            "raw_claims": decoded_token,  # Keep original claims for reference
        }

    except ImportError:
        logger.error("python-jose not available - use API Gateway Cognito Authorizer instead")
        return None
    except Exception as e:
        logger.error(f"Token verification error: {str(e)}")
        return None


def get_user_from_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Extract user information from JWT token.

    Args:
        token: JWT token string

    Returns:
        User information dictionary or None if invalid
    """
    decoded = verify_jwt_token(token)

    if decoded:
        return {
            "user_id": decoded.get("username") or decoded.get("sub"),
            "email": decoded.get("email"),
            "name": decoded.get("name"),
            "role": decoded.get("custom:role"),
            "department": decoded.get("custom:department"),
            "employee_id": decoded.get("custom:employee_id"),
        }

    return None


def extract_user_from_event(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Extract user information from Lambda event (API Gateway authorizer context).
    """
    # Get from request context (API Gateway Cognito authorizer)
    request_context = event.get("requestContext", {})
    authorizer = request_context.get("authorizer", {})

    if "claims" in authorizer:
        claims = authorizer["claims"]
        # デフォルトでveteranロールを設定（custom:roleが未設定の場合）
        role = claims.get("custom:role") or "veteran"
        
        return {
            "user_id": claims.get("username") or claims.get("sub"),
            "email": claims.get("email"),
            "name": claims.get("name"),
            "role": role,
            "department": claims.get("custom:department") or "未設定",
            "employee_id": claims.get("custom:employee_id") or claims.get("email"),
        }

    return None


def require_auth(roles: Optional[List[str]] = None):
    """
    Decorator to require authentication and optionally specific roles.

    Args:
        roles: List of allowed roles. If None, any authenticated user is allowed.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(event, context):
            user = extract_user_from_event(event)

            if not user:
                return {
                    "statusCode": 401,
                    "headers": {
                        "Content-Type": "application/json",
                        "Access-Control-Allow-Origin": "*",
                    },
                    "body": '{"error": "Authentication required"}',
                }

            # Check role if specified
            if roles and user.get("role") not in roles:
                return {
                    "statusCode": 403,
                    "headers": {
                        "Content-Type": "application/json",
                        "Access-Control-Allow-Origin": "*",
                    },
                    "body": '{"error": "Insufficient permissions"}',
                }

            # Add user to event for use in handler
            event["user"] = user

            return func(event, context)

        return wrapper

    return decorator


def require_role(*allowed_roles: str):
    """
    Decorator to require specific roles.

    Args:
        allowed_roles: Variable number of allowed role strings
    """
    return require_auth(list(allowed_roles))


def is_admin(user: Dict[str, Any]) -> bool:
    """
    Check if user has admin role.
    """
    return user.get("role") == "admin"


def is_veteran(user: Dict[str, Any]) -> bool:
    """
    Check if user has veteran role.
    """
    return user.get("role") == "veteran"


def is_external_recruiter(user: Dict[str, Any]) -> bool:
    """
    Check if user has external recruiter role.
    """
    return user.get("role") == "external_recruiter"


def can_access_profile(user: Dict[str, Any], profile_user_id: str) -> bool:
    """
    Check if user can access a specific profile.

    Rules:
    - Users can access their own profile
    - Admins can access any profile
    - External recruiters can only access publicly visible profiles
    """
    if user.get("user_id") == profile_user_id:
        return True

    if is_admin(user):
        return True

    # For external recruiters, additional checks would be needed
    # to verify if the profile is publicly visible
    return False


def log_security_event(event_type: str, user_id: str, details: Dict[str, Any] = None):
    """
    Log security-related events for audit purposes.
    """
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "user_id": user_id,
        "details": details or {},
    }

    logger.info(f"SECURITY_EVENT: {log_entry}")


def validate_password_strength(password: str) -> Dict[str, Any]:
    """
    Validate password strength according to security requirements.
    """
    errors = []

    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")

    if not any(c.isupper() for c in password):
        errors.append("Password must contain at least one uppercase letter")

    if not any(c.islower() for c in password):
        errors.append("Password must contain at least one lowercase letter")

    if not any(c.isdigit() for c in password):
        errors.append("Password must contain at least one number")

    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        errors.append("Password must contain at least one special character")

    return {"valid": len(errors) == 0, "errors": errors}


def create_audit_log(
    action: str, user_id: str, resource: str = None, details: Dict[str, Any] = None
) -> None:
    """
    Create audit log entry for compliance and security monitoring.
    """
    audit_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "user_id": user_id,
        "resource": resource,
        "details": details or {},
        "source": "auth_system",
    }

    # In a production system, this would be sent to a centralized logging system
    logger.info(f"AUDIT_LOG: {audit_entry}")


def sanitize_user_data(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove sensitive information from user data before returning to client.
    """
    sensitive_fields = ["password", "refresh_token", "access_token"]

    sanitized = {}
    for key, value in user_data.items():
        if key not in sensitive_fields:
            sanitized[key] = value

    return sanitized
