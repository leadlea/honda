"""
Unit tests for business title handler.
"""

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.handlers.business_title_handler import BusinessTitleHandler
from src.models.user import User
from src.models.veteran_profile import VeteranProfile


class TestBusinessTitleHandler:
    """Test cases for BusinessTitleHandler class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.handler = BusinessTitleHandler()

    @patch("src.handlers.business_title_handler.get_user_from_token")
    @patch("src.handlers.business_title_handler.get_ai_service")
    @pytest.mark.asyncio
    async def test_generate_business_titles_success(
        self, mock_get_ai_service, mock_get_user
    ):
        """Test successful business title generation."""
        # Mock user authentication
        mock_get_user.return_value = {"user_id": "user123"}

        # Mock user data
        mock_user = User(
            user_id="user123",
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
            user_id="user123",
            business_title="Senior Engineer",
            skills=[
                {"name": "Python", "level": "Expert", "years": 5, "certifications": []}
            ],
            experiences=[
                {
                    "title": "Software Engineer",
                    "department": "Engineering",
                    "duration": 3,
                    "achievements": [],
                }
            ],
            preferences={"preferred_roles": ["Team Lead", "Architect"]},
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

        # Replace the handler's AI service with the mock
        self.handler.ai_service = mock_ai_service

        # Mock repositories
        self.handler.user_repo.get_by_id = AsyncMock(return_value=mock_user)
        self.handler.profile_repo.get_by_user_id = AsyncMock(return_value=mock_profile)
        self.handler._store_title_generation_history = AsyncMock()

        # Test event
        event = {"headers": {"Authorization": "Bearer valid_token"}}

        # Execute
        result = await self.handler.generate_business_titles(event, {})

        # Verify
        assert result["statusCode"] == 200
        response_body = json.loads(result["body"])
        assert len(response_body["titles"]) == 2
        assert response_body["recommended_title"] == "Senior Software Architect"
        assert "reasoning" in response_body
        assert "generated_at" in response_body

    @patch("src.handlers.business_title_handler.get_user_from_token")
    @pytest.mark.asyncio
    async def test_generate_business_titles_no_profile(self, mock_get_user):
        """Test business title generation when profile doesn't exist."""
        mock_get_user.return_value = {"user_id": "user123"}

        # Mock user
        mock_user = User(
            user_id="user123",
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

        result = await self.handler.generate_business_titles(event, {})

        assert result["statusCode"] == 404
        response_body = json.loads(result["body"])
        assert "Profile not found" in response_body["error"]

    @patch("src.handlers.business_title_handler.get_user_from_token")
    @pytest.mark.asyncio
    async def test_select_business_title_success(self, mock_get_user):
        """Test successful business title selection."""
        mock_get_user.return_value = {"user_id": "user123"}

        # Mock profile
        mock_profile = VeteranProfile(
            user_id="user123",
            business_title="Engineer",
            skills=[],
            experiences=[],
            preferences={},
            privacy_settings={},
            questionnaire_responses=[],
            is_publicly_visible="false",
            last_updated="2020-01-01T00:00:00Z",
        )

        self.handler.profile_repo.get_by_user_id = AsyncMock(return_value=mock_profile)
        self.handler.profile_repo.update_profile = AsyncMock()

        event = {
            "headers": {"Authorization": "Bearer valid_token"},
            "body": json.dumps({"title": "Senior Software Architect"}),
        }

        result = await self.handler.select_business_title(event, {})

        assert result["statusCode"] == 200
        response_body = json.loads(result["body"])
        assert response_body["title"] == "Senior Software Architect"
        assert "updated_at" in response_body

        # Verify update was called
        self.handler.profile_repo.update_profile.assert_called_once()
        call_args = self.handler.profile_repo.update_profile.call_args
        assert call_args[0][0] == "user123"  # user_id
        update_data = call_args[0][1]
        assert update_data["business_title"] == "Senior Software Architect"
        assert "title_history" in update_data

    @patch("src.handlers.business_title_handler.get_user_from_token")
    @pytest.mark.asyncio
    async def test_select_business_title_invalid_json(self, mock_get_user):
        """Test business title selection with invalid JSON."""
        mock_get_user.return_value = {"user_id": "user123"}

        event = {
            "headers": {"Authorization": "Bearer valid_token"},
            "body": "invalid json",
        }

        result = await self.handler.select_business_title(event, {})

        assert result["statusCode"] == 400
        response_body = json.loads(result["body"])
        assert "Invalid JSON" in response_body["error"]

    @patch("src.handlers.business_title_handler.get_user_from_token")
    @pytest.mark.asyncio
    async def test_select_business_title_missing_title(self, mock_get_user):
        """Test business title selection with missing title."""
        mock_get_user.return_value = {"user_id": "user123"}

        event = {
            "headers": {"Authorization": "Bearer valid_token"},
            "body": json.dumps({}),
        }

        result = await self.handler.select_business_title(event, {})

        assert result["statusCode"] == 400
        response_body = json.loads(result["body"])
        assert "Missing title" in response_body["error"]

    @patch("src.handlers.business_title_handler.get_user_from_token")
    @patch("src.handlers.business_title_handler.get_ai_service")
    @pytest.mark.asyncio
    async def test_regenerate_business_titles_success(
        self, mock_get_ai_service, mock_get_user
    ):
        """Test successful business title regeneration."""
        mock_get_user.return_value = {"user_id": "user123"}

        # Mock user and profile
        mock_user = User(
            user_id="user123",
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
            user_id="user123",
            business_title="Senior Engineer",
            skills=[{"name": "Python", "level": "Expert"}],
            experiences=[],
            preferences={"preferred_roles": ["Architect"]},
            privacy_settings={},
            questionnaire_responses=[],
            is_publicly_visible="false",
            last_updated="2020-01-01T00:00:00Z",
        )

        # Mock AI service response
        titles_data = {
            "titles": [
                {
                    "title": "Principal Software Engineer",
                    "description": "Senior technical leader",
                    "focus_areas": ["Technical Leadership", "Architecture"],
                    "market_appeal": "high",
                }
            ],
            "recommended_title": "Principal Software Engineer",
            "reasoning": "Reflects senior technical expertise",
        }

        # Mock AI service
        mock_ai_service = Mock()
        mock_ai_service.generate_business_titles = AsyncMock(return_value=titles_data)
        mock_get_ai_service.return_value = mock_ai_service

        # Replace the handler's AI service with the mock
        self.handler.ai_service = mock_ai_service

        # Mock repositories
        self.handler.user_repo.get_by_id = AsyncMock(return_value=mock_user)
        self.handler.profile_repo.get_by_user_id = AsyncMock(return_value=mock_profile)
        self.handler._store_title_generation_history = AsyncMock()

        event = {
            "headers": {"Authorization": "Bearer valid_token"},
            "body": json.dumps(
                {"context": {"additional_interests": ["Innovation", "Mentoring"]}}
            ),
        }

        result = await self.handler.regenerate_business_titles(event, {})

        assert result["statusCode"] == 200
        response_body = json.loads(result["body"])
        assert len(response_body["titles"]) == 1
        assert response_body["recommended_title"] == "Principal Software Engineer"
        assert "regenerated_at" in response_body
        assert "context_used" in response_body

    @patch("src.handlers.business_title_handler.get_user_from_token")
    @pytest.mark.asyncio
    async def test_get_title_history_success(self, mock_get_user):
        """Test successful title history retrieval."""
        mock_get_user.return_value = {"user_id": "user123"}

        # Mock profile with history
        mock_profile = VeteranProfile(
            user_id="user123",
            business_title="Senior Software Architect",
            skills=[],
            experiences=[],
            preferences={},
            privacy_settings={},
            questionnaire_responses=[],
            is_publicly_visible="false",
            last_updated="2020-01-01T00:00:00Z",
        )

        # Add history attributes
        mock_profile.title_history = [
            {
                "title": "Senior Software Architect",
                "selected_at": "2024-01-01T00:00:00Z",
                "previous_title": "Software Engineer",
            }
        ]

        mock_profile.title_generation_history = [
            {
                "generated_at": "2024-01-01T00:00:00Z",
                "titles": [
                    {"title": "Senior Software Architect", "market_appeal": "high"}
                ],
                "recommended_title": "Senior Software Architect",
                "regenerated": False,
                "title_count": 1,
            }
        ]

        self.handler.profile_repo.get_by_user_id = AsyncMock(return_value=mock_profile)

        event = {"headers": {"Authorization": "Bearer valid_token"}}

        result = await self.handler.get_title_history(event, {})

        assert result["statusCode"] == 200
        response_body = json.loads(result["body"])
        assert response_body["current_title"] == "Senior Software Architect"
        assert len(response_body["selection_history"]) == 1
        assert len(response_body["generation_history"]) == 1
        assert response_body["total_generations"] == 1
        assert response_body["total_selections"] == 1

    @pytest.mark.asyncio
    async def test_store_title_generation_history(self):
        """Test storing title generation history."""
        # Mock profile
        mock_profile = VeteranProfile(
            user_id="user123",
            business_title="Engineer",
            skills=[],
            experiences=[],
            preferences={},
            privacy_settings={},
            questionnaire_responses=[],
            is_publicly_visible="false",
            last_updated="2020-01-01T00:00:00Z",
        )

        # Add existing history
        mock_profile.title_generation_history = [
            {
                "generated_at": "2024-01-01T00:00:00Z",
                "titles": [{"title": "Old Title"}],
                "regenerated": False,
            }
        ]

        self.handler.profile_repo.get_by_user_id = AsyncMock(return_value=mock_profile)
        self.handler.profile_repo.update_profile = AsyncMock()

        titles_data = {
            "titles": [{"title": "New Title", "market_appeal": "high"}],
            "recommended_title": "New Title",
            "reasoning": "Test reasoning",
        }

        await self.handler._store_title_generation_history(
            "user123", titles_data, regenerated=True
        )

        # Verify update was called
        self.handler.profile_repo.update_profile.assert_called_once()
        call_args = self.handler.profile_repo.update_profile.call_args

        assert call_args[0][0] == "user123"  # user_id
        update_data = call_args[0][1]

        # Check history was updated
        assert "title_generation_history" in update_data
        history = update_data["title_generation_history"]
        assert len(history) == 2  # Original + new
        assert history[-1]["regenerated"] is True
        assert history[-1]["recommended_title"] == "New Title"
        assert history[-1]["title_count"] == 1

    @patch("src.handlers.business_title_handler.get_user_from_token")
    @pytest.mark.asyncio
    async def test_unauthorized_access(self, mock_get_user):
        """Test unauthorized access to business title endpoints."""
        mock_get_user.return_value = None

        event = {"headers": {"Authorization": "Bearer invalid_token"}}

        # Test all endpoints
        endpoints = [
            self.handler.generate_business_titles,
            self.handler.select_business_title,
            self.handler.regenerate_business_titles,
            self.handler.get_title_history,
        ]

        for endpoint in endpoints:
            result = await endpoint(event, {})
            assert result["statusCode"] == 401
            response_body = json.loads(result["body"])
            assert "Invalid authorization token" in response_body["error"]

    @patch("src.handlers.business_title_handler.get_user_from_token")
    @pytest.mark.asyncio
    async def test_non_veteran_access(self, mock_get_user):
        """Test non-veteran user access to business title generation."""
        mock_get_user.return_value = {"user_id": "user123"}

        # Mock non-veteran user
        mock_user = User(
            user_id="user123",
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

        result = await self.handler.generate_business_titles(event, {})

        assert result["statusCode"] == 403
        response_body = json.loads(result["body"])
        assert "Access denied" in response_body["error"]
