"""
Property-based tests for repository parameter correctness.

Feature: fix-backend-handler-bugs, Property 3: Repository parameter correctness
Validates: Requirements 2.2
"""

import json
from typing import Any, Dict
from unittest.mock import Mock, patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from src.handlers.profile_handler import update_profile
from src.models.veteran_profile import VeteranProfile


# Strategy for generating valid profile update data
@st.composite
def profile_update_data(draw):
    """Generate valid profile update data."""
    update_fields = {}
    
    # Randomly include business_title
    if draw(st.booleans()):
        update_fields["business_title"] = draw(st.text(min_size=1, max_size=100))
    
    # Randomly include skills
    if draw(st.booleans()):
        num_skills = draw(st.integers(min_value=0, max_value=5))
        skills = []
        for _ in range(num_skills):
            skill = {
                "name": draw(st.text(min_size=1, max_size=50)),
                "level": draw(st.sampled_from(["Beginner", "Intermediate", "Advanced", "Expert"])),
                "years": draw(st.integers(min_value=0, max_value=30)),
                "certifications": []
            }
            skills.append(skill)
        update_fields["skills"] = skills
    
    # Randomly include experiences
    if draw(st.booleans()):
        num_experiences = draw(st.integers(min_value=0, max_value=3))
        experiences = []
        for _ in range(num_experiences):
            experience = {
                "title": draw(st.text(min_size=1, max_size=50)),
                "company": draw(st.text(min_size=1, max_size=50)),
                "duration": draw(st.text(min_size=1, max_size=20)),
                "description": draw(st.text(min_size=1, max_size=200))
            }
            experiences.append(experience)
        update_fields["experiences"] = experiences
    
    # Randomly include preferences
    if draw(st.booleans()):
        update_fields["preferences"] = {
            "job_type": draw(st.sampled_from(["full-time", "part-time", "contract"])),
            "remote": draw(st.booleans()),
            "location": draw(st.text(min_size=1, max_size=50))
        }
    
    return update_fields


