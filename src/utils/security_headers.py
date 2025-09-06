"""
Security headers and middleware for API responses.
Implements security best practices for web applications.
"""

from typing import Dict, Any, Optional
import json
import logging

logger = logging.getLogger(__name__)


class SecurityHeaders:
    """Security headers configuration and utilities."""
    
    # Security headers for API responses
    DEFAULT_HEADERS = {
        # Prevent XSS attacks
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        
        # HTTPS enforcement
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains; preload',
        
        # Content Security Policy
        'Content-Security-Policy': (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https://*.amazonaws.com; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        ),
        
        # Referrer policy
        'Referrer-Policy': 'strict-origin-when-cross-origin',
        
        # Permissions policy
        'Permissions-Policy': (
            'geolocation=(), microphone=(), camera=(), '
            'payment=(), usb=(), magnetometer=(), gyroscope=()'
        ),
        
        # Cache control for sensitive data
        'Cache-Control': 'no-store, no-cache, must-revalidate, private',
        'Pragma': 'no-cache',
        'Expires': '0'
    }
    
    # CORS headers for API
    CORS_HEADERS = {
        'Access-Control-Allow-Origin': '*',  # Will be overridden with specific origins
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': (
            'Content-Type, Authorization, X-Requested-With, '
            'X-API-Key, X-User-Role, X-Request-ID'
        ),
        'Access-Control-Max-Age': '86400'  # 24 hours
    }
    
    @classmethod
    def get_security_headers(cls, include_cors: bool = True) -> Dict[str, str]:
        """Get all security headers."""
        headers = cls.DEFAULT_HEADERS.copy()
        
        if include_cors:
            headers.update(cls.CORS_HEADERS)
        
        return headers
    
    @classmethod
    def get_cors_headers(cls, origin: Optional[str] = None) -> Dict[str, str]:
        """Get CORS headers with specific origin."""
        headers = cls.CORS_HEADERS.copy()
        
        if origin:
            # Validate origin against allowed origins
            allowed_origins = [
                'https://honda-veteran-bank.com',
                'https://www.honda-veteran-bank.com',
                'https://dev.honda-veteran-bank.com',
                'http://localhost:3000',  # Development
                'http://localhost:3001'   # Development
            ]
            
            if origin in allowed_origins:
                headers['Access-Control-Allow-Origin'] = origin
            else:
                headers['Access-Control-Allow-Origin'] = 'null'
        
        return headers
    
    @classmethod
    def add_security_headers(cls, response: Dict[str, Any], 
                           origin: Optional[str] = None) -> Dict[str, Any]:
        """Add security headers to Lambda response."""
        if 'headers' not in response:
            response['headers'] = {}
        
        # Add security headers
        security_headers = cls.get_security_headers(include_cors=False)
        response['headers'].update(security_headers)
        
        # Add CORS headers
        cors_headers = cls.get_cors_headers(origin)
        response['headers'].update(cors_headers)
        
        return response


def create_secure_response(status_code: int, body: Any, 
                         headers: Optional[Dict[str, str]] = None,
                         origin: Optional[str] = None) -> Dict[str, Any]:
    """Create a secure API response with proper headers."""
    response = {
        'statusCode': status_code,
        'headers': headers or {},
        'body': json.dumps(body) if not isinstance(body, str) else body
    }
    
    # Add security headers
    response = SecurityHeaders.add_security_headers(response, origin)
    
    return response


def create_error_response(status_code: int, error_message: str, 
                         error_code: Optional[str] = None,
                         details: Optional[Any] = None,
                         origin: Optional[str] = None) -> Dict[str, Any]:
    """Create a secure error response."""
    error_body = {
        'error': {
            'code': error_code or 'UNKNOWN_ERROR',
            'message': error_message,
            'timestamp': str(int(time.time())),
            'requestId': str(uuid.uuid4())
        }
    }
    
    if details and not is_production():
        error_body['error']['details'] = details
    
    return create_secure_response(status_code, error_body, origin=origin)


def sanitize_input(data: Any) -> Any:
    """Sanitize input data to prevent injection attacks."""
    if isinstance(data, str):
        # Remove potentially dangerous characters
        dangerous_chars = ['<', '>', '"', "'", '&', '\x00', '\n', '\r']
        sanitized = data
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, '')
        return sanitized.strip()
    
    elif isinstance(data, dict):
        return {key: sanitize_input(value) for key, value in data.items()}
    
    elif isinstance(data, list):
        return [sanitize_input(item) for item in data]
    
    return data


def validate_content_type(event: Dict[str, Any]) -> bool:
    """Validate request content type."""
    headers = event.get('headers', {})
    content_type = headers.get('Content-Type', '').lower()
    
    allowed_types = [
        'application/json',
        'application/x-www-form-urlencoded',
        'multipart/form-data'
    ]
    
    return any(allowed_type in content_type for allowed_type in allowed_types)


def is_production() -> bool:
    """Check if running in production environment."""
    import os
    return os.environ.get('ENVIRONMENT', 'dev').lower() == 'production'


# Rate limiting utilities
class RateLimiter:
    """Simple rate limiting implementation."""
    
    def __init__(self):
        self.requests = {}
    
    def is_rate_limited(self, identifier: str, limit: int = 100, 
                       window: int = 3600) -> bool:
        """Check if request should be rate limited."""
        import time
        
        current_time = int(time.time())
        window_start = current_time - window
        
        if identifier not in self.requests:
            self.requests[identifier] = []
        
        # Clean old requests
        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier] 
            if req_time > window_start
        ]
        
        # Check if limit exceeded
        if len(self.requests[identifier]) >= limit:
            return True
        
        # Add current request
        self.requests[identifier].append(current_time)
        return False


# Global rate limiter instance
rate_limiter = RateLimiter()


# Security middleware decorator
def security_middleware(func):
    """Decorator to add security middleware to Lambda functions."""
    import functools
    import time
    import uuid
    
    @functools.wraps(func)
    def wrapper(event, context):
        try:
            # Extract origin for CORS
            origin = event.get('headers', {}).get('Origin')
            
            # Validate content type for POST/PUT requests
            http_method = event.get('httpMethod', '').upper()
            if http_method in ['POST', 'PUT'] and not validate_content_type(event):
                return create_error_response(
                    400, 'Invalid content type', 'INVALID_CONTENT_TYPE', origin=origin
                )
            
            # Rate limiting
            client_ip = event.get('requestContext', {}).get('identity', {}).get('sourceIp', 'unknown')
            if rate_limiter.is_rate_limited(client_ip):
                return create_error_response(
                    429, 'Rate limit exceeded', 'RATE_LIMIT_EXCEEDED', origin=origin
                )
            
            # Sanitize input
            if 'body' in event and event['body']:
                try:
                    body = json.loads(event['body'])
                    event['body'] = json.dumps(sanitize_input(body))
                except json.JSONDecodeError:
                    pass  # Not JSON, skip sanitization
            
            # Call the original function
            response = func(event, context)
            
            # Ensure response has security headers
            if isinstance(response, dict) and 'statusCode' in response:
                response = SecurityHeaders.add_security_headers(response, origin)
            
            return response
            
        except Exception as e:
            logger.error(f"Security middleware error: {e}")
            return create_error_response(
                500, 'Internal server error', 'SECURITY_ERROR', origin=origin
            )
    
    return wrapper