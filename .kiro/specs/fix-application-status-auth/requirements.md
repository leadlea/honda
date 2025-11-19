# Requirements Document

## Introduction

This document specifies the requirements for fixing the authentication error that occurs when users attempt to fetch their application status. The error message "Invalid key=value pair (missing equal-sign) in Authorization header" indicates that the RecommendationService is not properly integrating with AWS Amplify's API client, which handles authentication automatically for API Gateway endpoints protected by Cognito authorizers.

## Glossary

- **RecommendationService**: Frontend service class responsible for making API calls to fetch and manage user recommendations and applications
- **AWS Amplify API**: AWS Amplify's API module that provides methods (get, post, put, delete) for making authenticated API calls
- **Cognito Authorizer**: API Gateway authorizer that validates JWT tokens from AWS Cognito
- **ID Token**: JWT token issued by AWS Cognito that authenticates API requests
- **fetch API**: Native browser API for making HTTP requests (currently used incorrectly in RecommendationService)

## Requirements

### Requirement 1

**User Story:** As a veteran user, I want to view my job applications without encountering authentication errors, so that I can track my application status.

#### Acceptance Criteria

1. WHEN the veteran requests their applications, THE RecommendationService SHALL use AWS Amplify API methods to make authenticated requests
2. WHEN the API request is made, THE AWS Amplify API SHALL automatically include the correct authentication headers
3. IF the authentication token is not available, THEN THE AWS Amplify API SHALL throw a descriptive error message
4. WHEN the API request is made with valid authentication, THE backend SHALL return a 200 status code with application data

### Requirement 2

**User Story:** As a developer, I want all frontend services to use AWS Amplify API methods consistently, so that authentication is handled uniformly across the application.

#### Acceptance Criteria

1. THE RecommendationService SHALL use AWS Amplify's get, post, put methods instead of native fetch API
2. THE RecommendationService SHALL NOT manually construct Authorization headers
3. WHEN any service needs to make authenticated API calls, THE service SHALL use AWS Amplify API methods
4. THE RecommendationService SHALL follow the same pattern as ProfileService for API calls

### Requirement 3

**User Story:** As a system administrator, I want proper error handling for authentication failures, so that users receive clear feedback when authentication issues occur.

#### Acceptance Criteria

1. WHEN API requests fail due to authentication, THE RecommendationService SHALL log the error with sufficient context
2. WHEN an API request returns an error, THE RecommendationService SHALL provide a user-friendly error message in Japanese
3. IF the user is not authenticated, THEN THE system SHALL handle the error gracefully
4. THE error messages SHALL be consistent with other services in the application
