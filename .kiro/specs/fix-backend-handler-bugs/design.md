# Design Document

## Overview

This design addresses critical bugs in the Lambda handlers for business title generation and profile updates. The primary issues are:

1. **Async/Await Misuse**: The business title handler uses `async def` functions but Lambda requires synchronous handlers
2. **Repository Method Mismatch**: The profile handler calls `update_profile()` with incorrect parameters
3. **Error Handling**: Inconsistent error responses across handlers

The solution involves converting async handlers to synchronous execution with proper event loop management and fixing repository method calls.

## Architecture

### Current Architecture Issues

```
┌─────────────────┐
│  API Gateway    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Lambda Handler  │ ❌ async def (incorrect)
│  (async)        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Repository     │ ❌ Wrong parameters
│   Methods       │
└─────────────────┘
```

### Fixed Architecture

```
┌─────────────────┐
│  API Gateway    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Lambda Handler  │ ✅ def (synchronous)
│  (sync wrapper) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Async Business  │ ✅ asyncio.run()
│     Logic       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Repository     │ ✅ Correct parameters
│   Methods       │
└─────────────────┘
```

## Components and Interfaces

### 1. Business Title Handler

**Current Issues:**
- Handler functions are defined as `async def` but Lambda expects synchronous functions
- No event loop management for async operations

**Fixed Interface:**
```python
def generate_business_titles(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Synchronous Lambda handler that wraps async logic."""
    return asyncio.run(_generate_business_titles_async(event, context))

async def _generate_business_titles_async(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Async implementation of business title generation."""
    # Existing async logic here
```

### 2. Profile Handler

**Current Issues:**
- Calls `profile_repo.update_profile(existing_profile)` with profile object
- Repository expects `update_profile(user_id: str, update_data: dict)`

**Fixed Interface:**
```python
def update_profile(event: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    """Update user profile with correct repository method call."""
    # Build update_data dictionary
    update_data = {
        "business_title": value,
        "skills": value,
        # ...
    }
    # Call repository with correct parameters
    success = profile_repo.update_profile(user_id, update_data)
```

### 3. Repository Interface

**VeteranProfileRepository.update_profile():**
```python
def update_profile(self, user_id: str, update_data: Dict[str, Any]) -> bool:
    """
    Update veteran profile with provided data.
    
    Args:
        user_id: User ID (partition key)
        update_data: Dictionary of fields to update
        
    Returns:
        bool: True if update succeeded
    """
```

## Data Models

No changes to data models are required. The existing models are correct:

- **VeteranProfile**: Contains business_title, skills, experiences, preferences, privacy_settings
- **User**: Contains user_id, name, email, role, department

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Handler synchronicity

*For any* Lambda handler function, the function signature should be synchronous (def, not async def), ensuring AWS Lambda can properly invoke and manage the function lifecycle.

**Validates: Requirements 3.1, 3.2**

### Property 2: Async operation completion

*For any* handler that uses asynchronous operations internally, all async operations should complete before the handler returns a response.

**Validates: Requirements 3.3**

### Property 3: Repository parameter correctness

*For any* call to `VeteranProfileRepository.update_profile()`, the method should receive exactly two arguments: a user_id string and an update_data dictionary.

**Validates: Requirements 2.2**

### Property 4: Profile update persistence

*For any* successful profile update operation, the changes should be persisted to DynamoDB and reflected in subsequent GET requests.

**Validates: Requirements 2.1, 2.3**

### Property 5: Error response consistency

*For any* error condition, the handler should return a response with an appropriate HTTP status code (401, 403, 400, 404, or 500) and a JSON body containing an "error" field.

**Validates: Requirements 4.2, 4.3, 4.4, 4.5, 4.6**

### Property 6: Title generation success response

*For any* successful business title generation, the response should have status code 200 and include "titles", "recommended_title", and "reasoning" fields.

**Validates: Requirements 1.5**

### Property 7: Title selection history preservation

*For any* business title selection, the system should append a new entry to the title_history array containing the selected title, timestamp, and previous title.

**Validates: Requirements 5.2, 5.3**

## Error Handling

### Error Categories and Responses

1. **Authentication Errors (401)**
   - Missing Authorization header
   - Invalid JWT token
   - Expired token

2. **Authorization Errors (403)**
   - User lacks required role
   - User attempting to access another user's resources
   - Insufficient permissions

3. **Validation Errors (400)**
   - Invalid JSON in request body
   - Missing required fields
   - Invalid field values
   - Profile validation failures

4. **Not Found Errors (404)**
   - Profile does not exist
   - User does not exist

5. **Server Errors (500)**
   - Database connection failures
   - AI service failures
   - Unexpected exceptions

### Error Response Format

All errors should follow this consistent format:

```json
{
  "error": "Human-readable error message",
  "details": {
    "field": "Additional context (optional)"
  }
}
```

### Logging Strategy

- **INFO**: Successful operations with user_id
- **WARNING**: Validation failures, authorization denials
- **ERROR**: Exceptions with full stack trace

## Testing Strategy

### Unit Tests

Unit tests will verify:
- Handler function signatures are synchronous
- Repository methods are called with correct parameters
- Error responses have correct status codes and format
- Success responses contain required fields

### Property-Based Tests

We will use **Hypothesis** for Python property-based testing.

Property tests will verify:
- All handlers return valid HTTP response structures
- Error responses always include "error" field
- Update operations with valid data always succeed
- Async operations complete before handler returns

Each property-based test will run a minimum of 100 iterations to ensure comprehensive coverage.

### Integration Tests

Integration tests will verify:
- End-to-end business title generation flow
- End-to-end profile update flow
- Error handling across the full stack
- DynamoDB persistence after updates

### Test Tagging

Each property-based test will be tagged with:
```python
# Feature: fix-backend-handler-bugs, Property 1: Handler synchronicity
```

This links tests directly to correctness properties in this design document.

## Implementation Notes

### Async to Sync Conversion Pattern

For all business title handler functions:

```python
# Old (incorrect)
async def generate_business_titles(event, context):
    result = await some_async_operation()
    return result

# New (correct)
def generate_business_titles(event, context):
    return asyncio.run(_generate_business_titles_async(event, context))

async def _generate_business_titles_async(event, context):
    result = await some_async_operation()
    return result
```

### Profile Update Fix Pattern

```python
# Old (incorrect)
success = profile_repo.update_profile(existing_profile)

# New (correct)
update_data = {
    "business_title": existing_profile.business_title,
    "skills": existing_profile.skills,
    "experiences": existing_profile.experiences,
    "preferences": existing_profile.preferences,
    "last_updated": datetime.now(timezone.utc).isoformat()
}
success = profile_repo.update_profile(user_id, update_data)
```

### Event Loop Management

- Use `asyncio.run()` for Python 3.7+
- Ensure event loop is created and closed properly
- Handle event loop exceptions gracefully

## Security Considerations

- No changes to authentication/authorization logic
- Maintain existing RBAC checks
- Continue logging security events
- Preserve existing input validation

## Performance Considerations

- Synchronous wrapper adds minimal overhead (~1-2ms)
- No impact on cold start times
- Repository method calls remain unchanged in performance
- DynamoDB operations unaffected

## Deployment Strategy

1. Deploy updated handlers to staging environment
2. Run integration tests against staging
3. Monitor CloudWatch logs for errors
4. Deploy to production with canary deployment
5. Monitor production metrics for 24 hours
6. Roll back if error rate increases

## Rollback Plan

If issues occur after deployment:
1. Revert to previous Lambda function versions
2. Investigate root cause in staging
3. Apply additional fixes
4. Re-deploy with additional testing
