"""
Test to verify the profile handler repository method call fix.
This test validates that the profile handler correctly calls the repository
with user_id and update_data parameters (Requirements 2.1, 2.2, 2.3).
"""

import json
from unittest.mock import Mock, patch

from src.handlers.profile_handler import update_profile
from src.models.veteran_profile import VeteranProfile


def test_profile_handler_calls_repository_with_correct_parameters():
    """
    Test that update_profile handler calls repository.update_profile
    with correct parameters: user_id (str) and update_data (dict).
    
    This validates Requirements 2.2: "WHEN the profile repository update method 
    is called THEN the system SHALL receive the correct parameters 
    (user_id and update_data dictionary)"
    """
    # Setup mock repository
    with patch("src.handlers.profile_handler.VeteranProfileRepository") as mock_repo_class:
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        
        # Create existing profile
        existing_profile = VeteranProfile(
            user_id="test-user-123",
            business_title="Software Engineer",
            skills=[{"name": "Python", "level": "Expert", "years": 5, "certifications": []}],
            experiences=[],
            preferences={},
            privacy_settings={"is_publicly_visible": False, "external_contact": False},
        )
        
        # Mock repository methods
        mock_repo.get_profile.return_value = existing_profile
        mock_repo.update_profile.return_value = True
        
        # Prepare update data
        update_data = {
            "business_title": "Senior Software Engineer",
            "skills": [{"name": "Python", "level": "Expert", "years": 6, "certifications": []}],
        }
        
        # Create event
        event = {
            "user": {"user_id": "test-user-123", "role": "veteran"},
            "path": "/profiles/test-user-123",
            "body": json.dumps(update_data),
            "profile_user_id": "test-user-123",
        }
        
        # Mock security auditor and request info
        with patch("src.handlers.profile_handler.security_auditor") as mock_auditor, \
             patch("src.handlers.profile_handler.extract_request_info") as mock_extract_info:
            mock_extract_info.return_value = {"source_ip": "127.0.0.1"}
            
            # Call the handler
            result = update_profile(event, {})
            
            # Verify the response
            assert result["statusCode"] == 200
            response_body = json.loads(result["body"])
            assert response_body["message"] == "Profile updated successfully"
            
            # CRITICAL VERIFICATION: Check that update_profile was called with correct parameters
            # It should be called with (user_id: str, update_data: dict), NOT with a profile object
            mock_repo.update_profile.assert_called_once()
            call_args = mock_repo.update_profile.call_args
            
            # Verify first argument is user_id (string)
            assert call_args[0][0] == "test-user-123", "First argument should be user_id string"
            assert isinstance(call_args[0][0], str), "First argument should be a string"
            
            # Verify second argument is update_data (dict)
            assert call_args[0][1] == update_data, "Second argument should be update_data dict"
            assert isinstance(call_args[0][1], dict), "Second argument should be a dictionary"
            
            # Verify it's NOT being called with a VeteranProfile object
            assert not isinstance(call_args[0][0], VeteranProfile), \
                "Should NOT be called with VeteranProfile object as first argument"


def test_repository_update_profile_method_signature():
    """
    Test that the repository update_profile method accepts the correct parameters.
    
    This validates Requirements 2.2: "WHEN the profile repository update method 
    is called THEN the system SHALL receive the correct parameters 
    (user_id and update_data dictionary)"
    """
    from src.repositories.veteran_profile_repository import VeteranProfileRepository
    import inspect
    
    # Get the method signature
    repo = VeteranProfileRepository()
    method = repo.update_profile
    sig = inspect.signature(method)
    
    # Verify parameters
    params = list(sig.parameters.keys())
    assert "user_id" in params, "Method should have user_id parameter"
    assert "update_data" in params, "Method should have update_data parameter"
    
    # Verify parameter types from annotations if available
    if sig.parameters["user_id"].annotation != inspect.Parameter.empty:
        assert sig.parameters["user_id"].annotation == str, "user_id should be typed as str"
    
    if sig.parameters["update_data"].annotation != inspect.Parameter.empty:
        assert sig.parameters["update_data"].annotation == dict, "update_data should be typed as dict"
