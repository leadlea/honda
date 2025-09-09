"""
Lambda handler for AI-generated questionnaire operations.
Removes local JWT verification/cryptography dependency and relies on
API Gateway Cognito User Pool Authorizer (claims from event.requestContext).
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from src.repositories.questionnaire_repository import QuestionnaireRepository
from src.repositories.user_repository import UserRepository
from src.repositories.veteran_profile_repository import VeteranProfileRepository
from src.services.ai_utils import get_ai_service

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# ---------- helpers ----------

def _get_user_from_event(event: Dict[str, Any]) -> Tuple[Optional[str], Dict[str, Any]]:
    """
    Get user_id and raw claims from API Gateway authorizer claims.
    Falls back to path parameter if claims are unavailable.
    """
    claims = (
        event.get("requestContext", {})
        .get("authorizer", {})
        .get("claims", {})
        or {}
    )

    user_id = (
        claims.get("sub")
        or claims.get("username")
        or claims.get("cognito:username")
    )

    # safe fallback to path parameter (case variations)
    if not user_id:
        path_params = event.get("pathParameters", {}) or {}
        user_id = path_params.get("userId") or path_params.get("user_id")

    return user_id, claims


def _json_response(status: int, body: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body, default=str),
    }


# ---------- handler class ----------

class QuestionnaireHandler:
    """Handler for questionnaire-related operations."""

    def __init__(self):
        self.ai_service = get_ai_service()
        self.questionnaire_repo = QuestionnaireRepository()
        self.user_repo = UserRepository()
        self.profile_repo = VeteranProfileRepository()

    # === GET /questionnaire/{userId} (generate on demand) ===
    async def generate_questionnaire(
        self, event: Dict[str, Any], context: Any
    ) -> Dict[str, Any]:
        try:
            user_id, claims = _get_user_from_event(event)
            if not user_id:
                return _json_response(401, {"error": "Unauthorized"})
            # (任意) パスの userId と一致チェック
            path_uid = (event.get("pathParameters") or {}).get("userId")
            if path_uid and path_uid != user_id:
                return _json_response(403, {"error": "Forbidden"})

            # Check role (veteran)
            user = await self.user_repo.get_by_id(user_id)
            if not user or getattr(user, "role", None) != "veteran":
                return _json_response(403, {"error": "Access denied. Veteran role required."})

            # Get profile
            profile = await self.profile_repo.get_by_user_id(user_id)

            # previous answers for context
            previous_questionnaires = await self.questionnaire_repo.get_user_questionnaires(user_id)
            previous_responses: List[Dict[str, Any]] = []
            if previous_questionnaires:
                latest = max(previous_questionnaires, key=lambda q: q.created_at)
                if getattr(latest, "responses", None):
                    previous_responses = latest.responses

            # years of experience
            years_experience = 0
            if getattr(user, "join_date", None):
                join_date = datetime.fromisoformat(str(user.join_date).replace("Z", "+00:00"))
                years_experience = (datetime.now(timezone.utc) - join_date).days // 365

            # ask AI
            questionnaire_data = await self.ai_service.generate_questionnaire(
                name=getattr(user, "name", "User"),
                department=getattr(user, "department", "General"),
                years_experience=years_experience,
                current_role=getattr(profile, "business_title", "Employee") if profile else "Employee",
                previous_responses=previous_responses,
            )

            # persist
            created = await self.questionnaire_repo.create_questionnaire(
                user_id=user_id,
                questionnaire_data=questionnaire_data,
                ai_generated=True,
            )

            logger.info("Generated questionnaire %s for user %s", created.questionnaire_id, user_id)

            # フロントが扱いやすい形：質問票をトップレベルで返す
            shaped = {
                "questionnaire_id": created.questionnaire_id,
                "status": getattr(created, "status", "generated"),
                "created_at": getattr(created, "created_at", datetime.now(timezone.utc).isoformat()),
                **questionnaire_data,  # expected to include `title`, `questions`, `responses` (optional)
            }
            return _json_response(200, shaped)

        except Exception as e:
            logger.exception("Error generating questionnaire: %s", e)
            return _json_response(500, {"error": "Internal server error"})

    # === POST /questionnaire/{userId}/submit ===
    async def submit_questionnaire(
        self, event: Dict[str, Any], context: Any
    ) -> Dict[str, Any]:
        try:
            user_id, _ = _get_user_from_event(event)
            if not user_id:
                return _json_response(401, {"error": "Unauthorized"})

            try:
                body = json.loads(event.get("body") or "{}")
            except json.JSONDecodeError:
                return _json_response(400, {"error": "Invalid JSON in request body"})

            questionnaire_id = body.get("questionnaire_id")
            responses = body.get("responses") or []

            if not questionnaire_id or not isinstance(responses, list) or not responses:
                return _json_response(400, {"error": "Missing questionnaire_id or responses"})

            questionnaire = await self.questionnaire_repo.get_by_id(questionnaire_id)
            if not questionnaire or questionnaire.user_id != user_id:
                return _json_response(404, {"error": "Questionnaire not found"})

            await self.questionnaire_repo.submit_responses(
                questionnaire_id=questionnaire_id, responses=responses
            )

            # Update profile heuristically from responses
            await self._update_profile_from_responses(user_id, responses)

            logger.info("Submitted questionnaire %s for user %s", questionnaire_id, user_id)

            return _json_response(
                200,
                {
                    "message": "Questionnaire submitted successfully",
                    "questionnaire_id": questionnaire_id,
                    "submitted_at": datetime.now(timezone.utc).isoformat(),
                },
            )

        except Exception as e:
            logger.exception("Error submitting questionnaire: %s", e)
            return _json_response(500, {"error": "Internal server error"})

    # === GET /questionnaire/{userId}/history ===
    async def get_questionnaire_history(
        self, event: Dict[str, Any], context: Any
    ) -> Dict[str, Any]:
        try:
            user_id, _ = _get_user_from_event(event)
            if not user_id:
                return _json_response(401, {"error": "Unauthorized"})

            questionnaires = await self.questionnaire_repo.get_user_questionnaires(user_id)

            history: List[Dict[str, Any]] = []
            for q in questionnaires:
                history.append(
                    {
                        "questionnaire_id": q.questionnaire_id,
                        "title": getattr(q, "title", None) or getattr(q, "questionnaire", {}).get("title"),
                        "status": getattr(q, "status", "generated"),
                        "created_at": getattr(q, "created_at", None),
                        "submitted_at": getattr(q, "submitted_at", None),
                        "ai_generated": getattr(q, "ai_generated", True),
                        "question_count": len(getattr(q, "questions", []) or getattr(q, "questionnaire", {}).get("questions", []) or []),
                        "response_count": len(getattr(q, "responses", []) or []),
                        # Optional fields used by UI
                        "questions": getattr(q, "questions", None) or getattr(q, "questionnaire", {}).get("questions"),
                        "responses": getattr(q, "responses", None),
                        "generated_at": getattr(q, "created_at", None),
                        "completed_at": getattr(q, "submitted_at", None),
                    }
                )

            return _json_response(200, {"questionnaires": history, "total_count": len(history)})

        except Exception as e:
            logger.exception("Error getting questionnaire history: %s", e)
            return _json_response(500, {"error": "Internal server error"})

    # === PUT /questionnaire/{userId}/regenerate ===
    async def regenerate_questionnaire(
        self, event: Dict[str, Any], context: Any
    ) -> Dict[str, Any]:
        try:
            user_id, _ = _get_user_from_event(event)
            if not user_id:
                return _json_response(401, {"error": "Unauthorized"})

            # original questionnaire_id (optional) from body or path
            body = {}
            if event.get("body"):
                try:
                    body = json.loads(event["body"])
                except json.JSONDecodeError:
                    body = {}
            from_qid = (event.get("pathParameters") or {}).get("questionnaire_id") or body.get("questionnaire_id")

            user = await self.user_repo.get_by_id(user_id)
            profile = await self.profile_repo.get_by_user_id(user_id)

            years_experience = 0
            if getattr(user, "join_date", None):
                join_date = datetime.fromisoformat(str(user.join_date).replace("Z", "+00:00"))
                years_experience = (datetime.now(timezone.utc) - join_date).days // 365

            previous_responses: List[Dict[str, Any]] = []
            if from_qid:
                original = await self.questionnaire_repo.get_by_id(from_qid)
                if original and getattr(original, "responses", None):
                    previous_responses = original.responses

            questionnaire_data = await self.ai_service.generate_questionnaire(
                name=getattr(user, "name", "User"),
                department=getattr(user, "department", "General"),
                years_experience=years_experience,
                current_role=getattr(profile, "business_title", "Employee") if profile else "Employee",
                previous_responses=previous_responses,
            )

            created = await self.questionnaire_repo.create_questionnaire(
                user_id=user_id,
                questionnaire_data=questionnaire_data,
                ai_generated=True,
            )

            logger.info("Regenerated questionnaire %s for user %s", created.questionnaire_id, user_id)

            shaped = {
                "questionnaire_id": created.questionnaire_id,
                "status": getattr(created, "status", "generated"),
                "created_at": getattr(created, "created_at", datetime.now(timezone.utc).isoformat()),
                "regenerated_from": from_qid,
                **questionnaire_data,
            }
            return _json_response(200, shaped)

        except Exception as e:
            logger.exception("Error regenerating questionnaire: %s", e)
            return _json_response(500, {"error": "Internal server error"})

    # ---------- profile updater ----------

    async def _update_profile_from_responses(self, user_id: str, responses: List[Dict[str, Any]]) -> None:
        try:
            profile = await self.profile_repo.get_by_user_id(user_id)
            if not profile:
                logger.warning("No profile found for user %s", user_id)
                return

            new_skills: List[str] = []
            new_interests: List[str] = []

            for r in responses:
                qid = str(r.get("question_id", "")).lower()
                answer = r.get("answer", "")
                if "skill" in qid and answer:
                    new_skills.extend(answer if isinstance(answer, list) else [answer])
                if "interest" in qid or "career" in qid:
                    new_interests.extend(answer if isinstance(answer, list) else [answer])

            update: Dict[str, Any] = {}

            if new_skills:
                existing = list(getattr(profile, "skills", []) or [])
                names = {s.get("name", "") for s in existing if isinstance(s, dict)}
                for s in new_skills:
                    if s and s not in names:
                        existing.append({"name": s, "level": "Intermediate", "years": 1, "certifications": []})
                update["skills"] = existing

            if new_interests:
                prefs = dict(getattr(profile, "preferences", {}) or {})
                roles = list(prefs.get("preferred_roles", []) or [])
                for i in new_interests:
                    if i and i not in roles:
                        roles.append(i)
                prefs["preferred_roles"] = roles
                update["preferences"] = prefs

            q_responses = list(getattr(profile, "questionnaire_responses", []) or [])
            q_responses.append({"timestamp": datetime.now(timezone.utc).isoformat(), "responses": responses})
            update["questionnaire_responses"] = q_responses

            if update:
                await self.profile_repo.update_profile(user_id, update)
                logger.info("Updated profile for user %s based on questionnaire responses", user_id)

        except Exception as e:
            logger.exception("Error updating profile from responses: %s", e)


# ---------- Lambda entrypoints ----------

handler_instance = QuestionnaireHandler()

async def generate_questionnaire(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    return await handler_instance.generate_questionnaire(event, context)

async def submit_questionnaire(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    return await handler_instance.submit_questionnaire(event, context)

async def get_questionnaire_history(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    return await handler_instance.get_questionnaire_history(event, context)

async def regenerate_questionnaire(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    return await handler_instance.regenerate_questionnaire(event, context)
