"""
Lambda handler for AI-generated questionnaire operations.
Handles questionnaire generation, submission, and history management.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict

from src.repositories.questionnaire_repository import QuestionnaireRepository
from src.repositories.user_repository import UserRepository
from src.repositories.veteran_profile_repository import VeteranProfileRepository
from src.services.ai_utils import get_ai_service
from src.utils.auth_utils import get_user_from_token

logger = logging.getLogger(__name__)


class QuestionnaireHandler:
    """Handler for questionnaire-related operations."""

    def __init__(self):
        self.ai_service = get_ai_service()
        self.questionnaire_repo = QuestionnaireRepository()
        self.user_repo = UserRepository()
        self.profile_repo = VeteranProfileRepository()

    async def generate_questionnaire(
        self, event: Dict[str, Any], context: Any
    ) -> Dict[str, Any]:
        """
        Generate a personalized AI questionnaire for a veteran.

        Args:
            event: Lambda event containing user information
            context: Lambda context

        Returns:
            API Gateway response with generated questionnaire
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

            # Get user profile information
            profile = await self.profile_repo.get_by_user_id(user_id)

            # Get previous questionnaire responses
            previous_questionnaires = (
                await self.questionnaire_repo.get_user_questionnaires(user_id)
            )
            previous_responses = []
            if previous_questionnaires:
                # Get the most recent questionnaire responses
                latest_questionnaire = max(
                    previous_questionnaires, key=lambda q: q.created_at
                )
                if (
                    hasattr(latest_questionnaire, "responses")
                    and latest_questionnaire.responses
                ):
                    previous_responses = latest_questionnaire.responses

            # Calculate years of experience
            years_experience = 0
            if user.join_date:
                join_date = datetime.fromisoformat(
                    user.join_date.replace("Z", "+00:00")
                )
                years_experience = (datetime.now(timezone.utc) - join_date).days // 365

            # Generate AI questionnaire
            questionnaire_data = await self.ai_service.generate_questionnaire(
                name=user.name,
                department=user.department,
                years_experience=years_experience,
                current_role=getattr(profile, "business_title", "Employee")
                if profile
                else "Employee",
                previous_responses=previous_responses,
            )

            # Save questionnaire to database
            questionnaire = await self.questionnaire_repo.create_questionnaire(
                user_id=user_id,
                questionnaire_data=questionnaire_data,
                ai_generated=True,
            )

            logger.info(
                f"Generated questionnaire {questionnaire.questionnaire_id} for user {user_id}"
            )

            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps(
                    {
                        "questionnaire_id": questionnaire.questionnaire_id,
                        "questionnaire": questionnaire_data,
                        "created_at": questionnaire.created_at,
                    }
                ),
            }

        except Exception as e:
            logger.error(f"Error generating questionnaire: {str(e)}")
            return {
                "statusCode": 500,
                "body": json.dumps({"error": "Internal server error"}),
            }

    async def submit_questionnaire(
        self, event: Dict[str, Any], context: Any
    ) -> Dict[str, Any]:
        """
        Submit questionnaire responses and update user profile.

        Args:
            event: Lambda event containing questionnaire responses
            context: Lambda context

        Returns:
            API Gateway response with submission confirmation
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

            questionnaire_id = body.get("questionnaire_id")
            responses = body.get("responses", [])

            if not questionnaire_id or not responses:
                return {
                    "statusCode": 400,
                    "body": json.dumps(
                        {"error": "Missing questionnaire_id or responses"}
                    ),
                }

            # Verify questionnaire belongs to user
            questionnaire = await self.questionnaire_repo.get_by_id(questionnaire_id)
            if not questionnaire or questionnaire.user_id != user_id:
                return {
                    "statusCode": 404,
                    "body": json.dumps({"error": "Questionnaire not found"}),
                }

            # Submit responses
            await self.questionnaire_repo.submit_responses(
                questionnaire_id=questionnaire_id, responses=responses
            )

            # Update user profile based on responses
            await self._update_profile_from_responses(user_id, responses)

            logger.info(
                f"Submitted questionnaire {questionnaire_id} for user {user_id}"
            )

            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps(
                    {
                        "message": "Questionnaire submitted successfully",
                        "questionnaire_id": questionnaire_id,
                        "submitted_at": datetime.now(timezone.utc).isoformat(),
                    }
                ),
            }

        except Exception as e:
            logger.error(f"Error submitting questionnaire: {str(e)}")
            return {
                "statusCode": 500,
                "body": json.dumps({"error": "Internal server error"}),
            }

    async def get_questionnaire_history(
        self, event: Dict[str, Any], context: Any
    ) -> Dict[str, Any]:
        """
        Get questionnaire history for a user.

        Args:
            event: Lambda event
            context: Lambda context

        Returns:
            API Gateway response with questionnaire history
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

            # Get questionnaire history
            questionnaires = await self.questionnaire_repo.get_user_questionnaires(
                user_id
            )

            # Format response
            history = []
            for q in questionnaires:
                history.append(
                    {
                        "questionnaire_id": q.questionnaire_id,
                        "title": q.title,
                        "status": q.status,
                        "created_at": q.created_at,
                        "submitted_at": q.submitted_at,
                        "ai_generated": q.ai_generated,
                        "question_count": len(q.questions) if q.questions else 0,
                        "response_count": len(q.responses) if q.responses else 0,
                    }
                )

            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps(
                    {"questionnaires": history, "total_count": len(history)}
                ),
            }

        except Exception as e:
            logger.error(f"Error getting questionnaire history: {str(e)}")
            return {
                "statusCode": 500,
                "body": json.dumps({"error": "Internal server error"}),
            }

    async def regenerate_questionnaire(
        self, event: Dict[str, Any], context: Any
    ) -> Dict[str, Any]:
        """
        Regenerate a questionnaire with updated AI prompts.

        Args:
            event: Lambda event
            context: Lambda context

        Returns:
            API Gateway response with regenerated questionnaire
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

            # Get path parameters
            questionnaire_id = event.get("pathParameters", {}).get("questionnaire_id")
            if not questionnaire_id:
                return {
                    "statusCode": 400,
                    "body": json.dumps({"error": "Missing questionnaire_id"}),
                }

            # Verify questionnaire belongs to user
            original_questionnaire = await self.questionnaire_repo.get_by_id(
                questionnaire_id
            )
            if not original_questionnaire or original_questionnaire.user_id != user_id:
                return {
                    "statusCode": 404,
                    "body": json.dumps({"error": "Questionnaire not found"}),
                }

            # Get user and profile information
            user = await self.user_repo.get_by_id(user_id)
            profile = await self.profile_repo.get_by_user_id(user_id)

            # Calculate years of experience
            years_experience = 0
            if user.join_date:
                join_date = datetime.fromisoformat(
                    user.join_date.replace("Z", "+00:00")
                )
                years_experience = (datetime.now(timezone.utc) - join_date).days // 365

            # Get previous responses for context
            previous_responses = (
                original_questionnaire.responses
                if original_questionnaire.responses
                else []
            )

            # Generate new questionnaire
            questionnaire_data = await self.ai_service.generate_questionnaire(
                name=user.name,
                department=user.department,
                years_experience=years_experience,
                current_role=getattr(profile, "business_title", "Employee")
                if profile
                else "Employee",
                previous_responses=previous_responses,
            )

            # Create new questionnaire
            new_questionnaire = await self.questionnaire_repo.create_questionnaire(
                user_id=user_id,
                questionnaire_data=questionnaire_data,
                ai_generated=True,
            )

            logger.info(
                f"Regenerated questionnaire {new_questionnaire.questionnaire_id} for user {user_id}"
            )

            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps(
                    {
                        "questionnaire_id": new_questionnaire.questionnaire_id,
                        "questionnaire": questionnaire_data,
                        "created_at": new_questionnaire.created_at,
                        "regenerated_from": questionnaire_id,
                    }
                ),
            }

        except Exception as e:
            logger.error(f"Error regenerating questionnaire: {str(e)}")
            return {
                "statusCode": 500,
                "body": json.dumps({"error": "Internal server error"}),
            }

    async def _update_profile_from_responses(
        self, user_id: str, responses: list
    ) -> None:
        """
        Update user profile based on questionnaire responses.

        Args:
            user_id: User ID
            responses: List of questionnaire responses
        """
        try:
            # Get current profile
            profile = await self.profile_repo.get_by_user_id(user_id)
            if not profile:
                logger.warning(f"No profile found for user {user_id}")
                return

            # Extract skills and interests from responses
            new_skills = []
            new_interests = []

            for response in responses:
                question_id = response.get("question_id", "")
                answer = response.get("answer", "")

                # Parse skills from responses
                if "skill" in question_id.lower() and answer:
                    if isinstance(answer, list):
                        new_skills.extend(answer)
                    else:
                        new_skills.append(answer)

                # Parse interests from responses
                if "interest" in question_id.lower() or "career" in question_id.lower():
                    if isinstance(answer, list):
                        new_interests.extend(answer)
                    else:
                        new_interests.append(answer)

            # Update profile with new information
            update_data = {}

            if new_skills:
                # Merge with existing skills
                existing_skills = profile.skills or []
                skill_names = {skill.get("name", "") for skill in existing_skills}

                for skill in new_skills:
                    if skill and skill not in skill_names:
                        existing_skills.append(
                            {
                                "name": skill,
                                "level": "Intermediate",  # Default level
                                "years": 1,
                                "certifications": [],
                            }
                        )

                update_data["skills"] = existing_skills

            if new_interests:
                # Update preferences
                preferences = profile.preferences or {}
                current_interests = preferences.get("preferred_roles", [])

                for interest in new_interests:
                    if interest and interest not in current_interests:
                        current_interests.append(interest)

                preferences["preferred_roles"] = current_interests
                update_data["preferences"] = preferences

            # Add questionnaire responses to profile
            questionnaire_responses = profile.questionnaire_responses or []
            questionnaire_responses.append(
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "responses": responses,
                }
            )
            update_data["questionnaire_responses"] = questionnaire_responses

            # Update profile
            if update_data:
                await self.profile_repo.update_profile(user_id, update_data)
                logger.info(
                    f"Updated profile for user {user_id} based on questionnaire responses"
                )

        except Exception as e:
            logger.error(f"Error updating profile from responses: {str(e)}")


# Lambda function handlers
questionnaire_handler = QuestionnaireHandler()


async def generate_questionnaire(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler for generating questionnaires."""
    return await questionnaire_handler.generate_questionnaire(event, context)


async def submit_questionnaire(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler for submitting questionnaire responses."""
    return await questionnaire_handler.submit_questionnaire(event, context)


async def get_questionnaire_history(
    event: Dict[str, Any], context: Any
) -> Dict[str, Any]:
    """Lambda handler for getting questionnaire history."""
    return await questionnaire_handler.get_questionnaire_history(event, context)


async def regenerate_questionnaire(
    event: Dict[str, Any], context: Any
) -> Dict[str, Any]:
    """Lambda handler for regenerating questionnaires."""
    return await questionnaire_handler.regenerate_questionnaire(event, context)
