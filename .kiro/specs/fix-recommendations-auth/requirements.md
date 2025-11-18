# Requirements Document

## Introduction

This document specifies the requirements for fixing the 401 Unauthorized error that occurs when users click the recommendations button. The issue stems from inconsistent authentication token retrieval methods across different frontend services.

## Glossary

- **RecommendationService**: Frontend service class responsible for making API calls to fetch and manage user recommendations
- **AuthService**: Frontend service class that handles authentication operations using AWS Amplify
- **ID Token**: JWT token issued by AWS Cognito that authenticates API requests
- **localStorage**: Browser storage mechanism for persisting data across sessions
- **fetchAuthSession**: AWS Amplify method that retrieves the current authentication session including tokens

## Requirements

### Requirement 1

**User Story:** As a veteran user, I want to view my job recommendations without encountering authentication errors, so that I can explore relevant opportunities.

#### Acceptance Criteria

1. WHEN the veteran clicks the recommendations button, THE RecommendationService SHALL retrieve the authentication token using the same method as AuthService
2. WHEN the RecommendationService makes an API request, THE RecommendationService SHALL include a valid Bearer token in the Authorization header
3. IF the authentication token is not available, THEN THE RecommendationService SHALL throw a descriptive error message
4. WHEN the API request is made with a valid token, THE backend SHALL return a 200 status code with recommendations data

### Requirement 2

**User Story:** As a developer, I want all frontend services to use a consistent authentication method, so that token management is centralized and maintainable.

#### Acceptance Criteria

1. THE RecommendationService SHALL use the authService.getAuthToken() method to retrieve authentication tokens
2. THE RecommendationService SHALL NOT access localStorage directly for authentication tokens
3. WHEN any service needs an authentication token, THE service SHALL use the centralized authService method
4. THE getAuthHeaders method in RecommendationService SHALL be updated to use async/await pattern for token retrieval

### Requirement 3

**User Story:** As a system administrator, I want proper error handling for authentication failures, so that users receive clear feedback when authentication issues occur.

#### Acceptance Criteria

1. WHEN token retrieval fails, THE RecommendationService SHALL log the error with sufficient context
2. WHEN an API request returns 401, THE RecommendationService SHALL provide a user-friendly error message
3. IF the user is not authenticated, THEN THE system SHALL redirect the user to the login page
4. THE error messages SHALL be displayed in Japanese to match the application locale
