"""
AI Questionnaire Lambda (no external crypto deps)
- Uses API Gateway Cognito authorizer claims for the user.
- Talks to DynamoDB directly via boto3 (no repository imports).
- Generates questionnaire via Bedrock; falls back to a static template if it fails.
"""

from __future__ import annotations

import json
import os
import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import boto3
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ---------- Env & clients ----------
REGION = os.environ.get("AWS_REGION") or os.environ.get("REGION") or "ap-northeast-1"
PREFIX = os.environ.get("DYNAMODB_TABLE_PREFIX", "honda-veteran-talent-matching-dev")
MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0")

ddb = boto3.resource("dynamodb", region_name=REGION)
bedrock = boto3.client("bedrock-runtime", region_name=REGION)

TBL_USERS = ddb.Table(f"{PREFIX}-users")
TBL_PROFILES = ddb.Table(f"{PREFIX}-veteran-profiles")
TBL_Q = ddb.Table(f"{PREFIX}-questionnaires")


# ---------- small helpers ----------
def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resp(status: int, body: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body, default=str),
    }


def _get_user_from_event(event: Dict[str, Any]) -> Optional[str]:
    claims = (
        event.get("requestContext", {})
        .get("authorizer", {})
        .get("claims", {})
        or {}
    )
    uid = claims.get("sub") or claims.get("username") or claims.get("cognito:username")
    if not uid:
        path = event.get("pathParameters") or {}
        uid = path.get("userId") or path.get("user_id")
    return uid


# ---------- Dynamo helpers ----------
def _get_user(uid: str) -> Optional[Dict[str, Any]]:
    try:
        r = TBL_USERS.get_item(Key={"user_id": uid})
        return r.get("Item")
    except ClientError as e:
        logger.error("Get user failed: %s", e)
        return None


def _get_profile(uid: str) -> Optional[Dict[str, Any]]:
    try:
        r = TBL_PROFILES.get_item(Key={"user_id": uid})
        return r.get("Item")
    except ClientError as e:
        logger.error("Get profile failed: %s", e)
        return None


def _save_questionnaire(uid: str, qdata: Dict[str, Any]) -> Dict[str, Any]:
    qid = str(uuid.uuid4())
    item = {
        "questionnaire_id": qid,
        "user_id": uid,
        "status": "generated",
        "created_at": _now_iso(),
        "ai_generated": True,
        # 保存時はネストした "questionnaire" に格納（既存スキーマ互換）
        "questionnaire": qdata,
        "responses": [],
    }
    TBL_Q.put_item(Item=item)
    return item


def _get_questionnaire(qid: str) -> Optional[Dict[str, Any]]:
    r = TBL_Q.get_item(Key={"questionnaire_id": qid})
    return r.get("Item")


def _query_user_questionnaires(uid: str) -> List[Dict[str, Any]]:
    # GSI: UserIdIndex (HASH user_id)
    try:
        r = TBL_Q.query(
            IndexName="UserIdIndex",
            KeyConditionExpression=boto3.dynamodb.conditions.Key("user_id").eq(uid),
        )
        return r.get("Items", [])
    except ClientError as e:
        logger.error("Query questionnaires failed: %s", e)
        return []


def _submit_responses(qid: str, responses: List[Dict[str, Any]]) -> None:
    TBL_Q.update_item(
        Key={"questionnaire_id": qid},
        UpdateExpression="SET #r = :r, #s = :s, #t = :t",
        ExpressionAttributeNames={"#r": "responses", "#s": "status", "#t": "submitted_at"},
        ExpressionAttributeValues={":r": responses, ":s": "completed", ":t": _now_iso()},
    )


