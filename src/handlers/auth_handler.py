"""
双日テックイノベーション：AI人材発掘・配置マッチングMVP（AI CoE支援）
認証ハンドラー - Cognito User Pool 連携

社内AI人材候補（社員）およびAIポジションオーナーの
ユーザー登録・ログイン・ログアウト・JWTトークン処理を担当します。
RBACシステムおよびセキュリティ監査と連携します。

※ PyJWT への依存を排除しました。トークン検証は API Gateway の
   Cognito オーソライザーで行われる前提で、Lambda では
   requestContext.authorizer.claims を優先利用します。
"""

from __future__ import annotations

import base64
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import boto3
from botocore.exceptions import ClientError

from src.utils.performance import optimize_lambda_handler
from src.utils.rbac import get_available_roles, rbac_manager, validate_role
from src.utils.security_audit import extract_request_info, security_auditor
from src.utils.security_headers import create_secure_response, security_middleware
from src.config.message_config import message_config
from src.utils.branding_logger import get_branding_logger

# ──────────────────────────────────────────────────────────────
# Logging / AWS clients / Env
# ──────────────────────────────────────────────────────────────
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# ブランディングロガーを初期化（双日TI向けAI人材発掘・配置マッチングMVP）
branding_logger = get_branding_logger('auth_handler')

cognito_client = boto3.client("cognito-idp")
dynamodb = boto3.resource("dynamodb")

USER_POOL_ID = os.environ.get("COGNITO_USER_POOL_ID")  # e.g. ap-northeast-1_y0c315iUX
CLIENT_ID = os.environ.get("COGNITO_CLIENT_ID")        # e.g. 146raomfft06uhv8d93rv7iiol
TABLE_PREFIX = os.environ.get("DYNAMODB_TABLE_PREFIX")  # e.g. honda-veteran-talent-matching-prod
USERS_TABLE_NAME = f"{TABLE_PREFIX}-users" if TABLE_PREFIX else os.environ.get("USERS_TABLE", "")

users_table = dynamodb.Table(USERS_TABLE_NAME)


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────
def create_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """Create standardized HTTP response with security headers."""
    origin = None  # security_middleware / create_secure_response 側で最終決定
    return create_secure_response(status_code, body, origin=origin)


def extract_token_from_header(event: Dict[str, Any]) -> Optional[str]:
    """
    Extract JWT from Authorization header.
    Accepts both 'Bearer <token>' and raw '<token>'.
    """
    headers = event.get("headers", {}) or {}
    auth_header = headers.get("Authorization") or headers.get("authorization")
    if not auth_header:
        return None
    ah = auth_header.strip()
    if ah.lower().startswith("bearer "):
        return ah.split(" ", 1)[1].strip()
    return ah  # raw token


def _decode_jwt_payload_no_verify(token: str) -> Dict[str, Any]:
    """
    Decode JWT payload without signature verification.
    API Gateway + Cognito authorizer already verified the token.
    """
    try:
        payload_b64 = token.split(".")[1]
        padding = "=" * (-len(payload_b64) % 4)
        data = base64.urlsafe_b64decode(payload_b64 + padding)
        return json.loads(data)
    except Exception:
        return {}


def get_user_id_from_token(jwt_token: str) -> Optional[str]:
    """
    Extract user identifier from JWT payload.
    Tries sub -> cognito:username -> username (AccessToken では username が多い)
    """
    claims = _decode_jwt_payload_no_verify(jwt_token)
    return claims.get("sub") or claims.get("cognito:username") or claims.get("username")


def get_claims_from_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """Safely extract claims from authorizer (preferred source)."""
    return (
        event.get("requestContext", {})
        .get("authorizer", {})
        .get("claims", {})
    ) or {}


def get_user_id_from_event(event: Dict[str, Any]) -> Optional[str]:
    """Prefer claims; fall back to decoding header token."""
    claims = get_claims_from_event(event)
    uid = claims.get("sub") or claims.get("cognito:username") or claims.get("username")
    if uid:
        return uid
    token = extract_token_from_header(event)
    if token:
        return get_user_id_from_token(token)
    return None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ──────────────────────────────────────────────────────────────
