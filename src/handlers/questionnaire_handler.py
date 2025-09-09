"""
Lambda handler for AI-generated questionnaire operations.
- GET  /questionnaire/{userId}           : 既存問診があれば返す。なければAI生成して返す（idトークンのユーザーのみ）
- POST /questionnaire/{userId}/submit    : 回答保存。questionnaire_id 省略時は最新の未完了を自動採用
- GET  /questionnaire/{userId}/history   : 履歴一覧（フロントの型に合わせたフィールド名で返却）
- PUT  /questionnaire/{userId}/regenerate: 直近または指定idを元に再生成して返却
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.repositories.questionnaire_repository import QuestionnaireRepository
from src.repositories.user_repository import UserRepository
from src.repositories.veteran_profile_repository import VeteranProfileRepository
from src.services.ai_utils import get_ai_service
from src.utils.auth_utils import get_user_from_token

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def _cors_headers(extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    base = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
    }
    if extra:
        base.update(extra)
    return base


def _asdict(obj: Any) -> Dict[str, Any]:
    """Repositoryの戻りがオブジェクトでもdictでも扱えるように吸収。"""
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    d = {}
    for k in dir(obj):
        if k.startswith("_"):
            continue
        try:
            v = getattr(obj, k)
        except Exception:
            continue
        if callable(v):
            continue
        d[k] = v
    return d


def _get(d: Dict[str, Any], key: str, default=None):
    return d.get(key, default)


def _normalize_questionnaire(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    フロントが期待するフィールド名に正規化。
    - questions: List[Question]
    - responses: List[{question_id, answer, answered_at}]
    - status: 'generated' | 'in_progress' | 'completed'
    - generated_at / completed_at
    """
    qid = (
        _get(record, "questionnaire_id")
        or _get(record, "id")
        or _get(record, "pk")
    )
    questions = (
        _get(record, "questions")
        or _get(record, "questionnaire", {}).get("questions", [])
        or _get(record, "questionnaire_data", {}).get("questions", [])
        or []
    )
    responses = _get(record, "responses", []) or []
    status = _get(record, "status") or ("completed" if responses else "generated")
    created_at = _get(record, "created_at") or _get(record, "generated_at")
    submitted_at = _get(record, "submitted_at") or _get(record, "completed_at")

    return {
        "questionnaire_id": qid,
        "title": _get(record, "title") or "AI問診",
        "questions": questions,
        "responses": responses,
        "status": status,
        "generated_at": created_at,
        "created_at": created_at,
        "completed_at": submitted_at,
    }


