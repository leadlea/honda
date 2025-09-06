"""
Authentication handler for Cognito User Pool integration.
Handles user registration, login, logout, and JWT token verification.
Integrates with RBAC system and security auditing.
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import boto3
import jwt
from botocore.exceptions import ClientError

from src.utils.performance import optimize_lambda_handler

# Import RBAC and security audit modules
from src.utils.rbac import get_available_roles, rbac_manager, validate_role
from src.utils.security_audit import (
    extract_request_info,
    security_auditor,
)
from src.utils.security_headers import (
    create_secure_response,
    security_middleware,
)

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
cognito_client = boto3.client("cognito-idp")
dynamodb = boto3.resource("dynamodb")

# Environment variables
USER_POOL_ID = os.environ.get("COGNITO_USER_POOL_ID")
CLIENT_ID = os.environ.get("COGNITO_CLIENT_ID")
USERS_TABLE_NAME = f"{os.environ.get('DYNAMODB_TABLE_PREFIX')}-users"

# Initialize DynamoDB table
users_table = dynamodb.Table(USERS_TABLE_NAME)


@optimize_lambda_handler
@security_middleware
def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for authentication operations.
    Routes requests based on HTTP method and path.
    """
    try:
        http_method = event.get("httpMethod")
        path = event.get("path", "")
        path_parameters = event.get("pathParameters") or {}

        # Extract the action from the path
        path_parts = path.strip("/").split("/")
        if len(path_parts) >= 2:
            action = path_parts[1]  # auth/{action}
        else:
            action = (
                path_parameters.get("proxy", "").split("/")[0]
                if path_parameters.get("proxy")
                else ""
            )

        logger.info(f"Processing {http_method} request for action: {action}")

        # Route to appropriate handler
        if http_method == "POST":
            if action == "register":
                return register_user(event)
            elif action == "login":
                return login_user(event)
            elif action == "logout":
                return logout_user(event)
            elif action == "refresh":
                return refresh_token(event)
        elif http_method == "GET":
            if action == "profile":
                return get_user_profile(event)
            elif action == "verify":
                return verify_token(event)
        elif http_method == "PUT":
            if action == "profile":
                return update_user_profile(event)

        return create_response(400, {"error": "Invalid action or method"})

    except Exception as e:
        logger.error(f"Error in auth handler: {str(e)}")
        return create_response(500, {"error": "Internal server error"})


