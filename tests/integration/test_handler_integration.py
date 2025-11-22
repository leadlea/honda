"""
Integration tests for end-to-end handler flows.
Tests business title generation, profile updates, and error handling with DynamoDB persistence.

Feature: fix-backend-handler-bugs
Validates: Requirements 1.1, 2.1, 4.1
"""

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.handlers.business_title_handler import BusinessTitleHandler
from src.handlers.profile_handler import create_profile, update_profile
from src.models.user import User
from src.models.veteran_profile import VeteranProfile
from src.repositories.veteran_profile_repository import VeteranProfileRepository


class TestBusinessTitleGenerationIntegration:
    """Integration tests for business title generation end-to-end flow."""

    def setup_method(self):
        """Set up test fixtures."""
        self.handler = BusinessTitleHandler()
        self.test_user_id = "integration-test-user-123"
        self.test_token = "test-jwt-token"

    @patch("src.handlers.business_title_handler.get_user_from_token")
    @patch("src.handlers.business_title_handler.get_ai_service")
    @pytest.mark.asyncio
    async def test_business_title_generation_end_to_end(
        self, mock_get_ai_service, mock_get_user
    ):
        """
        Test complete business title generation flow from request to DynamoDB persistence.
        
        Validates:
        - Handler receives request and authenticates user
        - AI service generates titles
        - Title generation history is stored in DynamoDB
        - Response contains all required fields
        """
        # Mock authentication
        mock_get_user.return_value = {"user_id": self.test_user_id}

        # Mock user data
        mock_user = User(
            user_id=self.test_user_id,
            employee_id="emp123",
            email="test@example.com",
            name="John Doe",
            department="Engineering",
            join_date="2020-01-01T00:00:00Z",
            role="veteran",
            is_active=True,
            created_at="2020-01-01T00:00:00Z",
            updated_at="2020-01-01T00:00:00Z",
        )

        # Mock profile data
        mock_profile = VeteranProfile(
            user_id=self.test_user_id,
            business_title="Software Engineer",
            skills=[
                {"name": "Python", "level": "Expert", "years": 5, "certifications": []},
                {"name": "AWS", "level": "Advanced", "years": 3, "certifications": []},
            ],
            experiences=[
                {
                    "title": "Software Engineer",
                    "department": "Engineering",
                    "duration": 36,
                    "achievements": ["Led team of 5 developers"],
                }
            ],
            preferences={"preferred_roles": ["Senior Engineer", "Tech Lead"]},
            privacy_settings={},
            questionnaire_responses=[],
            is_publicly_visible="false",
            last_updated="2020-01-01T00:00:00Z",
        )

        # Mock AI service response
        titles_data = {
            "titles": [
                {
                    "title": "Senior Software Architect",
                    "description": "Combines technical expertise with leadership",
                    "focus_areas": ["Architecture", "Leadership", "Innovation"],
                    "market_appeal": "high",
                },
                {
                    "title": "Technical Lead Engineer",
                    "description": "Leads technical initiatives and mentors team",
                    "focus_areas": ["Leadership", "Mentoring", "Technical Excellence"],
                    "market_appeal": "high",
                },
            ],
            "recommended_title": "Senior Software Architect",
            "reasoning": "Best reflects technical and leadership skills",
        }

        # Mock AI service
        mock_ai_service = Mock()
        mock_ai_service.generate_business_titles = AsyncMock(return_value=titles_data)
        mock_get_ai_service.return_value = mock_ai_service

        # Replace handler's AI service
        self.handler.ai_service = mock_ai_service

        # Mock repositories
        self.handler.user_repo.get_by_id = AsyncMock(return_value=mock_user)
        self.handler.profile_repo.get_by_user_id = AsyncMock(return_value=mock_profile)
        
        # Track update_profile calls to verify persistence
        update_calls = []
        
        async def mock_update_profile(user_id: str, update_data: Dict[str, Any]):
            update_calls.append({"user_id": user_id, "update_data": update_data})
            return True
        
        self.handler.profile_repo.update_profile = mock_update_profile

        # Create test event
        event = {
            "headers": {"Authorization": f"Bearer {self.test_token}"},
        }

        # Execute the handler
        result = await self.handler._generate_business_titles_async(event, {})

        # Verify response structure
        assert result["statusCode"] == 200
        response_body = json.loads(result["body"])
        
        # Verify all required fields are present
        assert "titles" in response_body
        assert "recommended_title" in response_body
        assert "reasoning" in response_body
        assert "generated_at" in response_body
        
        # Verify titles data
        assert len(response_body["titles"]) == 2
        assert response_body["recommended_title"] == "Senior Software Architect"
        assert response_body["reasoning"] == "Best reflects technical and leadership skills"
        
        # Verify DynamoDB persistence - check that update_profile was called
        assert len(update_calls) == 1
        update_call = update_calls[0]
        assert update_call["user_id"] == self.test_user_id
        assert "title_generation_history" in update_call["update_data"]
        
        # Verify history structure
        history = update_call["update_data"]["title_generation_history"]
        assert len(history) > 0
        latest_generation = history[-1]
        assert "generated_at" in latest_generation
        assert "titles" in latest_generation
        assert "recommended_title" in latest_generation
        assert latest_generation["recommended_title"] == "Senior Software Architect"
        assert latest_generation["regenerated"] is False

    @patch("src.handlers.business_title_handler.get_user_from_token")
    @pytest.mark.asyncio
    async def test_business_title_selection_with_history_tracking(
        self, mock_get_user
    ):
        """
        Test business title selection with history preservation.
        
        Validates:
        - Title selection updates profile
        - Title history is maintained with previous title
        - Timestamp is recorded
        - DynamoDB is updated with correct parameters
        """
        mock_get_user.return_value = {"user_id": self.test_user_id}

        # Mock profile with existing title
        mock_profile = VeteranProfile(
            user_id=self.test_user_id,
            business_title="Software Engineer",
            skills=[],
            experiences=[],
            preferences={},
            privacy_settings={},
            questionnaire_responses=[],
            is_publicly_visible="false",
            last_updated="2020-01-01T00:00:00Z",
        )
        mock_profile.title_history = []

        self.handler.profile_repo.get_by_user_id = AsyncMock(return_value=mock_profile)
        
        # Track update calls
        update_calls = []
        
        async def mock_update_profile(user_id: str, update_data: Dict[str, Any]):
            update_calls.append({"user_id": user_id, "update_data": update_data})
            return True
        
        self.handler.profile_repo.update_profile = mock_update_profile

        # Create selection event
        event = {
            "headers": {"Authorization": f"Bearer {self.test_token}"},
            "body": json.dumps({"title": "Senior Software Architect"}),
        }

        # Execute selection
        result = await self.handler._select_business_title_async(event, {})

        # Verify response
        assert result["statusCode"] == 200
        response_body = json.loads(result["body"])
        assert response_body["title"] == "Senior Software Architect"
        assert "updated_at" in response_body

        # Verify DynamoDB update
        assert len(update_calls) == 1
        update_call = update_calls[0]
        assert update_call["user_id"] == self.test_user_id
        
        update_data = update_call["update_data"]
        assert update_data["business_title"] == "Senior Software Architect"
        assert "title_history" in update_data
        
        # Verify history structure
        history = update_data["title_history"]
        assert len(history) == 1
        history_entry = history[0]
        assert history_entry["title"] == "Senior Software Architect"
        assert history_entry["previous_title"] == "Software Engineer"
        assert "selected_at" in history_entry