def _update_profile_from_responses(uid: str, responses: List[Dict[str, Any]]) -> None:
    profile = _get_profile(uid)
    if not profile:
        logger.warning("No profile for user %s", uid)
        return

    new_skills: List[str] = []
    new_interests: List[str] = []

    for r in responses:
        qid = str(r.get("question_id", "")).lower()
        ans = r.get("answer", "")
        if "skill" in qid and ans:
            new_skills.extend(ans if isinstance(ans, list) else [ans])
        if "interest" in qid or "career" in qid:
            new_interests.extend(ans if isinstance(ans, list) else [ans])

    update_expr = []
    names: Dict[str, str] = {}
    values: Dict[str, Any] = {}

    if new_skills:
        existing = list(profile.get("skills", []) or [])
        names_set = {s.get("name", "") for s in existing if isinstance(s, dict)}
        for s in new_skills:
            if s and s not in names_set:
                existing.append({"name": s, "level": "Intermediate", "years": 1, "certifications": []})
        update_expr.append("#skills = :skills")
        names["#skills"] = "skills"
        values[":skills"] = existing

    if new_interests:
        prefs = dict(profile.get("preferences") or {})
        roles = list(prefs.get("preferred_roles", []) or [])
        for i in new_interests:
            if i and i not in roles:
                roles.append(i)
        prefs["preferred_roles"] = roles
        update_expr.append("#prefs = :prefs")
        names["#prefs"] = "preferences"
        values[":prefs"] = prefs

    q_hist = list(profile.get("questionnaire_responses", []) or [])
    q_hist.append({"timestamp": _now_iso(), "responses": responses})
    update_expr.append("#qh = :qh")
    names["#qh"] = "questionnaire_responses"
    values[":qh"] = q_hist

    if update_expr:
        TBL_PROFILES.update_item(
            Key={"user_id": uid},
            UpdateExpression="SET " + ", ".join(update_expr),
            ExpressionAttributeNames=names,
            ExpressionAttributeValues=values,
        )


# ---------- Bedrock ----------
def _fallback_questionnaire(name: str) -> Dict[str, Any]:
    return {
        "title": f"{name}さん向けキャリアAI問診",
        "questions": [
            {"id": "skills_primary", "text": "現在の主な専門スキルは何ですか？", "type": "text", "category": "skills", "required": True},
            {"id": "skills_lang", "text": "業務で使ったことのあるプログラミング言語を選んでください。", "type": "multiple_choice", "options": ["Python", "Java", "C/C++", "Go", "その他"], "category": "skills", "required": False},
            {"id": "exp_years", "text": "現在の職種の経験年数を教えてください（1〜5で評価）。", "type": "rating", "category": "experience", "required": True},
            {"id": "domain_exp", "text": "自動車・ロボティクス・モビリティ領域で携わったことのある分野を教えてください。", "type": "text", "category": "experience", "required": False},
            {"id": "interest_roles", "text": "今後挑戦したいロール（職務）を教えてください。", "type": "text", "category": "preferences", "required": True},
            {"id": "work_style", "text": "勤務地・働き方（出社/リモート/ハイブリッド）の希望はありますか？", "type": "text", "category": "preferences", "required": False},
            {"id": "leadership", "text": "ピープルマネジメントに関心はありますか？", "type": "boolean", "category": "goals", "required": False},
            {"id": "goal_6m", "text": "今後6か月で達成したいキャリア目標は何ですか？", "type": "text", "category": "goals", "required": False},
        ],
        "responses": [],
    }


def _generate_with_bedrock(name: str, department: str, years_experience: int, current_role: str,
                           previous_responses: List[Dict[str, Any]]) -> Dict[str, Any]:
    system = (
        "You are a career counselor. Create a short personalized questionnaire in Japanese "
        "as compact JSON with fields: title (string), questions (array of {id,text,type,category,required,options?}). "
        "Use types: text|multiple_choice|rating|boolean. Keep 6-10 questions. "
        "Return ONLY JSON."
    )
    user_msg = {
        "name": name,
        "department": department,
        "years_experience": years_experience,
        "current_role": current_role,
        "previous_responses": previous_responses,
    }
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1000,
        "temperature": 0.3,
        "system": system,
        "messages": [{"role": "user", "content": [{"type": "text", "text": json.dumps(user_msg, ensure_ascii=False)}]}],
    })

    try:
        res = bedrock.invoke_model(modelId=MODEL_ID, body=body)
        payload = res["body"].read().decode("utf-8")
        data = json.loads(payload)
        text = ""
        for c in data.get("content", []):
            if c.get("type") == "text":
                text += c.get("text", "")
        # 有効な JSON 抽出
        parsed = json.loads(text)
        # 最低限のバリデーション
        if not isinstance(parsed.get("questions", []), list):
            raise ValueError("Invalid questions")
        return {"title": parsed.get("title") or f"{name}さん向けAI問診", "questions": parsed["questions"], "responses": []}
    except Exception as e:
        logger.warning("Bedrock generation failed, fallback used: %s", e)
        return _fallback_questionnaire(name)


