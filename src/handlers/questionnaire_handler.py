"""
双日テックイノベーション：AI人材発掘・配置マッチングMVP（AI CoE支援）
AIスキル棚卸し（セルフ診断）Lambdaハンドラー（同期版、暗号化依存なし）

社内AI人材候補のAIスキル棚卸し（セルフ診断）を担当します。
- API Gateway Cognito オーソライザーのクレームからユーザーを取得します
- boto3 経由で DynamoDB に直接アクセスします（リポジトリインポートなし）
- Bedrock でAIスキル棚卸し問診を生成し、失敗時は静的テンプレートにフォールバックします
"""

from __future__ import annotations

import json
import os
import uuid
import logging
import base64
from decimal import Decimal
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import ClientError

from src.utils.branding_logger import get_branding_logger
from src.config.ai_content_config import ai_content_config

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ブランディングロガーを初期化（双日TI向けAIスキル棚卸し（セルフ診断））
branding_logger = get_branding_logger('questionnaire_handler')

# ---------- Env & clients ----------
REGION = os.environ.get("AWS_REGION") or os.environ.get("REGION") or "ap-northeast-1"
PREFIX = os.environ.get("DYNAMODB_TABLE_PREFIX", "honda-veteran-talent-matching-dev")
# v1 はオンデマンド可
MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20240620-v1:0")
PROFILE_ARN = os.environ.get("BEDROCK_INFERENCE_PROFILE_ARN")  # 任意

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
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Methods": "OPTIONS,GET,POST,PUT",
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