def register_user(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Register a new user in Cognito User Pool and create user record in DynamoDB.
    """
    try:
        body = json.loads(event.get("body", "{}"))

        # Validate required fields
        required_fields = ["email", "password", "name", "employee_id", "department"]
        for field in required_fields:
            if not body.get(field):
                return create_response(
                    400, {"error": f"Missing required field: {field}"}
                )

        email = body["email"]
        password = body["password"]
        name = body["name"]
        employee_id = body["employee_id"]
        department = body["department"]
        role = body.get("role", "veteran")  # Default to veteran role

        # Validate role using RBAC system
        if not validate_role(role):
            available_roles = get_available_roles()
            return create_response(
                400, {"error": f"Invalid role. Must be one of: {available_roles}"}
            )

        # Create user in Cognito
        cognito_response = cognito_client.admin_create_user(
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
            MessageAction="SUPPRESS",  # Don't send welcome email
        )

        user_id = cognito_response["User"]["Username"]

        # Set permanent password
        cognito_client.admin_set_user_password(
            UserPoolId=USER_POOL_ID, Username=user_id, Password=password, Permanent=True
        )

        # Create user record in DynamoDB
        current_time = datetime.now(timezone.utc).isoformat()
        user_record = {
            "user_id": user_id,
            "employee_id": employee_id,
            "email": email,
            "name": name,
            "department": department,
            "role": role,
            "is_active": True,
            "created_at": current_time,
            "updated_at": current_time,
        }

        users_table.put_item(Item=user_record)

        logger.info(f"User registered successfully: {email}")

        return create_response(
            201,
            {
                "message": "User registered successfully",
                "user_id": user_id,
                "email": email,
                "role": role,
            },
        )

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code == "UsernameExistsException":
            return create_response(409, {"error": "User already exists"})
        elif error_code == "InvalidPasswordException":
            return create_response(
                400, {"error": "Password does not meet requirements"}
            )
        else:
            logger.error(f"Cognito error: {str(e)}")
            return create_response(500, {"error": "Registration failed"})
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        return create_response(500, {"error": "Registration failed"})


def login_user(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Authenticate user and return JWT tokens.
    """
    request_info = extract_request_info(event)

    try:
        body = json.loads(event.get("body", "{}"))

        email = body.get("email")
        password = body.get("password")

        if not email or not password:
            return create_response(400, {"error": "Email and password are required"})

        # Authenticate with Cognito
        auth_response = cognito_client.admin_initiate_auth(
            UserPoolId=USER_POOL_ID,
            ClientId=CLIENT_ID,
            AuthFlow="ADMIN_NO_SRP_AUTH",
            AuthParameters={"USERNAME": email, "PASSWORD": password},
        )

        # Extract tokens
        tokens = auth_response["AuthenticationResult"]
        access_token = tokens["AccessToken"]
        id_token = tokens["IdToken"]
        refresh_token = tokens["RefreshToken"]

        # Get user details from DynamoDB
        user_id = get_user_id_from_token(access_token)
        user_response = users_table.get_item(Key={"user_id": user_id})
        user_data = user_response.get("Item", {})

        # Log successful login
        security_auditor.log_login_attempt(
            user_id=user_id,
            success=True,
            source_ip=request_info.get("source_ip"),
            user_agent=request_info.get("user_agent"),
        )

        logger.info(f"User logged in successfully: {email}")

        return create_response(
            200,
            {
                "message": "Login successful",
                "tokens": {
                    "access_token": access_token,
                    "id_token": id_token,
                    "refresh_token": refresh_token,
                    "expires_in": tokens["ExpiresIn"],
                },
                "user": {
                    "user_id": user_data.get("user_id"),
                    "email": user_data.get("email"),
                    "name": user_data.get("name"),
                    "role": user_data.get("role"),
                    "department": user_data.get("department"),
                    "permissions": [
                        perm.value
                        for perm in rbac_manager.get_user_permissions(
                            user_data.get("role", "")
                        )
                    ],
                },
            },
        )

    except ClientError as e:
        error_code = e.response["Error"]["Code"]

        # Log failed login attempt
        security_auditor.log_login_attempt(
            user_id=email,  # Use email as identifier for failed attempts
            success=False,
            source_ip=request_info.get("source_ip"),
            user_agent=request_info.get("user_agent"),
            failure_reason=error_code,
        )

        if error_code in ["NotAuthorizedException", "UserNotFoundException"]:
            return create_response(401, {"error": "Invalid credentials"})
        elif error_code == "UserNotConfirmedException":
            return create_response(401, {"error": "User not confirmed"})
        else:
            logger.error(f"Cognito login error: {str(e)}")
            return create_response(500, {"error": "Login failed"})
    except Exception as e:
        # Log failed login attempt
        security_auditor.log_login_attempt(
            user_id=email or "unknown",
            success=False,
            source_ip=request_info.get("source_ip"),
            user_agent=request_info.get("user_agent"),
            failure_reason="system_error",
        )

        logger.error(f"Login error: {str(e)}")
        return create_response(500, {"error": "Login failed"})


def logout_user(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Logout user by invalidating tokens.
    """
    request_info = extract_request_info(event)

    try:
        # Extract access token from Authorization header
        access_token = extract_token_from_header(event)
        if not access_token:
            return create_response(401, {"error": "Access token required"})

        # Get user ID for audit logging
        user_id = get_user_id_from_token(access_token)

        # Global sign out (invalidates all tokens)
        cognito_client.global_sign_out(AccessToken=access_token)

        # Log logout
        if user_id:
            security_auditor.log_logout(
                user_id=user_id, source_ip=request_info.get("source_ip")
            )

        logger.info("User logged out successfully")

        return create_response(200, {"message": "Logout successful"})

    except ClientError as e:
        logger.error(f"Logout error: {str(e)}")
        return create_response(500, {"error": "Logout failed"})
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        return create_response(500, {"error": "Logout failed"})


def refresh_token(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Refresh access token using refresh token.
    """
    try:
        body = json.loads(event.get("body", "{}"))
        refresh_token = body.get("refresh_token")

        if not refresh_token:
            return create_response(400, {"error": "Refresh token required"})

        # Refresh tokens
        auth_response = cognito_client.admin_initiate_auth(
            UserPoolId=USER_POOL_ID,
            ClientId=CLIENT_ID,
            AuthFlow="REFRESH_TOKEN_AUTH",
            AuthParameters={"REFRESH_TOKEN": refresh_token},
        )

        tokens = auth_response["AuthenticationResult"]

        return create_response(
            200,
            {
                "message": "Token refreshed successfully",
                "tokens": {
                    "access_token": tokens["AccessToken"],
                    "id_token": tokens["IdToken"],
                    "expires_in": tokens["ExpiresIn"],
                },
            },
        )

    except ClientError as e:
        logger.error(f"Token refresh error: {str(e)}")
        return create_response(401, {"error": "Invalid refresh token"})
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        return create_response(500, {"error": "Token refresh failed"})


def get_user_profile(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get current user profile information.
    """
    try:
        # Extract user ID from token
        user_id = get_user_id_from_event(event)
        if not user_id:
            return create_response(401, {"error": "Invalid token"})

        # Get user from DynamoDB
        response = users_table.get_item(Key={"user_id": user_id})

        if "Item" not in response:
            return create_response(404, {"error": "User not found"})

        user_data = response["Item"]

        # Remove sensitive information
        user_profile = {
            "user_id": user_data["user_id"],
            "employee_id": user_data["employee_id"],
            "email": user_data["email"],
            "name": user_data["name"],
            "department": user_data["department"],
            "role": user_data["role"],
            "is_active": user_data["is_active"],
            "created_at": user_data["created_at"],
        }

        return create_response(200, {"user": user_profile})

    except Exception as e:
        logger.error(f"Get profile error: {str(e)}")
        return create_response(500, {"error": "Failed to get user profile"})


def update_user_profile(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update user profile information.
    """
    try:
        # Extract user ID from token
        user_id = get_user_id_from_event(event)
        if not user_id:
            return create_response(401, {"error": "Invalid token"})

        body = json.loads(event.get("body", "{}"))

        # Allowed fields to update
        allowed_fields = ["name", "department"]
        update_expression = "SET updated_at = :updated_at"
        expression_values = {":updated_at": datetime.now(timezone.utc).isoformat()}

        for field in allowed_fields:
            if field in body:
                update_expression += f", {field} = :{field}"
                expression_values[f":{field}"] = body[field]

        # Update in DynamoDB
        users_table.update_item(
            Key={"user_id": user_id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_values,
        )

        # Also update Cognito attributes if name is updated
        if "name" in body:
            cognito_client.admin_update_user_attributes(
                UserPoolId=USER_POOL_ID,
                Username=user_id,
                UserAttributes=[{"Name": "name", "Value": body["name"]}],
            )

        return create_response(200, {"message": "Profile updated successfully"})

    except Exception as e:
        logger.error(f"Update profile error: {str(e)}")
        return create_response(500, {"error": "Failed to update profile"})


def verify_token(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verify JWT token and return user information.
    """
    try:
        access_token = extract_token_from_header(event)
        if not access_token:
            return create_response(401, {"error": "Access token required"})

        # Get user info from Cognito
        user_info = cognito_client.get_user(AccessToken=access_token)

        # Extract user attributes
        attributes = {
            attr["Name"]: attr["Value"] for attr in user_info["UserAttributes"]
        }

        return create_response(
            200,
            {
                "valid": True,
                "user": {
                    "user_id": user_info["Username"],
                    "email": attributes.get("email"),
                    "name": attributes.get("name"),
                    "role": attributes.get("custom:role"),
                    "department": attributes.get("custom:department"),
                },
            },
        )

    except ClientError as e:
        logger.error(f"Token verification error: {str(e)}")
        return create_response(401, {"valid": False, "error": "Invalid token"})
    except Exception as e:
        logger.error(f"Token verification error: {str(e)}")
        return create_response(500, {"error": "Token verification failed"})


def extract_token_from_header(event: Dict[str, Any]) -> Optional[str]:
    """
    Extract JWT token from Authorization header.
    """
    headers = event.get("headers", {})
    auth_header = headers.get("Authorization") or headers.get("authorization")

    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:]  # Remove 'Bearer ' prefix

    return None


def get_user_id_from_token(access_token: str) -> Optional[str]:
    """
    Extract user ID from JWT access token without verification.
    Note: This is for internal use only, token should be verified by API Gateway.
    """
    try:
        # Decode without verification (API Gateway already verified it)
        decoded = jwt.decode(access_token, options={"verify_signature": False})
        return decoded.get("username")
    except Exception:
        return None


def get_user_id_from_event(event: Dict[str, Any]) -> Optional[str]:
    """
    Extract user ID from event (either from token or request context).
    """
    # Try to get from request context (set by API Gateway authorizer)
    request_context = event.get("requestContext", {})
    authorizer = request_context.get("authorizer", {})

    if "claims" in authorizer:
        return authorizer["claims"].get("username")

    # Fallback: extract from token
    access_token = extract_token_from_header(event)
    if access_token:
        return get_user_id_from_token(access_token)

    return None


def create_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create standardized HTTP response with security headers.
    """
    origin = None  # Will be handled by security middleware
    return create_secure_response(status_code, body, origin=origin)
