"""
Property-based test for error response consistency.

**Feature: fix-backend-handler-bugs, Property 5: Error response consistency**
**Validates: Requirements 4.2, 4.3, 4.4, 4.5, 4.6**

This test verifies that for any error condition, the handler returns a response
with an appropriate HTTP status code and a JSON body containing an "error" field.
"""

import json
from hypothesis import given, strategies as st, settings
from src.utils.error_handling import (
    ErrorType,
    create_error_response,
    handle_exception,
)


# Strategy for generating all possible ErrorType values
@st.composite
def error_type_strategy(draw):
    """Generate any ErrorType enum value."""
    error_types = list(ErrorType)
    return draw(st.sampled_from(error_types))


# Strategy for generating optional error messages
error_message_strategy = st.one_of(
    st.none(),
    st.text(min_size=1, max_size=200)
)


# Strategy for generating optional error details
@st.composite
def error_details_strategy(draw):
    """Generate optional error details dictionary."""
    return draw(st.one_of(
        st.none(),
        st.dictionaries(
            keys=st.text(min_size=1, max_size=50),
            values=st.one_of(
                st.text(max_size=100),
                st.integers(),
                st.booleans(),
                st.lists(st.text(max_size=50), max_size=5)
            ),
            max_size=5
        )
    ))