def _parse_body(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Robust JSON body parser:
    - Handles empty body
    - Handles isBase64Encoded=True
    - Handles double-encoded JSON strings: '"{}"', '"{...}"'
    - Returns {} on any parsing problem
    """
    raw = event.get("body")
    if not raw:
        return {}
    try:
        if event.get("isBase64Encoded"):
            raw = base64.b64decode(raw).decode("utf-8")
        parsed = json.loads(raw)
        if isinstance(parsed, str):
            try:
                parsed2 = json.loads(parsed)
                return parsed2 if isinstance(parsed2, dict) else {}
            except Exception:
                return {}
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


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


def _ensure_profile(uid: str) -> Dict[str, Any]:
    prof = _get_profile(uid)
    if prof:
        return prof
    item = {
        "user_id": uid,
        "created_at": _now_iso(),
        "business_title": "",
        "skills": [],
        "preferences": {"preferred_roles": []},
        "questionnaire_responses": [],
    }
    TBL_PROFILES.put_item(Item=item)
    logger.info("Profile created for user %s", uid)
    branding_logger.log_custom_event('profile_created', {'user_id': uid})
    return item


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
    from boto3.dynamodb.conditions import Key  # ローカル import（コールドスタート最適化）
    try:
        r = TBL_Q.query(IndexName="UserIdIndex", KeyConditionExpression=Key("user_id").eq(uid))
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
    profile = _ensure_profile(uid)

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


# ---------- JSON/Decimal ----------
def _to_plain(obj: Any) -> Any:
    """DynamoDB Decimal を JSON 可能な型に再帰変換"""
    if isinstance(obj, Decimal):
        try:
            return int(obj) if obj == obj.to_integral_value() else float(obj)
        except Exception:
            return float(obj)
    if isinstance(obj, list):
        return [_to_plain(v) for v in obj]
    if isinstance(obj, dict):
        return {k: _to_plain(v) for k, v in obj.items()}
    return obj


# ---------- Bedrock ----------
def _fallback_questionnaire(name: str) -> Dict[str, Any]:
    # AIスキル棚卸し（セルフ診断）のフォールバックプロンプトを使用
    fallback_intro = ai_content_config.get_questionnaire_prompt('fallback_prompt')
    
    return {
        "title": f"{name}さん向けAIスキル棚卸し（セルフ診断）",
        "description": fallback_intro,
        "questions": [
            {"id": "skills_primary", "text": "現在の主なAI関連スキル・技術は何ですか？", "type": "text", "category": "skills", "required": True},
            {"id": "manufacturing_exp", "text": "AI・データ活用の経験分野を教えてください（複数選択可）", "type": "multiple_choice", "options": ["機械学習", "データ分析", "自然言語処理", "画像認識", "業務自動化（RPA）", "その他"], "category": "experience", "required": True},
            {"id": "exp_years", "text": "AI・データ活用の経験年数を教えてください（1〜5で評価）", "type": "rating", "category": "experience", "required": True},
            {"id": "improvement_activities", "text": "これまでに取り組んだAI活用・改善活動や成果を教えてください", "type": "text", "category": "achievements", "required": False},
            {"id": "leadership_exp", "text": "AIプロジェクトのリーダーやマネジメントの経験はありますか？", "type": "boolean", "category": "experience", "required": False},
            {"id": "participation_interest", "text": "今後参加したいAIポジション／プロジェクトの分野・役割を教えてください", "type": "text", "category": "preferences", "required": True},
            {"id": "work_style", "text": "希望する勤務形態を教えてください", "type": "multiple_choice", "options": ["常駐", "リモート", "ハイブリッド", "プロジェクト単位", "その他"], "category": "preferences", "required": False},
            {"id": "skill_development", "text": "今後伸ばしたいAIスキルや学びたい技術はありますか？", "type": "text", "category": "goals", "required": False},
            {"id": "contribution_goal", "text": "双日TIのAI内製化推進にどのような貢献をしたいですか？", "type": "text", "category": "goals", "required": False},
        ],
        "responses": [],
    }


def _generate_with_bedrock(name: str, department: str, years_experience: int,
                           current_role: str, previous_responses: List[Dict[str, Any]]) -> Dict[str, Any]:
    # Use AI content config for branded prompts
    system_prompt = ai_content_config.get_questionnaire_prompt('system_prompt')
    
    context_prompt = ai_content_config.get_questionnaire_prompt(
        'context_prompt',
        name=name,
        department=department,
        experience_years=years_experience,
        skills=current_role,
        achievements="過去の実績情報"  # This could be enhanced with actual achievements
    )
    
    # Combine system and context prompts
    full_system_prompt = f"{system_prompt}\n\n{context_prompt}"
    
    user_msg = _to_plain({
        "name": name,
        "department": department,
        "years_experience": years_experience,
        "current_role": current_role,
        "previous_responses": previous_responses,
    })

    try:
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1500,  # Increased for more detailed responses
            "temperature": 0.3,
            "system": full_system_prompt,
            "messages": [{"role": "user", "content": [{"type": "text", "text": json.dumps(user_msg, ensure_ascii=False)}]}],
        })

        if PROFILE_ARN:
            res = bedrock.invoke_model(inferenceProfileId=PROFILE_ARN, body=body)
        else:
            res = bedrock.invoke_model(modelId=MODEL_ID, body=body)

        payload = res["body"].read().decode("utf-8")
        data = json.loads(payload)
        text = ""
        for c in data.get("content", []):
            if c.get("type") == "text":
                text += c.get("text", "")
        parsed = json.loads(text)
        if not isinstance(parsed.get("questions", []), list):
            raise ValueError("Invalid questions")
        
        # Apply branding to the title
        title = parsed.get("title") or f"{name}さん向けAIスキル棚卸し（セルフ診断）"
        branded_title = ai_content_config.apply_branding_context(title)
        
        return {"title": branded_title, "questions": parsed["questions"], "responses": []}
    except Exception as e:
        logger.warning("Bedrock generation failed, fallback used: %s", e)
        branding_logger.log_error_occurred('ai_generation_failed', str(e))
        return _fallback_questionnaire(name)


# ---------- Handlers (SYNC) ----------
def generate_questionnaire(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    try:
        uid = _get_user_from_event(event)
        if not uid:
            return _resp(401, {"error": "Unauthorized"})

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


def submit_questionnaire(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    try:
        uid = _get_user_from_event(event)
        if not uid:
            return _resp(401, {"error": "Unauthorized"})

        body = _parse_body(event)
        path = event.get("pathParameters") or {}
        qid = body.get("questionnaire_id") or path.get("questionnaire_id") or path.get("id")
        responses = body.get("responses") or []
        if not qid or not isinstance(responses, list) or not responses:
            return _resp(400, {"error": "Missing questionnaire_id or responses"})

        item = _get_questionnaire(qid)
        if not item or item.get("user_id") != uid:
            return _resp(404, {"error": "Questionnaire not found"})

        _submit_responses(qid, responses)
        _update_profile_from_responses(uid, responses)
        
        # Log questionnaire completion
        branding_logger.log_questionnaire_completed(uid)

        return _resp(200, {"message": "AIスキル棚卸し（セルフ診断）が正常に完了しました", "questionnaire_id": qid})
    except Exception as e:
        logger.exception("submit_questionnaire error: %s", e)
        return _resp(500, {"error": "Internal server error"})


def get_questionnaire_history(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
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


def regenerate_questionnaire(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    try:
        uid = _get_user_from_event(event)
        if not uid:
            return _resp(401, {"error": "Unauthorized"})

        body = _parse_body(event)
        path = event.get("pathParameters") or {}
        from_qid = path.get("questionnaire_id") or path.get("id") \
                   or (body.get("questionnaire_id") if isinstance(body, dict) else None)

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
