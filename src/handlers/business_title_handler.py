"""
双日テックイノベーション：AI人材発掘・配置マッチングMVP（AI CoE支援）
ビジネスタイトルハンドラー - AIスキルポートフォリオ向けビジネスタイトル生成

社内AI人材候補のAIスキルポートフォリオに基づいたビジネスタイトルの
AI生成・選択・再生成を担当します。
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict

from src.repositories.user_repository import UserRepository
from src.repositories.veteran_profile_repository import VeteranProfileRepository
from src.services.ai_utils import get_ai_service
from src.utils.auth_utils import extract_user_from_event
from src.utils.error_handling import (
    ErrorType,
    create_error_response,
    create_success_response,
    handle_exception,
    parse_json_body,
)
from src.utils.branding_logger import get_branding_logger
from src.config.ai_content_config import ai_content_config

logger = logging.getLogger(__name__)

# ブランディングロガーを初期化（双日TI向けAIスキルポートフォリオ・ビジネスタイトル生成）
branding_logger = get_branding_logger('business_title_handler')


def convert_decimals(obj):
    """Convert Decimal objects to float for JSON serialization."""
    if isinstance(obj, list):
        return [convert_decimals(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_decimals(value) for key, value in obj.items()}
    elif isinstance(obj, Decimal):
        return float(obj)
    return obj


class BusinessTitleHandler:
    """社内AI人材候補のAIスキルポートフォリオ向けビジネスタイトル生成操作を担当するハンドラー"""

    def __init__(self):
        self.ai_service = get_ai_service()
        self.profile_repo = VeteranProfileRepository()
        self.user_repo = UserRepository()

    def generate_business_titles(
        self, event: Dict[str, Any], context: Any
    ) -> Dict[str, Any]:
        """
        社内AI人材候補向けAIスキルポートフォリオに基づいたビジネスタイトルを生成します（同期ラッパー）。

        Args:
            event: ユーザー情報を含むLambdaイベント
            context: Lambdaコンテキスト

        Returns:
            生成されたビジネスタイトルを含むAPIゲートウェイレスポンス
        """
        return asyncio.run(self._generate_business_titles_async(event, context))

    def select_business_title(
        self, event: Dict[str, Any], context: Any
    ) -> Dict[str, Any]:
        """
        AIスキルポートフォリオのビジネスタイトルを選択してプロフィールに適用します（同期ラッパー）。

        Args:
            event: 選択されたタイトルを含むLambdaイベント
            context: Lambdaコンテキスト

        Returns:
            確認を含むAPIゲートウェイレスポンス
        """
        return asyncio.run(self._select_business_title_async(event, context))

    def regenerate_business_titles(
        self, event: Dict[str, Any], context: Any
    ) -> Dict[str, Any]:
        """
        更新されたコンテキストでAIスキルポートフォリオのビジネスタイトルを再生成します（同期ラッパー）。

        Args:
            event: Lambdaイベント
            context: Lambdaコンテキスト

        Returns:
            再生成されたタイトルを含むAPIゲートウェイレスポンス
        """
        return asyncio.run(self._regenerate_business_titles_async(event, context))

    def get_title_history(
        self, event: Dict[str, Any], context: Any
    ) -> Dict[str, Any]:
        """
        AIスキルポートフォリオのビジネスタイトル生成・選択履歴を取得します（同期ラッパー）。

        Args:
            event: Lambdaイベント
            context: Lambdaコンテキスト

        Returns:
            タイトル履歴を含むAPIゲートウェイレスポンス
        """
        return asyncio.run(self._get_title_history_async(event, context))

    async def _generate_business_titles_async(
        self, event: Dict[str, Any], context: Any
    ) -> Dict[str, Any]:
        """
        社内AI人材候補向けAIスキルポートフォリオに基づいたビジネスタイトルを生成します（非同期実装）。

        Args:
            event: ユーザー情報を含むLambdaイベント
            context: Lambdaコンテキスト

        Returns:
            生成されたビジネスタイトルを含むAPIゲートウェイレスポンス
        """
        try:
            # Extract and verify user from event (API Gateway authorizer)
            user_info = extract_user_from_event(event)
            if not user_info:
                return create_error_response(ErrorType.INVALID_AUTH)

            user_id = user_info["user_id"]
            user_name = user_info.get("name", "User")
            user_department = user_info.get("department", "")

            # Check if user has veteran role
            user_role = user_info.get("role", "")
            if user_role != "veteran":
                logger.warning(f"User {user_id} with role '{user_role}' attempted to access veteran-only feature")
                return create_error_response(
                    ErrorType.ACCESS_DENIED,
                    message="Access denied. Veteran role required."
                )

            # Get user profile
            profile = self.profile_repo.get_profile(user_id)
            if not profile:
                return create_error_response(
                    ErrorType.PROFILE_NOT_FOUND,
                    message="Profile not found. Please complete your profile first."
                )

            # Extract career interests from preferences
            career_interests = []
            if profile.preferences:
                career_interests = profile.preferences.get("preferred_roles", [])
                if "career_interests" in profile.preferences:
                    career_interests.extend(profile.preferences["career_interests"])

            # Generate business titles using AI with branding context
            branding_context = ai_content_config.get_business_title_context()
            
            titles_data = await self.ai_service.generate_business_titles(
                name=user_name,
                department=user_department,
                skills=profile.skills or [],
                experience=profile.experiences or [],
                career_interests=career_interests,
                current_role=profile.business_title or "社内AI人材候補",
                branding_context=branding_context,
                platform_name=ai_content_config.get_brand_context('platform_name')
            )

            # Store generation history in profile
            self._store_title_generation_history(user_id, titles_data)

            logger.info(f"Generated business titles for user {user_id}")
            branding_logger.log_ai_generation('business_title', user_id)

            return create_success_response(
                {
                    "titles": titles_data.get("titles", []),
                    "recommended_title": titles_data.get("recommended_title"),
                    "reasoning": titles_data.get("reasoning"),
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                }
            )

        except Exception as e:
            return handle_exception(e, "generating business titles", user_id)

    async def _select_business_title_async(
        self, event: Dict[str, Any], context: Any
    ) -> Dict[str, Any]:
        """
        AIスキルポートフォリオのビジネスタイトルを選択してプロフィールに適用します（非同期実装）。

        Args:
            event: 選択されたタイトルを含むLambdaイベント
            context: Lambdaコンテキスト

        Returns:
            確認を含むAPIゲートウェイレスポンス
        """
        try:
            # Extract and verify user from event (API Gateway authorizer)
            user_info = extract_user_from_event(event)
            if not user_info:
                return create_error_response(ErrorType.INVALID_AUTH)

            user_id = user_info["user_id"]

            # Parse request body
            body, error_response = parse_json_body(event)
            if error_response:
                return error_response

            selected_title = body.get("title")
            if not selected_title:
                return create_error_response(
                    ErrorType.MISSING_FIELD,
                    message="Missing title in request body"
                )

            # Get current profile
            profile = self.profile_repo.get_profile(user_id)
            if not profile:
                return create_error_response(ErrorType.PROFILE_NOT_FOUND)

            # Update profile with selected title
            update_data = {
                "business_title": selected_title,
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }

            # Store selection history
            title_history = profile.title_history.copy() if profile.title_history else []
            title_history.append(
                {
                    "title": selected_title,
                    "selected_at": datetime.now(timezone.utc).isoformat(),
                    "previous_title": profile.business_title,
                }
            )
            update_data["title_history"] = title_history

            self.profile_repo.update_profile(user_id, update_data)

            logger.info(
                f"Updated business title for user {user_id} to: {selected_title}"
            )

            return create_success_response(
                {
                    "title": selected_title,
                    "updated_at": update_data["last_updated"],
                },
                message="Business title updated successfully"
            )

        except Exception as e:
            return handle_exception(e, "selecting business title", user_id)

    async def _regenerate_business_titles_async(
        self, event: Dict[str, Any], context: Any
    ) -> Dict[str, Any]:
        """
        更新されたコンテキストでAIスキルポートフォリオのビジネスタイトルを再生成します（非同期実装）。

        Args:
            event: Lambdaイベント
            context: Lambdaコンテキスト

        Returns:
            再生成されたタイトルを含むAPIゲートウェイレスポンス
        """
        try:
            # Extract and verify user from event (API Gateway authorizer)
            user_info = extract_user_from_event(event)
            if not user_info:
                return {
                    "statusCode": 401,
                    "body": json.dumps({"error": "Invalid authorization token"}),
                }

            user_id = user_info["user_id"]
            user_name = user_info.get("name", "User")
            user_department = user_info.get("department", "")

            # Get profile
            profile = self.profile_repo.get_profile(user_id)

            if not profile:
                return {
                    "statusCode": 404,
                    "body": json.dumps({"error": "Profile not found"}),
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

            # Generate new business titles with branding context
            branding_context = ai_content_config.get_business_title_context()
            
            titles_data = await self.ai_service.generate_business_titles(
                name=user_name,
                department=user_department,
                skills=profile.skills or [],
                experience=profile.experiences or [],
                career_interests=career_interests,
                current_role=profile.business_title or "社内AI人材候補",
                branding_context=branding_context,
                platform_name=ai_content_config.get_brand_context('platform_name')
            )

            # Store regeneration history
            self._store_title_generation_history(
                user_id, titles_data, regenerated=True
            )

            logger.info(f"Regenerated business titles for user {user_id}")
            branding_logger.log_ai_generation('business_title_regeneration', user_id)

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

    async def _get_title_history_async(
        self, event: Dict[str, Any], context: Any
    ) -> Dict[str, Any]:
        """
        AIスキルポートフォリオのビジネスタイトル生成・選択履歴を取得します（非同期実装）。

        Args:
            event: Lambdaイベント
            context: Lambdaコンテキスト

        Returns:
            タイトル履歴を含むAPIゲートウェイレスポンス
        """
        try:
            # Extract and verify user from event (API Gateway authorizer)
            user_info = extract_user_from_event(event)
            if not user_info:
                return {
                    "statusCode": 401,
                    "body": json.dumps({"error": "Invalid authorization token"}),
                }

            user_id = user_info["user_id"]

            # Get profile
            profile = self.profile_repo.get_profile(user_id)
            if not profile:
                return {
                    "statusCode": 404,
                    "body": json.dumps({"error": "Profile not found"}),
                }

            # Get title history
            title_history = profile.title_history if profile.title_history else []
            generation_history = profile.title_generation_history if profile.title_generation_history else []

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

    def _store_title_generation_history(
        self, user_id: str, titles_data: Dict[str, Any], regenerated: bool = False
    ) -> None:
        """
        AIスキルポートフォリオのタイトル生成履歴をユーザープロフィールに保存します。

        Args:
            user_id: ユーザーID
            titles_data: 生成されたタイトルデータ
            regenerated: 再生成かどうか
        """
        try:
            profile = self.profile_repo.get_profile(user_id)
            if not profile:
                return

            # Get existing history and convert any Decimals
            existing_history = profile.title_generation_history if profile.title_generation_history else []
            generation_history = convert_decimals(existing_history.copy() if isinstance(existing_history, list) else [])

            # Add new generation record (convert Decimals in titles_data)
            generation_record = {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "titles": convert_decimals(titles_data.get("titles", [])),
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
            self.profile_repo.update_profile(
                user_id, {"title_generation_history": generation_history}
            )

        except Exception as e:
            logger.error(f"Error storing title generation history: {str(e)}")


# Lambda function handlers
business_title_handler = BusinessTitleHandler()


def generate_business_titles(
    event: Dict[str, Any], context: Any
) -> Dict[str, Any]:
    """AIスキルポートフォリオ向けビジネスタイトル生成のLambdaハンドラー"""
    return business_title_handler.generate_business_titles(event, context)


def select_business_title(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """AIスキルポートフォリオのビジネスタイトル選択のLambdaハンドラー"""
    return business_title_handler.select_business_title(event, context)


def regenerate_business_titles(
    event: Dict[str, Any], context: Any
) -> Dict[str, Any]:
    """AIスキルポートフォリオのビジネスタイトル再生成のLambdaハンドラー"""
    return business_title_handler.regenerate_business_titles(event, context)


def get_title_history(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """AIスキルポートフォリオのタイトル履歴取得のLambdaハンドラー"""
    return business_title_handler.get_title_history(event, context)