class TestProfileUpdateIntegration:
    """Integration tests for profile update end-to-end flow."""

    def setup_method(self):
        """Set up test fixtures."""
        self.test_user_id = "integration-test-user-456"
        self.mock_user = {
            "user_id": self.test_user_id,
            "role": "veteran",
            "email": "test@example.com",
        }

    @patch("src.handlers.profile_handler.VeteranProfileRepository")
    @patch("src.handlers.profile_handler.security_auditor")
    @patch("src.handlers.profile_handler.extract_request_info")
    def test_profile_update_end_to_end(
        self, mock_extract_info, mock_auditor, mock_repo_class
    ):
        """
        Test complete profile update flow from request to DynamoDB persistence.
        
        Validates:
        - Handler receives update request
        - Profile is retrieved from DynamoDB
        - Update data is validated
        - Profile is updated in DynamoDB with correct parameters
        - Updated profile is returned in response
        """
        mock_extract_info.return_value = {"source_ip": "127.0.0.1"}
        
        # Mock repository
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

        # Mock existing profile
        existing_profile = VeteranProfile(
            user_id=self.test_user_id,
            business_title="Software Engineer",
            skills=[
                {"name": "Python", "level": "Advanced", "years": 3, "certifications": []}
            ],
            experiences=[],
            preferences={},
            privacy_settings={},
            questionnaire_responses=[],
            is_publicly_visible="false",
            last_updated="2020-01-01T00:00:00Z",
        )

        # Mock updated profile
        updated_profile = VeteranProfile(
            user_id=self.test_user_id,
            business_title="Senior Software Engineer",
            skills=[
                {"name": "Python", "level": "Expert", "years": 5, "certifications": []},
                {"name": "AWS", "level": "Advanced", "years": 2, "certifications": []},
            ],
            experiences=[],
            preferences={"preferred_roles": ["Tech Lead"]},
            privacy_settings={},
            questionnaire_responses=[],
            is_publicly_visible="false",
            last_updated=datetime.now(timezone.utc).isoformat(),
        )

        # Mock repository methods
        mock_repo.get_profile.side_effect = [existing_profile, updated_profile]
        mock_repo.update_profile.return_value = True

        # Create update event
        update_data = {
            "business_title": "Senior Software Engineer",
            "skills": [
                {"name": "Python", "level": "Expert", "years": 5, "certifications": []},
                {"name": "AWS", "level": "Advanced", "years": 2, "certifications": []},
            ],
            "preferences": {"preferred_roles": ["Tech Lead"]},
        }

        event = {
            "user": self.mock_user,
            "path": f"/profiles/{self.test_user_id}",
            "body": json.dumps(update_data),
            "profile_user_id": self.test_user_id,
        }

        # Execute update
        result = update_profile(event, {})

        # Verify response
        assert result["statusCode"] == 200
        response_body = json.loads(result["body"])
        assert response_body["message"] == "Profile updated successfully"
        assert "updated_fields" in response_body
        assert "profile" in response_body
        
        # Verify updated fields
        assert set(response_body["updated_fields"]) == {"business_title", "skills", "preferences"}
        
        # Verify profile data in response
        profile_data = response_body["profile"]
        assert profile_data["business_title"] == "Senior Software Engineer"
        assert len(profile_data["skills"]) == 2
        assert profile_data["preferences"]["preferred_roles"] == ["Tech Lead"]

        # Verify repository was called with correct parameters
        mock_repo.update_profile.assert_called_once()
        call_args = mock_repo.update_profile.call_args
        assert call_args[0][0] == self.test_user_id  # user_id
        assert call_args[0][1] == update_data  # update_data dictionary

        # Verify security audit was logged
        mock_auditor.log_profile_access.assert_called_once()

    @patch("src.handlers.profile_handler.VeteranProfileRepository")
    @patch("src.handlers.profile_handler.security_auditor")
    @patch("src.handlers.profile_handler.extract_request_info")
    def test_profile_update_with_validation_error(
        self, mock_extract_info, mock_auditor, mock_repo_class
    ):
        """
        Test profile update with invalid data.
        
        Validates:
        - Invalid data causes repository validation to fail
        - Error is propagated to handler
        - Appropriate error response is returned
        """
        mock_extract_info.return_value = {"source_ip": "127.0.0.1"}
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

        # Mock existing profile
        existing_profile = VeteranProfile(
            user_id=self.test_user_id,
            business_title="Software Engineer",
            skills=[],
            experiences=[],
            preferences={},
            privacy_settings={},
            questionnaire_responses=[],
            is_publicly_visible="false",
            last_updated="2020-01-01T00:00:00Z",
        )

        mock_repo.get_profile.return_value = existing_profile
        
        # Mock repository to raise validation error
        mock_repo.update_profile.side_effect = ValueError(
            "Profile validation failed: Skill 'Python' missing required field 'level'"
        )

        # Create event with invalid data (missing required skill fields)
        invalid_update = {
            "skills": [{"name": "Python"}]  # Missing level and years
        }

        event = {
            "user": self.mock_user,
            "path": f"/profiles/{self.test_user_id}",
            "body": json.dumps(invalid_update),
            "profile_user_id": self.test_user_id,
        }

        # Execute update
        result = update_profile(event, {})

        # Verify error response
        assert result["statusCode"] == 400
        response_body = json.loads(result["body"])
        assert "error" in response_body

        # Verify update was attempted but failed validation
        mock_repo.update_profile.assert_called_once()


