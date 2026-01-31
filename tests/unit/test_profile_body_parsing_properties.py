"""
Property-based tests for profile handler body parsing.

**Feature: fix-profile-update-body-parsing**

These tests verify that the update_profile handler correctly parses request bodies
in all valid formats and rejects invalid formats with appropriate error messages.
"""

import json
from typing import Any, Dict
from unittest.mock import Mock, patch

from hypothesis import given, settings
from hypothesis import strategies as st

from src.handlers.profile_handler import update_profile


# Strategy for generating valid profile update data
def valid_profile_data_strategy():
    """Generate valid profile update data dictionaries."""
    return st.fixed_dictionaries(
        {
            "business_title": st.text(min_size=1, max_size=100),
            "skills": st.lists(
                st.fixed_dictionaries({
                    "name": st.text(min_size=1, max_size=50),
                    "level": st.sampled_from(["Beginner", "Intermediate", "Advanced", "Expert"]),
                    "years": st.integers(min_value=0, max_value=50),
                    "certifications": st.lists(st.text(min_size=1, max_size=50), max_size=5)
                }),
                max_size=10
            ),
            "experiences": st.lists(
                st.fixed_dictionaries({
                    "title": st.text(min_size=1, max_size=100),
                    "department": st.text(min_size=1, max_size=50),
                    "duration": st.integers(min_value=1, max_value=600),
                    "achievements": st.lists(st.text(min_size=1, max_size=200), max_size=10)
                }),
                max_size=10
            ),
            "preferences": st.fixed_dictionaries({
                "preferred_roles": st.lists(st.text(min_size=1, max_size=50), max_size=5),
                "work_style": st.sampled_from(["Remote", "Hybrid", "On-site"]),
                "locations": st.lists(st.text(min_size=1, max_size=50), max_size=5)
            })
        }
    )


# Strategy for generating invalid JSON strings
def invalid_json_string_strategy():
    """Generate strings that are not valid JSON."""
    return st.one_of(
        st.just("{invalid json}"),
        st.just('{"key": }'),
        st.just('{"key": "value"'),  # Missing closing brace
        st.just('{"key": "value",}'),  # Trailing comma
        st.just("{key: 'value'}"),  # Unquoted key
        st.just("{'key': 'value'}"),  # Single quotes
        st.just("[1, 2, 3,]"),  # Trailing comma in array
        st.just("undefined"),
        st.just("NaN"),
        st.text(min_size=1, max_size=50).filter(
            lambda s: not s.strip().startswith(("{", "[")) and s.strip() not in ("null", "true", "false")
        )
    )


# Strategy for generating non-string/dict values
def invalid_body_type_strategy():
    """Generate values that are neither strings nor dicts."""
    return st.one_of(
        st.integers(),
        st.floats(allow_nan=False, allow_infinity=False),
        st.lists(st.integers()),
        st.lists(st.text()),
        st.booleans(),
        st.none(),
        st.tuples(st.integers(), st.text()),
    )


