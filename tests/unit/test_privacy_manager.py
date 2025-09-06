"""
Unit tests for privacy manager
"""
from unittest.mock import Mock


from src.models.public_profile import PublicProfile
from src.models.veteran_profile import VeteranProfile
from src.services.privacy_manager import PrivacyManager, privacy_manager


class TestPrivacyManager:
    """Test cases for privacy manager"""

    def setup_method(self):
        """Setup test fixtures"""
        self.mock_profile_repo = Mock()
        self.mock_public_repo = Mock()
        self.privacy_manager = PrivacyManager(
            profile_repo=self.mock_profile_repo,
            public_profile_repo=self.mock_public_repo,
        )

        self.mock_profile = VeteranProfile(
            user_id="test-user-123",
            business_title="Senior Engineer",
            skills=[
                {"name": "Python", "level": "Expert", "years": 5, "certifications": []}
            ],
            experiences=[
                {
                    "title": "Software Engineer",
                    "department": "Engineering",
                    "duration": 36,
                    "achievements": ["Led team of 5"],
                }
            ],
            preferences={"preferred_roles": ["Senior Engineer"]},
            privacy_settings={"is_publicly_visible": False, "external_contact": True},
        )

    def test_update_privacy_settings_success(self):
        """Test successful privacy settings update"""
        # Setup mocks
        self.mock_profile_repo.get_profile.return_value = self.mock_profile
        self.mock_profile_repo.update_profile.return_value = True
        self.mock_public_repo.create_or_update_profile.return_value = True

        privacy_settings = {"is_publicly_visible": True, "external_contact": True}

        result = self.privacy_manager.update_privacy_settings(
            "test-user-123", privacy_settings
        )

        assert result["success"] is True
        assert result["updated_settings"] == privacy_settings
        assert "sync_result" in result
        assert "profile_updated_at" in result

        self.mock_profile_repo.get_profile.assert_called_once_with("test-user-123")
        self.mock_profile_repo.update_profile.assert_called_once()

    def test_update_privacy_settings_profile_not_found(self):
        """Test privacy settings update when profile doesn't exist"""
        self.mock_profile_repo.get_profile.return_value = None

        privacy_settings = {"is_publicly_visible": True}

        result = self.privacy_manager.update_privacy_settings(
            "nonexistent-user", privacy_settings
        )

        assert result["success"] is False
        assert "Profile not found" in result["error"]

    def test_sync_external_visibility_make_public(self):
        """Test syncing when profile is made public"""
        self.mock_public_repo.create_or_update_profile.return_value = True

        # Profile was private, now public
        profile = self.mock_profile
        profile.privacy_settings = {
            "is_publicly_visible": True,
            "external_contact": True,
        }

        result = self.privacy_manager._sync_external_visibility(
            profile, was_public=False
        )

        assert result["sync_performed"] is True
        assert len(result["actions"]) == 1
        assert result["actions"][0]["action"] == "create_public_profile"
        assert result["actions"][0]["success"] is True

        self.mock_public_repo.create_or_update_profile.assert_called_once()

    def test_sync_external_visibility_make_private(self):
        """Test syncing when profile is made private"""
        # Setup mock for delete operation
        self.mock_public_repo.delete_profile.return_value = True

        # Profile was public, now private
        profile = self.mock_profile
        profile.privacy_settings = {
            "is_publicly_visible": False,
            "external_contact": False,
        }

        result = self.privacy_manager._sync_external_visibility(
            profile, was_public=True
        )

        assert result["sync_performed"] is True
        assert len(result["actions"]) == 1
        assert result["actions"][0]["action"] == "remove_public_profile"
        assert result["actions"][0]["success"] is True

        self.mock_public_repo.delete_profile.assert_called_once_with("test-user-123")

    def test_sync_external_visibility_update_public(self):
        """Test syncing when public profile needs update"""
        existing_public_profile = PublicProfile(
            user_id="test-user-123",
            business_title="Old Title",
            skills=[],
            contact_preferences={"allow_contact": False},
        )
        self.mock_public_repo.get_profile.return_value = existing_public_profile
        self.mock_public_repo.update_profile.return_value = True

        # Profile was public and still public
        profile = self.mock_profile
        profile.privacy_settings = {
            "is_publicly_visible": True,
            "external_contact": True,
        }

        result = self.privacy_manager._sync_external_visibility(
            profile, was_public=True
        )

        assert result["sync_performed"] is True
        assert len(result["actions"]) == 1
        assert result["actions"][0]["action"] == "update_public_profile"
        assert result["actions"][0]["success"] is True

        self.mock_public_repo.get_profile.assert_called_once_with("test-user-123")
        self.mock_public_repo.update_profile.assert_called_once()

    def test_create_public_profile_success(self):
        """Test successful public profile creation"""
        self.mock_public_repo.create_or_update_profile.return_value = True

        result = self.privacy_manager._create_public_profile(self.mock_profile)

        assert result["success"] is True
        assert "created successfully" in result["details"]

        self.mock_public_repo.create_or_update_profile.assert_called_once()

    def test_create_public_profile_failure(self):
        """Test public profile creation failure"""
        self.mock_public_repo.create_or_update_profile.return_value = False

        result = self.privacy_manager._create_public_profile(self.mock_profile)

        assert result["success"] is False
        assert "Failed to create" in result["details"]

    def test_remove_public_profile_success(self):
        """Test successful public profile removal"""
        self.mock_public_repo.delete_profile.return_value = True

        result = self.privacy_manager._remove_public_profile("test-user-123")

        assert result["success"] is True
        assert "removed from public visibility" in result["details"]

        self.mock_public_repo.delete_profile.assert_called_once_with("test-user-123")

    def test_get_privacy_status_success(self):
        """Test successful privacy status retrieval"""
        self.mock_profile_repo.get_profile.return_value = self.mock_profile
        mock_public_profile = PublicProfile(
            user_id="test-user-123",
            business_title="Engineer",
            skills=[],
            contact_preferences={"allow_contact": True},
        )
        mock_public_profile.updated_at = "2023-01-01T00:00:00"
        self.mock_public_repo.get_profile.return_value = mock_public_profile

        result = self.privacy_manager.get_privacy_status("test-user-123")

        assert result["success"] is True
        assert "privacy_settings" in result
        assert result["is_publicly_visible"] is False
        assert result["external_contact_allowed"] is True
        assert result["public_profile_exists"] is True
        assert "last_updated" in result
        assert "public_profile_last_updated" in result

    def test_get_privacy_status_profile_not_found(self):
        """Test privacy status when profile doesn't exist"""
        self.mock_profile_repo.get_profile.return_value = None

        result = self.privacy_manager.get_privacy_status("nonexistent-user")

        assert result["success"] is False
        assert "Profile not found" in result["error"]

    def test_validate_privacy_settings_valid(self):
        """Test validation of valid privacy settings"""
        privacy_settings = {"is_publicly_visible": True, "external_contact": False}

        result = self.privacy_manager.validate_privacy_settings(privacy_settings)

        assert result["valid"] is True
        assert len(result["errors"]) == 0

    def test_validate_privacy_settings_invalid_types(self):
        """Test validation of invalid privacy settings types"""
        privacy_settings = {
            "is_publicly_visible": "true",  # Should be boolean
            "external_contact": 1,  # Should be boolean
        }

        result = self.privacy_manager.validate_privacy_settings(privacy_settings)

        assert result["valid"] is False
        assert len(result["errors"]) == 2
        assert "must be a boolean value" in result["errors"][0]
        assert "must be a boolean value" in result["errors"][1]

    def test_validate_privacy_settings_warnings(self):
        """Test validation warnings for privacy settings"""
        privacy_settings = {
            "is_publicly_visible": False,
            "external_contact": True,  # Warning: contact enabled but not public
        }

        result = self.privacy_manager.validate_privacy_settings(privacy_settings)

        assert result["valid"] is True
        assert len(result["warnings"]) == 1
        assert (
            "external_contact is enabled but profile is not publicly visible"
            in result["warnings"][0]
        )

    def test_bulk_privacy_update_success(self):
        """Test successful bulk privacy update"""
        # Setup mocks for successful updates
        self.mock_profile_repo.get_profile.return_value = self.mock_profile
        self.mock_profile_repo.update_profile.return_value = True
        self.mock_public_repo.create_or_update_profile.return_value = True

        privacy_updates = {
            "user1": {"is_publicly_visible": True},
            "user2": {"is_publicly_visible": False},
        }

        result = self.privacy_manager.bulk_privacy_update(privacy_updates)

        assert result["total_processed"] == 2
        assert len(result["successful_updates"]) == 2
        assert len(result["failed_updates"]) == 0
        assert result["success_rate"] == 1.0

    def test_bulk_privacy_update_partial_failure(self):
        """Test bulk privacy update with partial failures"""

        # First user succeeds, second fails
        def mock_get_profile(user_id):
            if user_id == "user1":
                return self.mock_profile
            else:
                return None  # Profile not found

        self.mock_profile_repo.get_profile.side_effect = mock_get_profile
        self.mock_profile_repo.update_profile.return_value = True

        privacy_updates = {
            "user1": {"is_publicly_visible": True},
            "user2": {"is_publicly_visible": False},
        }

        result = self.privacy_manager.bulk_privacy_update(privacy_updates)

        assert result["total_processed"] == 2
        assert len(result["successful_updates"]) == 1
        assert len(result["failed_updates"]) == 1
        assert result["success_rate"] == 0.5
        assert result["failed_updates"][0]["user_id"] == "user2"
        assert "Profile not found" in result["failed_updates"][0]["error"]

    def test_global_privacy_manager_instance(self):
        """Test that global privacy manager instance exists"""
        assert privacy_manager is not None
        assert isinstance(privacy_manager, PrivacyManager)