class TestErrorHandlingIntegration:
    """Integration tests for error handling scenarios across handlers."""

    def setup_method(self):
        """Set up test fixtures."""
        self.handler = BusinessTitleHandler()
        self.test_user_id = "integration-test-user-789"

    @patch("src.handlers.business_title_handler.get_user_from_token")
    @pytest.mark.asyncio
    async def test_authentication_error_flow(self, mock_get_user):
        """
        Test authentication error handling end-to-end.
        
        Validates:
        - Missing token returns 401
        - Invalid token returns 401
        - Error response has correct format
        """
        # Test missing token
        event_no_token = {"headers": {}}
        result = await self.handler._generate_business_titles_async(event_no_token, {})
        
        assert result["statusCode"] == 401
        response_body = json.loads(result["body"])
        assert "error" in response_body

        # Test invalid token
        mock_get_user.return_value = None
        event_invalid_token = {"headers": {"Authorization": "Bearer invalid_token"}}
        result = await self.handler._generate_business_titles_async(event_invalid_token, {})
        
        assert result["statusCode"] == 401
        response_body = json.loads(result["body"])
        assert "error" in response_body

    @patch("src.handlers.business_title_handler.get_user_from_token")
    @pytest.mark.asyncio
    async def test_authorization_error_flow(self, mock_get_user):
        """
        Test authorization error handling (non-veteran user).
        
        Validates:
        - Non-veteran users are denied access
        - Returns 403 Forbidden
        - Error response has correct format
        """
        mock_get_user.return_value = {"user_id": self.test_user_id}

        # Mock non-veteran user
        mock_user = User(
            user_id=self.test_user_id,
            employee_id="emp123",
            email="test@example.com",
            name="John Doe",
            department="Engineering",
            join_date="2020-01-01T00:00:00Z",
            role="admin",  # Not veteran
            is_active=True,
            created_at="2020-01-01T00:00:00Z",
            updated_at="2020-01-01T00:00:00Z",
        )

        self.handler.user_repo.get_by_id = AsyncMock(return_value=mock_user)

        event = {"headers": {"Authorization": "Bearer valid_token"}}
        result = await self.handler._generate_business_titles_async(event, {})

        assert result["statusCode"] == 403
        response_body = json.loads(result["body"])
        assert "error" in response_body
        assert "Access denied" in response_body["error"]

    @patch("src.handlers.business_title_handler.get_user_from_token")
    @pytest.mark.asyncio
    async def test_not_found_error_flow(self, mock_get_user):
        """
        Test not found error handling (profile doesn't exist).
        
        Validates:
        - Missing profile returns 404
        - Error response has correct format
        """
        mock_get_user.return_value = {"user_id": self.test_user_id}

        # Mock veteran user
        mock_user = User(
            user_id=self.test_user_id,
            employee_id="emp123",
            email="test@example.com",
            name="John Doe",
            department="Engineering",
            join_date="2020-01-01T00:00:00Z",
            role="veteran",
            is_active=True,
            created_at="2020-01-01T00:00:00Z",
            updated_at="2020-01-01T00:00:00Z",
        )

        self.handler.user_repo.get_by_id = AsyncMock(return_value=mock_user)
        self.handler.profile_repo.get_by_user_id = AsyncMock(return_value=None)

        event = {"headers": {"Authorization": "Bearer valid_token"}}
        result = await self.handler._generate_business_titles_async(event, {})

        assert result["statusCode"] == 404
        response_body = json.loads(result["body"])
        assert "error" in response_body
        assert "Profile not found" in response_body["error"]

    @patch("src.handlers.business_title_handler.get_user_from_token")
    @pytest.mark.asyncio
    async def test_validation_error_flow(self, mock_get_user):
        """
        Test validation error handling (invalid request body).
        
        Validates:
        - Invalid JSON returns 400
        - Missing required fields returns 400
        - Error response has correct format
        """
        mock_get_user.return_value = {"user_id": self.test_user_id}

        # Test invalid JSON
        event_invalid_json = {
            "headers": {"Authorization": "Bearer valid_token"},
            "body": "invalid json",
        }
        result = await self.handler._select_business_title_async(event_invalid_json, {})
        
        assert result["statusCode"] == 400
        response_body = json.loads(result["body"])
        assert "error" in response_body

        # Test missing required field
        event_missing_field = {
            "headers": {"Authorization": "Bearer valid_token"},
            "body": json.dumps({}),  # Missing 'title' field
        }
        result = await self.handler._select_business_title_async(event_missing_field, {})
        
        assert result["statusCode"] == 400
        response_body = json.loads(result["body"])
        assert "error" in response_body
        assert "Missing title" in response_body["error"]

    @patch("src.handlers.business_title_handler.get_user_from_token")
    @patch("src.handlers.business_title_handler.get_ai_service")
    @pytest.mark.asyncio
    async def test_server_error_flow(self, mock_get_ai_service, mock_get_user):
        """
        Test server error handling (AI service failure).
        
        Validates:
        - Service failures return 500
        - Error is logged
        - Error response has correct format
        """
        mock_get_user.return_value = {"user_id": self.test_user_id}

        # Mock user and profile
        mock_user = User(
            user_id=self.test_user_id,
            employee_id="emp123",
            email="test@example.com",
            name="John Doe",
            department="Engineering",
            join_date="2020-01-01T00:00:00Z",
            role="veteran",
            is_active=True,
            created_at="2020-01-01T00:00:00Z",
            updated_at="2020-01-01T00:00:00Z",
        )

        mock_profile = VeteranProfile(
            user_id=self.test_user_id,
            business_title="Engineer",
            skills=[],
            experiences=[],
            preferences={},
            privacy_settings={},
            questionnaire_responses=[],
            is_publicly_visible="false",
            last_updated="2020-01-01T00:00:00Z",
        )

        self.handler.user_repo.get_by_id = AsyncMock(return_value=mock_user)
        self.handler.profile_repo.get_by_user_id = AsyncMock(return_value=mock_profile)

        # Mock AI service to raise exception
        mock_ai_service = Mock()
        mock_ai_service.generate_business_titles = AsyncMock(
            side_effect=Exception("AI service unavailable")
        )
        mock_get_ai_service.return_value = mock_ai_service
        self.handler.ai_service = mock_ai_service

        event = {"headers": {"Authorization": "Bearer valid_token"}}
        result = await self.handler._generate_business_titles_async(event, {})

        assert result["statusCode"] == 500
        response_body = json.loads(result["body"])
        assert "error" in response_body


