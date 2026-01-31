"""
Veteran Profile repository for DynamoDB operations
"""
import logging
import os
from datetime import datetime
from typing import List, Optional

from ..models.veteran_profile import VeteranProfile
from .base_repository import BaseRepository

logger = logging.getLogger(__name__)


class VeteranProfileRepository(BaseRepository):
    """Repository for veteran profile operations"""

    def __init__(self):
        table_name = f"{os.environ.get('DYNAMODB_TABLE_PREFIX', 'honda-veteran-talent-matching-dev')}-veteran-profiles"
        super().__init__(table_name)

    def create_profile(self, profile: VeteranProfile) -> bool:
        """Create a new veteran profile"""
        try:
            # Validate profile before saving
            errors = profile.validate()
            if errors:
                raise ValueError(f"Profile validation failed: {', '.join(errors)}")

            item = profile.to_dynamodb_item()
            return self.put_item(item)
        except Exception as e:
            logger.error(f"Error creating veteran profile: {e}")
            raise

    def get_profile(self, user_id: str) -> Optional[VeteranProfile]:
        """Get veteran profile by user ID"""
        try:
            item = self.get_item({"user_id": user_id})
            if item:
                return VeteranProfile.from_dynamodb_item(item)
            return None
        except Exception as e:
            logger.error(f"Error getting veteran profile for user {user_id}: {e}")
            raise

    def update_profile(self, user_id: str, update_data: dict) -> bool:
        """Update an existing veteran profile with provided data"""
        try:
            # Get existing profile
            profile = self.get_profile(user_id)
            if not profile:
                raise ValueError(f"Profile not found for user {user_id}")

            # Ensure update_data is a dictionary
            if not isinstance(update_data, dict):
                logger.error(f"update_data is not a dict, it's a {type(update_data)}: {update_data}")
                raise TypeError(f"update_data must be a dictionary, got {type(update_data)}")

            # Update profile fields from update_data
            for key, value in update_data.items():
                if hasattr(profile, key):
                    setattr(profile, key, value)

            # Validate profile before updating
            errors = profile.validate()
            if errors:
                raise ValueError(f"Profile validation failed: {', '.join(errors)}")

            # Update timestamp
            profile.last_updated = datetime.utcnow().isoformat()

            item = profile.to_dynamodb_item()
            return self.put_item(item)
        except Exception as e:
            logger.error(f"Error updating veteran profile: {e}")
            raise

    def delete_profile(self, user_id: str) -> bool:
        """Delete a veteran profile"""
        try:
            return self.delete_item({"user_id": user_id})
        except Exception as e:
            logger.error(f"Error deleting veteran profile for user {user_id}: {e}")
            raise

    def get_public_profiles(self, limit: Optional[int] = None) -> List[VeteranProfile]:
        """Get all publicly visible veteran profiles"""
        try:
            items = self.query(
                key_condition_expression="is_publicly_visible = :visible",
                expression_attribute_values={":visible": "true"},
                index_name="PublicProfilesIndex",
                limit=limit,
            )
            return [VeteranProfile.from_dynamodb_item(item) for item in items]
        except Exception as e:
            logger.error(f"Error getting public profiles: {e}")
            raise

    def search_profiles_by_skills(
        self, skills: List[str], limit: Optional[int] = None
    ) -> List[VeteranProfile]:
        """Search profiles by skills (requires scan operation)"""
        try:
            # Note: This is a scan operation which can be expensive for large datasets
            # In production, consider using ElasticSearch or similar for text search
            items = self.scan(limit=limit)

            matching_profiles = []
            for item in items:
                profile = VeteranProfile.from_dynamodb_item(item)
                profile_skills = [
                    skill.get("name", "").lower() for skill in profile.skills
                ]

                # Check if any of the search skills match profile skills
                if any(skill.lower() in profile_skills for skill in skills):
                    matching_profiles.append(profile)

            return matching_profiles
        except Exception as e:
            logger.error(f"Error searching profiles by skills: {e}")
            raise

    def update_privacy_settings(self, user_id: str, privacy_settings: dict) -> bool:
        """Update privacy settings for a profile"""
        try:
            # Get current profile
            profile = self.get_profile(user_id)
            if not profile:
                raise ValueError(f"Profile not found for user {user_id}")

            # Update privacy settings
            profile.update_privacy_settings(privacy_settings)

            # Build update data dictionary
            update_data = {
                "privacy_settings": profile.privacy_settings,
                "is_publicly_visible": profile.is_publicly_visible,
            }

            # Save updated profile
            return self.update_profile(user_id, update_data)
        except Exception as e:
            logger.error(f"Error updating privacy settings for user {user_id}: {e}")
            raise

    def get_profiles_by_department(
        self, department: str, limit: Optional[int] = None
    ) -> List[VeteranProfile]:
        """Get profiles by department (requires scan with filter)"""
        try:
            # Note: This requires scanning the Users table first to get user_ids by department
            # Then batch get the profiles. This is a simplified implementation.
            items = self.scan(limit=limit)

            # This would need to be enhanced to join with Users table data
            # For now, returning all profiles (would need user data to filter by department)
            return [VeteranProfile.from_dynamodb_item(item) for item in items]
        except Exception as e:
            logger.error(f"Error getting profiles by department {department}: {e}")
            raise

    def get_profiles_needing_update(self, days_old: int = 90) -> List[VeteranProfile]:
        """Get profiles that haven't been updated in specified days"""
        try:
            cutoff_date = datetime.utcnow().replace(microsecond=0)
            cutoff_date = cutoff_date.replace(day=cutoff_date.day - days_old)
            cutoff_iso = cutoff_date.isoformat()

            items = self.scan(
                filter_expression="last_updated < :cutoff",
                expression_attribute_values={":cutoff": cutoff_iso},
            )

            return [VeteranProfile.from_dynamodb_item(item) for item in items]
        except Exception as e:
            logger.error(f"Error getting profiles needing update: {e}")
            raise

    def profile_exists(self, user_id: str) -> bool:
        """Check if a profile exists for the given user ID"""
        try:
            return self.item_exists({"user_id": user_id})
        except Exception as e:
            logger.error(f"Error checking if profile exists for user {user_id}: {e}")
            raise

    def increment_profile_views(self, user_id: str) -> bool:
        """
        Increment the profile view count for a user.
        Uses atomic counter increment to avoid race conditions.
        """
        try:
            self.table.update_item(
                Key={"user_id": user_id},
                UpdateExpression="SET profile_views = if_not_exists(profile_views, :zero) + :inc",
                ExpressionAttributeValues={":zero": 0, ":inc": 1},
            )
            logger.info(f"Incremented profile views for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error incrementing profile views for user {user_id}: {e}")
            # Don't raise exception - profile view tracking is non-critical
            return False