# Handler (routing)
# ──────────────────────────────────────────────────────────────
@optimize_lambda_handler
@security_middleware
def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    認証操作のメインLambdaハンドラー。
    HTTPメソッドとパスに基づいてリクエストをルーティングします。
    双日TI：AI人材発掘・配置マッチングMVP（AI CoE支援）向け認証処理。
    """
    try:
        http_method = event.get("httpMethod")
        path = event.get("path", "")
        path_parameters = event.get("pathParameters") or {}

        # Extract action from /auth/{action}
        path_parts = path.strip("/").split("/")
        if len(path_parts) >= 2:
            action = path_parts[1]
        else:
            action = (
                path_parameters.get("proxy", "").split("/")[0]
                if path_parameters.get("proxy")
                else ""
            )

        logger.info(f"Processing {http_method} request for action: {action}")
        branding_logger.log_api_request(http_method, f"/auth/{action}")

        if http_method == "POST":
            if action == "register":
                return register_user(event)
            if action == "login":
                return login_user(event)
            if action == "logout":
                return logout_user(event)
            if action == "refresh":
                return refresh_token(event)

        elif http_method == "GET":
            if action == "profile":
                return get_user_profile(event)  # ← 初回アクセスで upsert
            if action == "verify":
                return verify_token(event)

        elif http_method == "PUT":
            if action == "profile":
                return update_user_profile(event)

        return create_response(400, {"error": message_config.get_error_message('invalid_input')})

    except Exception as e:
        logger.exception("Error in auth handler")
        return create_response(500, {"error": message_config.get_error_message('internal_error')})


# ──────────────────────────────────────────────────────────────
# Actions
# ──────────────────────────────────────────────────────────────
def register_user(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    社内AI人材候補（社員）を Cognito User Pool に登録し、DynamoDB にユーザーレコードを作成します。
    （管理者作成フロー / AdminCreate を想定。UI サインアップ利用時は未使用のことも）
    """
    try:
        body = json.loads(event.get("body", "{}"))

        required_fields = ["email", "password", "name", "employee_id", "department"]
        for field in required_fields:
            if not body.get(field):
                return create_response(400, {"error": f"必須フィールドが不足しています: {field}"})

        email = body["email"]
        password = body["password"]
        name = body["name"]
        employee_id = body["employee_id"]
        department = body["department"]
        role = body.get("role", "veteran")

        if not validate_role(role):
            available = get_available_roles()
            return create_response(400, {"error": f"無効な役割です。次のいずれかである必要があります: {available}"})

        # Admin create
        u = cognito_client.admin_create_user(
            UserPoolId=USER_POOL_ID,
            Username=email,
            UserAttributes=[
                {"Name": "email", "Value": email},
                {"Name": "email_verified", "Value": "true"},
                {"Name": "name", "Value": name},
                {"Name": "custom:employee_id", "Value": employee_id},
                {"Name": "custom:department", "Value": department},
                {"Name": "custom:role", "Value": role},
            ],
            TemporaryPassword=password,
            MessageAction="SUPPRESS",
        )
        # Cognito の Username は email を指定しているが、今後の一貫性のため
        # DynamoDB の主キーは "sub" を推奨（ここでは username を暫定採用）
        user_id = u["User"]["Username"]

        # Set permanent password
        cognito_client.admin_set_user_password(
            UserPoolId=USER_POOL_ID, Username=user_id, Password=password, Permanent=True
        )

        # Create user record
        now = _now_iso()
        users_table.put_item(Item={
            "user_id": user_id,
            "employee_id": employee_id,
            "email": email,
            "name": name,
            "department": department,
            "role": role,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        })

        logger.info(f"User registered successfully: {email}")
        branding_logger.log_custom_event('user_registration', {'email': email, 'role': role})
        return create_response(201, {
            "message": message_config.get_success_message('user_created'),
            "user_id": user_id,
            "email": email,
            "role": role,
        })

    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code == "UsernameExistsException":
            return create_response(409, {"error": "社内AI人材候補として既に登録されています"})
        if code == "InvalidPasswordException":
            return create_response(400, {"error": "パスワードが要件を満たしていません"})
        logger.exception("Cognito error on register_user")
        return create_response(500, {"error": message_config.get_error_message('registration_failed')})
    except Exception:
        logger.exception("Registration error")
        return create_response(500, {"error": message_config.get_error_message('registration_failed')})