class TestRepositoryParameterCorrectness:
    """
    Property-based tests for repository parameter correctness.
    
    Feature: fix-backend-handler-bugs, Property 3: Repository parameter correctness
    Validates: Requirements 2.2
    """
    
    @given(
        user_id=st.text(min_size=1, max_size=50, alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"), 
            whitelist_characters="-_"
        )),
        update_data=profile_update_data()
    )
    @settings(max_examples=100)
    def test_update_profile_calls_repository_with_correct_parameter_types(
        self, user_id: str, update_data: Dict[str, Any]
    ):
        """
        Property 3: Repository parameter correctness
        
        For any call to VeteranProfileRepository.update_profile(), the method 
        should receive exactly two arguments: a user_id string and an 
        update_data dictionary.
        
        This property ensures that the handler never incorrectly passes a 
        VeteranProfile object or any other type to the repository method.
        
        Validates: Requirements 2.2
        """
        # Skip if update_data is empty (handler would reject this)
        if not update_data:
            return
        
        # Setup mock repository
        with patch("src.handlers.profile_handler.VeteranProfileRepository") as mock_repo_class:
            mock_repo = Mock()
            mock_repo_class.return_value = mock_repo
            
            # Create existing profile
            existing_profile = VeteranProfile(
                user_id=user_id,
                business_title="Software Engineer",
                skills=[{"name": "Python", "level": "Expert", "years": 5, "certifications": []}],
                experiences=[],
                preferences={},
                privacy_settings={"is_publicly_visible": False, "external_contact": False},
            )
            
            # Mock repository methods
            mock_repo.get_profile.return_value = existing_profile
            mock_repo.update_profile.return_value = True
            
            # Create event
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
                
                # Call the handler
                result = update_profile(event, {})
                
                # Verify the handler was called
                assert mock_repo.update_profile.called, (
                    "Repository update_profile method should be called"
                )
                
                # Get the call arguments
                call_args = mock_repo.update_profile.call_args
                
                # PROPERTY VERIFICATION: First argument must be user_id (string)
                first_arg = call_args[0][0]
                assert isinstance(first_arg, str), (
                    f"First argument to update_profile must be a string (user_id), "
                    f"but got {type(first_arg).__name__}"
                )
                assert first_arg == user_id, (
                    f"First argument should be user_id '{user_id}', got '{first_arg}'"
                )
                
                # PROPERTY VERIFICATION: Second argument must be update_data (dict)
                second_arg = call_args[0][1]
                assert isinstance(second_arg, dict), (
                    f"Second argument to update_profile must be a dict (update_data), "
                    f"but got {type(second_arg).__name__}"
                )
                
                # PROPERTY VERIFICATION: Should NOT be called with VeteranProfile object
                assert not isinstance(first_arg, VeteranProfile), (
                    "First argument should NOT be a VeteranProfile object. "
                    "The repository expects (user_id: str, update_data: dict)"
                )
                assert not isinstance(second_arg, VeteranProfile), (
                    "Second argument should NOT be a VeteranProfile object. "
                    "The repository expects (user_id: str, update_data: dict)"
                )
                
                # Verify the update_data contains only allowed fields
                allowed_fields = {"business_title", "skills", "experiences", "preferences"}
                for key in second_arg.keys():
                    assert key in allowed_fields, (
                        f"Update data contains disallowed field '{key}'"
                    )
    
    @given(
        user_id=st.text(min_size=1, max_size=50, alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"), 
            whitelist_characters="-_"
        ))
    )
    @settings(max_examples=100)
    def test_repository_method_signature_accepts_correct_types(self, user_id: str):
        """
        Property test: Repository method signature accepts correct parameter types.
        
        For any user_id and update_data, the repository's update_profile method
        should accept these parameters without type errors.
        
        Validates: Requirements 2.2
        """
        from src.repositories.veteran_profile_repository import VeteranProfileRepository
        import inspect
        
        # Get the method signature
        repo = VeteranProfileRepository()
        method = repo.update_profile
        sig = inspect.signature(method)
        
        # Verify parameters exist
        params = list(sig.parameters.keys())
        assert "user_id" in params, (
            "Repository update_profile method must have 'user_id' parameter"
        )
        assert "update_data" in params, (
            "Repository update_profile method must have 'update_data' parameter"
        )
        
        # Verify parameter order (user_id should come before update_data)
        user_id_index = params.index("user_id")
        update_data_index = params.index("update_data")
        assert user_id_index < update_data_index, (
            "Parameter 'user_id' should come before 'update_data' in method signature"
        )
        
        # Verify parameter types from annotations if available
        if sig.parameters["user_id"].annotation != inspect.Parameter.empty:
            assert sig.parameters["user_id"].annotation == str, (
                "Parameter 'user_id' should be annotated as str"
            )
        
        if sig.parameters["update_data"].annotation != inspect.Parameter.empty:
            assert sig.parameters["update_data"].annotation == dict, (
                "Parameter 'update_data' should be annotated as dict"
            )
    
    @given(
        update_data=profile_update_data()
    )
    @settings(max_examples=100)
    def test_handler_never_passes_profile_object_to_repository(
        self, update_data: Dict[str, Any]
    ):
        """
        Property test: Handler never passes VeteranProfile object to repository.
        
        For any update operation, the handler should construct an update_data
        dictionary and pass it to the repository, never passing the profile
        object itself.
        
        This is the core bug that was fixed: the handler was incorrectly calling
        profile_repo.update_profile(existing_profile) instead of
        profile_repo.update_profile(user_id, update_data).
        
        Validates: Requirements 2.2
        """
        # Skip if update_data is empty
        if not update_data:
            return
        
        user_id = "test-user-123"
        
        # Setup mock repository
        with patch("src.handlers.profile_handler.VeteranProfileRepository") as mock_repo_class:
            mock_repo = Mock()
            mock_repo_class.return_value = mock_repo
            
            # Create existing profile
            existing_profile = VeteranProfile(
                user_id=user_id,
                business_title="Software Engineer",
                skills=[],
                experiences=[],
                preferences={},
                privacy_settings={"is_publicly_visible": False, "external_contact": False},
            )
            
            # Mock repository methods
            mock_repo.get_profile.return_value = existing_profile
            mock_repo.update_profile.return_value = True
            
            # Create event
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
                
                # Call the handler
                result = update_profile(event, {})
                
                # Verify the repository method was called
                assert mock_repo.update_profile.called, (
                    "Repository update_profile should be called"
                )
                
                # Get all arguments passed to the repository method
                call_args = mock_repo.update_profile.call_args
                all_args = call_args[0] if call_args[0] else []
                all_kwargs = call_args[1] if call_args[1] else {}
                
                # CRITICAL PROPERTY: No argument should be a VeteranProfile object
                for i, arg in enumerate(all_args):
                    assert not isinstance(arg, VeteranProfile), (
                        f"Argument {i} to update_profile is a VeteranProfile object. "
                        f"This is incorrect! The method expects (user_id: str, update_data: dict)"
                    )
                
                for key, value in all_kwargs.items():
                    assert not isinstance(value, VeteranProfile), (
                        f"Keyword argument '{key}' is a VeteranProfile object. "
                        f"This is incorrect! The method expects (user_id: str, update_data: dict)"
                    )
                
                # Verify correct call pattern: exactly 2 positional arguments
                assert len(all_args) == 2, (
                    f"update_profile should be called with exactly 2 arguments, "
                    f"got {len(all_args)}"
                )
                
                # Verify first argument is string (user_id)
                assert isinstance(all_args[0], str), (
                    f"First argument should be user_id (str), got {type(all_args[0])}"
                )
                
                # Verify second argument is dict (update_data)
                assert isinstance(all_args[1], dict), (
                    f"Second argument should be update_data (dict), got {type(all_args[1])}"
                )
