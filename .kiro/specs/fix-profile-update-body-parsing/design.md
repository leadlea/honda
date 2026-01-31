# Design Document

## Overview

This design addresses a critical production bug in the profile update handler where request body parsing fails when the Lambda proxy integration provides the body in different formats. The solution implements robust body parsing that handles both string and dictionary inputs, with comprehensive error handling and logging.

## Architecture

The fix is implemented in the `update_profile` function within `src/handlers/profile_handler.py`. The architecture follows these principles:

1. **Defensive Parsing**: Check the type of the incoming body before attempting to parse
2. **Type Safety**: Validate that the parsed result is a dictionary before proceeding
3. **Clear Error Messages**: Provide specific error messages for different failure modes
4. **Comprehensive Logging**: Log all parsing attempts and their results for debugging

## Components and Interfaces

### Modified Component: update_profile Handler

**Location**: `src/handlers/profile_handler.py`

**Changes**:
- Replace direct `json.loads()` call with type-aware parsing logic
- Add type checking for the raw body before parsing
- Add error handling for unexpected body types
- Add detailed logging of body type and content

**Interface**:
```python
def update_profile(event: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    """
    Update user profile with RBAC protection and data validation.
    
    Args:
        event: Lambda event containing request data
        context: Lambda context (optional)
        
    Returns:
        Dict with statusCode, headers, and body
    """
```

## Data Models

No changes to data models are required. The fix operates on the request parsing layer before data reaches the model layer.

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Body parsing handles all valid input types

*For any* valid Lambda event with a body field containing either a JSON string or a dictionary, the parsing logic should successfully extract a dictionary without raising an exception.

**Validates: Requirements 1.1, 1.2, 1.3**

### Property 2: Invalid body types are rejected with clear errors

*For any* Lambda event where the body is neither a string nor a dictionary, the handler should return a 400 status code with an error message indicating "Invalid request body format".

**Validates: Requirements 1.4, 2.2**

### Property 3: JSON parsing errors are caught and reported

*For any* Lambda event where the body is a string but not valid JSON, the handler should return a 400 status code with an error message "Invalid JSON in request body".

**Validates: Requirements 2.1**

### Property 4: Successful parsing preserves data integrity

*For any* valid profile update request, the parsed body dictionary should contain exactly the same keys and values as the original JSON data.

**Validates: Requirements 1.5**

## Error Handling

### Error Scenarios

1. **Invalid JSON String**
   - Trigger: Body is a string but not valid JSON
   - Response: 400 status with "Invalid JSON in request body"
   - Logging: Error logged with the invalid string content

2. **Unexpected Body Type**
   - Trigger: Body is neither string nor dict (e.g., list, number, None)
   - Response: 400 status with "Invalid request body format"
   - Logging: Error logged with actual type received

3. **Missing Body**
   - Trigger: Event has no body field
   - Response: Treated as empty dict "{}", parsed normally
   - Logging: Info log indicating empty body

### Error Response Format

All errors follow the standardized format:
```json
{
  "statusCode": 400,
  "headers": {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*"
  },
  "body": "{\"error\": \"<error message>\"}"
}
```

## Testing Strategy

### Unit Tests

Unit tests verify specific parsing scenarios:

1. **String body parsing**: Verify JSON string is correctly parsed to dict
2. **Dict body passthrough**: Verify dict body is used directly
3. **Invalid JSON handling**: Verify malformed JSON returns 400 error
4. **Unexpected type handling**: Verify non-string/dict types return 400 error
5. **Empty body handling**: Verify missing body defaults to empty dict

### Property-Based Tests

Property-based tests will use the Hypothesis library to verify correctness properties across many randomly generated inputs:

1. **Property 1 Test**: Generate random valid JSON strings and dicts, verify all parse successfully
2. **Property 2 Test**: Generate random non-string/dict values, verify all return 400 errors
3. **Property 3 Test**: Generate random invalid JSON strings, verify all return 400 errors
4. **Property 4 Test**: Generate random valid profile data, verify parsing preserves all data

Each property-based test will run a minimum of 100 iterations to ensure comprehensive coverage.

### Integration Tests

Integration tests verify the fix works in the full request flow:

1. Test profile update with string body through full handler
2. Test profile update with dict body through full handler
3. Test error handling with invalid bodies through full handler

## Implementation Notes

### Code Changes

The fix replaces this vulnerable code:
```python
body = json.loads(event.get("body", "{}"))
```

With this robust parsing logic:
```python
# Parse body - handle both string and dict cases
raw_body = event.get("body", "{}")
if isinstance(raw_body, str):
    body = json.loads(raw_body)
elif isinstance(raw_body, dict):
    body = raw_body
else:
    logger.error(f"Unexpected body type: {type(raw_body)}")
    return create_response(400, {"error": "Invalid request body format"})
```

### Logging Strategy

The implementation includes comprehensive logging:

1. Log the raw body type before parsing
2. Log the parsed body structure after successful parsing
3. Log errors with full context when parsing fails
4. Log unexpected types with the actual type received

### Backward Compatibility

This fix is fully backward compatible:
- Existing requests with JSON string bodies continue to work
- Requests with dict bodies (from internal calls) continue to work
- Error responses maintain the same format
- No changes to the API contract

## Performance Considerations

The fix adds minimal overhead:
- One additional `isinstance()` check (O(1) operation)
- No additional parsing for dict bodies (actually faster)
- Logging overhead is negligible
- No impact on database operations

## Security Considerations

The fix improves security by:
- Preventing crashes from malformed requests
- Providing clear error messages without exposing internals
- Logging suspicious requests for security monitoring
- Maintaining proper error handling throughout the request lifecycle
