# Error Handling Standardization

## Overview

This document describes the standardized error handling implementation across all Lambda handlers in the Honda Veteran Talent Matching system.

## Implementation

### Core Module: `src/utils/error_handling.py`

The error handling module provides:

1. **Standardized Error Types** - Enum-based error types with consistent HTTP status codes
2. **Error Response Creation** - Consistent error response format
3. **Success Response Creation** - Consistent success response format
4. **Exception Handling** - Centralized exception handling with logging
5. **Input Validation** - Common validation utilities

### Error Types and Status Codes

| Error Type | HTTP Status | Use Case |
|------------|-------------|----------|
| `MISSING_AUTH` | 401 | Missing Authorization header |
| `INVALID_AUTH` | 401 | Invalid JWT token |
| `EXPIRED_TOKEN` | 401 | Expired token |
| `AUTH_REQUIRED` | 401 | Authentication required |
| `ACCESS_DENIED` | 403 | User lacks required role |
| `INSUFFICIENT_PERMISSIONS` | 403 | User lacks required permissions |
| `FORBIDDEN` | 403 | General forbidden access |
| `INVALID_JSON` | 400 | Invalid JSON in request body |
| `MISSING_FIELD` | 400 | Missing required fields |
| `INVALID_FIELD` | 400 | Invalid field values |
| `VALIDATION_FAILED` | 400 | Validation failures |
| `INVALID_REQUEST` | 400 | General invalid request |
| `NOT_FOUND` | 404 | Resource not found |
| `PROFILE_NOT_FOUND` | 404 | Profile does not exist |
| `USER_NOT_FOUND` | 404 | User does not exist |
| `ALREADY_EXISTS` | 409 | Resource already exists |
| `CONFLICT` | 409 | General conflict |
| `RATE_LIMIT` | 429 | Rate limit exceeded |
| `INTERNAL_ERROR` | 500 | Internal server error |
| `DATABASE_ERROR` | 500 | Database operation failed |
| `SERVICE_ERROR` | 500 | External service error |

### Response Format

All responses follow a consistent format:

#### Error Response
```json
{
  "error": "Human-readable error message",
  "error_code": "machine_readable_code",
  "details": {
    "additional": "context"
  }
}
```

#### Success Response
```json
{
  "data_field_1": "value",
  "data_field_2": "value",
  "message": "Optional success message"
}
```

### CORS Headers

All responses include standardized CORS headers:
- `Content-Type: application/json`
- `Access-Control-Allow-Origin: *`
- `Access-Control-Allow-Headers: Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token`
- `Access-Control-Allow-Methods: GET,POST,PUT,DELETE,OPTIONS`

### Logging

Error logging follows these conventions:

- **Status 500+**: Logged as ERROR with full stack trace
- **Status 400-499**: Logged as WARNING
- **Status 200-399**: Logged as INFO

All error logs include:
- Error message
- Error code
- Optional context (operation, user_id)
- Stack trace (for 500+ errors)

## Usage Examples

### Basic Error Response

```python
from src.utils.error_handling import ErrorType, create_error_response

# Missing authentication
if not token:
    return create_error_response(ErrorType.MISSING_AUTH)

# Invalid authentication
if not user_info:
    return create_error_response(ErrorType.INVALID_AUTH)

# Access denied with custom message
if user.role != "admin":
    return create_error_response(
        ErrorType.ACCESS_DENIED,
        message="Admin role required for this operation"
    )

# Not found with details
if not profile:
    return create_error_response(
        ErrorType.PROFILE_NOT_FOUND,
        details={"user_id": user_id}
    )
```

### Success Response

```python
from src.utils.error_handling import create_success_response

# Basic success
return create_success_response({
    "user_id": user_id,
    "name": user.name
})

# Success with message
return create_success_response(
    {"profile_id": profile_id},
    message="Profile created successfully"
)

# Success with custom status code
return create_success_response(
    {"resource_id": new_id},
    status_code=201,
    message="Resource created"
)
```

### Exception Handling

```python
from src.utils.error_handling import handle_exception

try:
    # Operation that might fail
    result = perform_operation()
except Exception as e:
    return handle_exception(
        e,
        context="performing operation",
        user_id=user_id
    )
```

