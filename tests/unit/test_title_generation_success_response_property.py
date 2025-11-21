"""
Property-based tests for title generation success response.

Feature: fix-backend-handler-bugs, Property 6: Title generation success response
Validates: Requirements 1.5
"""

import json
from typing import Any, Dict, List
from unittest.mock import AsyncMock, Mock, patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from src.handlers.business_title_handler import BusinessTitleHandler
from src.models.user import User
from src.models.veteran_profile import VeteranProfile


# Strategy for generating valid title objects
@st.composite
def title_object(draw):
    """Generate a valid title object."""
    return {
        "title": draw(st.text(alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 ', min_size=5, max_size=40)),
        "description": draw(st.text(alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 .,', min_size=10, max_size=80)),
        "focus_areas": draw(st.lists(st.text(alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz', min_size=3, max_size=15), min_size=1, max_size=3)),
        "market_appeal": draw(st.sampled_from(["low", "medium", "high"])),
    }


# Strategy for generating AI service responses
@st.composite
def ai_service_response(draw):
    """Generate a valid AI service response for title generation."""
    titles = draw(st.lists(title_object(), min_size=1, max_size=5))
    recommended_title = draw(st.sampled_from([t["title"] for t in titles]))
    reasoning = draw(st.text(alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 .,', min_size=10, max_size=80))
    
    return {
        "titles": titles,
        "recommended_title": recommended_title,
        "reasoning": reasoning,
    }


# Strategy for generating user data
@st.composite
def user_data(draw):
    """Generate valid user data."""
    user_id = draw(st.text(alphabet='abcdefghijklmnopqrstuvwxyz0123456789', min_size=5, max_size=15))
    name = draw(st.text(alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz ', min_size=3, max_size=20))
    department = draw(st.text(alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz', min_size=3, max_size=15))
    email_name = draw(st.text(alphabet='abcdefghijklmnopqrstuvwxyz', min_size=3, max_size=10))
    return {
        "user_id": user_id,
        "name": name,
        "department": department,
        "email": f"{email_name}@example.com",
    }


# Strategy for generating profile data
@st.composite
def profile_data(draw):
    """Generate valid profile data."""
    return {
        "skills": draw(st.lists(
            st.fixed_dictionaries({
                "name": st.text(alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz', min_size=1, max_size=15),
                "level": st.text(alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz', min_size=1, max_size=10),
                "years": st.integers(min_value=0, max_value=30)
            }),
            min_size=0,
            max_size=3
        )),
        "experiences": draw(st.lists(
            st.fixed_dictionaries({
                "title": st.text(alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz ', min_size=1, max_size=20),
                "department": st.text(alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz', min_size=1, max_size=15),
                "duration": st.integers(min_value=0, max_value=20)
            }),
            min_size=0,
            max_size=3
        )),
        "preferences": draw(st.fixed_dictionaries({
            "preferred_roles": st.lists(st.text(alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz ', min_size=3, max_size=20), min_size=0, max_size=2),
            "career_interests": st.lists(st.text(alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz', min_size=3, max_size=15), min_size=0, max_size=2)
        })),
    }


class TestTitleGenerationSuccessResponse:
    """
    Property-based tests for title generation success response.
    
    Feature: fix-backend-handler-bugs, Property 6: Title generation success response
    Validates: Requirements 1.5
    """
    
    @given(
        user=user_data(),
        profile=profile_data(),
        ai_response=ai_service_response()
    )
    @settings(max_examples=100)
    def test_successful_title_generation_response_structure(
        self,
        user: Dict[str, Any],
        profile: Dict[str, Any],
        ai_response: Dict[str, Any]
    ):
        """
        Property 6: Title generation success response
        
        For any successful business title generation, the response should have 
        status code 200 and include "titles", "recommended_title", and "reasoning" fields.
        
        This property ensures that regardless of the input data (user info, profile data,
        or AI service response), the handler always returns a properly structured success
        response when the operation succeeds.
        
        Validates: Requirements 1.5
        """
        with patch("src.handlers.business_title_handler.get_user_from_token") as mock_get_user, \
             patch("src.handlers.business_title_handler.get_ai_service") as mock_get_ai_service:
            
            # Setup mocks
            mock_get_user.return_value = {"user_id": user["user_id"]}
            
            # Create mock user
            mock_user = User(
                user_id=user["user_id"],
                employee_id="emp123",
                email=user["email"],
                name=user["name"],
                department=user["department"],
                join_date="2020-01-01T00:00:00Z",
                role="veteran",
                is_active=True,
                created_at="2020-01-01T00:00:00Z",
                updated_at="2020-01-01T00:00:00Z",
            )
            
            # Create mock profile
            mock_profile = VeteranProfile(
                user_id=user["user_id"],
                business_title="Current Title",
                skills=profile["skills"],
                experiences=profile["experiences"],
                preferences=profile["preferences"],
                privacy_settings={},
                questionnaire_responses=[],
                is_publicly_visible="false",
                last_updated="2020-01-01T00:00:00Z",
            )
            
            # Mock AI service
            mock_ai_service = Mock()
            mock_ai_service.generate_business_titles = AsyncMock(return_value=ai_response)
            mock_get_ai_service.return_value = mock_ai_service
            
            # Create handler and setup mocks
            handler = BusinessTitleHandler()
            handler.ai_service = mock_ai_service
            handler.user_repo.get_by_id = AsyncMock(return_value=mock_user)
            handler.profile_repo.get_by_user_id = AsyncMock(return_value=mock_profile)
            handler._store_title_generation_history = AsyncMock()
            
            # Create test event
            event = {"headers": {"Authorization": "Bearer valid_token"}}
            
            # Execute the handler using the synchronous wrapper
            result = handler.generate_business_titles(event, {})
            
            # Property: Response must have status code 200
            assert "statusCode" in result, (
                "Success response must include 'statusCode' field"
            )
            assert result["statusCode"] == 200, (
                f"Successful title generation must return status code 200, got {result['statusCode']}"
            )
            
            # Property: Response must have a body
            assert "body" in result, (
                "Success response must include 'body' field"
            )
            
            # Parse the response body
            response_body = json.loads(result["body"])
            
            # Property: Response must include "titles" field
            assert "titles" in response_body, (
                "Success response body must include 'titles' field. "
                "This field contains the list of generated business titles."
            )
            
            # Property: "titles" must be a list
            assert isinstance(response_body["titles"], list), (
                f"'titles' field must be a list, got {type(response_body['titles'])}"
            )
            
            # Property: "titles" list must not be empty
            assert len(response_body["titles"]) > 0, (
                "'titles' list must contain at least one title"
            )
            
            # Property: Response must include "recommended_title" field
            assert "recommended_title" in response_body, (
                "Success response body must include 'recommended_title' field. "
                "This field contains the AI's recommended title from the generated options."
            )
            
            # Property: "recommended_title" must be a string
            assert isinstance(response_body["recommended_title"], str), (
                f"'recommended_title' must be a string, got {type(response_body['recommended_title'])}"
            )
            
            # Property: Response must include "reasoning" field
            assert "reasoning" in response_body, (
                "Success response body must include 'reasoning' field. "
                "This field contains the AI's explanation for the recommendation."
            )
            
            # Property: "reasoning" must be a string
            assert isinstance(response_body["reasoning"], str), (
                f"'reasoning' must be a string, got {type(response_body['reasoning'])}"
            )
            
            # Property: Response should include "generated_at" timestamp
            assert "generated_at" in response_body, (
                "Success response should include 'generated_at' timestamp"
            )
    
    @given(
        titles_count=st.integers(min_value=1, max_value=20)
    )
    @settings(max_examples=100)
    def test_response_preserves_all_generated_titles(
        self,
        titles_count: int
    ):
        """
        Property test: Response includes all titles generated by AI service.
        
        For any number of titles generated by the AI service, the response
        should include all of them in the "titles" field.
        
        Validates: Requirements 1.5
        """
        with patch("src.handlers.business_title_handler.get_user_from_token") as mock_get_user, \
             patch("src.handlers.business_title_handler.get_ai_service") as mock_get_ai_service:
            
            # Setup mocks
            mock_get_user.return_value = {"user_id": "test_user"}
            
            # Generate titles
            generated_titles = [
                {
                    "title": f"Title {i}",
                    "description": f"Description {i}",
                    "focus_areas": ["Area 1", "Area 2"],
                    "market_appeal": "high",
                }
                for i in range(titles_count)
            ]
            
            ai_response = {
                "titles": generated_titles,
                "recommended_title": generated_titles[0]["title"],
                "reasoning": "Test reasoning",
            }
            
            # Create mock user and profile
            mock_user = User(
                user_id="test_user",
                employee_id="emp123",
                email="test@example.com",
                name="Test User",
                department="Engineering",
                join_date="2020-01-01T00:00:00Z",
                role="veteran",
                is_active=True,
                created_at="2020-01-01T00:00:00Z",
                updated_at="2020-01-01T00:00:00Z",
            )
            
            mock_profile = VeteranProfile(
                user_id="test_user",
                business_title="Current Title",
                skills=[],
                experiences=[],
                preferences={},
                privacy_settings={},
                questionnaire_responses=[],
                is_publicly_visible="false",
                last_updated="2020-01-01T00:00:00Z",
            )
            
            # Mock AI service
            mock_ai_service = Mock()
            mock_ai_service.generate_business_titles = AsyncMock(return_value=ai_response)
            mock_get_ai_service.return_value = mock_ai_service
            
            # Create handler and setup mocks
            handler = BusinessTitleHandler()
            handler.ai_service = mock_ai_service
            handler.user_repo.get_by_id = AsyncMock(return_value=mock_user)
            handler.profile_repo.get_by_user_id = AsyncMock(return_value=mock_profile)
            handler._store_title_generation_history = AsyncMock()
            
            # Create test event
            event = {"headers": {"Authorization": "Bearer valid_token"}}
            
            # Execute the handler
            result = handler.generate_business_titles(event, {})
            
            # Parse response
            assert result["statusCode"] == 200
            response_body = json.loads(result["body"])
            
            # Property: Response must include all generated titles
            assert len(response_body["titles"]) == titles_count, (
                f"Response must include all {titles_count} generated titles, "
                f"but got {len(response_body['titles'])}"
            )
            
            # Property: Each title in response matches the generated titles
            for i, title in enumerate(response_body["titles"]):
                assert title == generated_titles[i], (
                    f"Title at index {i} does not match generated title"
                )
    
    @given(
        recommended_index=st.integers(min_value=0, max_value=9)
    )
    @settings(max_examples=100)
    def test_recommended_title_is_from_generated_titles(
        self,
        recommended_index: int
    ):
        """
        Property test: Recommended title is one of the generated titles.
        
        For any AI response, the recommended_title should be one of the
        titles in the titles list.
        
        Validates: Requirements 1.5
        """
        with patch("src.handlers.business_title_handler.get_user_from_token") as mock_get_user, \
             patch("src.handlers.business_title_handler.get_ai_service") as mock_get_ai_service:
            
            # Setup mocks
            mock_get_user.return_value = {"user_id": "test_user"}
            
            # Generate titles
            generated_titles = [
                {
                    "title": f"Title {i}",
                    "description": f"Description {i}",
                    "focus_areas": ["Area 1"],
                    "market_appeal": "high",
                }
                for i in range(10)
            ]
            
            ai_response = {
                "titles": generated_titles,
                "recommended_title": generated_titles[recommended_index]["title"],
                "reasoning": "Test reasoning",
            }
            
            # Create mock user and profile
            mock_user = User(
                user_id="test_user",
                employee_id="emp123",
                email="test@example.com",
                name="Test User",
                department="Engineering",
                join_date="2020-01-01T00:00:00Z",
                role="veteran",
                is_active=True,
                created_at="2020-01-01T00:00:00Z",
                updated_at="2020-01-01T00:00:00Z",
            )
            
            mock_profile = VeteranProfile(
                user_id="test_user",
                business_title="Current Title",
                skills=[],
                experiences=[],
                preferences={},
                privacy_settings={},
                questionnaire_responses=[],
                is_publicly_visible="false",
                last_updated="2020-01-01T00:00:00Z",
            )
            
            # Mock AI service
            mock_ai_service = Mock()
            mock_ai_service.generate_business_titles = AsyncMock(return_value=ai_response)
            mock_get_ai_service.return_value = mock_ai_service
            
            # Create handler and setup mocks
            handler = BusinessTitleHandler()
            handler.ai_service = mock_ai_service
            handler.user_repo.get_by_id = AsyncMock(return_value=mock_user)
            handler.profile_repo.get_by_user_id = AsyncMock(return_value=mock_profile)
            handler._store_title_generation_history = AsyncMock()
            
            # Create test event
            event = {"headers": {"Authorization": "Bearer valid_token"}}
            
            # Execute the handler
            result = handler.generate_business_titles(event, {})
            
            # Parse response
            assert result["statusCode"] == 200
            response_body = json.loads(result["body"])
            
            # Property: Recommended title must be one of the generated titles
            title_strings = [t["title"] for t in response_body["titles"]]
            assert response_body["recommended_title"] in title_strings, (
                f"Recommended title '{response_body['recommended_title']}' must be "
                f"one of the generated titles: {title_strings}"
            )
    
    def test_synchronous_wrapper_returns_success_response(self):
        """
        Test that the synchronous wrapper properly returns success response.
        
        The synchronous wrapper (generate_business_titles) should return the
        same success response structure as the async implementation.
        
        Validates: Requirements 1.5
        """
        with patch("src.handlers.business_title_handler.get_user_from_token") as mock_get_user, \
             patch("src.handlers.business_title_handler.get_ai_service") as mock_get_ai_service:
            
            # Setup mocks
            mock_get_user.return_value = {"user_id": "test_user"}
            
            ai_response = {
                "titles": [
                    {
                        "title": "Test Title",
                        "description": "Test Description",
                        "focus_areas": ["Area 1"],
                        "market_appeal": "high",
                    }
                ],
                "recommended_title": "Test Title",
                "reasoning": "Test reasoning",
            }
            
            # Create mock user and profile
            mock_user = User(
                user_id="test_user",
                employee_id="emp123",
                email="test@example.com",
                name="Test User",
                department="Engineering",
                join_date="2020-01-01T00:00:00Z",
                role="veteran",
                is_active=True,
                created_at="2020-01-01T00:00:00Z",
                updated_at="2020-01-01T00:00:00Z",
            )
            
            mock_profile = VeteranProfile(
                user_id="test_user",
                business_title="Current Title",
                skills=[],
                experiences=[],
                preferences={},
                privacy_settings={},
                questionnaire_responses=[],
                is_publicly_visible="false",
                last_updated="2020-01-01T00:00:00Z",
            )
            
            # Mock AI service
            mock_ai_service = Mock()
            mock_ai_service.generate_business_titles = AsyncMock(return_value=ai_response)
            mock_get_ai_service.return_value = mock_ai_service
            
            # Create handler and setup mocks
            handler = BusinessTitleHandler()
            handler.ai_service = mock_ai_service
            handler.user_repo.get_by_id = AsyncMock(return_value=mock_user)
            handler.profile_repo.get_by_user_id = AsyncMock(return_value=mock_profile)
            handler._store_title_generation_history = AsyncMock()
            
            # Create test event
            event = {"headers": {"Authorization": "Bearer valid_token"}}
            
            # Execute the SYNCHRONOUS wrapper
            result = handler.generate_business_titles(event, {})
            
            # Verify success response structure
            assert result["statusCode"] == 200
            response_body = json.loads(result["body"])
            
            # Verify all required fields are present
            assert "titles" in response_body
            assert "recommended_title" in response_body
            assert "reasoning" in response_body
            assert "generated_at" in response_body
            
            # Verify field types
            assert isinstance(response_body["titles"], list)
            assert isinstance(response_body["recommended_title"], str)
            assert isinstance(response_body["reasoning"], str)
            assert isinstance(response_body["generated_at"], str)
