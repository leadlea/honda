"""
Property-based tests for title selection history preservation.

Feature: fix-backend-handler-bugs, Property 7: Title selection history preservation
Validates: Requirements 5.2, 5.3
"""

import json
from datetime import datetime
from typing import Any, Dict, List
from unittest.mock import AsyncMock, patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from src.handlers.business_title_handler import BusinessTitleHandler
from src.models.veteran_profile import VeteranProfile


# Strategy for generating valid title strings
@st.composite
def title_string(draw):
    """Generate a valid business title string."""
    return draw(
        st.text(
            alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 -',
            min_size=5,
            max_size=50
        )
    ).strip()


# Strategy for generating existing title history
@st.composite
def existing_history(draw):
    """Generate existing title history entries."""
    num_entries = draw(st.integers(min_value=0, max_value=5))
    history = []
    
    for i in range(num_entries):
        entry = {
            "title": draw(title_string()),
            "selected_at": f"2024-01-{i+1:02d}T00:00:00Z",
            "previous_title": draw(st.one_of(st.none(), title_string())),
        }
        history.append(entry)
    
    return history


# Strategy for generating profile data
@st.composite
def profile_with_history(draw):
    """Generate a veteran profile with existing title and history."""
    current_title = draw(st.one_of(st.none(), title_string()))
    history = draw(existing_history())
    
    return {
        "current_title": current_title,
        "history": history,
    }