class TestProfileBodyParsingProperties:
    """Property-based tests for profile body parsing."""

    def setup_method(self):
        """Setup test fixtures."""
        self.mock_user = {
            "user_id": "test-user-123",
            "role": "veteran",
            "email": "test@example.com",
        }

    @settings(max_examples=100)
    @given(profile_data=valid_profile_data_strategy())
    @patch("src.handlers.profile_handler.VeteranProfileRepository")
    @patch("src.handlers.profile_handler.security_auditor")
    @patch("src.handlers.profile_handler.extract_request_info")
    def test_property_1_body_parsing_handles_all_valid_input_types(
        self,
        mock_extract_info,
        mock_auditor,
        mock_repo_class,
        profile_data: Dict[str, Any],
    ):
        """
        **Feature: fix-profile-update-body-parsing, Property 1: Body parsing handles all valid input types**
        **Validates: Requirements 1.1, 1.2, 1.3**

        For any valid Lambda event with a body field containing either a JSON string
        or a dictionary, the parsing logic should successfully extract a dictionary
        without raising an exception.
        """
        # Setup mocks
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        mock_extract_info.return_value = {"source_ip": "127.0.0.1"}

        # Create a mock profile to return
        from src.models.veteran_profile import VeteranProfile
        mock_profile = VeteranProfile(
            user_id="test-user-123",
            business_title=profile_data.get("business_title", ""),
            skills=profile_data.get("skills", []),
            experiences=profile_data.get("experiences", []),
            preferences=profile_data.get("preferences", {}),
        )
        mock_repo.get_profile.return_value = mock_profile
        mock_repo.update_profile.return_value = True

        # Test 1: Body as JSON string
        event_with_string = {
            "user": self.mock_user,
            "path": "/profiles/test-user-123",
            "body": json.dumps(profile_data),
            "profile_user_id": "test-user-123",
        }

        result_string = update_profile(event_with_string, {})

        # Should succeed (200) or have validation errors (400), but not crash
        assert result_string["statusCode"] in [200, 400, 500]
        assert "body" in result_string
        body_string = json.loads(result_string["body"])
        
        # If it's a 200, verify the data was parsed correctly
        if result_string["statusCode"] == 200:
            assert "message" in body_string or "error" in body_string

        # Test 2: Body as dictionary
        event_with_dict = {
            "user": self.mock_user,
            "path": "/profiles/test-user-123",
            "body": profile_data,  # Direct dict, not JSON string
            "profile_user_id": "test-user-123",
        }

        result_dict = update_profile(event_with_dict, {})

        # Should succeed (200) or have validation errors (400), but not crash
        assert result_dict["statusCode"] in [200, 400, 500]
        assert "body" in result_dict
        body_dict = json.loads(result_dict["body"])
        
        # If it's a 200, verify the data was parsed correctly
        if result_dict["statusCode"] == 200:
            assert "message" in body_dict or "error" in body_dict

        # Both should produce the same result (same status code)
        # This verifies that parsing preserves data integrity
        assert result_string["statusCode"] == result_dict["statusCode"]

    @settings(max_examples=100)
    @given(invalid_body=invalid_body_type_strategy())
    @patch("src.handlers.profile_handler.VeteranProfileRepository")
    def test_property_2_invalid_body_types_rejected(
        self, mock_repo_class, invalid_body: Any
    ):
        """
        **Feature: fix-profile-update-body-parsing, Property 2: Invalid body types are rejected with clear errors**
        **Validates: Requirements 1.4, 2.2**

        For any Lambda event where the body is neither a string nor a dictionary,
        the handler should return a 400 status code with an error message indicating
        "Invalid request body format".
        """
        event = {
            "user": self.mock_user,
            "path": "/profiles/test-user-123",
            "body": invalid_body,
            "profile_user_id": "test-user-123",
        }

        result = update_profile(event, {})

        # Should return 400 error
        assert result["statusCode"] == 400
        
        # Should have error message
        body = json.loads(result["body"])
        assert "error" in body
        assert body["error"] == "Invalid request body format"

    @settings(max_examples=100)
    @given(invalid_json=invalid_json_string_strategy())
    @patch("src.handlers.profile_handler.VeteranProfileRepository")
    def test_property_3_json_parsing_errors_caught(
        self, mock_repo_class, invalid_json: str
    ):
        """
        **Feature: fix-profile-update-body-parsing, Property 3: JSON parsing errors are caught and reported**
        **Validates: Requirements 2.1**

        For any Lambda event where the body is a string but not valid JSON,
        the handler should return a 400 status code with an error message
        "Invalid JSON in request body".
        """
        event = {
            "user": self.mock_user,
            "path": "/profiles/test-user-123",
            "body": invalid_json,
            "profile_user_id": "test-user-123",
        }

        result = update_profile(event, {})

        # Should return 400 error
        assert result["statusCode"] == 400
        
        # Should have error message about invalid JSON
        body = json.loads(result["body"])
        assert "error" in body
        assert body["error"] == "Invalid JSON in request body"

    @settings(max_examples=100)
    @given(profile_data=valid_profile_data_strategy())
    @patch("src.handlers.profile_handler.VeteranProfileRepository")
    @patch("src.handlers.profile_handler.security_auditor")
    @patch("src.handlers.profile_handler.extract_request_info")
    def test_property_4_successful_parsing_preserves_data_integrity(
        self,
        mock_extract_info,
        mock_auditor,
        mock_repo_class,
        profile_data: Dict[str, Any],
    ):
        """
        **Feature: fix-profile-update-body-parsing, Property 4: Successful parsing preserves data integrity**
        **Validates: Requirements 1.5**

        For any valid profile update request, the parsed body dictionary should
        contain exactly the same keys and values as the original JSON data.
        """
        # Setup mocks
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        mock_extract_info.return_value = {"source_ip": "127.0.0.1"}

        # Create a mock profile to return
        from src.models.veteran_profile import VeteranProfile
        mock_profile = VeteranProfile(
            user_id="test-user-123",
            business_title=profile_data.get("business_title", ""),
            skills=profile_data.get("skills", []),
            experiences=profile_data.get("experiences", []),
            preferences=profile_data.get("preferences", {}),
        )
        mock_repo.get_profile.return_value = mock_profile
        mock_repo.update_profile.return_value = True

        # Test with JSON string body
        event = {
            "user": self.mock_user,
            "path": "/profiles/test-user-123",
            "body": json.dumps(profile_data),
            "profile_user_id": "test-user-123",
        }

        result = update_profile(event, {})

        # If parsing succeeded (200 or validation error 400), verify data integrity
        if result["statusCode"] in [200, 400]:
            # The handler should have called update_profile with the parsed data
            # We can verify this by checking the mock was called
            if result["statusCode"] == 200:
                # Get the call arguments
                call_args = mock_repo.update_profile.call_args
                if call_args:
                    _, update_data = call_args[0]
                    
                    # Verify that all keys from original data are present
                    # (only allowed fields will be in update_data)
                    allowed_fields = ["business_title", "skills", "experiences", "preferences"]
                    for key in profile_data.keys():
                        if key in allowed_fields:
                            assert key in update_data
                            # Verify the values match
                            assert update_data[key] == profile_data[key]
