# Design Document

## Overview

This design addresses the 401 Unauthorized error occurring when users attempt to fetch recommendations. The root cause is that `RecommendationService` attempts to retrieve authentication tokens from `localStorage`, while the application's authentication system (AWS Amplify) stores tokens in its own session management system. The solution involves refactoring `RecommendationService` to use the centralized `authService` for token retrieval.

## Architecture

### Current Architecture (Problematic)

```
RecommendationService
  └─> localStorage.getItem('authToken')  ❌ Token not found
      └─> API Request with empty/invalid token
          └─> 401 Unauthorized Error
```

### Proposed Architecture (Fixed)

```
RecommendationService
  └─> authService.getAuthToken()
      └─> fetchAuthSession() (AWS Amplify)
          └─> Returns valid ID Token
              └─> API Request with Bearer token
                  └─> 200 OK with recommendations
```

## Components and Interfaces

### 1. RecommendationService (Modified)

**File**: `frontend/src/services/recommendationService.ts`

**Changes**:
- Import `authService` from `./authService`
- Convert `getAuthHeaders()` from synchronous to asynchronous method
- Replace `localStorage.getItem('authToken')` with `await authService.getAuthToken()`
- Add proper error handling for missing tokens
- Update all methods that call `getAuthHeaders()` to use `await`

**Method Signature Changes**:

```typescript
// Before
private static getAuthHeaders(): HeadersInit {
  const token = localStorage.getItem('authToken');
  return {
    'Content-Type': 'application/json',
    'Authorization': token ? `Bearer ${token}` : '',
  };
}

// After
private static async getAuthHeaders(): Promise<HeadersInit> {
  const token = await authService.getAuthToken();
  if (!token) {
    throw new Error('認証トークンが見つかりません。再度ログインしてください。');
  }
  return {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
  };
}
```

### 2. AuthService (No Changes Required)

**File**: `frontend/src/services/authService.ts`

The existing `getAuthToken()` method already provides the correct functionality:

```typescript
async getAuthToken(): Promise<string | null> {
  try {
    const s = await fetchAuthSession();
    return s.tokens?.idToken?.toString() ?? null;
  } catch (error) {
    console.error('Get auth token error:', error);
    return null;
  }
}
```

## Data Models

No data model changes are required. The authentication token format remains the same (JWT ID token from AWS Cognito).

## Error Handling

### Token Retrieval Errors

1. **Missing Token**: When `authService.getAuthToken()` returns `null`, throw a descriptive error in Japanese
2. **API 401 Response**: Catch and re-throw with user-friendly message
3. **Network Errors**: Preserve existing error handling behavior

### Error Flow

```
getAuthToken() returns null
  └─> Throw Error: "認証トークンが見つかりません。再度ログインしてください。"
      └─> Caught by calling component
          └─> Display error message to user
              └─> Optional: Redirect to login page
```

## Implementation Details

### Files to Modify

1. **frontend/src/services/recommendationService.ts**
   - Add import for `authService`
   - Make `getAuthHeaders()` async
   - Update all method calls to `getAuthHeaders()` with `await`
   - Add error handling for missing tokens

### Methods Requiring Updates

All public static methods in `RecommendationService` that call `getAuthHeaders()`:
- `getRecommendations()`
- `markRecommendationAsViewed()`
- `dismissRecommendation()`
- `applyToOpportunity()`
- `getApplications()`
- `withdrawApplication()`

Each method needs to:
1. Add `async` keyword if not already present
2. Use `await this.getAuthHeaders()` instead of `this.getAuthHeaders()`

## Testing Strategy

### Manual Testing

1. **Login Flow Test**
   - Log in as a veteran user
   - Navigate to dashboard
   - Click recommendations button
   - Verify recommendations load without 401 error

2. **Token Expiration Test**
   - Log in and wait for token to expire
   - Attempt to fetch recommendations
   - Verify appropriate error message is displayed

3. **Unauthenticated Access Test**
   - Clear browser session
   - Attempt to access recommendations
   - Verify redirect to login or error message

### Browser Console Verification

After fix, the console should show:
- Successful API call: `GET .../recommendations/{userId} 200 OK`
- No "Authorization token required" errors
- Proper Bearer token in request headers

## Security Considerations

1. **Token Exposure**: Tokens are retrieved from AWS Amplify's secure session storage, not localStorage
2. **Token Format**: Bearer token format is maintained for API compatibility
3. **Error Messages**: Error messages do not expose sensitive token information
4. **HTTPS**: All API calls continue to use HTTPS in production

## Backward Compatibility

This change is backward compatible:
- No API contract changes
- No database schema changes
- No changes to backend authentication logic
- Only frontend token retrieval method is updated

## Rollout Plan

1. Deploy frontend changes
2. Verify in staging environment
3. Monitor for authentication errors
4. Deploy to production
5. Monitor user feedback and error logs
