# Design Document

## Overview

This design addresses the authentication error occurring when users attempt to fetch their application status. The error message "Invalid key=value pair (missing equal-sign) in Authorization header" indicates that the Authorization header format is incorrect for API Gateway's Cognito authorizer.

The root cause is that `RecommendationService` is sending `Authorization: Bearer <token>`, but API Gateway's Cognito authorizer expects just `Authorization: <token>` (without the "Bearer " prefix).

## Architecture

### Current Architecture (Problematic)

```
RecommendationService
  └─> fetch() with "Authorization: Bearer <token>"
      └─> API Gateway (Cognito Authorizer)
          └─> ❌ Expects "Authorization: <token>" (no Bearer prefix)
              └─> 401 Error: "Invalid key=value pair"
```

### Proposed Architecture (Fixed)

```
RecommendationService
  └─> fetch() with "Authorization: <token>" (no Bearer prefix)
      └─> API Gateway (Cognito Authorizer)
          └─> ✅ Valid authentication
              └─> 200 OK with data
```

## Components and Interfaces

### 1. RecommendationService (Simple Fix)

**File**: `frontend/src/services/recommendationService.ts`

**Changes**:
- Modify `getAuthHeaders()` method to remove "Bearer " prefix from Authorization header
- Keep using `fetch` API (no need to change to Amplify)
- All other methods remain unchanged

**Method Fix**:

```typescript
// Before (incorrect)
private static async getAuthHeaders(): Promise<HeadersInit> {
  const token = await authService.getAuthToken();
  if (!token) {
    throw new Error('認証トークンが見つかりません。再度ログインしてください。');
  }
  return {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,  // ❌ Bearer prefix causes error
  };
}

// After (correct)
private static async getAuthHeaders(): Promise<HeadersInit> {
  const token = await authService.getAuthToken();
  if (!token) {
    throw new Error('認証トークンが見つかりません。再度ログインしてください。');
  }
  return {
    'Content-Type': 'application/json',
    'Authorization': token,  // ✅ No Bearer prefix
  };
}
```

### 2. AuthService (Reference)

**File**: `frontend/src/services/authService.ts`

The `authHeaders()` method in AuthService already uses the correct format (no Bearer prefix):

```typescript
private async authHeaders(): Promise<Record<string, string>> {
  const s = await fetchAuthSession();
  const idToken = s.tokens?.idToken?.toString();
  if (!idToken) throw new Error('No ID token in session');
  return { Authorization: idToken };  // ✅ Correct format
}
```

This confirms that the correct format is `Authorization: <token>` without "Bearer ".

## Data Models

No data model changes are required. The request/response formats remain the same.

## Error Handling

### Fetch API Error Handling

The existing error handling in RecommendationService will continue to work:
- HTTP errors are caught and logged
- Error messages are thrown to calling components
- Components display errors to users

### Error Flow

```
fetch() call fails
  └─> Catch error in service method
      └─> Log error with context
          └─> Throw error
              └─> Component catches and displays to user
```

### Error Messages

Existing error messages are already in place and will continue to work correctly once the Authorization header format is fixed.

## Implementation Details

### Files to Modify

1. **frontend/src/services/recommendationService.ts**
   - Modify `getAuthHeaders()` method to remove "Bearer " prefix
   - Change `Authorization: \`Bearer ${token}\`` to `Authorization: token`
   - No other changes needed

### Single Line Change

The fix requires changing only one line in the `getAuthHeaders()` method:

```typescript
// Line to change:
'Authorization': `Bearer ${token}`,

// Change to:
'Authorization': token,
```

## Testing Strategy

### Manual Testing

1. **Application Status Test**
   - Log in as a veteran user
   - Navigate to dashboard
   - Click on application status/recommendations
   - Verify data loads without authentication errors
   - Confirm no "Invalid key=value pair" error appears

### Browser Console Verification

After fix, the console should show:
- No "Invalid key=value pair" errors
- Successful API calls with 200 status codes
- Authorization header contains token without "Bearer " prefix

## Security Considerations

1. **Token Format**: Using the correct Authorization header format ensures proper authentication
2. **Token Management**: AuthService continues to handle token retrieval securely
3. **HTTPS**: All API calls use HTTPS in production
4. **No Token Exposure**: Tokens are not logged or exposed in error messages

## Backward Compatibility

This change is backward compatible:
- No API contract changes
- No database schema changes
- No changes to backend authentication logic
- Only frontend HTTP client implementation is updated

## Benefits of This Approach

1. **Minimal Change**: Only one line needs to be modified
2. **Low Risk**: No architectural changes or refactoring required
3. **Quick Fix**: Can be deployed immediately
4. **Consistency**: Matches the Authorization header format used by AuthService
5. **Proven Pattern**: AuthService already uses this format successfully

## Rollout Plan

1. Update Authorization header format in RecommendationService
2. Test locally to verify fix
3. Deploy to production
4. Monitor for any authentication errors
