# Implementation Plan

- [x] 1. Update RecommendationService authentication method
  - Modify `frontend/src/services/recommendationService.ts` to import authService
  - Convert `getAuthHeaders()` from synchronous to async method
  - Replace localStorage token retrieval with `authService.getAuthToken()`
  - Add error handling for missing authentication tokens
  - _Requirements: 1.1, 1.3, 2.1, 2.2, 2.4_

- [x] 2. Update all RecommendationService methods to use async token retrieval
  - Modify `getRecommendations()` to await `getAuthHeaders()`
  - Modify `markRecommendationAsViewed()` to await `getAuthHeaders()`
  - Modify `dismissRecommendation()` to await `getAuthHeaders()`
  - Modify `applyToOpportunity()` to await `getAuthHeaders()`
  - Modify `getApplications()` to await `getAuthHeaders()`
  - Modify `withdrawApplication()` to await `getAuthHeaders()`
  - _Requirements: 1.2, 2.3_

- [x] 3. Verify the fix resolves the 401 error
  - Test login flow and recommendations fetch
  - Verify Bearer token is included in API requests
  - Check browser console for successful API responses
  - Confirm no 401 Unauthorized errors occur
  - _Requirements: 1.4, 3.1, 3.2_