### Input Validation

```python
from src.utils.error_handling import parse_json_body, validate_required_fields

# Parse JSON body
body, error_response = parse_json_body(event)
if error_response:
    return error_response

# Validate required fields
error_response = validate_required_fields(
    body,
    ["name", "email", "password"]
)
if error_response:
    return error_response
```

## Handler Updates

### Updated Handlers

The following handlers have been updated to use standardized error handling:

1. ✅ `business_title_handler.py` - Partially updated
2. ⏳ `profile_handler.py` - Pending
3. ⏳ `application_handler.py` - Pending
4. ⏳ `auth_handler.py` - Pending
5. ⏳ `questionnaire_handler.py` - Pending
6. ⏳ `contact_handler.py` - Pending
7. ⏳ `matching_handler.py` - Pending
8. ⏳ `public_search_handler.py` - Pending
9. ⏳ `stats_handler.py` - Pending

### Migration Pattern

When updating a handler:

1. **Import the error handling utilities**:
   ```python
   from src.utils.error_handling import (
       ErrorType,
       create_error_response,
       create_success_response,
       handle_exception,
       parse_json_body,
       validate_required_fields,
   )
   ```

2. **Replace authentication checks**:
   ```python
   # Before
   if not token:
       return {
           "statusCode": 401,
           "body": json.dumps({"error": "Missing authorization token"}),
       }
   
   # After
   if not token:
       return create_error_response(ErrorType.MISSING_AUTH)
   ```

3. **Replace authorization checks**:
   ```python
   # Before
   if user.role != "admin":
       return {
           "statusCode": 403,
           "body": json.dumps({"error": "Access denied"}),
       }
   
   # After
   if user.role != "admin":
       return create_error_response(ErrorType.ACCESS_DENIED)
   ```

4. **Replace validation errors**:
   ```python
   # Before
   try:
       body = json.loads(event.get("body", "{}"))
   except json.JSONDecodeError:
       return {
           "statusCode": 400,
           "body": json.dumps({"error": "Invalid JSON"}),
       }
   
   # After
   body, error_response = parse_json_body(event)
   if error_response:
       return error_response
   ```

5. **Replace success responses**:
   ```python
   # Before
   return {
       "statusCode": 200,
       "headers": {
           "Content-Type": "application/json",
           "Access-Control-Allow-Origin": "*",
       },
       "body": json.dumps({"data": result}),
   }
   
   # After
   return create_success_response({"data": result})
   ```

6. **Replace exception handling**:
   ```python
   # Before
   except Exception as e:
       logger.error(f"Error: {str(e)}")
       return {
           "statusCode": 500,
           "body": json.dumps({"error": "Internal server error"}),
       }
   
   # After
   except Exception as e:
       return handle_exception(e, "operation context", user_id)
   ```

## Benefits

1. **Consistency**: All handlers return errors in the same format
2. **Maintainability**: Error handling logic is centralized
3. **Debugging**: Comprehensive logging with context
4. **Type Safety**: Enum-based error types prevent typos
5. **Testing**: Easier to test error scenarios
6. **Documentation**: Self-documenting error codes
7. **Client Experience**: Predictable error responses for frontend

## Testing

The error handling module includes comprehensive unit tests covering:

- All error types and status codes
- Custom messages and details
- Success responses
- Exception handling
- Input validation
- JSON parsing
- CORS headers
- Response format consistency

Run tests with:
```bash
python3 -m pytest tests/unit/test_error_handling.py -v
```

## Requirements Validation

This implementation satisfies the following requirements from the spec:

- **Requirement 4.1**: All exceptions are logged with full error details including stack trace
- **Requirement 4.2**: All error responses include appropriate HTTP status codes
- **Requirement 4.3**: Authentication failures return 401 Unauthorized
- **Requirement 4.4**: Authorization failures return 403 Forbidden
- **Requirement 4.5**: Validation failures return 400 Bad Request with validation details
- **Requirement 4.6**: Server errors return 500 Internal Server Error

## Next Steps

1. Complete migration of all remaining handlers
2. Update integration tests to verify error responses
3. Document error codes in API documentation
4. Add error monitoring/alerting for 500 errors
