# Implementation Plan

- [x] 1. Fix business title handler async/sync issues
  - Convert all async handler functions to synchronous wrappers
  - Implement async helper functions for business logic
  - Use asyncio.run() to execute async operations
  - _Requirements: 1.1, 1.2, 3.1, 3.2, 3.3_

- [x] 1.1 Write property test for handler synchronicity
  - **Property 1: Handler synchronicity**
  - **Validates: Requirements 3.1, 3.2**

- [x] 1.2 Write property test for async operation completion
  - **Property 2: Async operation completion**
  - **Validates: Requirements 3.3**

- [x] 2. Fix profile handler repository method calls
  - Update profile_handler.py update_profile() function
  - Build update_data dictionary from profile fields
  - Call profile_repo.update_profile(user_id, update_data) with correct parameters
  - Remove incorrect profile_repo.update_profile(existing_profile) call
  - _Requirements: 2.1, 2.2, 2.3_

- [x] 2.1 Write property test for repository parameter correctness
  - **Property 3: Repository parameter correctness**
  - **Validates: Requirements 2.2**

- [x] 2.2 Write property test for profile update persistence
  - **Property 4: Profile update persistence**
  - **Validates: Requirements 2.1, 2.3**

- [x] 3. Standardize error handling across handlers
  - Ensure all error responses include appropriate HTTP status codes
  - Verify error response format consistency (JSON with "error" field)
  - Add comprehensive error logging with stack traces
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

- [x] 3.1 Write property test for error response consistency
  - **Property 5: Error response consistency**
  - **Validates: Requirements 4.2, 4.3, 4.4, 4.5, 4.6**

- [x] 4. Fix business title selection and history tracking
  - Verify title selection updates profile correctly
  - Ensure title_history array is properly maintained
  - Include previous_title and timestamp in history entries
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 4.1 Write property test for title generation success response
  - **Property 6: Title generation success response**
  - **Validates: Requirements 1.5**

- [x] 4.2 Write property test for title selection history preservation
  - **Property 7: Title selection history preservation**
  - **Validates: Requirements 5.2, 5.3**

- [x] 5. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Add integration tests for end-to-end flows
  - Write integration test for business title generation flow
  - Write integration test for profile update flow
  - Write integration test for error handling scenarios
  - Verify DynamoDB persistence after operations
  - _Requirements: 1.1, 2.1, 4.1_

- [x] 7. Final checkpoint - Verify production readiness
  - Ensure all tests pass, ask the user if questions arise.