class QuestionnaireHandler:
    """Handler for questionnaire-related operations."""

    def __init__(self):
        self.ai_service = get_ai_service()
        self.questionnaire_repo = QuestionnaireRepository()
        self.user_repo = UserRepository()
        self.profile_repo = VeteranProfileRepository()

    # ---------- helpers ----------

    async def _assert_and_get_user(self, event: Dict[str, Any]) -> Dict[str, str]:
        token = (event.get("headers", {}).get("Authorization", "") or "").replace(
            "Bearer ", ""
        )
        if not token:
            raise PermissionError("Missing authorization token")

        user_info = get_user_from_token(token)
        if not user_info:
            raise PermissionError("Invalid authorization token")

        user_id = user_info["user_id"]
        path_user = event.get("pathParameters", {}).get("userId")
        if path_user and path_user != user_id:
            raise PermissionError("User mismatch")

        return {"user_id": user_id}

    async def _latest_open_questionnaire(self, user_id: str) -> Optional[Dict[str, Any]]:
        """未完了（generated/in_progress）で一番新しいものを返す。なければNone。"""
        items = await self.questionnaire_repo.get_user_questionnaires(user_id)
        if not items:
            return None
        # dict化＆ソート
        rows: List[Dict[str, Any]] = [_asdict(x) for x in items]
        rows = sorted(rows, key=lambda r: _get(r, "created_at", ""), reverse=True)
        for r in rows:
            st = _get(r, "status", "")
            if st in ("generated", "in_progress", ""):
                return r
            # statusが無い実装の場合、responsesが無ければ未完了扱い
            if not _get(r, "status") and not _get(r, "responses"):
                return r
        return None

    async def _generate_and_store(
        self, user: Any, profile: Any, previous_responses: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        years_experience = 0
        if getattr(user, "join_date", None):
            join_date = datetime.fromisoformat(user.join_date.replace("Z", "+00:00"))
            years_experience = (datetime.now(timezone.utc) - join_date).days // 365

        questionnaire_data = await self.ai_service.generate_questionnaire(
            name=user.name,
            department=getattr(user, "department", None),
            years_experience=years_experience,
            current_role=getattr(profile, "business_title", "Employee")
            if profile
            else "Employee",
            previous_responses=previous_responses or [],
        )

        created = await self.questionnaire_repo.create_questionnaire(
            user_id=user.user_id,
            questionnaire_data=questionnaire_data,
            ai_generated=True,
        )
        return _normalize_questionnaire(_asdict(created) | {"questions": questionnaire_data.get("questions", [])})

    # ---------- endpoints ----------

    async def generate_questionnaire(
        self, event: Dict[str, Any], context: Any
    ) -> Dict[str, Any]:
        """既存があれば返却。無ければAIで生成して返却。"""
        try:
            ids = await self._assert_and_get_user(event)
            user_id = ids["user_id"]

            user = await self.user_repo.get_by_id(user_id)
            if not user or getattr(user, "role", "") != "veteran":
                return {
                    "statusCode": 403,
                    "headers": _cors_headers(),
                    "body": json.dumps({"error": "Access denied. Veteran role required."}),
                }

            profile = await self.profile_repo.get_by_user_id(user_id)

            # 直近の未完了があればそれを返す
            existing = await self._latest_open_questionnaire(user_id)
            if existing:
                normalized = _normalize_questionnaire(existing)
                logger.info(f"Return existing questionnaire {normalized['questionnaire_id']} for user {user_id}")
                return {"statusCode": 200, "headers": _cors_headers(), "body": json.dumps(normalized)}

            # なければ新規生成
            prev = await self.questionnaire_repo.get_user_questionnaires(user_id) or []
            latest = None
            if prev:
                latest = max(prev, key=lambda q: getattr(q, "created_at", ""))
            previous_responses = _asdict(latest).get("responses", []) if latest else []

            normalized = await self._generate_and_store(user, profile, previous_responses)

            logger.info(f"Generated questionnaire {normalized['questionnaire_id']} for user {user_id}")
            return {"statusCode": 200, "headers": _cors_headers(), "body": json.dumps(normalized)}

        except PermissionError as e:
            return {"statusCode": 401, "headers": _cors_headers(), "body": json.dumps({"error": str(e)})}
        except Exception as e:
            logger.exception("Error generating questionnaire")
            return {"statusCode": 500, "headers": _cors_headers(), "body": json.dumps({"error": "Internal server error"})}

    async def submit_questionnaire(
        self, event: Dict[str, Any], context: Any
    ) -> Dict[str, Any]:
        """回答保存。questionnaire_id 省略時は最新の未完了を採用。プロフィールも更新。"""
        try:
            ids = await self._assert_and_get_user(event)
            user_id = ids["user_id"]

            try:
                body = json.loads(event.get("body", "{}"))
            except json.JSONDecodeError:
                return {"statusCode": 400, "headers": _cors_headers(), "body": json.dumps({"error": "Invalid JSON in request body"})}

            questionnaire_id = body.get("questionnaire_id")
            responses = body.get("responses", [])

            if not responses:
                return {"statusCode": 400, "headers": _cors_headers(), "body": json.dumps({"error": "Missing responses"})}

            # id未指定なら最新の未完了を自動採用。無ければ生成して採用。
            if not questionnaire_id:
                q = await self._latest_open_questionnaire(user_id)
                if not q:
                    user = await self.user_repo.get_by_id(user_id)
                    profile = await self.profile_repo.get_by_user_id(user_id)
                    normalized = await self._generate_and_store(user, profile, [])
                    questionnaire_id = normalized["questionnaire_id"]
                else:
                    questionnaire_id = _normalize_questionnaire(q)["questionnaire_id"]

            # 所有確認
            record = await self.questionnaire_repo.get_by_id(questionnaire_id)
            record_d = _asdict(record)
            if not record or _get(record_d, "user_id") != user_id:
                return {"statusCode": 404, "headers": _cors_headers(), "body": json.dumps({"error": "Questionnaire not found"})}

            # 保存
            await self.questionnaire_repo.submit_responses(
                questionnaire_id=questionnaire_id, responses=responses
            )

            # プロフィール反映
            await self._update_profile_from_responses(user_id, responses)

            return {
                "statusCode": 200,
                "headers": _cors_headers(),
                "body": json.dumps(
                    {
                        "message": "Questionnaire submitted successfully",
                        "questionnaire_id": questionnaire_id,
                        "submitted_at": datetime.now(timezone.utc).isoformat(),
                    }
                ),
            }

        except PermissionError as e:
            return {"statusCode": 401, "headers": _cors_headers(), "body": json.dumps({"error": str(e)})}
        except Exception as e:
            logger.exception("Error submitting questionnaire")
            return {"statusCode": 500, "headers": _cors_headers(), "body": json.dumps({"error": "Internal server error"})}

    async def get_questionnaire_history(
        self, event: Dict[str, Any], context: Any
    ) -> Dict[str, Any]:
        """履歴一覧。フロントの表示に合わせ、generated_at等も付けて返却。"""
        try:
            ids = await self._assert_and_get_user(event)
            user_id = ids["user_id"]

            items = await self.questionnaire_repo.get_user_questionnaires(user_id) or []
            history = []
            for q in items:
                d = _normalize_questionnaire(_asdict(q))
                # 追加で表示に役立つ統計
                d["question_count"] = len(d.get("questions", []))
                d["response_count"] = len(d.get("responses", []))
                history.append(d)

            return {
                "statusCode": 200,
                "headers": _cors_headers(),
                "body": json.dumps({"questionnaires": history, "total_count": len(history)}),
            }

        except PermissionError as e:
            return {"statusCode": 401, "headers": _cors_headers(), "body": json.dumps({"error": str(e)})}
        except Exception:
            logger.exception("Error getting questionnaire history")
            return {"statusCode": 500, "headers": _cors_headers(), "body": json.dumps({"error": "Internal server error"})}

    async def regenerate_questionnaire(
        self, event: Dict[str, Any], context: Any
    ) -> Dict[str, Any]:
        """
        直近または指定idを元に再生成。
        - pathParameters.questionnaire_id（オプション）
        - body.questionnaire_id（オプション）
        いずれも無い場合は直近のものをベースにして再生成
        """
        try:
            ids = await self._assert_and_get_user(event)
            user_id = ids["user_id"]

            qp = event.get("pathParameters", {}) or {}
            maybe_id = qp.get("questionnaire_id")

            if not maybe_id and event.get("body"):
                try:
                    body = json.loads(event["body"])
                    maybe_id = body.get("questionnaire_id")
                except Exception:
                    pass

            if not maybe_id:
                latest = await self._latest_open_questionnaire(user_id)
                if latest:
                    maybe_id = _normalize_questionnaire(latest)["questionnaire_id"]

            # 元データ
            if maybe_id:
                base = await self.questionnaire_repo.get_by_id(maybe_id)
                base_d = _asdict(base)
                if not base or _get(base_d, "user_id") != user_id:
                    return {"statusCode": 404, "headers": _cors_headers(), "body": json.dumps({"error": "Questionnaire not found"})}
                previous_responses = _get(base_d, "responses", [])
            else:
                previous_responses = []

            user = await self.user_repo.get_by_id(user_id)
            profile = await self.profile_repo.get_by_user_id(user_id)

            normalized = await self._generate_and_store(user, profile, previous_responses)
            normalized["regenerated_from"] = maybe_id

            logger.info(f"Regenerated questionnaire {normalized['questionnaire_id']} for user {user_id}")
            return {"statusCode": 200, "headers": _cors_headers(), "body": json.dumps(normalized)}

        except PermissionError as e:
            return {"statusCode": 401, "headers": _cors_headers(), "body": json.dumps({"error": str(e)})}
        except Exception:
            logger.exception("Error regenerating questionnaire")
            return {"statusCode": 500, "headers": _cors_headers(), "body": json.dumps({"error": "Internal server error"})}

    # ---------- profile update ----------

    async def _update_profile_from_responses(
        self, user_id: str, responses: list
    ) -> None:
        """回答からスキル/興味を抽出してプロフィールにマージ保存。"""
        try:
            profile = await self.profile_repo.get_by_user_id(user_id)
            if not profile:
                logger.warning(f"No profile found for user {user_id}")
                return

            new_skills: List[str] = []
            new_interests: List[str] = []

            for r in responses:
                qid = r.get("question_id", "") or r.get("id", "")
                ans = r.get("answer", r.get("value"))
                if not qid:
                    continue

                if "skill" in qid.lower() and ans:
                    if isinstance(ans, list):
                        new_skills.extend([str(a) for a in ans])
                    else:
                        new_skills.append(str(ans))

                if "interest" in qid.lower() or "career" in qid.lower():
                    if isinstance(ans, list):
                        new_interests.extend([str(a) for a in ans])
                    else:
                        new_interests.append(str(ans))

            update_data: Dict[str, Any] = {}

            if new_skills:
                existing_skills = getattr(profile, "skills", []) or []
                names = {s.get("name", "") for s in existing_skills if isinstance(s, dict)}
                for s in new_skills:
                    if s and s not in names:
                        existing_skills.append({"name": s, "level": "Intermediate", "years": 1, "certifications": []})
                update_data["skills"] = existing_skills

            if new_interests:
                preferences = getattr(profile, "preferences", {}) or {}
                current = preferences.get("preferred_roles", []) or []
                for it in new_interests:
                    if it and it not in current:
                        current.append(it)
                preferences["preferred_roles"] = current
                update_data["preferences"] = preferences

            qrs = getattr(profile, "questionnaire_responses", []) or []
            qrs.append({"timestamp": datetime.now(timezone.utc).isoformat(), "responses": responses})
            update_data["questionnaire_responses"] = qrs

            if update_data:
                await self.profile_repo.update_profile(user_id, update_data)
                logger.info(f"Updated profile for user {user_id} from questionnaire responses")

        except Exception:
            logger.exception("Error updating profile from responses")


# Lambda function handlers
questionnaire_handler = QuestionnaireHandler()

async def generate_questionnaire(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    return await questionnaire_handler.generate_questionnaire(event, context)

async def submit_questionnaire(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    return await questionnaire_handler.submit_questionnaire(event, context)

async def get_questionnaire_history(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    return await questionnaire_handler.get_questionnaire_history(event, context)

async def regenerate_questionnaire(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    return await questionnaire_handler.regenerate_questionnaire(event, context)