class TestTitleSelectionHistoryPreservation:
    """
    Property-based tests for title selection history preservation.
    
    Feature: fix-backend-handler-bugs, Property 7: Title selection history preservation
    Validates: Requirements 5.2, 5.3
    """
    
    @given(
        profile_data=profile_with_history(),
        new_title=title_string()
    )
    @settings(max_examples=100)
    def test_title_selection_appends_to_history(
        self,
        profile_data: Dict[str, Any],
        new_title: str
    ):
        """
        Property 7: Title selection history preservation
        
        For any business title selection, the system should append a new entry 
        to the title_history array containing the selected title, timestamp, 
        and previous title.
        
        This property ensures that:
        1. The history array grows by exactly one entry
        2. The new entry contains the selected title
        3. The new entry contains the previous title
        4. The new entry contains a timestamp
        5. All existing history entries are preserved
        
        Validates: Requirements 5.2, 5.3
        """
        with patch("src.handlers.business_title_handler.get_user_from_token") as mock_get_user:
            
            # Setup mocks
            mock_get_user.return_value = {"user_id": "test_user"}
            
            # Create mock profile with existing history
            mock_profile = VeteranProfile(
                user_id="test_user",
                business_title=profile_data["current_title"] or "",
                skills=[],
                experiences=[],
                preferences={},
                privacy_settings={},
                questionnaire_responses=[],
                title_history=profile_data["history"].copy(),
                title_generation_history=[],
                is_publicly_visible="false",
                last_updated="2020-01-01T00:00:00Z",
            )
            
            # Create handler and setup mocks
            handler = BusinessTitleHandler()
            handler.profile_repo.get_by_user_id = AsyncMock(return_value=mock_profile)
            handler.profile_repo.update_profile = AsyncMock()
            
            # Create test event
            event = {
                "headers": {"Authorization": "Bearer valid_token"},
                "body": json.dumps({"title": new_title}),
            }
            
            # Execute the handler
            result = handler.select_business_title(event, {})
            
            # Verify response is successful
            assert result["statusCode"] == 200, (
                f"Title selection should succeed, got status {result['statusCode']}"
            )
            
            # Verify update_profile was called
            handler.profile_repo.update_profile.assert_called_once()
            call_args = handler.profile_repo.update_profile.call_args
            
            # Extract the update_data
            user_id = call_args[0][0]
            update_data = call_args[0][1]
            
            # Property 1: user_id should be correct
            assert user_id == "test_user", (
                f"Update should be for correct user, got {user_id}"
            )
            
            # Property 2: update_data must contain title_history
            assert "title_history" in update_data, (
                "Update data must include 'title_history' field"
            )
            
            new_history = update_data["title_history"]
            
            # Property 3: History must be a list
            assert isinstance(new_history, list), (
                f"title_history must be a list, got {type(new_history)}"
            )
            
            # Property 4: History length should increase by exactly 1
            original_length = len(profile_data["history"])
            new_length = len(new_history)
            assert new_length == original_length + 1, (
                f"History should grow by 1 entry. "
                f"Original: {original_length}, New: {new_length}"
            )
            
            # Property 5: All existing history entries should be preserved
            for i, original_entry in enumerate(profile_data["history"]):
                assert new_history[i] == original_entry, (
                    f"Existing history entry at index {i} should be preserved. "
                    f"Expected: {original_entry}, Got: {new_history[i]}"
                )
            
            # Property 6: New entry should be appended at the end
            new_entry = new_history[-1]
            
            # Property 7: New entry must contain "title" field
            assert "title" in new_entry, (
                "New history entry must contain 'title' field"
            )
            
            # Property 8: New entry title must match selected title
            assert new_entry["title"] == new_title, (
                f"New entry title should be '{new_title}', got '{new_entry['title']}'"
            )
            
            # Property 9: New entry must contain "previous_title" field
            assert "previous_title" in new_entry, (
                "New history entry must contain 'previous_title' field"
            )
            
            # Property 10: Previous title should match the profile's current title
            expected_previous = profile_data["current_title"] or ""
            assert new_entry["previous_title"] == expected_previous, (
                f"Previous title should be '{expected_previous}', "
                f"got '{new_entry['previous_title']}'"
            )
            
            # Property 11: New entry must contain "selected_at" field
            assert "selected_at" in new_entry, (
                "New history entry must contain 'selected_at' timestamp"
            )
            
            # Property 12: Timestamp should be a valid ISO format string
            try:
                datetime.fromisoformat(new_entry["selected_at"].replace('Z', '+00:00'))
            except (ValueError, AttributeError) as e:
                pytest.fail(
                    f"'selected_at' should be valid ISO format timestamp, "
                    f"got '{new_entry['selected_at']}': {e}"
                )
    
    @given(
        initial_history_size=st.integers(min_value=0, max_value=10),
        num_selections=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=100)
    def test_multiple_selections_preserve_order(
        self,
        initial_history_size: int,
        num_selections: int
    ):
        """
        Property test: Multiple title selections preserve chronological order.
        
        For any sequence of title selections, each selection should append
        to the history in order, and all previous entries should remain
        in their original positions.
        
        Validates: Requirements 5.2, 5.3
        """
        with patch("src.handlers.business_title_handler.get_user_from_token") as mock_get_user:
            
            # Setup mocks
            mock_get_user.return_value = {"user_id": "test_user"}
            
            # Create initial history
            initial_history = [
                {
                    "title": f"Initial Title {i}",
                    "selected_at": f"2024-01-{i+1:02d}T00:00:00Z",
                    "previous_title": f"Previous {i}" if i > 0 else None,
                }
                for i in range(initial_history_size)
            ]
            
            # Track current state
            current_title = initial_history[-1]["title"] if initial_history else "Original Title"
            current_history = initial_history.copy()
            
            # Create handler
            handler = BusinessTitleHandler()
            
            # Perform multiple selections
            for selection_num in range(num_selections):
                new_title = f"Selected Title {selection_num}"
                
                # Create mock profile with current state
                mock_profile = VeteranProfile(
                    user_id="test_user",
                    business_title=current_title,
                    skills=[],
                    experiences=[],
                    preferences={},
                    privacy_settings={},
                    questionnaire_responses=[],
                    title_history=current_history.copy(),
                    title_generation_history=[],
                    is_publicly_visible="false",
                    last_updated="2020-01-01T00:00:00Z",
                )
                
                handler.profile_repo.get_by_user_id = AsyncMock(return_value=mock_profile)
                handler.profile_repo.update_profile = AsyncMock()
                
                # Create test event
                event = {
                    "headers": {"Authorization": "Bearer valid_token"},
                    "body": json.dumps({"title": new_title}),
                }
                
                # Execute the handler
                result = handler.select_business_title(event, {})
                
                # Verify success
                assert result["statusCode"] == 200
                
                # Get the updated history
                call_args = handler.profile_repo.update_profile.call_args
                update_data = call_args[0][1]
                updated_history = update_data["title_history"]
                
                # Property: History should have grown by 1
                assert len(updated_history) == len(current_history) + 1, (
                    f"Selection {selection_num}: History should grow by 1"
                )
                
                # Property: All previous entries should be preserved in order
                for i, original_entry in enumerate(current_history):
                    assert updated_history[i] == original_entry, (
                        f"Selection {selection_num}: Entry at index {i} should be preserved"
                    )
                
                # Property: New entry should have correct previous_title
                new_entry = updated_history[-1]
                assert new_entry["previous_title"] == current_title, (
                    f"Selection {selection_num}: Previous title should be '{current_title}'"
                )
                
                # Update current state for next iteration
                current_title = new_title
                current_history = updated_history.copy()
    
    @given(
        current_title=st.one_of(st.none(), title_string()),
        new_title=title_string()
    )
    @settings(max_examples=100)
    def test_history_entry_structure(
        self,
        current_title: str,
        new_title: str
    ):
        """
        Property test: History entry has correct structure.
        
        For any title selection, the new history entry should have exactly
        three fields: title, selected_at, and previous_title.
        
        Validates: Requirements 5.2, 5.3
        """
        with patch("src.handlers.business_title_handler.get_user_from_token") as mock_get_user:
            
            # Setup mocks
            mock_get_user.return_value = {"user_id": "test_user"}
            
            # Create mock profile
            mock_profile = VeteranProfile(
                user_id="test_user",
                business_title=current_title or "",
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
            
            # Create handler and setup mocks
            handler = BusinessTitleHandler()
            handler.profile_repo.get_by_user_id = AsyncMock(return_value=mock_profile)
            handler.profile_repo.update_profile = AsyncMock()
            
            # Create test event
            event = {
                "headers": {"Authorization": "Bearer valid_token"},
                "body": json.dumps({"title": new_title}),
            }
            
            # Execute the handler
            result = handler.select_business_title(event, {})
            
            # Verify success
            assert result["statusCode"] == 200
            
            # Get the new history entry
            call_args = handler.profile_repo.update_profile.call_args
            update_data = call_args[0][1]
            history = update_data["title_history"]
            
            assert len(history) == 1, "Should have exactly one history entry"
            
            new_entry = history[0]
            
            # Property: Entry should have exactly the required fields
            required_fields = {"title", "selected_at", "previous_title"}
            actual_fields = set(new_entry.keys())
            
            assert actual_fields == required_fields, (
                f"History entry should have exactly these fields: {required_fields}. "
                f"Got: {actual_fields}"
            )
            
            # Property: Field types should be correct
            assert isinstance(new_entry["title"], str), (
                f"'title' should be string, got {type(new_entry['title'])}"
            )
            
            assert isinstance(new_entry["selected_at"], str), (
                f"'selected_at' should be string, got {type(new_entry['selected_at'])}"
            )
            
            # previous_title can be None or string
            assert new_entry["previous_title"] is None or isinstance(new_entry["previous_title"], str), (
                f"'previous_title' should be None or string, got {type(new_entry['previous_title'])}"
            )
    
    @given(
        history_size=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=100)
    def test_history_preserves_all_fields(
        self,
        history_size: int
    ):
        """
        Property test: All fields in existing history entries are preserved.
        
        For any existing history with various field values, all fields
        should be preserved exactly when a new selection is made.
        
        Validates: Requirements 5.2
        """
        with patch("src.handlers.business_title_handler.get_user_from_token") as mock_get_user:
            
            # Setup mocks
            mock_get_user.return_value = {"user_id": "test_user"}
            
            # Create history with various field values
            existing_history = []
            for i in range(history_size):
                entry = {
                    "title": f"Title {i}",
                    "selected_at": f"2024-01-{i+1:02d}T{i:02d}:00:00Z",
                    "previous_title": f"Previous {i}" if i > 0 else None,
                }
                existing_history.append(entry)
            
            # Create mock profile
            mock_profile = VeteranProfile(
                user_id="test_user",
                business_title="Current Title",
                skills=[],
                experiences=[],
                preferences={},
                privacy_settings={},
                questionnaire_responses=[],
                title_history=existing_history.copy(),
                title_generation_history=[],
                is_publicly_visible="false",
                last_updated="2020-01-01T00:00:00Z",
            )
            
            # Create handler and setup mocks
            handler = BusinessTitleHandler()
            handler.profile_repo.get_by_user_id = AsyncMock(return_value=mock_profile)
            handler.profile_repo.update_profile = AsyncMock()
            
            # Create test event
            event = {
                "headers": {"Authorization": "Bearer valid_token"},
                "body": json.dumps({"title": "New Title"}),
            }
            
            # Execute the handler
            result = handler.select_business_title(event, {})
            
            # Verify success
            assert result["statusCode"] == 200
            
            # Get the updated history
            call_args = handler.profile_repo.update_profile.call_args
            update_data = call_args[0][1]
            new_history = update_data["title_history"]
            
            # Property: All existing entries should be preserved exactly
            for i, original_entry in enumerate(existing_history):
                preserved_entry = new_history[i]
                
                # Check each field is preserved
                for field in ["title", "selected_at", "previous_title"]:
                    assert preserved_entry[field] == original_entry[field], (
                        f"Entry {i}, field '{field}' should be preserved. "
                        f"Expected: {original_entry[field]}, Got: {preserved_entry[field]}"
                    )
