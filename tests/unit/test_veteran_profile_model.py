"""
Unit tests for VeteranProfile model.
"""

import pytest
from datetime import datetime
from src.models.veteran_profile import VeteranProfile


class TestVeteranProfile:
    """Test cases for VeteranProfile model."""
    
    def test_veteran_profile_creation_valid(self):
        """Test creating a valid veteran profile."""
        profile = VeteranProfile(
            user_id="user123",
            business_title="Senior Software Engineer",
            skills=[{"name": "Python", "level": "Expert", "years": 5, "certifications": []}],
            experiences=[{"title": "Software Engineer", "department": "IT", "duration": 3, "achievements": []}]
        )
        
        assert profile.user_id == "user123"
        assert profile.business_title == "Senior Software Engineer"
        assert len(profile.skills) == 1
        assert len(profile.experiences) == 1
        assert profile.is_publicly_visible == "false"
    
    def test_veteran_profile_validation_valid(self):
        """Test validation of valid veteran profile."""
        profile = VeteranProfile(
            user_id="user123",
            skills=[{"name": "Python", "level": "Expert", "years": 5}],
            experiences=[{"title": "Engineer", "department": "IT", "duration": 3}]
        )
        
        errors = profile.validate()
        assert len(errors) == 0
    
    def test_veteran_profile_validation_missing_user_id(self):
        """Test validation with missing user_id."""
        profile = VeteranProfile(user_id="")
        
        errors = profile.validate()
        assert "user_id is required" in errors
    
    def test_veteran_profile_validation_invalid_skills(self):
        """Test validation with invalid skills format."""
        profile = VeteranProfile(
            user_id="user123",
            skills=[{"name": "Python"}]  # Missing required fields
        )
        
        errors = profile.validate()
        assert any("missing required field" in error for error in errors)
    
    def test_veteran_profile_to_dynamodb_item(self):
        """Test converting profile to DynamoDB item."""
        profile = VeteranProfile(
            user_id="user123",
            business_title="Engineer",
            skills=[{"name": "Python", "level": "Expert", "years": 5}]
        )
        
        item = profile.to_dynamodb_item()
        
        assert item["user_id"] == "user123"
        assert item["business_title"] == "Engineer"
        assert "skills" in item
        assert item["is_publicly_visible"] == "false"
    
    def test_veteran_profile_from_dynamodb_item(self):
        """Test creating profile from DynamoDB item."""
        item = {
            "user_id": "user123",
            "business_title": "Engineer",
            "skills": '[{"name": "Python", "level": "Expert", "years": 5}]',
            "experiences": "[]",
            "preferences": "{}",
            "privacy_settings": "{}",
            "questionnaire_responses": "[]",
            "is_publicly_visible": "true",
            "last_updated": "2023-01-01T00:00:00",
            "created_at": "2023-01-01T00:00:00"
        }
        
        profile = VeteranProfile.from_dynamodb_item(item)
        
        assert profile.user_id == "user123"
        assert profile.business_title == "Engineer"
        assert len(profile.skills) == 1
        assert profile.skills[0]["name"] == "Python"
        assert profile.is_publicly_visible == "true"
    
    def test_update_privacy_settings(self):
        """Test updating privacy settings."""
        profile = VeteranProfile(user_id="user123")
        
        profile.update_privacy_settings({"is_publicly_visible": True})
        
        assert profile.privacy_settings["is_publicly_visible"] is True
        assert profile.is_publicly_visible == "true"
        
        profile.update_privacy_settings({"is_publicly_visible": False})
        
        assert profile.privacy_settings["is_publicly_visible"] is False
        assert profile.is_publicly_visible == "false"