# ---------- Handlers ----------
async def generate_questionnaire(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    try:
        uid = _get_user_from_event(event)
        if not uid:
            return _resp(401, {"error": "Unauthorized"})

        user = _get_user(uid) or {}
        profile = _get_profile(uid) or {}

        # years of experience
        years = 0
        j = user.get("join_date")
        if j:
            try:
                dt = datetime.fromisoformat(str(j).replace("Z", "+00:00"))
                years = (datetime.now(timezone.utc) - dt).days // 365
            except Exception:
                years = 0

        # context from latest questionnaire
        prev_items = _query_user_questionnaires(uid)
        previous_responses: List[Dict[str, Any]] = []
        if prev_items:
            latest = max(prev_items, key=lambda x: x.get("created_at", ""))
            previous_responses = latest.get("responses") or []

        qdata = _generate_with_bedrock(
            name=user.get("name", "ユーザー"),
            department=user.get("department", "General"),
            years_experience=years,
            current_role=profile.get("business_title", "Employee"),
            previous_responses=previous_responses,
        )

        saved = _save_questionnaire(uid, qdata)
        # フロントの期待に合わせて { questionnaire: {...} } で返す
        shaped = {
            "questionnaire_id": saved["questionnaire_id"],
            "status": saved["status"],
            "created_at": saved["created_at"],
            **qdata,
        }
        return _resp(200, {"questionnaire": shaped})
    except Exception as e:
        logger.exception("generate_questionnaire error: %s", e)
        return _resp(500, {"error": "Internal server error"})


async def submit_questionnaire(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    try:
        uid = _get_user_from_event(event)
        if not uid:
            return _resp(401, {"error": "Unauthorized"})

        try:
            body = json.loads(event.get("body") or "{}")
        except json.JSONDecodeError:
            return _resp(400, {"error": "Invalid JSON in request body"})

        qid = body.get("questionnaire_id")
        responses = body.get("responses") or []
        if not qid or not isinstance(responses, list) or not responses:
            return _resp(400, {"error": "Missing questionnaire_id or responses"})

        item = _get_questionnaire(qid)
        if not item or item.get("user_id") != uid:
            return _resp(404, {"error": "Questionnaire not found"})

        _submit_responses(qid, responses)
        _update_profile_from_responses(uid, responses)

        return _resp(200, {"message": "Questionnaire submitted successfully", "questionnaire_id": qid})
    except Exception as e:
        logger.exception("submit_questionnaire error: %s", e)
        return _resp(500, {"error": "Internal server error"})


async def get_questionnaire_history(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    try:
        uid = _get_user_from_event(event)
        if not uid:
            return _resp(401, {"error": "Unauthorized"})

        items = _query_user_questionnaires(uid)
        history: List[Dict[str, Any]] = []
        for it in items:
            q = it.get("questionnaire") or {}
            history.append({
                "questionnaire_id": it.get("questionnaire_id"),
                "title": q.get("title"),
                "status": it.get("status"),
                "created_at": it.get("created_at"),
                "submitted_at": it.get("submitted_at"),
                "ai_generated": it.get("ai_generated", True),
                "questions": q.get("questions", []),
                "responses": it.get("responses", []),
                "generated_at": it.get("created_at"),
                "completed_at": it.get("submitted_at"),
            })
        return _resp(200, {"questionnaires": history, "total_count": len(history)})
    except Exception as e:
        logger.exception("get_questionnaire_history error: %s", e)
        return _resp(500, {"error": "Internal server error"})


async def regenerate_questionnaire(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    try:
        uid = _get_user_from_event(event)
        if not uid:
            return _resp(401, {"error": "Unauthorized"})

        # optional: body.questionnaire_id to reuse previous responses
        body = {}
        if event.get("body"):
            try:
                body = json.loads(event["body"])
            except json.JSONDecodeError:
                body = {}
        from_qid = body.get("questionnaire_id")

        user = _get_user(uid) or {}
        profile = _get_profile(uid) or {}

        years = 0
        j = user.get("join_date")
        if j:
            try:
                dt = datetime.fromisoformat(str(j).replace("Z", "+00:00"))
                years = (datetime.now(timezone.utc) - dt).days // 365
            except Exception:
                years = 0

        prev_responses: List[Dict[str, Any]] = []
        if from_qid:
            orig = _get_questionnaire(from_qid)
            if orig:
                prev_responses = orig.get("responses") or []

        qdata = _generate_with_bedrock(
            name=user.get("name", "ユーザー"),
            department=user.get("department", "General"),
            years_experience=years,
            current_role=profile.get("business_title", "Employee"),
            previous_responses=prev_responses,
        )

        saved = _save_questionnaire(uid, qdata)
        shaped = {
            "questionnaire_id": saved["questionnaire_id"],
            "status": saved["status"],
            "created_at": saved["created_at"],
            "regenerated_from": from_qid,
            **qdata,
        }
        return _resp(200, {"questionnaire": shaped})
    except Exception as e:
        logger.exception("regenerate_questionnaire error: %s", e)
        return _resp(500, {"error": "Internal server error"})
