"""
Lambda handler for AI-generated business title operations.
Handles business title generation, selection, and regeneration.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.repositories.user_repository import UserRepository
from src.repositories.veteran_profile_repository import VeteranProfileRepository
from src.services.ai_utils import get_ai_service
from src.utils.auth_utils import get_user_from_token
from src.utils.rbac import Permission, require_role

logger = logging.getLogger(__name__)


class BusinessTitleHandler:
    """Handler for business title generation operations."""

    def __init__(self):
        self.ai_service = get_ai_service()
        self.profile_repo = VeteranProfileRepository()
        self.user_repo = UserRepository()

    async def generate_business_titles(
        self, event: Dict[str, Any], context: Any
    ) -> Dict[str, Any]:
        """
        Generate AI-powered business titles for a veteran.

        Args:
            event: Lambda event containing user information
            context: Lambda context

        Returns:
            API Gateway response with generated business titles
        """
        try:
            # Extract and verify user from JWT token
            token = (
                event.get("headers", {}).get("Authorization", "").replace("Bearer ", "")
            )
            if not token:
                return {
                    "statusCode": 401,
                    "body": json.dumps({"error": "Missing authorization token"}),
                }

            user_info = get_user_from_token(token)
            if not user_info:
                return {
                    "statusCode": 401,
                    "body": json.dumps({"error": "Invalid authorization token"}),
                }

            user_id = user_info["user_id"]

            # Check if user has veteran role
            user = await self.user_repo.get_by_id(user_id)
            if not user or user.role != "veteran":
                return {
                    "statusCode": 403,
                    "body": json.dumps(
                        {"error": "Access denied. Veteran role required."}
                    ),
                }

            # Get user profile
            profile = await self.profile_repo.get_by_user_id(user_id)
            if not profile:
                return {
                    "statusCode": 404,
                    "body": json.dumps(
                        {
                            "error": "Profile not found. Please complete your profile first."
                        }
                    ),
                }

            # Extract career interests from preferences
            career_interests = []
            if profile.preferences:
                career_interests = profile.preferences.get("preferred_roles", [])
                if "career_interests" in profile.preferences:
                    career_interests.extend(profile.preferences["career_interests"])

            # Generate business titles using AI
            titles_data = await self.ai_service.generate_business_titles(
                name=user.name,
                department=user.department,
                skills=profile.skills or [],
                experience=profile.experiences or [],
                career_interests=career_interests,
                current_role=profile.business_title or "Employee",
            )

            # Store generation history in profile
            await self._store_title_generation_history(user_id, titles_data)

            logger.info(f"Generated business titles for user {user_id}")

            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps(
                    {
                        "titles": titles_data.get("titles", []),
                        "recommended_title": titles_data.get("recommended_title"),
                        "reasoning": titles_data.get("reasoning"),
                        "generated_at": datetime.now(timezone.utc).isoformat(),
                    }
                ),
            }

        except Exception as e:
            logger.error(f"Error generating business titles: {str(e)}")
            return {
                "statusCode": 500,
                "body": json.dumps({"error": "Internal server error"}),
            }

    async def select_business_title(
        self, event: Dict[str, Any], context: Any
    ) -> Dict[str, Any]:
        """
        Select and apply a business title to user profile.

        Args:
            event: Lambda event containing selected title
            context: Lambda context

        Returns:
            API Gateway response with confirmation
        """
        try:
            # Extract and verify user from JWT token
            token = (
                event.get("headers", {}).get("Authorization", "").replace("Bearer ", "")
            )
            if not token:
                return {
                    "statusCode": 401,
                    "body": json.dumps({"error": "Missing authorization token"}),
                }

            user_info = get_user_from_token(token)
            if not user_info:
                return {
                    "statusCode": 401,
                    "body": json.dumps({"error": "Invalid authorization token"}),
                }

            user_id = user_info["user_id"]

            # Parse request body
            try:
                body = json.loads(event.get("body", "{}"))
            except json.JSONDecodeError:
                return {
                    "statusCode": 400,
                    "body": json.dumps({"error": "Invalid JSON in request body"}),
                }

            selected_title = body.get("title")
            if not selected_title:
                return {
                    "statusCode": 400,
                    "body": json.dumps({"error": "Missing title in request body"}),
                }

            # Get current profile
            profile = await self.profile_repo.get_by_user_id(user_id)
            if not profile:
                return {
                    "statusCode": 404,
                    "body": json.dumps({"error": "Profile not found"}),
                }

            # Update profile with selected title
            update_data = {
                "business_title": selected_title,
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }

            # Store selection history
            title_history = getattr(profile, "title_history", [])
            title_history.append(
                {
                    "title": selected_title,
                    "selected_at": datetime.now(timezone.utc).isoformat(),
                    "previous_title": profile.business_title,
                }
            )
            update_data["title_history"] = title_history

            await self.profile_repo.update_profile(user_id, update_data)

            logger.info(
                f"Updated business title for user {user_id} to: {selected_title}"
            )

            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps(
                    {
                        "message": "Business title updated successfully",
                        "title": selected_title,
                        "updated_at": update_data["last_updated"],
                    }
                ),
            }

        except Exception as e:
            logger.error(f"Error selecting business title: {str(e)}")
            return {
                "statusCode": 500,
                "body": json.dumps({"error": "Internal server error"}),
            }

    async def regenerate_business_titles(
        self, event: Dict[str, Any], context: Any
    ) -> Dict[str, Any]:
        """
        Regenerate business titles with updated context.

        Args:
            event: Lambda event
            context: Lambda context

        Returns:
            API Gateway response with regenerated titles
        """
        try:
            # Extract and verify user from JWT token
            token = (
                event.get("headers", {}).get("Authorization", "").replace("Bearer ", "")
            )
            if not token:
                return {
                    "statusCode": 401,
                    "body": json.dumps({"error": "Missing authorization token"}),
                }

            user_info = get_user_from_token(token)
            if not user_info:
                return {
                    "statusCode": 401,
                    "body": json.dumps({"error": "Invalid authorization token"}),
                }

            user_id = user_info["user_id"]

            # Get user and profile
            user = await self.user_repo.get_by_id(user_id)
            profile = await self.profile_repo.get_by_user_id(user_id)

            if not user or not profile:
                return {
                    "statusCode": 404,
                    "body": json.dumps({"error": "User or profile not found"}),
                }

            # Parse optional request body for additional context
            additional_context = {}
            if event.get("body"):
                try:
                    body = json.loads(event["body"])
                    additional_context = body.get("context", {})
                except json.JSONDecodeError:
                    pass

            # Extract career interests
            career_interests = []
            if profile.preferences:
                career_interests = profile.preferences.get("preferred_roles", [])
                if "career_interests" in profile.preferences:
                    career_interests.extend(profile.preferences["career_interests"])

            # Add any additional interests from request
            if "additional_interests" in additional_context:
                career_interests.extend(additional_context["additional_interests"])

            # Generate new business titles
            titles_data = await self.ai_service.generate_business_titles(
                name=user.name,
                department=user.department,
                skills=profile.skills or [],
                experience=profile.experiences or [],
                career_interests=career_interests,
                current_role=profile.business_title or "Employee",
            )

            # Store regeneration history
            await self._store_title_generation_history(
                user_id, titles_data, regenerated=True
            )

            logger.info(f"Regenerated business titles for user {user_id}")

            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps(
                    {
                        "titles": titles_data.get("titles", []),
                        "recommended_title": titles_data.get("recommended_title"),
                        "reasoning": titles_data.get("reasoning"),
                        "regenerated_at": datetime.now(timezone.utc).isoformat(),
                        "context_used": additional_context,
                    }
                ),
            }

        except Exception as e:
            logger.error(f"Error regenerating business titles: {str(e)}")
            return {
                "statusCode": 500,
                "body": json.dumps({"error": "Internal server error"}),
            }

    async def get_title_history(
        self, event: Dict[str, Any], context: Any
    ) -> Dict[str, Any]:
        """
        Get business title generation and selection history.

        Args:
            event: Lambda event
            context: Lambda context

        Returns:
            API Gateway response with title history
        """
        try:
            # Extract and verify user from JWT token
            token = (
                event.get("headers", {}).get("Authorization", "").replace("Bearer ", "")
            )
            if not token:
                return {
                    "statusCode": 401,
                    "body": json.dumps({"error": "Missing authorization token"}),
                }

            user_info = get_user_from_token(token)
            if not user_info:
                return {
                    "statusCode": 401,
                    "body": json.dumps({"error": "Invalid authorization token"}),
                }

            user_id = user_info["user_id"]

            # Get profile
            profile = await self.profile_repo.get_by_user_id(user_id)
            if not profile:
                return {
                    "statusCode": 404,
                    "body": json.dumps({"error": "Profile not found"}),
                }

            # Get title history
            title_history = getattr(profile, "title_history", [])
            generation_history = getattr(profile, "title_generation_history", [])

            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps(
                    {
                        "current_title": profile.business_title,
                        "selection_history": title_history,
                        "generation_history": generation_history,
                        "total_generations": len(generation_history),
                        "total_selections": len(title_history),
                    }
                ),
            }

        except Exception as e:
            logger.error(f"Error getting title history: {str(e)}")
            return {
                "statusCode": 500,
                "body": json.dumps({"error": "Internal server error"}),
            }

    async def _store_title_generation_history(
        self, user_id: str, titles_data: Dict[str, Any], regenerated: bool = False
    ) -> None:
        """
        Store title generation history in user profile.

        Args:
            user_id: User ID
            titles_data: Generated titles data
            regenerated: Whether this was a regeneration
        """
        try:
            profile = await self.profile_repo.get_by_user_id(user_id)
            if not profile:
                return

            # Get existing history
            generation_history = getattr(profile, "title_generation_history", [])

            # Add new generation record
            generation_record = {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "titles": titles_data.get("titles", []),
                "recommended_title": titles_data.get("recommended_title"),
                "reasoning": titles_data.get("reasoning"),
                "regenerated": regenerated,
                "title_count": len(titles_data.get("titles", [])),
            }

            generation_history.append(generation_record)

            # Keep only last 10 generations to avoid excessive storage
            if len(generation_history) > 10:
                generation_history = generation_history[-10:]

            # Update profile
            await self.profile_repo.update_profile(
                user_id, {"title_generation_history": generation_history}
            )

        except Exception as e:
            logger.error(f"Error storing title generation history: {str(e)}")


# Lambda function handlers
business_title_handler = BusinessTitleHandler()


async def generate_business_titles(
    event: Dict[str, Any], context: Any
) -> Dict[str, Any]:
    """Lambda handler for generating business titles."""
    return await business_title_handler.generate_business_titles(event, context)


async def select_business_title(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler for selecting a business title."""
    return await business_title_handler.select_business_title(event, context)


async def regenerate_business_titles(
    event: Dict[str, Any], context: Any
) -> Dict[str, Any]:
    """Lambda handler for regenerating business titles."""
    return await business_title_handler.regenerate_business_titles(event, context)


async def get_title_history(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler for getting title history."""
    return await business_title_handler.get_title_history(event, context)
