"""
Unit tests for security headers utilities.
"""

import pytest
import json
from unittest.mock import Mock, patch
from src.utils.security_headers import (
    SecurityHeaders, create_secure_response, create_error_response,
    sanitize_input, validate_content_type, RateLimiter, security_middleware
)


class TestSecurityHeaders:
    """Test security headers functionality."""
    
    def test_get_security_headers(self):
        """Test getting security headers."""
        headers = SecurityHeaders.get_security_headers()
        
        # Check required security headers
        assert 'X-Content-Type-Options' in headers
        assert 'X-Frame-Options' in headers
        assert 'X-XSS-Protection' in headers
        assert 'Strict-Transport-Security' in headers
        assert 'Content-Security-Policy' in headers
        assert 'Referrer-Policy' in headers
        
        # Check CORS headers are included by default
        assert 'Access-Control-Allow-Origin' in headers
        assert 'Access-Control-Allow-Methods' in headers
    
    def test_get_cors_headers_with_allowed_origin(self):
        """Test CORS headers with allowed origin."""
        allowed_origin = 'https://honda-veteran-bank.com'
        headers = SecurityHeaders.get_cors_headers(allowed_origin)
        
        assert headers['Access-Control-Allow-Origin'] == allowed_origin
    
    def test_get_cors_headers_with_disallowed_origin(self):
        """Test CORS headers with disallowed origin."""
        disallowed_origin = 'https://malicious-site.com'
        headers = SecurityHeaders.get_cors_headers(disallowed_origin)
        
        assert headers['Access-Control-Allow-Origin'] == 'null'
    
    def test_add_security_headers(self):
        """Test adding security headers to response."""
        response = {
            'statusCode': 200,
            'body': 'test body'
        }
        
        updated_response = SecurityHeaders.add_security_headers(response)
        
        assert 'headers' in updated_response
        assert 'X-Content-Type-Options' in updated_response['headers']
        assert 'Access-Control-Allow-Origin' in updated_response['headers']


class TestSecureResponse:
    """Test secure response creation."""
    
    def test_create_secure_response(self):
        """Test creating secure response."""
        body = {'message': 'success'}
        response = create_secure_response(200, body)
        
        assert response['statusCode'] == 200
        assert 'headers' in response
        assert 'X-Content-Type-Options' in response['headers']
        
        # Body should be JSON string
        parsed_body = json.loads(response['body'])
        assert parsed_body == body
    
    def test_create_error_response(self):
        """Test creating error response."""
        response = create_error_response(400, 'Bad request', 'INVALID_INPUT')
        
        assert response['statusCode'] == 400
        assert 'headers' in response
        
        body = json.loads(response['body'])
        assert 'error' in body
        assert body['error']['code'] == 'INVALID_INPUT'
        assert body['error']['message'] == 'Bad request'
        assert 'timestamp' in body['error']
        assert 'requestId' in body['error']


class TestInputSanitization:
    """Test input sanitization functionality."""
    
    def test_sanitize_string(self):
        """Test string sanitization."""
        dangerous_input = "<script>alert('xss')</script>"
        sanitized = sanitize_input(dangerous_input)
        
        assert '<' not in sanitized
        assert '>' not in sanitized
        assert 'script' in sanitized  # Content remains, just tags removed
    
    def test_sanitize_dict(self):
        """Test dictionary sanitization."""
        dangerous_dict = {
            'name': 'John<script>',
            'email': 'test@example.com',
            'nested': {
                'value': 'safe"value'
            }
        }
        
        sanitized = sanitize_input(dangerous_dict)
        
        assert '<' not in sanitized['name']
        assert 'script' in sanitized['name']
        assert sanitized['email'] == 'test@example.com'  # Safe input unchanged
        assert '"' not in sanitized['nested']['value']
    
    def test_sanitize_list(self):
        """Test list sanitization."""
        dangerous_list = ['safe', '<script>', 'also&safe']
        sanitized = sanitize_input(dangerous_list)
        
        assert sanitized[0] == 'safe'
        assert '<' not in sanitized[1]
        assert '&' not in sanitized[2]
    
    def test_sanitize_non_string(self):
        """Test sanitization of non-string types."""
        assert sanitize_input(123) == 123
        assert sanitize_input(True) is True
        assert sanitize_input(None) is None


