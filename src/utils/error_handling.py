"""
Standardized error handling utilities for Lambda handlers.
Provides consistent error responses with appropriate HTTP status codes and logging.
"""

import json
import logging
import traceback
from enum import Enum
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """Standard error types with corresponding HTTP status codes."""
    
    # Authentication errors (401)
    MISSING_AUTH = ("missing_authorization", 401, "Missing authorization token")
    INVALID_AUTH = ("invalid_authorization", 401, "Invalid authorization token")
    EXPIRED_TOKEN = ("expired_token", 401, "Authorization token has expired")
    AUTH_REQUIRED = ("authentication_required", 401, "Authentication required")
    
    # Authorization errors (403)
    ACCESS_DENIED = ("access_denied", 403, "Access denied")
    INSUFFICIENT_PERMISSIONS = ("insufficient_permissions", 403, "Insufficient permissions")
    FORBIDDEN = ("forbidden", 403, "Forbidden")
    
    # Validation errors (400)
    INVALID_JSON = ("invalid_json", 400, "Invalid JSON in request body")
    MISSING_FIELD = ("missing_field", 400, "Missing required field")
    INVALID_FIELD = ("invalid_field", 400, "Invalid field value")
    VALIDATION_FAILED = ("validation_failed", 400, "Validation failed")
    INVALID_REQUEST = ("invalid_request", 400, "Invalid request")
    
    # Not found errors (404)
    NOT_FOUND = ("not_found", 404, "Resource not found")
    PROFILE_NOT_FOUND = ("profile_not_found", 404, "Profile not found")
    USER_NOT_FOUND = ("user_not_found", 404, "User not found")
    
    # Conflict errors (409)
    ALREADY_EXISTS = ("already_exists", 409, "Resource already exists")
    CONFLICT = ("conflict", 409, "Conflict")
    
    # Rate limiting (429)
    RATE_LIMIT = ("rate_limit_exceeded", 429, "Rate limit exceeded")
    
    # Server errors (500)
    INTERNAL_ERROR = ("internal_server_error", 500, "Internal server error")
    DATABASE_ERROR = ("database_error", 500, "Database operation failed")
    SERVICE_ERROR = ("service_error", 500, "External service error")


def create_error_response(
    error_type: ErrorType,
    message: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    log_error: bool = True,
    include_trace: bool = False
) -> Dict[str, Any]:
    """
    Create a standardized error response.
    
    Args:
        error_type: The type of error from ErrorType enum
        message: Optional custom error message (overrides default)
        details: Optional additional error details
        log_error: Whether to log the error
        include_trace: Whether to include stack trace in response (dev only)
        
    Returns:
        Dict containing standardized HTTP response
    """
    error_code, status_code, default_message = error_type.value
    error_message = message or default_message
    
    # Build error response body
    error_body = {
        "error": error_message,
        "error_code": error_code
    }
    
    if details:
        error_body["details"] = details
    
    if include_trace:
        error_body["trace"] = traceback.format_exc()
    
    # Log the error
    if log_error:
        log_message = f"Error {status_code} ({error_code}): {error_message}"
        if details:
            log_message += f" | Details: {json.dumps(details)}"
        
        if status_code >= 500:
            logger.error(log_message, exc_info=True)
        elif status_code >= 400:
            logger.warning(log_message)
        else:
            logger.info(log_message)
    
    return create_response(status_code, error_body)


def create_response(
    status_code: int,
    body: Dict[str, Any],
    headers: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Create a standardized HTTP response with CORS headers.
    
    Args:
        status_code: HTTP status code
        body: Response body dictionary
        headers: Optional additional headers
        
    Returns:
        Dict containing HTTP response
    """
    default_headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
    }
    
    if headers:
        default_headers.update(headers)
    
    return {
        "statusCode": status_code,
        "headers": default_headers,
        "body": json.dumps(body, default=str)
    }


def create_success_response(
    data: Dict[str, Any],
    status_code: int = 200,
    message: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a standardized success response.
    
    Args:
        data: Response data dictionary
        status_code: HTTP status code (default 200)
        message: Optional success message
        
    Returns:
        Dict containing HTTP response
    """
    body = data.copy()
    if message:
        body["message"] = message
    
    return create_response(status_code, body)


def handle_exception(
    exception: Exception,
    context: Optional[str] = None,
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Handle an unexpected exception and return appropriate error response.
    
    Args:
        exception: The exception that occurred
        context: Optional context description (e.g., "creating profile")
        user_id: Optional user ID for logging
        
    Returns:
        Dict containing HTTP error response
    """
    # Build error context for logging
    error_context = []
    if context:
        error_context.append(f"Context: {context}")
    if user_id:
        error_context.append(f"User: {user_id}")
    
    context_str = " | ".join(error_context) if error_context else ""
    
    # Log the full exception with stack trace
    logger.error(
        f"Unhandled exception: {str(exception)} {context_str}",
        exc_info=True
    )
    
    # Return generic error response (don't expose internal details)
    return create_error_response(
        ErrorType.INTERNAL_ERROR,
        message="An unexpected error occurred",
        log_error=False  # Already logged above
    )


def validate_required_fields(
    data: Dict[str, Any],
    required_fields: list[str]
) -> Optional[Dict[str, Any]]:
    """
    Validate that required fields are present in data.
    
    Args:
        data: Data dictionary to validate
        required_fields: List of required field names
        
    Returns:
        Error response if validation fails, None if validation passes
    """
    missing_fields = [field for field in required_fields if not data.get(field)]
    
    if missing_fields:
        return create_error_response(
            ErrorType.MISSING_FIELD,
            message=f"Missing required fields: {', '.join(missing_fields)}",
            details={"missing_fields": missing_fields}
        )
    
    return None


def parse_json_body(event: Dict[str, Any]) -> tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """
    Parse JSON body from Lambda event.
    
    Args:
        event: Lambda event dictionary
        
    Returns:
        Tuple of (parsed_body, error_response)
        If parsing succeeds: (body_dict, None)
        If parsing fails: (None, error_response_dict)
    """
    try:
        body = event.get("body", "{}")
        if isinstance(body, str):
            parsed_body = json.loads(body) if body else {}
        else:
            parsed_body = body
        
        return parsed_body, None
    
    except json.JSONDecodeError as e:
        logger.warning(f"JSON decode error: {str(e)}")
        error_response = create_error_response(
            ErrorType.INVALID_JSON,
            details={"parse_error": str(e)}
        )
        return None, error_response