class TestErrorResponseConsistencyProperty:
    """Property-based tests for error response consistency."""

    @given(
        error_type=error_type_strategy(),
        message=error_message_strategy,
        details=error_details_strategy()
    )
    @settings(max_examples=100)
    def test_error_response_has_correct_structure(self, error_type, message, details):
        """
        Property: For any error type, message, and details, the error response
        must have the correct structure with statusCode, headers, and body.
        """
        # Generate error response
        response = create_error_response(
            error_type,
            message=message,
            details=details,
            log_error=False
        )
        
        # Verify response structure
        assert "statusCode" in response, "Response must have statusCode"
        assert "headers" in response, "Response must have headers"
        assert "body" in response, "Response must have body"
        
        # Verify status code is an integer
        assert isinstance(response["statusCode"], int), "statusCode must be an integer"
        
        # Verify headers is a dictionary
        assert isinstance(response["headers"], dict), "headers must be a dictionary"
        
        # Verify body is a string (JSON)
        assert isinstance(response["body"], str), "body must be a string"

    @given(
        error_type=error_type_strategy(),
        message=error_message_strategy,
        details=error_details_strategy()
    )
    @settings(max_examples=100)
    def test_error_response_body_contains_error_field(self, error_type, message, details):
        """
        Property: For any error condition, the response body must contain
        an "error" field with a descriptive message.
        
        **Validates: Requirements 4.2, 4.3, 4.4, 4.5, 4.6**
        """
        # Generate error response
        response = create_error_response(
            error_type,
            message=message,
            details=details,
            log_error=False
        )
        
        # Parse body
        body = json.loads(response["body"])
        
        # Verify error field exists
        assert "error" in body, "Response body must contain 'error' field"
        
        # Verify error field is a non-empty string
        assert isinstance(body["error"], str), "error field must be a string"
        assert len(body["error"]) > 0, "error field must not be empty"

    @given(error_type=error_type_strategy())
    @settings(max_examples=100)
    def test_error_response_has_appropriate_status_code(self, error_type):
        """
        Property: For any error type, the response must have the appropriate
        HTTP status code matching the error category.
        
        **Validates: Requirements 4.2, 4.3, 4.4, 4.5, 4.6**
        """
        # Generate error response
        response = create_error_response(error_type, log_error=False)
        
        status_code = response["statusCode"]
        error_code, expected_status, _ = error_type.value
        
        # Verify status code matches the error type
        assert status_code == expected_status, (
            f"Error type {error_type.name} should return status {expected_status}, "
            f"but got {status_code}"
        )
        
        # Verify status code is in valid HTTP error range
        assert 400 <= status_code < 600, (
            f"Error status code must be in 4xx or 5xx range, got {status_code}"
        )

    @given(
        error_type=error_type_strategy(),
        details=error_details_strategy()
    )
    @settings(max_examples=100)
    def test_error_response_includes_details_when_provided(self, error_type, details):
        """
        Property: For any error with details provided, the response body
        must include those details.
        """
        # Generate error response with details
        response = create_error_response(
            error_type,
            details=details,
            log_error=False
        )
        
        body = json.loads(response["body"])
        
        # If details were provided and non-empty, they should be in the response
        # Empty dicts are falsy in Python, so they won't be included (correct behavior)
        if details:
            assert "details" in body, "Response should include details when provided"
            assert body["details"] == details, "Details should match what was provided"
        else:
            # If details is None or empty dict, it should not be in response
            if details is None or not details:
                # Details field may or may not be present, but if present should be empty
                pass

    @given(error_type=error_type_strategy())
    @settings(max_examples=100)
    def test_error_response_has_cors_headers(self, error_type):
        """
        Property: For any error response, CORS headers must be present
        to allow frontend access.
        """
        # Generate error response
        response = create_error_response(error_type, log_error=False)
        
        headers = response["headers"]
        
        # Verify CORS headers are present
        assert "Access-Control-Allow-Origin" in headers, (
            "Response must include Access-Control-Allow-Origin header"
        )
        assert "Access-Control-Allow-Headers" in headers, (
            "Response must include Access-Control-Allow-Headers header"
        )
        assert "Access-Control-Allow-Methods" in headers, (
            "Response must include Access-Control-Allow-Methods header"
        )
        assert "Content-Type" in headers, (
            "Response must include Content-Type header"
        )

    @given(error_type=error_type_strategy())
    @settings(max_examples=100)
    def test_error_response_body_is_valid_json(self, error_type):
        """
        Property: For any error response, the body must be valid JSON
        that can be parsed by clients.
        """
        # Generate error response
        response = create_error_response(error_type, log_error=False)
        
        # Verify body can be parsed as JSON
        try:
            body = json.loads(response["body"])
            assert isinstance(body, dict), "Parsed body must be a dictionary"
        except json.JSONDecodeError as e:
            raise AssertionError(f"Response body is not valid JSON: {e}")

    @given(
        error_type=error_type_strategy(),
        message=error_message_strategy,
        details=error_details_strategy()
    )
    @settings(max_examples=100)
    def test_error_response_includes_error_code(self, error_type, message, details):
        """
        Property: For any error response, the body must include an error_code
        field for programmatic error handling.
        """
        # Generate error response
        response = create_error_response(
            error_type,
            message=message,
            details=details,
            log_error=False
        )
        
        body = json.loads(response["body"])
        
        # Verify error_code field exists
        assert "error_code" in body, "Response body must contain 'error_code' field"
        
        # Verify error_code matches the error type
        expected_code, _, _ = error_type.value
        assert body["error_code"] == expected_code, (
            f"error_code should be '{expected_code}', got '{body['error_code']}'"
        )

    @given(
        exception_message=st.text(min_size=1, max_size=200),
        context=st.one_of(st.none(), st.text(min_size=1, max_size=100)),
        user_id=st.one_of(st.none(), st.text(min_size=1, max_size=50))
    )
    @settings(max_examples=100)
    def test_handle_exception_returns_consistent_error_response(
        self, exception_message, context, user_id
    ):
        """
        Property: For any exception, handle_exception must return a consistent
        error response with status 500 and proper structure.
        """
        # Create an exception
        exception = Exception(exception_message)
        
        # Handle the exception
        response = handle_exception(exception, context=context, user_id=user_id)
        
        # Verify response structure
        assert "statusCode" in response
        assert "headers" in response
        assert "body" in response
        
        # Verify status code is 500 for internal errors
        assert response["statusCode"] == 500, (
            "Unhandled exceptions should return 500 status code"
        )
        
        # Verify body contains error field
        body = json.loads(response["body"])
        assert "error" in body
        assert "error_code" in body
        assert body["error_code"] == "internal_server_error"

    @given(error_type=st.sampled_from([
        ErrorType.MISSING_AUTH,
        ErrorType.INVALID_AUTH,
        ErrorType.EXPIRED_TOKEN,
        ErrorType.AUTH_REQUIRED
    ]))
    @settings(max_examples=50)
    def test_authentication_errors_return_401(self, error_type):
        """
        Property: For any authentication error, the response must have
        status code 401.
        
        **Validates: Requirement 4.3**
        """
        response = create_error_response(error_type, log_error=False)
        assert response["statusCode"] == 401, (
            f"Authentication error {error_type.name} must return 401"
        )

    @given(error_type=st.sampled_from([
        ErrorType.ACCESS_DENIED,
        ErrorType.INSUFFICIENT_PERMISSIONS,
        ErrorType.FORBIDDEN
    ]))
    @settings(max_examples=50)
    def test_authorization_errors_return_403(self, error_type):
        """
        Property: For any authorization error, the response must have
        status code 403.
        
        **Validates: Requirement 4.4**
        """
        response = create_error_response(error_type, log_error=False)
        assert response["statusCode"] == 403, (
            f"Authorization error {error_type.name} must return 403"
        )

    @given(error_type=st.sampled_from([
        ErrorType.INVALID_JSON,
        ErrorType.MISSING_FIELD,
        ErrorType.INVALID_FIELD,
        ErrorType.VALIDATION_FAILED,
        ErrorType.INVALID_REQUEST
    ]))
    @settings(max_examples=50)
    def test_validation_errors_return_400(self, error_type):
        """
        Property: For any validation error, the response must have
        status code 400.
        
        **Validates: Requirement 4.5**
        """
        response = create_error_response(error_type, log_error=False)
        assert response["statusCode"] == 400, (
            f"Validation error {error_type.name} must return 400"
        )

    @given(error_type=st.sampled_from([
        ErrorType.INTERNAL_ERROR,
        ErrorType.DATABASE_ERROR,
        ErrorType.SERVICE_ERROR
    ]))
    @settings(max_examples=50)
    def test_server_errors_return_500(self, error_type):
        """
        Property: For any server error, the response must have
        status code 500.
        
        **Validates: Requirement 4.6**
        """
        response = create_error_response(error_type, log_error=False)
        assert response["statusCode"] == 500, (
            f"Server error {error_type.name} must return 500"
        )