class TestContentTypeValidation:
    """Test content type validation."""
    
    def test_valid_content_types(self):
        """Test valid content types."""
        valid_events = [
            {'headers': {'Content-Type': 'application/json'}},
            {'headers': {'Content-Type': 'application/x-www-form-urlencoded'}},
            {'headers': {'Content-Type': 'multipart/form-data; boundary=something'}}
        ]
        
        for event in valid_events:
            assert validate_content_type(event) is True
    
    def test_invalid_content_types(self):
        """Test invalid content types."""
        invalid_events = [
            {'headers': {'Content-Type': 'text/html'}},
            {'headers': {'Content-Type': 'application/xml'}},
            {'headers': {}}  # No content type
        ]
        
        for event in invalid_events:
            assert validate_content_type(event) is False


class TestRateLimiter:
    """Test rate limiting functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.rate_limiter = RateLimiter()
    
    @patch('time.time')
    def test_rate_limiting_within_limit(self, mock_time):
        """Test rate limiting within allowed limit."""
        mock_time.return_value = 1000
        
        # Make requests within limit
        for i in range(5):
            assert self.rate_limiter.is_rate_limited('user1', limit=10) is False
    
    @patch('time.time')
    def test_rate_limiting_exceeds_limit(self, mock_time):
        """Test rate limiting when limit is exceeded."""
        mock_time.return_value = 1000
        
        # Make requests up to limit
        for i in range(10):
            self.rate_limiter.is_rate_limited('user1', limit=10)
        
        # Next request should be rate limited
        assert self.rate_limiter.is_rate_limited('user1', limit=10) is True
    
    @patch('time.time')
    def test_rate_limiting_window_reset(self, mock_time):
        """Test rate limiting window reset."""
        # Start at time 1000
        mock_time.return_value = 1000
        
        # Make requests up to limit
        for i in range(10):
            self.rate_limiter.is_rate_limited('user1', limit=10, window=3600)
        
        # Should be rate limited
        assert self.rate_limiter.is_rate_limited('user1', limit=10, window=3600) is True
        
        # Move time forward past window
        mock_time.return_value = 5000  # 1 hour + 400 seconds later
        
        # Should not be rate limited anymore
        assert self.rate_limiter.is_rate_limited('user1', limit=10, window=3600) is False


class TestSecurityMiddleware:
    """Test security middleware functionality."""
    
    def test_security_middleware_decorator(self):
        """Test security middleware decorator."""
        @security_middleware
        def test_handler(event, context):
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'success'})
            }
        
        event = {
            'httpMethod': 'GET',
            'headers': {'Origin': 'https://honda-veteran-bank.com'},
            'requestContext': {'identity': {'sourceIp': '127.0.0.1'}}
        }
        context = {}
        
        response = test_handler(event, context)
        
        assert response['statusCode'] == 200
        assert 'headers' in response
        assert 'X-Content-Type-Options' in response['headers']
    
    def test_security_middleware_invalid_content_type(self):
        """Test security middleware with invalid content type."""
        @security_middleware
        def test_handler(event, context):
            return {'statusCode': 200, 'body': 'success'}
        
        event = {
            'httpMethod': 'POST',
            'headers': {'Content-Type': 'text/html'},
            'requestContext': {'identity': {'sourceIp': '127.0.0.1'}}
        }
        context = {}
        
        response = test_handler(event, context)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'INVALID_CONTENT_TYPE'
    
    @patch('src.utils.security_headers.rate_limiter')
    def test_security_middleware_rate_limited(self, mock_rate_limiter):
        """Test security middleware with rate limiting."""
        mock_rate_limiter.is_rate_limited.return_value = True
        
        @security_middleware
        def test_handler(event, context):
            return {'statusCode': 200, 'body': 'success'}
        
        event = {
            'httpMethod': 'GET',
            'headers': {},
            'requestContext': {'identity': {'sourceIp': '127.0.0.1'}}
        }
        context = {}
        
        response = test_handler(event, context)
        
        assert response['statusCode'] == 429
        body = json.loads(response['body'])
        assert body['error']['code'] == 'RATE_LIMIT_EXCEEDED'
    
    def test_security_middleware_sanitizes_input(self):
        """Test security middleware sanitizes input."""
        @security_middleware
        def test_handler(event, context):
            body = json.loads(event['body'])
            return {
                'statusCode': 200,
                'body': json.dumps({'received': body})
            }
        
        event = {
            'httpMethod': 'POST',
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'name': 'John<script>'}),
            'requestContext': {'identity': {'sourceIp': '127.0.0.1'}}
        }
        context = {}
        
        response = test_handler(event, context)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        # Input should be sanitized
        assert '<' not in body['received']['name']


if __name__ == '__main__':
    pytest.main([__file__])