"""
Unit tests for questionnaire handler.
"""

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.handlers.questionnaire_handler import (
    generate_questionnaire,
    submit_questionnaire,
    get_questionnaire_history,
    regenerate_questionnaire
)
from src.models.questionnaire import Questionnaire
from src.models.user import User
from src.models.veteran_profile import VeteranProfile


class TestQuestionnaireHandler:
    """Test cases for QuestionnaireHandler class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.handler = QuestionnaireHandler()

    @patch("src.handlers.questionnaire_handler.get_user_from_token")
    @patch("src.handlers.questionnaire_handler.get_ai_service")
    @pytest.mark.asyncio
    async def test_generate_questionnaire_success(
        self, mock_get_ai_service, mock_get_user
    ):
        """Test successful questionnaire generation."""
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
            skills=[],
            experiences=[],
            preferences={},
            privacy_settings={},
            questionnaire_responses=[],
            is_publicly_visible="false",
            last_updated="2020-01-01T00:00:00Z",
        )

        # Mock questionnaire data
        questionnaire_data = {
            "questionnaire_id": "q123",
            "title": "Career Assessment",
            "questions": [
                {
                    "id": "q1",
                    "type": "multiple_choice",
                    "question": "What is your primary skill?",
                    "options": ["Python", "Java", "JavaScript"],
                }
            ],
        }

        # Mock AI service
        mock_ai_service = Mock()
        mock_ai_service.generate_questionnaire = AsyncMock(
            return_value=questionnaire_data
        )
        mock_get_ai_service.return_value = mock_ai_service

        # Replace the handler's AI service with the mock
        self.handler.ai_service = mock_ai_service

        # Mock repositories
        self.handler.user_repo.get_by_id = AsyncMock(return_value=mock_user)
        self.handler.profile_repo.get_by_user_id = AsyncMock(return_value=mock_profile)
        self.handler.questionnaire_repo.get_user_questionnaires = AsyncMock(
            return_value=[]
        )

        mock_questionnaire = Questionnaire(
            questionnaire_id="q123",
            user_id="user123",
            title="Career Assessment",
            description="Test questionnaire",
            questions=[],
            responses=[],
            status="draft",
            ai_generated=True,
            created_at="2024-01-01T00:00:00Z",
            submitted_at=None,
        )
        self.handler.questionnaire_repo.create_questionnaire = AsyncMock(
            return_value=mock_questionnaire
        )

        # Test event
        event = {
            "headers": {"Authorization": "Bearer valid_token"},
            "pathParameters": {},
        }

        # Execute
        result = await self.handler.generate_questionnaire(event, {})

        # Verify
        assert result["statusCode"] == 200
        response_body = json.loads(result["body"])
        assert response_body["questionnaire_id"] == "q123"
        assert "questionnaire" in response_body

    @patch("src.handlers.questionnaire_handler.get_user_from_token")
    @pytest.mark.asyncio
    async def test_generate_questionnaire_unauthorized(self, mock_get_user):
        """Test questionnaire generation with invalid token."""
        mock_get_user.return_value = None

        event = {"headers": {"Authorization": "Bearer invalid_token"}}

        result = await self.handler.generate_questionnaire(event, {})

        assert result["statusCode"] == 401
        response_body = json.loads(result["body"])
        assert "error" in response_body

    @patch("src.handlers.questionnaire_handler.get_user_from_token")
    @pytest.mark.asyncio
    async def test_generate_questionnaire_non_veteran(self, mock_get_user):
        """Test questionnaire generation for non-veteran user."""
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

        result = await self.handler.generate_questionnaire(event, {})

        assert result["statusCode"] == 403
        response_body = json.loads(result["body"])
        assert "Access denied" in response_body["error"]

    @patch("src.handlers.questionnaire_handler.get_user_from_token")
    @pytest.mark.asyncio
    async def test_submit_questionnaire_success(self, mock_get_user):
        """Test successful questionnaire submission."""
        mock_get_user.return_value = {"user_id": "user123"}

        # Mock questionnaire
        mock_questionnaire = Questionnaire(
            questionnaire_id="q123",
            user_id="user123",
            title="Career Assessment",
            description="Test questionnaire",
            questions=[],
            responses=[],
            status="draft",
            ai_generated=True,
            created_at="2024-01-01T00:00:00Z",
            submitted_at=None,
        )

        self.handler.questionnaire_repo.get_by_id = AsyncMock(
            return_value=mock_questionnaire
        )
        self.handler.questionnaire_repo.submit_responses = AsyncMock()
        self.handler._update_profile_from_responses = AsyncMock()

        event = {
            "headers": {"Authorization": "Bearer valid_token"},
            "body": json.dumps(
                {
                    "questionnaire_id": "q123",
                    "responses": [{"question_id": "q1", "answer": "Python"}],
                }
            ),
        }

        result = await self.handler.submit_questionnaire(event, {})

        assert result["statusCode"] == 200
        response_body = json.loads(result["body"])
        assert response_body["message"] == "Questionnaire submitted successfully"
        assert response_body["questionnaire_id"] == "q123"

    @patch("src.handlers.questionnaire_handler.get_user_from_token")
    @pytest.mark.asyncio
    async def test_submit_questionnaire_invalid_json(self, mock_get_user):
        """Test questionnaire submission with invalid JSON."""
        mock_get_user.return_value = {"user_id": "user123"}

        event = {
            "headers": {"Authorization": "Bearer valid_token"},
            "body": "invalid json",
        }

        result = await self.handler.submit_questionnaire(event, {})

        assert result["statusCode"] == 400
        response_body = json.loads(result["body"])
        assert "Invalid JSON" in response_body["error"]

    @patch("src.handlers.questionnaire_handler.get_user_from_token")
    @pytest.mark.asyncio
    async def test_submit_questionnaire_not_found(self, mock_get_user):
        """Test questionnaire submission for non-existent questionnaire."""
        mock_get_user.return_value = {"user_id": "user123"}

        self.handler.questionnaire_repo.get_by_id = AsyncMock(return_value=None)

        event = {
            "headers": {"Authorization": "Bearer valid_token"},
            "body": json.dumps(
                {
                    "questionnaire_id": "nonexistent",
                    "responses": [{"question_id": "q1", "answer": "test"}],
                }
            ),
        }

        result = await self.handler.submit_questionnaire(event, {})

        assert result["statusCode"] == 404
        response_body = json.loads(result["body"])
        assert "not found" in response_body["error"]

    @patch("src.handlers.questionnaire_handler.get_user_from_token")
    @pytest.mark.asyncio
    async def test_get_questionnaire_history_success(self, mock_get_user):
        """Test successful questionnaire history retrieval."""
        mock_get_user.return_value = {"user_id": "user123"}

        # Mock questionnaire history
        mock_questionnaires = [
            Questionnaire(
                questionnaire_id="q1",
                user_id="user123",
                title="Assessment 1",
                description="First assessment",
                questions=[{"id": "q1"}],
                responses=[{"id": "r1"}],
                status="completed",
                ai_generated=True,
                created_at="2024-01-01T00:00:00Z",
                submitted_at="2024-01-01T01:00:00Z",
            ),
            Questionnaire(
                questionnaire_id="q2",
                user_id="user123",
                title="Assessment 2",
                description="Second assessment",
                questions=[{"id": "q1"}, {"id": "q2"}],
                responses=[],
                status="draft",
                ai_generated=True,
                created_at="2024-01-02T00:00:00Z",
                submitted_at=None,
            ),
        ]

        self.handler.questionnaire_repo.get_user_questionnaires = AsyncMock(
            return_value=mock_questionnaires
        )

        event = {"headers": {"Authorization": "Bearer valid_token"}}

        result = await self.handler.get_questionnaire_history(event, {})

        assert result["statusCode"] == 200
        response_body = json.loads(result["body"])
        assert response_body["total_count"] == 2
        assert len(response_body["questionnaires"]) == 2
        assert response_body["questionnaires"][0]["questionnaire_id"] == "q1"
        assert response_body["questionnaires"][0]["status"] == "completed"
        assert response_body["questionnaires"][1]["questionnaire_id"] == "q2"
        assert response_body["questionnaires"][1]["status"] == "draft"

    @patch("src.handlers.questionnaire_handler.get_user_from_token")
    @patch("src.handlers.questionnaire_handler.get_ai_service")
    @pytest.mark.asyncio
    async def test_regenerate_questionnaire_success(
        self, mock_get_ai_service, mock_get_user
    ):
        """Test successful questionnaire regeneration."""
        mock_get_user.return_value = {"user_id": "user123"}

        # Mock original questionnaire
        mock_original = Questionnaire(
            questionnaire_id="q123",
            user_id="user123",
            title="Original Assessment",
            description="Original questionnaire",
            questions=[],
            responses=[{"question_id": "q1", "answer": "Python"}],
            status="completed",
            ai_generated=True,
            created_at="2024-01-01T00:00:00Z",
            submitted_at="2024-01-01T01:00:00Z",
        )

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
            skills=[],
            experiences=[],
            preferences={},
            privacy_settings={},
            questionnaire_responses=[],
            is_publicly_visible="false",
            last_updated="2020-01-01T00:00:00Z",
        )

        # Mock new questionnaire data
        new_questionnaire_data = {
            "questionnaire_id": "q456",
            "title": "Updated Career Assessment",
            "questions": [
                {
                    "id": "q1",
                    "type": "open_ended",
                    "question": "Describe your leadership experience",
                }
            ],
        }

        mock_new_questionnaire = Questionnaire(
            questionnaire_id="q456",
            user_id="user123",
            title="Updated Career Assessment",
            description="Regenerated questionnaire",
            questions=[],
            responses=[],
            status="draft",
            ai_generated=True,
            created_at="2024-01-02T00:00:00Z",
            submitted_at=None,
        )

        # Mock AI service
        mock_ai_service = Mock()
        mock_ai_service.generate_questionnaire = AsyncMock(
            return_value=new_questionnaire_data
        )
        mock_get_ai_service.return_value = mock_ai_service

        # Replace the handler's AI service with the mock
        self.handler.ai_service = mock_ai_service

        # Mock repositories
        self.handler.questionnaire_repo.get_by_id = AsyncMock(
            return_value=mock_original
        )
        self.handler.user_repo.get_by_id = AsyncMock(return_value=mock_user)
        self.handler.profile_repo.get_by_user_id = AsyncMock(return_value=mock_profile)
        self.handler.questionnaire_repo.create_questionnaire = AsyncMock(
            return_value=mock_new_questionnaire
        )

        event = {
            "headers": {"Authorization": "Bearer valid_token"},
            "pathParameters": {"questionnaire_id": "q123"},
        }

        result = await self.handler.regenerate_questionnaire(event, {})

        assert result["statusCode"] == 200
        response_body = json.loads(result["body"])
        assert response_body["questionnaire_id"] == "q456"
        assert response_body["regenerated_from"] == "q123"
        assert "questionnaire" in response_body

    @pytest.mark.asyncio
    async def test_update_profile_from_responses(self):
        """Test profile update from questionnaire responses."""
        # Mock profile
        mock_profile = VeteranProfile(
            user_id="user123",
            business_title="Engineer",
            skills=[
                {"name": "Python", "level": "Expert", "years": 5, "certifications": []}
            ],
            experiences=[],
            preferences={"preferred_roles": ["Developer"]},
            privacy_settings={},
            questionnaire_responses=[],
            is_publicly_visible="false",
            last_updated="2020-01-01T00:00:00Z",
        )

        self.handler.profile_repo.get_by_user_id = AsyncMock(return_value=mock_profile)
        self.handler.profile_repo.update_profile = AsyncMock()

        responses = [
            {"question_id": "skill_q1", "answer": ["JavaScript", "React"]},
            {"question_id": "career_interest_q1", "answer": "Team Lead"},
            {"question_id": "other_q1", "answer": "Some other answer"},
        ]

        await self.handler._update_profile_from_responses("user123", responses)

        # Verify update was called
        self.handler.profile_repo.update_profile.assert_called_once()
        call_args = self.handler.profile_repo.update_profile.call_args

        assert call_args[0][0] == "user123"  # user_id
        update_data = call_args[0][1]

        # Check skills were added
        assert "skills" in update_data
        skill_names = [skill["name"] for skill in update_data["skills"]]
        assert "JavaScript" in skill_names
        assert "React" in skill_names
        assert "Python" in skill_names  # Existing skill preserved

        # Check preferences were updated
        assert "preferences" in update_data
        assert "Team Lead" in update_data["preferences"]["preferred_roles"]
        assert (
            "Developer" in update_data["preferences"]["preferred_roles"]
        )  # Existing preserved

        # Check questionnaire responses were added
        assert "questionnaire_responses" in update_data
        assert len(update_data["questionnaire_responses"]) == 1
