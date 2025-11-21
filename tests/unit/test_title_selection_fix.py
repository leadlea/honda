"""
Test to verify business title selection and history tracking fix.
"""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from src.handlers.business_title_handler import BusinessTitleHandler
from src.models.veteran_profile import VeteranProfile


class TestTitleSelectionFix:
    """Test cases for title selection and history tracking fix."""

    def setup_method(self):
        """Set up test fixtures."""
        self.handler = BusinessTitleHandler()

    @patch("src.handlers.business_title_handler.get_user_from_token")
    @pytest.mark.asyncio
    async def test_title_selection_updates_history(self, mock_get_user):
        """Test that title selection properly updates history with previous_title and timestamp."""
        mock_get_user.return_value = {"user_id": "user123"}

        # Create profile with existing title and empty history
        mock_profile = VeteranProfile(
            user_id="user123",
            business_title="Software Engineer",
            skills=[],
            experiences=[],
            preferences={},
            privacy_settings={},
            questionnaire_responses=[],
            title_history=[],
            title_generation_history=[],
            is_publicly_visible="false",
            last_updated="2020-01-01T00:00:00Z",
        )

        self.handler.profile_repo.get_by_user_id = AsyncMock(return_value=mock_profile)
        self.handler.profile_repo.update_profile = AsyncMock()

        event = {
            "headers": {"Authorization": "Bearer valid_token"},
            "body": json.dumps({"title": "Senior Software Architect"}),
        }

        # Execute the async method directly
        result = await self.handler._select_business_title_async(event, {})

        # Verify response
        assert result["statusCode"] == 200
        response_body = json.loads(result["body"])
        assert response_body["title"] == "Senior Software Architect"

        # Verify update was called with correct parameters
        self.handler.profile_repo.update_profile.assert_called_once()
        call_args = self.handler.profile_repo.update_profile.call_args
        
        # Check user_id
        assert call_args[0][0] == "user123"
        
        # Check update_data
        update_data = call_args[0][1]
        assert update_data["business_title"] == "Senior Software Architect"
        assert "title_history" in update_data
        
        # Verify history entry structure
        history = update_data["title_history"]
        assert len(history) == 1
        assert history[0]["title"] == "Senior Software Architect"
        assert history[0]["previous_title"] == "Software Engineer"
        assert "selected_at" in history[0]

    @patch("src.handlers.business_title_handler.get_user_from_token")
    @pytest.mark.asyncio
    async def test_title_selection_preserves_existing_history(self, mock_get_user):
        """Test that title selection preserves existing history entries."""
        mock_get_user.return_value = {"user_id": "user123"}

        # Create profile with existing history
        existing_history = [
            {
                "title": "Software Engineer",
                "selected_at": "2023-01-01T00:00:00Z",
                "previous_title": "Junior Engineer",
            }
        ]

        mock_profile = VeteranProfile(
            user_id="user123",
            business_title="Software Engineer",
            skills=[],
            experiences=[],
            preferences={},
            privacy_settings={},
            questionnaire_responses=[],
            title_history=existing_history,
            title_generation_history=[],
            is_publicly_visible="false",
            last_updated="2020-01-01T00:00:00Z",
        )

        self.handler.profile_repo.get_by_user_id = AsyncMock(return_value=mock_profile)
        self.handler.profile_repo.update_profile = AsyncMock()

        event = {
            "headers": {"Authorization": "Bearer valid_token"},
            "body": json.dumps({"title": "Senior Software Architect"}),
        }

        # Execute
        result = await self.handler._select_business_title_async(event, {})

        # Verify
        assert result["statusCode"] == 200
        
        call_args = self.handler.profile_repo.update_profile.call_args
        update_data = call_args[0][1]
        history = update_data["title_history"]
        
        # Should have 2 entries now
        assert len(history) == 2
        
        # First entry should be preserved
        assert history[0]["title"] == "Software Engineer"
        assert history[0]["previous_title"] == "Junior Engineer"
        
        # Second entry should be new
        assert history[1]["title"] == "Senior Software Architect"
        assert history[1]["previous_title"] == "Software Engineer"

    @patch("src.handlers.business_title_handler.get_user_from_token")
    @pytest.mark.asyncio
    async def test_get_title_history_returns_correct_data(self, mock_get_user):
        """Test that get_title_history returns selection and generation history."""
        mock_get_user.return_value = {"user_id": "user123"}

        # Create profile with both types of history
        selection_history = [
            {
                "title": "Senior Software Architect",
                "selected_at": "2024-01-01T00:00:00Z",
                "previous_title": "Software Engineer",
            }
        ]

        generation_history = [
            {
                "generated_at": "2024-01-01T00:00:00Z",
                "titles": [{"title": "Senior Software Architect"}],
                "recommended_title": "Senior Software Architect",
                "reasoning": "Test",
                "regenerated": False,
                "title_count": 1,
            }
        ]

        mock_profile = VeteranProfile(
            user_id="user123",
            business_title="Senior Software Architect",
            skills=[],
            experiences=[],
            preferences={},
            privacy_settings={},
            questionnaire_responses=[],
            title_history=selection_history,
            title_generation_history=generation_history,
            is_publicly_visible="false",
            last_updated="2020-01-01T00:00:00Z",
        )

        self.handler.profile_repo.get_by_user_id = AsyncMock(return_value=mock_profile)

        event = {"headers": {"Authorization": "Bearer valid_token"}}

        # Execute
        result = await self.handler._get_title_history_async(event, {})

        # Verify
        assert result["statusCode"] == 200
        response_body = json.loads(result["body"])
        
        assert response_body["current_title"] == "Senior Software Architect"
        assert len(response_body["selection_history"]) == 1
        assert len(response_body["generation_history"]) == 1
        assert response_body["total_selections"] == 1
        assert response_body["total_generations"] == 1

    def test_veteran_profile_model_includes_history_fields(self):
        """Test that VeteranProfile model includes title_history and title_generation_history fields."""
        profile = VeteranProfile(
            user_id="user123",
            business_title="Engineer",
        )

        # Verify fields exist and have correct default values
        assert hasattr(profile, "title_history")
        assert hasattr(profile, "title_generation_history")
        assert profile.title_history == []
        assert profile.title_generation_history == []

    def test_veteran_profile_serialization_includes_history(self):
        """Test that VeteranProfile serialization includes history fields."""
        history_data = [
            {
                "title": "Senior Engineer",
                "selected_at": "2024-01-01T00:00:00Z",
                "previous_title": "Engineer",
            }
        ]

        profile = VeteranProfile(
            user_id="user123",
            business_title="Senior Engineer",
            title_history=history_data,
        )

        # Serialize to DynamoDB format
        item = profile.to_dynamodb_item()

        # Verify history is included
        assert "title_history" in item
        assert "title_generation_history" in item

        # Deserialize back
        restored_profile = VeteranProfile.from_dynamodb_item(item)

        # Verify history is preserved
        assert restored_profile.title_history == history_data
        assert restored_profile.title_generation_history == []
