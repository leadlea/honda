"""
Property-based tests for profile update persistence.

Feature: fix-backend-handler-bugs, Property 4: Profile update persistence
Validates: Requirements 2.1, 2.3
"""

import json
from typing import Any, Dict
from unittest.mock import Mock, patch

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from src.handlers.profile_handler import update_profile
from src.models.veteran_profile import VeteranProfile
from src.repositories.veteran_profile_repository import VeteranProfileRepository


# Strategy for generating valid profile update data
@st.composite
def profile_update_data(draw):
    """Generate valid profile update data."""
    update_fields = {}
    
    # Use printable ASCII characters for text to avoid issues
    text_alphabet = st.characters(min_codepoint=32, max_codepoint=126, blacklist_characters='\x00\n\r\t')
    
    # Randomly include business_title
    if draw(st.booleans()):
        update_fields["business_title"] = draw(st.text(alphabet=text_alphabet, min_size=1, max_size=50))
    
    # Randomly include skills
    if draw(st.booleans()):
        num_skills = draw(st.integers(min_value=1, max_value=3))
        skills = []
        for _ in range(num_skills):
            skill = {
                "name": draw(st.text(alphabet=text_alphabet, min_size=1, max_size=30)),
                "level": draw(st.sampled_from(["Beginner", "Intermediate", "Advanced", "Expert"])),
                "years": draw(st.integers(min_value=0, max_value=30)),
                "certifications": []
            }
            skills.append(skill)
        update_fields["skills"] = skills
    
    # Randomly include experiences
    if draw(st.booleans()):
        num_experiences = draw(st.integers(min_value=1, max_value=2))
        experiences = []
        for _ in range(num_experiences):
            experience = {
                "title": draw(st.text(alphabet=text_alphabet, min_size=1, max_size=30)),
                "company": draw(st.text(alphabet=text_alphabet, min_size=1, max_size=30)),
                "duration": draw(st.text(alphabet=text_alphabet, min_size=1, max_size=15)),
                "description": draw(st.text(alphabet=text_alphabet, min_size=1, max_size=100))
            }
            experiences.append(experience)
        update_fields["experiences"] = experiences
    
    # Randomly include preferences
    if draw(st.booleans()):
        update_fields["preferences"] = {
            "job_type": draw(st.sampled_from(["full-time", "part-time", "contract"])),
            "remote": draw(st.booleans()),
            "location": draw(st.text(alphabet=text_alphabet, min_size=1, max_size=30))
        }
    
    # Ensure at least one field is present
    if not update_fields:
        update_fields["business_title"] = draw(st.text(alphabet=text_alphabet, min_size=1, max_size=50))
    
    return update_fields


class TestProfileUpdatePersistence:
    """
    Property-based tests for profile update persistence.
    
    Feature: fix-backend-handler-bugs, Property 4: Profile update persistence
    Validates: Requirements 2.1, 2.3
    """
    
    @given(
        user_id=st.text(min_size=1, max_size=50, alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"), 
            whitelist_characters="-_"
        )),
        update_data=profile_update_data()
    )
    @settings(max_examples=100)
    def test_profile_updates_are_persisted_to_dynamodb(
        self, user_id: str, update_data: Dict[str, Any]
    ):
        """
        Property 4: Profile update persistence
        
        For any successful profile update operation, the changes should be 
        persisted to DynamoDB and reflected in subsequent GET requests.
        
        This property ensures that:
        1. Update operations write to DynamoDB
        2. The updated data can be retrieved
        3. The retrieved data matches what was updated
        
        Validates: Requirements 2.1, 2.3
        """
        # Setup mock repository
        with patch("src.handlers.profile_handler.VeteranProfileRepository") as mock_repo_class:
            mock_repo = Mock()
            mock_repo_class.return_value = mock_repo
            
            # Create initial profile state
            initial_profile = VeteranProfile(
                user_id=user_id,
                business_title="Initial Title",
                skills=[{"name": "InitialSkill", "level": "Beginner", "years": 1, "certifications": []}],
                experiences=[],
                preferences={},
                privacy_settings={"is_publicly_visible": False, "external_contact": False},
            )
            
            # Create updated profile with the update_data applied
            updated_profile = VeteranProfile(
                user_id=user_id,
                business_title=update_data.get("business_title", initial_profile.business_title),
                skills=update_data.get("skills", initial_profile.skills),
                experiences=update_data.get("experiences", initial_profile.experiences),
                preferences=update_data.get("preferences", initial_profile.preferences),
                privacy_settings=initial_profile.privacy_settings,
            )
            
            # Mock repository methods
            # First call returns initial profile, second call returns updated profile
            mock_repo.get_profile.side_effect = [initial_profile, updated_profile]
            mock_repo.update_profile.return_value = True
            
            # Create event for update
            event = {
                "user": {"user_id": user_id, "role": "veteran"},
                "path": f"/profiles/{user_id}",
                "body": json.dumps(update_data),
                "profile_user_id": user_id,
            }
            
            # Mock security auditor and request info
            with patch("src.handlers.profile_handler.security_auditor") as mock_auditor, \
                 patch("src.handlers.profile_handler.extract_request_info") as mock_extract_info:
                mock_extract_info.return_value = {"source_ip": "127.0.0.1"}
                
                # Call the update handler
                result = update_profile(event, {})
                
                # PROPERTY VERIFICATION 1: Update should succeed
                assert result["statusCode"] == 200, (
                    f"Update should succeed with status 200, got {result['statusCode']}"
                )
                
                # PROPERTY VERIFICATION 2: Repository update_profile should be called
                assert mock_repo.update_profile.called, (
                    "Repository update_profile method should be called to persist changes"
                )
                
                # PROPERTY VERIFICATION 3: Update was called with correct parameters
                update_call_args = mock_repo.update_profile.call_args
                assert update_call_args[0][0] == user_id, (
                    f"Update should be called with user_id '{user_id}'"
                )
                assert isinstance(update_call_args[0][1], dict), (
                    "Update should be called with update_data dictionary"
                )
                
                # PROPERTY VERIFICATION 4: Profile should be retrieved after update
                # (to return in response)
                assert mock_repo.get_profile.call_count == 2, (
                    "Profile should be retrieved twice: once before update, once after"
                )
                
                # PROPERTY VERIFICATION 5: Response should contain updated data
                response_body = json.loads(result["body"])
                assert "profile" in response_body, (
                    "Response should contain updated profile data"
                )
                
                returned_profile = response_body["profile"]
                
                # Verify each updated field is reflected in the response
                for field, value in update_data.items():
                    assert field in returned_profile, (
                        f"Updated field '{field}' should be in response"
                    )
                    assert returned_profile[field] == value, (
                        f"Field '{field}' should have updated value in response. "
                        f"Expected {value}, got {returned_profile[field]}"
                    )
    

