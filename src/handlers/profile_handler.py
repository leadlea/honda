"""
Profile handler with RBAC integration and full CRUD operations.
Implements profile management with data validation and privacy controls.
"""

import json
import logging
from typing import Any, Dict

# Import data models and repositories
from src.models.veteran_profile import VeteranProfile
from src.repositories.user_repository import UserRepository
from src.repositories.veteran_profile_repository import VeteranProfileRepository
from src.services.privacy_manager import privacy_manager
from src.utils.auth_utils import extract_user_from_event

# Import RBAC and security audit modules
from src.utils.rbac import (
    AccessContext,
    Permission,
    check_resource_access,
    rbac_manager,
    require_permission,
    require_role,
)
from src.utils.security_audit import extract_request_info, security_auditor

logger = logging.getLogger()


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for profile operations.
    Routes requests based on HTTP method and path.
    """
    try:
        http_method = event.get("httpMethod")
        path = event.get("path", "")
        path_parameters = event.get("pathParameters") or {}

        # Extract the action from the path
        path_parts = path.strip("/").split("/")
        if len(path_parts) >= 2:
            action = path_parts[1]  # profiles/{action}
        else:
            action = (
                path_parameters.get("proxy", "").split("/")[0]
                if path_parameters.get("proxy")
                else ""
            )

        logger.info(f"Processing {http_method} request for action: {action}, path: {path}")

        # Add user information to event for RBAC
        user = extract_user_from_event(event)
        logger.info(f"Extracted user: {user}")
        
        if not user:
            logger.error("No user information found in event")
            logger.error(f"Request context: {event.get('requestContext', {})}")
            return create_response(401, {"error": "Authentication required"})
            
        event["user"] = user

        # Route to appropriate handler
        if http_method == "GET":
            if action == "privacy":
                return get_privacy_status(event)
            elif action and action != "profiles":
                return get_profile(event, context)
            else:
                return list_profiles(event)
        elif http_method == "POST":
            if action == "business-title":
                return generate_business_title(event)
            elif action == "privacy":
                return update_privacy_settings(event)
            else:
                return create_profile(event, context)
        elif http_method == "PUT":
            return update_profile(event, context)
        elif http_method == "DELETE":
            return delete_profile(event)

        return create_response(400, {"error": "Invalid action or method"})

    except Exception as e:
        logger.error(f"Error in profile handler: {str(e)}")
        return create_response(500, {"error": "Internal server error"})


def create_profile(event: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    """
    Create a new veteran profile.
    """
    try:
        user = event.get("user", {})
        user_id = user.get("user_id")

        if not user_id:
            return create_response(401, {"error": "Authentication required"})

        body = json.loads(event.get("body", "{}"))

        # Initialize repository
        profile_repo = VeteranProfileRepository()

        # Check if profile already exists
        if profile_repo.profile_exists(user_id):
            return create_response(
                409, {"error": "Profile already exists for this user"}
            )

        # Create new profile with provided data
        profile = VeteranProfile(
            user_id=user_id,
            business_title=body.get("business_title", ""),
            skills=body.get("skills", []),
            experiences=body.get("experiences", []),
            preferences=body.get("preferences", {}),
            privacy_settings=body.get(
                "privacy_settings",
                {"is_publicly_visible": False, "external_contact": False},
            ),
        )

        # Validate profile data
        validation_errors = profile.validate()
        if validation_errors:
            return create_response(
                400,
                {"error": "Profile validation failed", "details": validation_errors},
            )

        # Create profile in database
        success = profile_repo.create_profile(profile)

        if success:
            # Log profile creation
            request_info = extract_request_info(event)
            security_auditor.log_profile_access(
                user_id=user_id,
                accessed_profile_id=user_id,
                action="create",
                success=True,
                source_ip=request_info.get("source_ip"),
            )

            return create_response(
                201,
                {
                    "message": "Profile created successfully",
                    "profile": {
                        "user_id": profile.user_id,
                        "business_title": profile.business_title,
                        "skills": profile.skills,
                        "experiences": profile.experiences,
                        "preferences": profile.preferences,
                        "privacy_settings": profile.privacy_settings,
                        "created_at": profile.created_at,
                    },
                },
            )
        else:
            return create_response(500, {"error": "Failed to create profile"})

    except json.JSONDecodeError:
        return create_response(400, {"error": "Invalid JSON in request body"})
    except ValueError as e:
        return create_response(400, {"error": str(e)})
    except Exception as e:
        logger.error(f"Error creating profile: {str(e)}")
        return create_response(500, {"error": "Failed to create profile"})


@require_permission(Permission.VIEW_OWN_PROFILE, resource_owner_field="profile_user_id")
def get_profile(event: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    """
    Get user profile with RBAC protection.
    """
    try:
        user = event.get("user", {})
        user_id = user.get("user_id")
        user_role = user.get("role")

        # Extract profile user ID from path
        path_parts = event.get("path", "").strip("/").split("/")
        profile_user_id = path_parts[1] if len(path_parts) > 1 else user_id

        # Add profile_user_id to event for RBAC decorator
        event["profile_user_id"] = profile_user_id

        # Check if user can access this profile
        if not check_resource_access(
            user_role=user_role,
            user_id=user_id,
            resource_type="profile",
            resource_owner_id=profile_user_id,
            action="view",
        ):
            # Log access attempt
            request_info = extract_request_info(event)
            security_auditor.log_profile_access(
                user_id=user_id,
                accessed_profile_id=profile_user_id,
                action="view",
                success=False,
                source_ip=request_info.get("source_ip"),
            )

            return create_response(403, {"error": "Access denied"})

        # Initialize repository
        profile_repo = VeteranProfileRepository()

        # Get profile from database
        profile = profile_repo.get_profile(profile_user_id)

        if not profile:
            return create_response(404, {"error": "Profile not found"})

        # Log successful access
        request_info = extract_request_info(event)
        security_auditor.log_profile_access(
            user_id=user_id,
            accessed_profile_id=profile_user_id,
            action="view",
            success=True,
            source_ip=request_info.get("source_ip"),
        )

        # Return profile data
        profile_data = {
            "user_id": profile.user_id,
            "business_title": profile.business_title,
            "skills": profile.skills,
            "experiences": profile.experiences,
            "preferences": profile.preferences,
            "privacy_settings": profile.privacy_settings,
            "last_updated": profile.last_updated,
            "created_at": profile.created_at,
        }

        return create_response(200, {"profile": profile_data})

    except Exception as e:
        logger.error(f"Error getting profile: {str(e)}")
        return create_response(500, {"error": "Failed to get profile"})


@require_permission(Permission.EDIT_OWN_PROFILE, resource_owner_field="profile_user_id")
def update_profile(event: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    """
    Update user profile with RBAC protection and data validation.
    """
    try:
        user = event.get("user", {})
        user_id = user.get("user_id")

        # Extract profile user ID from path
        path_parts = event.get("path", "").strip("/").split("/")
        profile_user_id = path_parts[1] if len(path_parts) > 1 else user_id

        # Add profile_user_id to event for RBAC decorator
        event["profile_user_id"] = profile_user_id

        body = json.loads(event.get("body", "{}"))
        
        logger.info(f"Update profile request body: {body}")
        logger.info(f"Body type: {type(body)}, Body keys: {body.keys() if isinstance(body, dict) else 'NOT A DICT'}")

        # Initialize repository
        profile_repo = VeteranProfileRepository()

        # Get existing profile
        existing_profile = profile_repo.get_profile(profile_user_id)
        if not existing_profile:
            return create_response(404, {"error": "Profile not found"})

        # Validate update data - only allow specific fields
        allowed_fields = ["business_title", "skills", "experiences", "preferences"]
        
        # Parse any JSON string fields in the body
        parsed_body = {}
        for key, value in body.items():
            if key in allowed_fields:
                # If value is a JSON string, parse it
                if isinstance(value, str) and key in ["skills", "experiences", "preferences", "privacy_settings"]:
                    try:
                        parsed_body[key] = json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        parsed_body[key] = value
                else:
                    parsed_body[key] = value
        
        update_data = parsed_body
        logger.info(f"Parsed update_data: {update_data}")

        if not update_data:
            return create_response(400, {"error": "No valid fields to update"})

        # Build update_data dictionary from profile fields
        # Note: update_data already contains only allowed fields from earlier filtering
        # We can pass it directly to the repository
        
        # Update profile in database with correct parameters
        success = profile_repo.update_profile(profile_user_id, update_data)

        if success:
            # Get updated profile to return in response
            updated_profile = profile_repo.get_profile(profile_user_id)
            
            # Log profile update
            request_info = extract_request_info(event)
            security_auditor.log_profile_access(
                user_id=user_id,
                accessed_profile_id=profile_user_id,
                action="update",
                success=True,
                source_ip=request_info.get("source_ip"),
            )

            return create_response(
                200,
                {
                    "message": "Profile updated successfully",
                    "updated_fields": list(update_data.keys()),
                    "profile": {
                        "user_id": updated_profile.user_id,
                        "business_title": updated_profile.business_title,
                        "skills": updated_profile.skills,
                        "experiences": updated_profile.experiences,
                        "preferences": updated_profile.preferences,
                        "privacy_settings": updated_profile.privacy_settings,
                        "last_updated": updated_profile.last_updated,
                    },
                },
            )
        else:
            return create_response(500, {"error": "Failed to update profile"})

    except json.JSONDecodeError:
        return create_response(400, {"error": "Invalid JSON in request body"})
    except ValueError as e:
        return create_response(400, {"error": str(e)})
    except Exception as e:
        logger.error(f"Error updating profile: {str(e)}")
        return create_response(500, {"error": "Failed to update profile"})


@require_role("admin")
def delete_profile(event: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    """
    Delete user profile (admin only).
    """
    try:
        user = event.get("user", {})
        admin_user_id = user.get("user_id")

        # Extract profile user ID from path
        path_parts = event.get("path", "").strip("/").split("/")
        profile_user_id = path_parts[1] if len(path_parts) > 1 else None

        if not profile_user_id:
            return create_response(400, {"error": "Profile user ID required"})

        # Initialize repository
        profile_repo = VeteranProfileRepository()

        # Check if profile exists
        if not profile_repo.profile_exists(profile_user_id):
            return create_response(404, {"error": "Profile not found"})

        # Delete profile from database
        success = profile_repo.delete_profile(profile_user_id)

        if success:
            # Log admin action
            request_info = extract_request_info(event)
            security_auditor.log_admin_action(
                admin_user_id=admin_user_id,
                action="delete_profile",
                target_resource=f"profile:{profile_user_id}",
                source_ip=request_info.get("source_ip"),
            )

            return create_response(200, {"message": "Profile deleted successfully"})
        else:
            return create_response(500, {"error": "Failed to delete profile"})

    except Exception as e:
        logger.error(f"Error deleting profile: {str(e)}")
        return create_response(500, {"error": "Failed to delete profile"})


def list_profiles(event: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    """
    List profiles with role-based filtering and search capabilities.
    """
    try:
        user = event.get("user", {})
        user_role = user.get("role")
        user_id = user.get("user_id")

        if not user:
            return create_response(401, {"error": "Authentication required"})

        # Check permissions based on role
        access_context = AccessContext(user_id=user_id, role=user_role)

        if user_role == "admin":
            if not rbac_manager.has_permission(
                user_role, Permission.VIEW_ANY_PROFILE, access_context
            ):
                return create_response(403, {"error": "Insufficient permissions"})
        elif user_role == "external_recruiter":
            if not rbac_manager.has_permission(
                user_role, Permission.VIEW_PUBLIC_PROFILES, access_context
            ):
                return create_response(403, {"error": "Insufficient permissions"})
        else:
            return create_response(403, {"error": "Insufficient permissions"})

        # Get query parameters
        query_params = event.get("queryStringParameters") or {}
        skills_filter = (
            query_params.get("skills", "").split(",")
            if query_params.get("skills")
            else []
        )
        department_filter = query_params.get("department")
        limit = int(query_params.get("limit", 50))

        # Initialize repository
        profile_repo = VeteranProfileRepository()
        user_repo = UserRepository()

        profiles = []

        if user_role == "admin":
            # Admins can see all profiles
            if skills_filter:
                profiles = profile_repo.search_profiles_by_skills(skills_filter, limit)
            elif department_filter:
                profiles = profile_repo.get_profiles_by_department(
                    department_filter, limit
                )
            else:
                # Get all profiles (scan operation - use with caution in production)
                items = profile_repo.scan(limit=limit)
                profiles = [VeteranProfile.from_dynamodb_item(item) for item in items]

        elif user_role == "external_recruiter":
            # External recruiters can only see public profiles
            profiles = profile_repo.get_public_profiles(limit)

            # Apply skills filter if provided
            if skills_filter:
                filtered_profiles = []
                for profile in profiles:
                    profile_skills = [
                        skill.get("name", "").lower() for skill in profile.skills
                    ]
                    if any(skill.lower() in profile_skills for skill in skills_filter):
                        filtered_profiles.append(profile)
                profiles = filtered_profiles

        # Format response data
        profile_list = []
        for profile in profiles:
            # Get user data for additional context
            user_data = user_repo.get_user_by_id(profile.user_id)

            profile_data = {
                "user_id": profile.user_id,
                "business_title": profile.business_title,
                "skills": profile.skills,
                "experiences": profile.experiences,
                "is_publicly_visible": profile.is_publicly_visible == "true",
                "last_updated": profile.last_updated,
            }

            # Add user context if available
            if user_data:
                profile_data.update(
                    {"name": user_data.name, "department": user_data.department}
                )

            # Filter sensitive data for external recruiters
            if user_role == "external_recruiter":
                # Only include public information
                profile_data = {
                    "user_id": profile.user_id,
                    "business_title": profile.business_title,
                    "skills": profile.skills,
                    "experiences": profile.experiences,
                }

            profile_list.append(profile_data)

        return create_response(
            200,
            {
                "profiles": profile_list,
                "count": len(profile_list),
                "filters_applied": {
                    "skills": skills_filter,
                    "department": department_filter,
                    "limit": limit,
                },
            },
        )

    except Exception as e:
        logger.error(f"Error listing profiles: {str(e)}")
        return create_response(500, {"error": "Failed to list profiles"})


@require_permission(Permission.EDIT_OWN_PROFILE, resource_owner_field="profile_user_id")
def generate_business_title(
    event: Dict[str, Any], context: Any = None
) -> Dict[str, Any]:
    """
    Generate AI business title for user profile.
    """
    try:
        user = event.get("user", {})
        user_id = user.get("user_id")

        # Extract profile user ID from path
        path_parts = event.get("path", "").strip("/").split("/")
        profile_user_id = path_parts[1] if len(path_parts) > 1 else user_id

        # Add profile_user_id to event for RBAC decorator
        event["profile_user_id"] = profile_user_id

        # Mock AI title generation (in real implementation, this would use Bedrock)
        generated_titles = [
            "Senior Full-Stack Engineer & Cloud Architecture Specialist",
            "Expert Software Developer with AWS & Python Expertise",
            "Lead Engineer - Scalable Systems & DevOps Innovation",
        ]

        return create_response(
            200,
            {
                "message": "Business titles generated successfully",
                "suggested_titles": generated_titles,
            },
        )

    except Exception as e:
        logger.error(f"Error generating business title: {str(e)}")
        return create_response(500, {"error": "Failed to generate business title"})


@require_permission(Permission.VIEW_OWN_PROFILE, resource_owner_field="profile_user_id")
def get_privacy_status(event: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    """
    Get current privacy status and external visibility information.
    """
    try:
        user = event.get("user", {})
        user_id = user.get("user_id")

        # Extract profile user ID from path
        path_parts = event.get("path", "").strip("/").split("/")
        profile_user_id = path_parts[1] if len(path_parts) > 1 else user_id

        # Add profile_user_id to event for RBAC decorator
        event["profile_user_id"] = profile_user_id

        # Get privacy status using privacy manager
        status_result = privacy_manager.get_privacy_status(profile_user_id)

        if status_result["success"]:
            return create_response(200, {"privacy_status": status_result})
        else:
            return create_response(
                404, {"error": status_result.get("error", "Privacy status not found")}
            )

    except Exception as e:
        logger.error(f"Error getting privacy status: {str(e)}")
        return create_response(500, {"error": "Failed to get privacy status"})


@require_permission(Permission.EDIT_OWN_PROFILE, resource_owner_field="profile_user_id")
def update_privacy_settings(
    event: Dict[str, Any], context: Any = None
) -> Dict[str, Any]:
    """
    Update profile privacy settings with real-time synchronization.
    """
    try:
        user = event.get("user", {})
        user_id = user.get("user_id")

        # Extract profile user ID from path
        path_parts = event.get("path", "").strip("/").split("/")
        profile_user_id = path_parts[1] if len(path_parts) > 1 else user_id

        # Add profile_user_id to event for RBAC decorator
        event["profile_user_id"] = profile_user_id

        body = json.loads(event.get("body", "{}"))

        # Validate privacy settings
        allowed_settings = ["is_publicly_visible", "external_contact"]
        privacy_settings = {k: v for k, v in body.items() if k in allowed_settings}

        if not privacy_settings:
            return create_response(400, {"error": "No valid privacy settings provided"})

        # Validate privacy settings
        validation_result = privacy_manager.validate_privacy_settings(privacy_settings)
        if not validation_result["valid"]:
            return create_response(
                400,
                {
                    "error": "Privacy settings validation failed",
                    "details": validation_result["errors"],
                },
            )

        # Update privacy settings using privacy manager
        update_result = privacy_manager.update_privacy_settings(
            profile_user_id, privacy_settings
        )

        if update_result["success"]:
            # Log privacy settings change
            request_info = extract_request_info(event)
            security_auditor.log_profile_access(
                user_id=user_id,
                accessed_profile_id=profile_user_id,
                action="privacy_update",
                success=True,
                source_ip=request_info.get("source_ip"),
            )

            return create_response(
                200,
                {
                    "message": "Privacy settings updated successfully",
                    "updated_settings": update_result["updated_settings"],
                    "sync_result": update_result["sync_result"],
                    "profile_updated_at": update_result["profile_updated_at"],
                    "warnings": validation_result.get("warnings", []),
                },
            )
        else:
            return create_response(
                500,
                {
                    "error": "Failed to update privacy settings",
                    "details": update_result.get("error", "Unknown error"),
                },
            )

    except json.JSONDecodeError:
        return create_response(400, {"error": "Invalid JSON in request body"})
    except ValueError as e:
        return create_response(400, {"error": str(e)})
    except Exception as e:
        logger.error(f"Error updating privacy settings: {str(e)}")
        return create_response(500, {"error": "Failed to update privacy settings"})


def create_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create standardized HTTP response.
    """
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
        },
        "body": json.dumps(body),
    }
