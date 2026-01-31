"""
Unit tests for standardized error handling utilities.
"""

import json
import pytest

from src.utils.error_handling import (
    ErrorType,
    create_error_response,
    create_response,
    create_success_response,
    handle_exception,
    parse_json_body,
    validate_required_fields,
)


class TestErrorHandling:
    """Test error handling utilities."""

    def test_create_error_response_basic(self):
        """Test basic error response creation."""
        response = create_error_response(ErrorType.MISSING_AUTH, log_error=False)
        
        assert response["statusCode"] == 401
        assert "Content-Type" in response["headers"]
        assert response["headers"]["Access-Control-Allow-Origin"] == "*"
        
        body = json.loads(response["body"])
        assert "error" in body
        assert "error_code" in body
        assert body["error_code"] == "missing_authorization"

    def test_create_error_response_with_custom_message(self):
        """Test error response with custom message."""
        custom_message = "Custom error message"
        response = create_error_response(
            ErrorType.VALIDATION_FAILED,
            message=custom_message,
            log_error=False
        )
        
        body = json.loads(response["body"])
        assert body["error"] == custom_message

    def test_create_error_response_with_details(self):
        """Test error response with additional details."""
        details = {"field": "email", "reason": "invalid format"}
        response = create_error_response(
            ErrorType.INVALID_FIELD,
            details=details,
            log_error=False
        )
        
        body = json.loads(response["body"])
        assert "details" in body
        assert body["details"] == details

    def test_all_error_types_have_correct_status_codes(self):
        """Test that all error types return appropriate status codes."""
        # Authentication errors (401)
        for error_type in [ErrorType.MISSING_AUTH, ErrorType.INVALID_AUTH, 
                          ErrorType.EXPIRED_TOKEN, ErrorType.AUTH_REQUIRED]:
            response = create_error_response(error_type, log_error=False)
            assert response["statusCode"] == 401

        # Authorization errors (403)
        for error_type in [ErrorType.ACCESS_DENIED, ErrorType.INSUFFICIENT_PERMISSIONS,
                          ErrorType.FORBIDDEN]:
            response = create_error_response(error_type, log_error=False)
            assert response["statusCode"] == 403

        # Validation errors (400)
        for error_type in [ErrorType.INVALID_JSON, ErrorType.MISSING_FIELD,
                          ErrorType.INVALID_FIELD, ErrorType.VALIDATION_FAILED,
                          ErrorType.INVALID_REQUEST]:
            response = create_error_response(error_type, log_error=False)
            assert response["statusCode"] == 400

        # Not found errors (404)
        for error_type in [ErrorType.NOT_FOUND, ErrorType.PROFILE_NOT_FOUND,
                          ErrorType.USER_NOT_FOUND]:
            response = create_error_response(error_type, log_error=False)
            assert response["statusCode"] == 404

        # Conflict errors (409)
        for error_type in [ErrorType.ALREADY_EXISTS, ErrorType.CONFLICT]:
            response = create_error_response(error_type, log_error=False)
            assert response["statusCode"] == 409

        # Rate limiting (429)
        response = create_error_response(ErrorType.RATE_LIMIT, log_error=False)
        assert response["statusCode"] == 429

        # Server errors (500)
        for error_type in [ErrorType.INTERNAL_ERROR, ErrorType.DATABASE_ERROR,
                          ErrorType.SERVICE_ERROR]:
            response = create_error_response(error_type, log_error=False)
            assert response["statusCode"] == 500

    def test_create_response(self):
        """Test generic response creation."""
        body = {"data": "test"}
        response = create_response(200, body)
        
        assert response["statusCode"] == 200
        assert "headers" in response
        assert response["headers"]["Content-Type"] == "application/json"
        assert json.loads(response["body"]) == body

    def test_create_success_response(self):
        """Test success response creation."""
        data = {"user_id": "123", "name": "Test User"}
        response = create_success_response(data, message="Operation successful")
        
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["user_id"] == "123"
        assert body["name"] == "Test User"
        assert body["message"] == "Operation successful"

    def test_create_success_response_custom_status(self):
        """Test success response with custom status code."""
        data = {"id": "new-resource"}
        response = create_success_response(data, status_code=201)
        
        assert response["statusCode"] == 201

    def test_handle_exception(self):
        """Test exception handling."""
        try:
            raise ValueError("Test error")
        except Exception as e:
            response = handle_exception(e, context="test operation", user_id="user123")
        
        assert response["statusCode"] == 500
        body = json.loads(response["body"])
        assert "error" in body
        assert body["error_code"] == "internal_server_error"

    def test_validate_required_fields_success(self):
        """Test successful field validation."""
        data = {"name": "John", "email": "john@example.com"}
        required_fields = ["name", "email"]
        
        error_response = validate_required_fields(data, required_fields)
        assert error_response is None

    def test_validate_required_fields_missing(self):
        """Test field validation with missing fields."""
        data = {"name": "John"}
        required_fields = ["name", "email", "password"]
        
        error_response = validate_required_fields(data, required_fields)
        assert error_response is not None
        assert error_response["statusCode"] == 400
        
        body = json.loads(error_response["body"])
        assert "missing_fields" in body["details"]
        assert "email" in body["details"]["missing_fields"]
        assert "password" in body["details"]["missing_fields"]

    def test_parse_json_body_success(self):
        """Test successful JSON body parsing."""
        event = {"body": '{"name": "John", "age": 30}'}
        
        body, error_response = parse_json_body(event)
        assert error_response is None
        assert body == {"name": "John", "age": 30}

    def test_parse_json_body_empty(self):
        """Test parsing empty body."""
        event = {"body": ""}
        
        body, error_response = parse_json_body(event)
        assert error_response is None
        assert body == {}

    def test_parse_json_body_invalid_json(self):
        """Test parsing invalid JSON."""
        event = {"body": '{"name": invalid}'}
        
        body, error_response = parse_json_body(event)
        assert body is None
        assert error_response is not None
        assert error_response["statusCode"] == 400
        
        response_body = json.loads(error_response["body"])
        assert response_body["error_code"] == "invalid_json"

    def test_parse_json_body_dict_input(self):
        """Test parsing when body is already a dict."""
        event = {"body": {"name": "John", "age": 30}}
        
        body, error_response = parse_json_body(event)
        assert error_response is None
        assert body == {"name": "John", "age": 30}

    def test_cors_headers_present(self):
        """Test that CORS headers are present in all responses."""
        response = create_error_response(ErrorType.NOT_FOUND, log_error=False)
        
        headers = response["headers"]
        assert "Access-Control-Allow-Origin" in headers
        assert "Access-Control-Allow-Headers" in headers
        assert "Access-Control-Allow-Methods" in headers

    def test_error_response_format_consistency(self):
        """Test that all error responses follow consistent format."""
        response = create_error_response(
            ErrorType.VALIDATION_FAILED,
            message="Test validation error",
            details={"field": "email"},
            log_error=False
        )
        
        # Check response structure
        assert "statusCode" in response
        assert "headers" in response
        assert "body" in response
        
        # Check body structure
        body = json.loads(response["body"])
        assert "error" in body
        assert "error_code" in body
        assert "details" in body
        
        # Verify body is valid JSON
        assert isinstance(body, dict)
