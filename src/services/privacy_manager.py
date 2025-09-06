"""
Privacy management service for veteran profiles.
Handles visibility settings and external platform synchronization.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from ..models.public_profile import PublicProfile
from ..models.veteran_profile import VeteranProfile
from ..repositories.public_profile_repository import PublicProfileRepository
from ..repositories.veteran_profile_repository import VeteranProfileRepository

logger = logging.getLogger(__name__)


class PrivacyManager:
    """Manages privacy settings and external profile synchronization."""

    def __init__(self, profile_repo=None, public_profile_repo=None):
        self.profile_repo = profile_repo or VeteranProfileRepository()
        self.public_profile_repo = public_profile_repo or PublicProfileRepository()

    def update_privacy_settings(
        self, user_id: str, privacy_settings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update privacy settings with real-time synchronization.

        Args:
            user_id: User ID
            privacy_settings: New privacy settings

        Returns:
            Dict containing update result and sync status
        """
        try:
            # Get current profile
            profile = self.profile_repo.get_profile(user_id)
            if not profile:
                raise ValueError(f"Profile not found for user {user_id}")

            # Store previous visibility state
            was_public = profile.privacy_settings.get("is_publicly_visible", False)

            # Update privacy settings
            profile.update_privacy_settings(privacy_settings)

            # Save updated profile
            success = self.profile_repo.update_profile(profile)
            if not success:
                raise Exception("Failed to update profile in database")

            # Handle external platform synchronization
            sync_result = self._sync_external_visibility(profile, was_public)

            return {
                "success": True,
                "updated_settings": privacy_settings,
                "sync_result": sync_result,
                "profile_updated_at": profile.last_updated,
            }

        except Exception as e:
            logger.error(f"Error updating privacy settings for user {user_id}: {e}")
            return {"success": False, "error": str(e)}

    def _sync_external_visibility(
        self, profile: VeteranProfile, was_public: bool
    ) -> Dict[str, Any]:
        """
        Synchronize profile visibility with external platforms.

        Args:
            profile: Updated veteran profile
            was_public: Previous public visibility state

        Returns:
            Dict containing synchronization results
        """
        try:
            is_now_public = profile.privacy_settings.get("is_publicly_visible", False)
            sync_actions = []

            if not was_public and is_now_public:
                # Profile made public - create/update public profile
                sync_result = self._create_public_profile(profile)
                sync_actions.append(
                    {
                        "action": "create_public_profile",
                        "success": sync_result["success"],
                        "details": sync_result.get("details", ""),
                    }
                )

            elif was_public and not is_now_public:
                # Profile made private - remove from public platforms
                sync_result = self._remove_public_profile(profile.user_id)
                sync_actions.append(
                    {
                        "action": "remove_public_profile",
                        "success": sync_result["success"],
                        "details": sync_result.get("details", ""),
                    }
                )

            elif was_public and is_now_public:
                # Profile still public - update public profile
                sync_result = self._update_public_profile(profile)
                sync_actions.append(
                    {
                        "action": "update_public_profile",
                        "success": sync_result["success"],
                        "details": sync_result.get("details", ""),
                    }
                )

            return {
                "sync_performed": len(sync_actions) > 0,
                "actions": sync_actions,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(
                f"Error syncing external visibility for user {profile.user_id}: {e}"
            )
            return {
                "sync_performed": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }

    def _create_public_profile(self, profile: VeteranProfile) -> Dict[str, Any]:
        """
        Create or update public profile for external visibility.

        Args:
            profile: Veteran profile to make public

        Returns:
            Dict containing creation result
        """
        try:
            # Create public profile from veteran profile
            # Extract simplified skills list
            skills_list = [
                skill.get("name", "") for skill in profile.skills if skill.get("name")
            ]

            # Calculate total experience years
            total_experience = (
                sum(exp.get("duration", 0) for exp in profile.experiences) // 12
            )  # Convert months to years

            public_profile = PublicProfile(
                user_id=profile.user_id,
                business_title=profile.business_title,
                skills=skills_list,
                experience_years=total_experience,
                contact_preferences={
                    "allow_contact": profile.privacy_settings.get(
                        "external_contact", False
                    ),
                    "preferred_method": "platform",
                },
                updated_at=profile.last_updated,
            )

            # Save to public profiles repository
            success = self.public_profile_repo.create_or_update_profile(public_profile)

            if success:
                logger.info(
                    f"Public profile created/updated for user {profile.user_id}"
                )
                return {
                    "success": True,
                    "details": "Public profile created successfully",
                }
            else:
                return {"success": False, "details": "Failed to create public profile"}

        except Exception as e:
            logger.error(
                f"Error creating public profile for user {profile.user_id}: {e}"
            )
            return {
                "success": False,
                "details": f"Error creating public profile: {str(e)}",
            }

    def _update_public_profile(self, profile: VeteranProfile) -> Dict[str, Any]:
        """
        Update existing public profile.

        Args:
            profile: Updated veteran profile

        Returns:
            Dict containing update result
        """
        try:
            # Get existing public profile
            existing_public = self.public_profile_repo.get_profile(profile.user_id)

            if existing_public:
                # Update public profile with new data
                skills_list = [
                    skill.get("name", "")
                    for skill in profile.skills
                    if skill.get("name")
                ]
                total_experience = (
                    sum(exp.get("duration", 0) for exp in profile.experiences) // 12
                )

                existing_public.business_title = profile.business_title
                existing_public.skills = skills_list
                existing_public.experience_years = total_experience
                existing_public.contact_preferences = {
                    "allow_contact": profile.privacy_settings.get(
                        "external_contact", False
                    ),
                    "preferred_method": "platform",
                }
                existing_public.updated_at = profile.last_updated

                success = self.public_profile_repo.update_profile(existing_public)

                if success:
                    logger.info(f"Public profile updated for user {profile.user_id}")
                    return {
                        "success": True,
                        "details": "Public profile updated successfully",
                    }
                else:
                    return {
                        "success": False,
                        "details": "Failed to update public profile",
                    }
            else:
                # Public profile doesn't exist, create it
                return self._create_public_profile(profile)

        except Exception as e:
            logger.error(
                f"Error updating public profile for user {profile.user_id}: {e}"
            )
            return {
                "success": False,
                "details": f"Error updating public profile: {str(e)}",
            }

    def _remove_public_profile(self, user_id: str) -> Dict[str, Any]:
        """
        Remove profile from public visibility.

        Args:
            user_id: User ID to remove from public platforms

        Returns:
            Dict containing removal result
        """
        try:
            success = self.public_profile_repo.delete_profile(user_id)

            if success:
                logger.info(f"Public profile removed for user {user_id}")
                return {
                    "success": True,
                    "details": "Profile removed from public visibility",
                }
            else:
                return {"success": False, "details": "Failed to remove public profile"}

        except Exception as e:
            logger.error(f"Error removing public profile for user {user_id}: {e}")
            return {
                "success": False,
                "details": f"Error removing public profile: {str(e)}",
            }

    def get_privacy_status(self, user_id: str) -> Dict[str, Any]:
        """
        Get current privacy status and external visibility.

        Args:
            user_id: User ID

        Returns:
            Dict containing privacy status information
        """
        try:
            # Get veteran profile
            profile = self.profile_repo.get_profile(user_id)
            if not profile:
                return {"success": False, "error": "Profile not found"}

            # Check public profile existence
            public_profile = self.public_profile_repo.get_profile(user_id)

            return {
                "success": True,
                "privacy_settings": profile.privacy_settings,
                "is_publicly_visible": profile.privacy_settings.get(
                    "is_publicly_visible", False
                ),
                "external_contact_allowed": profile.privacy_settings.get(
                    "external_contact", False
                ),
                "public_profile_exists": public_profile is not None,
                "last_updated": profile.last_updated,
                "public_profile_last_updated": public_profile.updated_at
                if public_profile
                else None,
            }

        except Exception as e:
            logger.error(f"Error getting privacy status for user {user_id}: {e}")
            return {"success": False, "error": str(e)}

    def bulk_privacy_update(
        self, privacy_updates: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Perform bulk privacy updates for multiple users.

        Args:
            privacy_updates: Dict mapping user_id to privacy settings

        Returns:
            Dict containing bulk update results
        """
        results = {
            "successful_updates": [],
            "failed_updates": [],
            "total_processed": len(privacy_updates),
        }

        for user_id, privacy_settings in privacy_updates.items():
            try:
                update_result = self.update_privacy_settings(user_id, privacy_settings)

                if update_result["success"]:
                    results["successful_updates"].append(
                        {"user_id": user_id, "updated_settings": privacy_settings}
                    )
                else:
                    results["failed_updates"].append(
                        {
                            "user_id": user_id,
                            "error": update_result.get("error", "Unknown error"),
                        }
                    )

            except Exception as e:
                results["failed_updates"].append({"user_id": user_id, "error": str(e)})

        results["success_rate"] = (
            len(results["successful_updates"]) / results["total_processed"]
            if results["total_processed"] > 0
            else 0
        )

        logger.info(
            f"Bulk privacy update completed: {len(results['successful_updates'])}/{results['total_processed']} successful"
        )

        return results

    def validate_privacy_settings(
        self, privacy_settings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate privacy settings before applying.

        Args:
            privacy_settings: Privacy settings to validate

        Returns:
            Dict containing validation results
        """
        errors = []
        warnings = []

        # Check required fields and types
        if "is_publicly_visible" in privacy_settings:
            if not isinstance(privacy_settings["is_publicly_visible"], bool):
                errors.append("is_publicly_visible must be a boolean value")

        if "external_contact" in privacy_settings:
            if not isinstance(privacy_settings["external_contact"], bool):
                errors.append("external_contact must be a boolean value")

        # Business logic validations
        if privacy_settings.get("external_contact", False) and not privacy_settings.get(
            "is_publicly_visible", False
        ):
            warnings.append(
                "external_contact is enabled but profile is not publicly visible"
            )

        return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}


# Global privacy manager instance
privacy_manager = PrivacyManager()