def login_user(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Cognito（ADMIN_NO_SRP_AUTH）で認証し、トークンと社内AI人材候補情報を返します。
    双日TI：AI人材発掘・配置マッチングMVP（AI CoE支援）へのログイン処理。
    """
    request_info = extract_request_info(event)
    try:
        body = json.loads(event.get("body", "{}"))
        email = body.get("email")
        password = body.get("password")
        if not email or not password:
            return create_response(400, {"error": "メールアドレスとパスワードが必要です"})

        auth = cognito_client.admin_initiate_auth(
            UserPoolId=USER_POOL_ID,
            ClientId=CLIENT_ID,
            AuthFlow="ADMIN_NO_SRP_AUTH",
            AuthParameters={"USERNAME": email, "PASSWORD": password},
        )

        tokens = auth["AuthenticationResult"]
        access_token = tokens["AccessToken"]
        id_token = tokens["IdToken"]
        refresh_token = tokens.get("RefreshToken", "")

        # user_id は AccessToken の claims から（sub/username）
        uid = get_user_id_from_token(access_token) or email
        user = users_table.get_item(Key={"user_id": uid}).get("Item", {})

        security_auditor.log_login_attempt(
            user_id=uid,
            success=True,
            source_ip=request_info.get("source_ip"),
            user_agent=request_info.get("user_agent"),
        )

        return create_response(200, {
            "message": message_config.get_success_message('authentication_success'),
            "tokens": {
                "access_token": access_token,
                "id_token": id_token,
                "refresh_token": refresh_token,
                "expires_in": tokens["ExpiresIn"],
            },
            "user": {
                "user_id": user.get("user_id", uid),
                "email": user.get("email", email),
                "name": user.get("name", ""),
                "role": user.get("role", ""),
                "department": user.get("department", ""),
                "permissions": [
                    perm.value for perm in rbac_manager.get_user_permissions(user.get("role", ""))
                ],
            },
        })

    except ClientError as e:
        code = e.response["Error"]["Code"]
        security_auditor.log_login_attempt(
            user_id=email or "unknown",
            success=False,
            source_ip=request_info.get("source_ip"),
            user_agent=request_info.get("user_agent"),
            failure_reason=code,
        )
        if code in ["NotAuthorizedException", "UserNotFoundException"]:
            return create_response(401, {"error": message_config.get_error_message('invalid_credentials')})
        if code == "UserNotConfirmedException":
            return create_response(401, {"error": "ユーザーが確認されていません"})
        logger.exception("Cognito login error")
        return create_response(500, {"error": message_config.get_error_message('authentication_failed')})
    except Exception:
        security_auditor.log_login_attempt(
            user_id=email or "unknown",
            success=False,
            source_ip=request_info.get("source_ip"),
            user_agent=request_info.get("user_agent"),
            failure_reason="system_error",
        )
        logger.exception("Login error")
        return create_response(500, {"error": message_config.get_error_message('authentication_failed')})


def logout_user(event: Dict[str, Any]) -> Dict[str, Any]:
    """アクセストークンによるグローバルサインアウト（AI人材発掘・配置マッチングMVPからのログアウト）。"""
    request_info = extract_request_info(event)
    try:
        access_token = extract_token_from_header(event)
        if not access_token:
            return create_response(401, {"error": "アクセストークンが必要です"})

        uid = get_user_id_from_token(access_token)
        cognito_client.global_sign_out(AccessToken=access_token)

        if uid:
            security_auditor.log_logout(user_id=uid, source_ip=request_info.get("source_ip"))

        return create_response(200, {"message": "ログアウトが成功しました"})
    except ClientError:
        logger.exception("Logout error")
        return create_response(500, {"error": "ログアウトに失敗しました"})
    except Exception:
        logger.exception("Logout error")
        return create_response(500, {"error": "ログアウトに失敗しました"})


def refresh_token(event: Dict[str, Any]) -> Dict[str, Any]:
    """リフレッシュトークンを使用してアクセストークンを更新します。"""
    try:
        body = json.loads(event.get("body", "{}"))
        refresh_token = body.get("refresh_token")
        if not refresh_token:
            return create_response(400, {"error": "リフレッシュトークンが必要です"})

        auth = cognito_client.admin_initiate_auth(
            UserPoolId=USER_POOL_ID,
            ClientId=CLIENT_ID,
            AuthFlow="REFRESH_TOKEN_AUTH",
            AuthParameters={"REFRESH_TOKEN": refresh_token},
        )
        tokens = auth["AuthenticationResult"]

        return create_response(200, {
            "message": "トークンが正常に更新されました",
            "tokens": {
                "access_token": tokens["AccessToken"],
                "id_token": tokens["IdToken"],
                "expires_in": tokens["ExpiresIn"],
            },
        })

    except ClientError:
        logger.exception("Token refresh error")
        return create_response(401, {"error": "無効なリフレッシュトークンです"})
    except Exception:
        logger.exception("Token refresh error")
        return create_response(500, {"error": "トークンの更新に失敗しました"})


def get_user_profile(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    社内AI人材候補の現在のユーザープロフィールを返します。
    未登録の場合は初回アクセス時に自動作成（upsert）します。
    """
    try:
        claims = get_claims_from_event(event)
        user_id = get_user_id_from_event(event)
        if not user_id:
            return create_response(401, {"error": "Invalid token"})

        resp = users_table.get_item(Key={"user_id": user_id})
        item = resp.get("Item")

        if not item:
            now = _now_iso()
            item = {
                "user_id": user_id,
                "employee_id": claims.get("custom:employee_id", ""),
                "email": claims.get("email", ""),
                "name": claims.get("name", ""),
                "department": claims.get("custom:department", ""),
                "role": claims.get("custom:role", "veteran"),
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            }
            users_table.put_item(Item=item)

        user_profile = {
            "user_id": item.get("user_id"),
            "employee_id": item.get("employee_id", ""),
            "email": item.get("email", ""),
            "name": item.get("name", ""),
            "department": item.get("department", ""),
            "role": item.get("role", ""),
            "is_active": item.get("is_active", True),
            "created_at": item.get("created_at", ""),
        }
        return create_response(200, {"user": user_profile})

    except Exception:
        logger.exception("Get profile error")
        return create_response(500, {"error": message_config.get_error_message('profile_validation_failed')})


def update_user_profile(event: Dict[str, Any]) -> Dict[str, Any]:
    """許可されたプロフィールフィールドを更新します（社内AI人材候補の基本情報更新）。"""
    try:
        user_id = get_user_id_from_event(event)
        if not user_id:
            return create_response(401, {"error": "Invalid token"})

        body = json.loads(event.get("body", "{}"))
        allowed_fields = ["name", "department"]

        update_expression = "SET updated_at = :updated_at"
        expression_values = {":updated_at": _now_iso()}

        for field in allowed_fields:
            if field in body:
                update_expression += f", {field} = :{field}"
                expression_values[f":{field}"] = body[field]

        users_table.update_item(
            Key={"user_id": user_id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_values,
        )

        if "name" in body:
            cognito_client.admin_update_user_attributes(
                UserPoolId=USER_POOL_ID,
                Username=user_id,
                UserAttributes=[{"Name": "name", "Value": body["name"]}],
            )

        return create_response(200, {"message": message_config.get_success_message('profile_updated')})

    except Exception:
        logger.exception("Update profile error")
        return create_response(500, {"error": message_config.get_error_message('profile_validation_failed')})


def verify_token(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Cognito GetUser を呼び出してアクセストークンを検証します。
    AI人材発掘・配置マッチングMVP（AI CoE支援）へのアクセス権限を確認します。
    """
    try:
        token = extract_token_from_header(event)
        if not token:
            return create_response(401, {"error": "アクセストークンが必要です"})

        user_info = cognito_client.get_user(AccessToken=token)
        attrs = {a["Name"]: a["Value"] for a in user_info.get("UserAttributes", [])}

        return create_response(200, {
            "valid": True,
            "user": {
                "user_id": user_info.get("Username"),
                "email": attrs.get("email"),
                "name": attrs.get("name"),
                "role": attrs.get("custom:role"),
                "department": attrs.get("custom:department"),
            },
        })

    except ClientError:
        logger.exception("Token verification error (Cognito)")
        return create_response(401, {"valid": False, "error": "無効なトークンです"})
    except Exception:
        logger.exception("Token verification error")
        return create_response(500, {"error": "トークンの検証に失敗しました"})