class TestProfileUpdateBodyParsingIntegration:
    """
    Integration tests for profile update body parsing fix.
    
    Feature: fix-profile-update-body-parsing
    Validates: Requirements 1.5, 2.4, 3.4
    """

    def setup_method(self):
        """Set up test fixtures."""
        self.test_user_id = "integration-test-body-parsing"
        self.mock_user = {
            "user_id": self.test_user_id,
            "role": "veteran",
            "email": "test@example.com",
        }

    @patch("src.handlers.profile_handler.VeteranProfileRepository")
    @patch("src.handlers.profile_handler.security_auditor")
    @patch("src.handlers.profile_handler.extract_request_info")
    def test_profile_update_with_string_body_full_handler(
        self, mock_extract_info, mock_auditor, mock_repo_class
    ):
        """
        Test profile update with JSON string body through full handler.
        
        Validates:
        - String body is correctly parsed to dictionary
        - Profile update succeeds with string body
        - Response contains updated profile data
        - Logging captures body type and parsing
        
        Requirements: 1.5, 3.1, 3.4
        """
        mock_extract_info.return_value = {"source_ip": "127.0.0.1"}
        
        # Mock repository
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

        # Mock existing profile
        existing_profile = VeteranProfile(
            user_id=self.test_user_id,
            business_title="Software Engineer",
            skills=[
                {"name": "Python", "level": "Advanced", "years": 3, "certifications": []}
            ],
            experiences=[],
            preferences={},
            privacy_settings={},
            questionnaire_responses=[],
            is_publicly_visible="false",
            last_updated="2020-01-01T00:00:00Z",
        )

        # Mock updated profile
        updated_profile = VeteranProfile(
            user_id=self.test_user_id,
            business_title="Senior Software Engineer",
            skills=[
                {"name": "Python", "level": "Expert", "years": 5, "certifications": []},
            ],
            experiences=[],
            preferences={},
            privacy_settings={},
            questionnaire_responses=[],
            is_publicly_visible="false",
            last_updated=datetime.now(timezone.utc).isoformat(),
        )

        mock_repo.get_profile.side_effect = [existing_profile, updated_profile]
        mock_repo.update_profile.return_value = True

        # Create update event with STRING body (simulating Lambda proxy integration)
        update_data = {
            "business_title": "Senior Software Engineer",
            "skills": [
                {"name": "Python", "level": "Expert", "years": 5, "certifications": []},
            ],
        }

        event = {
            "user": self.mock_user,
            "path": f"/profiles/{self.test_user_id}",
            "body": json.dumps(update_data),  # STRING body
            "profile_user_id": self.test_user_id,
        }

        # Execute update
        with patch("src.handlers.profile_handler.logger") as mock_logger:
            result = update_profile(event, {})

            # Verify logging captured body type
            mock_logger.info.assert_any_call(
                f"Update profile request body: {update_data}"
            )

        # Verify response
        assert result["statusCode"] == 200
        response_body = json.loads(result["body"])
        assert response_body["message"] == "Profile updated successfully"
        assert "profile" in response_body
        
        # Verify profile data
        profile_data = response_body["profile"]
        assert profile_data["business_title"] == "Senior Software Engineer"
        assert len(profile_data["skills"]) == 1
        assert profile_data["skills"][0]["level"] == "Expert"

        # Verify repository was called correctly
        mock_repo.update_profile.assert_called_once()
        call_args = mock_repo.update_profile.call_args
        assert call_args[0][0] == self.test_user_id
        assert call_args[0][1] == update_data

    @patch("src.handlers.profile_handler.VeteranProfileRepository")
    @patch("src.handlers.profile_handler.security_auditor")
    @patch("src.handlers.profile_handler.extract_request_info")
    def test_profile_update_with_dict_body_full_handler(
        self, mock_extract_info, mock_auditor, mock_repo_class
    ):
        """
        Test profile update with dictionary body through full handler.
        
        Validates:
        - Dictionary body is used directly without parsing
        - Profile update succeeds with dict body
        - Response contains updated profile data
        - Logging captures body type
        
        Requirements: 1.5, 3.1, 3.4
        """
        mock_extract_info.return_value = {"source_ip": "127.0.0.1"}
        
        # Mock repository
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

        # Mock existing profile
        existing_profile = VeteranProfile(
            user_id=self.test_user_id,
            business_title="Engineer",
            skills=[],
            experiences=[],
            preferences={},
            privacy_settings={},
            questionnaire_responses=[],
            is_publicly_visible="false",
            last_updated="2020-01-01T00:00:00Z",
        )

        # Mock updated profile
        updated_profile = VeteranProfile(
            user_id=self.test_user_id,
            business_title="Lead Engineer",
            skills=[],
            experiences=[],
            preferences={"preferred_roles": ["Tech Lead", "Manager"]},
            privacy_settings={},
            questionnaire_responses=[],
            is_publicly_visible="false",
            last_updated=datetime.now(timezone.utc).isoformat(),
        )

        mock_repo.get_profile.side_effect = [existing_profile, updated_profile]
        mock_repo.update_profile.return_value = True

        # Create update event with DICT body (simulating internal call)
        update_data = {
            "business_title": "Lead Engineer",
            "preferences": {"preferred_roles": ["Tech Lead", "Manager"]},
        }

        event = {
            "user": self.mock_user,
            "path": f"/profiles/{self.test_user_id}",
            "body": update_data,  # DICT body (not JSON string)
            "profile_user_id": self.test_user_id,
        }

        # Execute update
        with patch("src.handlers.profile_handler.logger") as mock_logger:
            result = update_profile(event, {})

            # Verify logging captured body type
            mock_logger.info.assert_any_call(
                f"Update profile request body: {update_data}"
            )

        # Verify response
        assert result["statusCode"] == 200
        response_body = json.loads(result["body"])
        assert response_body["message"] == "Profile updated successfully"
        assert "profile" in response_body
        
        # Verify profile data
        profile_data = response_body["profile"]
        assert profile_data["business_title"] == "Lead Engineer"
        assert profile_data["preferences"]["preferred_roles"] == ["Tech Lead", "Manager"]

        # Verify repository was called correctly
        mock_repo.update_profile.assert_called_once()
        call_args = mock_repo.update_profile.call_args
        assert call_args[0][0] == self.test_user_id
        assert call_args[0][1] == update_data

    @patch("src.handlers.profile_handler.VeteranProfileRepository")
    @patch("src.handlers.profile_handler.security_auditor")
    @patch("src.handlers.profile_handler.extract_request_info")
    def test_profile_update_with_invalid_body_type(
        self, mock_extract_info, mock_auditor, mock_repo_class
    ):
        """
        Test profile update with invalid body type (list).
        
        Validates:
        - Invalid body types are rejected
        - Returns 400 error with clear message
        - Error is logged with actual type
        - No database update is attempted
        
        Requirements: 2.2, 2.4, 3.2, 3.3
        """
        mock_extract_info.return_value = {"source_ip": "127.0.0.1"}
        
        # Mock repository
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

        # Create event with INVALID body type (list instead of string/dict)
        event = {
            "user": self.mock_user,
            "path": f"/profiles/{self.test_user_id}",
            "body": ["invalid", "body", "type"],  # LIST body (invalid)
            "profile_user_id": self.test_user_id,
        }

        # Execute update
        with patch("src.handlers.profile_handler.logger") as mock_logger:
            result = update_profile(event, {})

            # Verify error was logged with actual type
            mock_logger.error.assert_called_once()
            error_call = mock_logger.error.call_args[0][0]
            assert "Unexpected body type" in error_call
            assert "list" in error_call

        # Verify error response
        assert result["statusCode"] == 400
        response_body = json.loads(result["body"])
        assert "error" in response_body
        assert response_body["error"] == "Invalid request body format"

        # Verify repository was NOT called
        mock_repo.get_profile.assert_not_called()
        mock_repo.update_profile.assert_not_called()

    @patch("src.handlers.profile_handler.VeteranProfileRepository")
    @patch("src.handlers.profile_handler.security_auditor")
    @patch("src.handlers.profile_handler.extract_request_info")
    def test_profile_update_with_invalid_json_string(
        self, mock_extract_info, mock_auditor, mock_repo_class
    ):
        """
        Test profile update with invalid JSON string.
        
        Validates:
        - Invalid JSON strings are caught
        - Returns 400 error with clear message
        - Error is logged
        - No database update is attempted
        
        Requirements: 2.1, 2.4, 3.2
        """
        mock_extract_info.return_value = {"source_ip": "127.0.0.1"}
        
        # Mock repository
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

        # Create event with INVALID JSON string
        event = {
            "user": self.mock_user,
            "path": f"/profiles/{self.test_user_id}",
            "body": "{invalid json: missing quotes}",  # Invalid JSON
            "profile_user_id": self.test_user_id,
        }

        # Execute update
        result = update_profile(event, {})

        # Verify error response
        assert result["statusCode"] == 400
        response_body = json.loads(result["body"])
        assert "error" in response_body
        assert response_body["error"] == "Invalid JSON in request body"

        # Verify repository was NOT called
        mock_repo.get_profile.assert_not_called()
        mock_repo.update_profile.assert_not_called()

    @patch("src.handlers.profile_handler.VeteranProfileRepository")
    @patch("src.handlers.profile_handler.security_auditor")
    @patch("src.handlers.profile_handler.extract_request_info")
    def test_profile_update_logging_output_verification(
        self, mock_extract_info, mock_auditor, mock_repo_class
    ):
        """
        Test that logging output is correct for each scenario.
        
        Validates:
        - Body type is logged before parsing
        - Parsed body structure is logged after parsing
        - Errors are logged with full context
        - Unexpected types are logged with actual type
        
        Requirements: 3.1, 3.2, 3.3, 3.4
        """
        mock_extract_info.return_value = {"source_ip": "127.0.0.1"}
        
        # Mock repository
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

        # Mock existing profile
        existing_profile = VeteranProfile(
            user_id=self.test_user_id,
            business_title="Engineer",
            skills=[],
            experiences=[],
            preferences={},
            privacy_settings={},
            questionnaire_responses=[],
            is_publicly_visible="false",
            last_updated="2020-01-01T00:00:00Z",
        )

        updated_profile = VeteranProfile(
            user_id=self.test_user_id,
            business_title="Senior Engineer",
            skills=[],
            experiences=[],
            preferences={},
            privacy_settings={},
            questionnaire_responses=[],
            is_publicly_visible="false",
            last_updated=datetime.now(timezone.utc).isoformat(),
        )

        mock_repo.get_profile.side_effect = [existing_profile, updated_profile]
        mock_repo.update_profile.return_value = True

        # Test 1: String body logging
        update_data = {"business_title": "Senior Engineer"}
        event_string = {
            "user": self.mock_user,
            "path": f"/profiles/{self.test_user_id}",
            "body": json.dumps(update_data),
            "profile_user_id": self.test_user_id,
        }

        with patch("src.handlers.profile_handler.logger") as mock_logger:
            result = update_profile(event_string, {})
            
            # Verify body was logged
            assert any(
                "Update profile request body" in str(call)
                for call in mock_logger.info.call_args_list
            )
            
            # Verify body type was logged
            assert any(
                "Body type" in str(call) and "Body keys" in str(call)
                for call in mock_logger.info.call_args_list
            )

        # Test 2: Invalid type logging
        event_invalid = {
            "user": self.mock_user,
            "path": f"/profiles/{self.test_user_id}",
            "body": 12345,  # Number (invalid)
            "profile_user_id": self.test_user_id,
        }

        with patch("src.handlers.profile_handler.logger") as mock_logger:
            result = update_profile(event_invalid, {})
            
            # Verify error was logged with type
            mock_logger.error.assert_called_once()
            error_message = mock_logger.error.call_args[0][0]
            assert "Unexpected body type" in error_message
            assert "int" in error_message


class TestDynamoDBPersistence:
    """Integration tests verifying DynamoDB persistence after operations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.handler = BusinessTitleHandler()
        self.test_user_id = "integration-test-user-persistence"

    @patch("src.handlers.business_title_handler.get_user_from_token")
    @pytest.mark.asyncio
    async def test_title_generation_history_persistence(self, mock_get_user):
        """
        Test that title generation history is persisted to DynamoDB.
        
        Validates:
        - Generation history is stored
        - History contains all required fields
        - Multiple generations are tracked
        - History is limited to last 10 entries
        """
        mock_get_user.return_value = {"user_id": self.test_user_id}

        # Mock profile with existing history
        mock_profile = VeteranProfile(
            user_id=self.test_user_id,
            business_title="Engineer",
            skills=[],
            experiences=[],
            preferences={},
            privacy_settings={},
            questionnaire_responses=[],
            is_publicly_visible="false",
            last_updated="2020-01-01T00:00:00Z",
        )
        
        # Add 9 existing history entries
        mock_profile.title_generation_history = [
            {
                "generated_at": f"2024-01-0{i}T00:00:00Z",
                "titles": [{"title": f"Title {i}"}],
                "recommended_title": f"Title {i}",
                "regenerated": False,
                "title_count": 1,
            }
            for i in range(1, 10)
        ]

        self.handler.profile_repo.get_by_user_id = AsyncMock(return_value=mock_profile)
        
        # Track update calls
        update_calls = []
        
        async def mock_update_profile(user_id: str, update_data: Dict[str, Any]):
            update_calls.append({"user_id": user_id, "update_data": update_data})
            return True
        
        self.handler.profile_repo.update_profile = mock_update_profile

        # Store new generation
        titles_data = {
            "titles": [{"title": "New Title"}],
            "recommended_title": "New Title",
            "reasoning": "Test",
        }

        await self.handler._store_title_generation_history(
            self.test_user_id, titles_data, regenerated=True
        )

        # Verify update was called
        assert len(update_calls) == 1
        update_call = update_calls[0]
        
        # Verify history structure
        history = update_call["update_data"]["title_generation_history"]
        assert len(history) == 10  # Should be limited to 10
        
        # Verify latest entry
        latest = history[-1]
        assert latest["recommended_title"] == "New Title"
        assert latest["regenerated"] is True
        assert "generated_at" in latest
        assert "title_count" in latest

    @patch("src.handlers.business_title_handler.get_user_from_token")
    @pytest.mark.asyncio
    async def test_title_selection_history_persistence(self, mock_get_user):
        """
        Test that title selection history is persisted to DynamoDB.
        
        Validates:
        - Selection history is stored
        - Previous title is recorded
        - Timestamp is recorded
        - History accumulates over multiple selections
        """
        mock_get_user.return_value = {"user_id": self.test_user_id}

        # Mock profile with existing history
        mock_profile = VeteranProfile(
            user_id=self.test_user_id,
            business_title="Software Engineer",
            skills=[],
            experiences=[],
            preferences={},
            privacy_settings={},
            questionnaire_responses=[],
            is_publicly_visible="false",
            last_updated="2020-01-01T00:00:00Z",
        )
        
        mock_profile.title_history = [
            {
                "title": "Software Engineer",
                "selected_at": "2024-01-01T00:00:00Z",
                "previous_title": "Junior Engineer",
            }
        ]

        self.handler.profile_repo.get_by_user_id = AsyncMock(return_value=mock_profile)
        
        # Track update calls
        update_calls = []
        
        async def mock_update_profile(user_id: str, update_data: Dict[str, Any]):
            update_calls.append({"user_id": user_id, "update_data": update_data})
            return True
        
        self.handler.profile_repo.update_profile = mock_update_profile

        # Select new title
        event = {
            "headers": {"Authorization": "Bearer test_token"},
            "body": json.dumps({"title": "Senior Software Engineer"}),
        }

        result = await self.handler._select_business_title_async(event, {})

        # Verify success
        assert result["statusCode"] == 200

        # Verify history was updated
        assert len(update_calls) == 1
        update_call = update_calls[0]
        
        history = update_call["update_data"]["title_history"]
        assert len(history) == 2  # Original + new
        
        # Verify new entry
        latest = history[-1]
        assert latest["title"] == "Senior Software Engineer"
        assert latest["previous_title"] == "Software Engineer"
        assert "selected_at" in latest
