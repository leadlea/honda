"""
双日テックイノベーション：AI人材発掘・配置マッチングMVP（AI CoE支援）
社内AI人材候補検索ハンドラー

AIポジションオーナー（各部門／AI CoE）向けに社内AI人材候補プロフィールへの
外部アクセスを提供します。フィルタリングとAIランキングをサポートします。
"""

import json
import logging
from typing import Any, Dict, List

from src.config.message_config import message_config
from src.repositories.public_profile_repository import PublicProfileRepository
from src.repositories.veteran_profile_repository import VeteranProfileRepository
from src.services.ai_utils import get_ai_service
from src.services.bedrock_client import BedrockClient
from src.utils.branding_logger import get_branding_logger

# Public API - no authentication required for external access

logger = logging.getLogger(__name__)

# ブランディングロガーを初期化（双日TI向け社内AI人材候補検索）
branding_logger = get_branding_logger('public_search_handler')


class PublicSearchHandler:
    def __init__(self):
        self.public_profile_repo = PublicProfileRepository()
        self.veteran_profile_repo = VeteranProfileRepository()
        self.bedrock_client = BedrockClient()
        self.ai_service = get_ai_service()

    def search_veterans(self, event: Dict, context: Any) -> Dict:
        """
        社内AI人材候補プロフィールの検索外部API。
        スキル・経験・空き状況によるフィルタリングをサポートします。
        AIポジションオーナー（各部門／AI CoE）向け社内AI人材候補検索機能。
        """
        try:
            # Parse query parameters
            query_params = event.get("queryStringParameters") or {}

            # Extract search filters
            filters = self._extract_search_filters(query_params)

            # Get public veteran profiles
            profiles = self.public_profile_repo.search_public_profiles(filters)

            if not profiles:
                return {
                    "statusCode": 200,
                    "headers": self._get_cors_headers(),
                    "body": json.dumps(
                        {
                            "talents": [],
                            "total_count": 0,
                            "message": "検索条件に一致する社内AI人材候補が見つかりませんでした",
                        }
                    ),
                }

            # Apply AI ranking if search query provided
            search_query = query_params.get("q", "")
            if search_query:
                ranked_profiles = self._rank_profiles_with_ai(profiles, search_query)
                branding_logger.log_search_performed(search_query)
            else:
                ranked_profiles = profiles
                branding_logger.log_search_performed("フィルターのみ検索")

            # Apply pagination
            page = int(query_params.get("page", 1))
            limit = min(
                int(query_params.get("limit", 20)), 50
            )  # Max 50 results per page

            paginated_profiles = self._paginate_results(ranked_profiles, page, limit)

            # Format response
            formatted_profiles = [
                self._format_public_profile(profile) for profile in paginated_profiles
            ]

            return {
                "statusCode": 200,
                "headers": self._get_cors_headers(),
                "body": json.dumps(
                    {
                        "talents": formatted_profiles,
                        "total_count": len(ranked_profiles),
                        "page": page,
                        "limit": limit,
                        "has_more": len(ranked_profiles) > page * limit,
                    }
                ),
            }

        except Exception as e:
            logger.error(f"Error in search_veterans: {str(e)}")
            return {
                "statusCode": 500,
                "headers": self._get_cors_headers(),
                "body": json.dumps(
                    {
                        "error": message_config.get_error_message('internal_error'),
                        "message": message_config.get_error_message('search_failed'),
                    }
                ),
            }

    def get_veteran_profile(self, event: Dict, context: Any) -> Dict:
        """
        特定の社内AI人材候補の公開プロフィールを取得します。
        AIポジションオーナーが候補者の詳細を確認するために使用します。
        """
        try:
            profile_id = event["pathParameters"]["profileId"]

            # Get public profile
            profile = self.public_profile_repo.get_public_profile(profile_id)

            if not profile:
                return {
                    "statusCode": 404,
                    "headers": self._get_cors_headers(),
                    "body": json.dumps(
                        {
                            "error": "プロフィールが見つかりません",
                            "message": "要求された社内AI人材候補のプロフィールは利用できません",
                        }
                    ),
                }

            # Increment profile view count
            # Note: profile_id in public profiles corresponds to user_id in veteran profiles
            user_id = profile.get("user_id") or profile_id
            self._increment_profile_views(user_id)

            # Format detailed profile
            formatted_profile = self._format_detailed_profile(profile)

            return {
                "statusCode": 200,
                "headers": self._get_cors_headers(),
                "body": json.dumps({"talent": formatted_profile}),
            }

        except Exception as e:
            logger.error(f"Error in get_veteran_profile: {str(e)}")
            return {
                "statusCode": 500,
                "headers": self._get_cors_headers(),
                "body": json.dumps(
                    {
                        "error": message_config.get_error_message('internal_error'),
                        "message": "社内AI人材候補プロフィールの取得に失敗しました",
                    }
                ),
            }

    def get_search_categories(self, event: Dict, context: Any) -> Dict:
        """
        フィルタリング用の利用可能なカテゴリを取得します（スキル・部門等）。
        社内AI人材候補検索の絞り込みに使用します。
        """
        try:
            categories = self.public_profile_repo.get_available_categories()

            return {
                "statusCode": 200,
                "headers": self._get_cors_headers(),
                "body": json.dumps({"categories": categories}),
            }

        except Exception as e:
            logger.error(f"Error in get_search_categories: {str(e)}")
            return {
                "statusCode": 500,
                "headers": self._get_cors_headers(),
                "body": json.dumps(
                    {
                        "error": message_config.get_error_message('internal_error'),
                        "message": "カテゴリの取得に失敗しました",
                    }
                ),
            }

    def _extract_search_filters(self, query_params: Dict) -> Dict:
        """社内AI人材候補検索のクエリパラメータからフィルターを抽出・バリデーションします"""
        filters = {}

        # Skills filter
        if "skills" in query_params:
            skills = query_params["skills"].split(",")
            filters["skills"] = [skill.strip() for skill in skills if skill.strip()]

        # Experience level filter
        if "experience_level" in query_params:
            filters["experience_level"] = query_params["experience_level"]

        # Department filter
        if "department" in query_params:
            filters["department"] = query_params["department"]

        # Location filter
        if "location" in query_params:
            filters["location"] = query_params["location"]

        # Availability filter
        if "availability" in query_params:
            filters["availability"] = query_params["availability"]

        # Years of experience range
        if "min_years" in query_params:
            try:
                filters["min_years"] = int(query_params["min_years"])
            except ValueError:
                pass

        if "max_years" in query_params:
            try:
                filters["max_years"] = int(query_params["max_years"])
            except ValueError:
                pass

        return filters

    def _rank_profiles_with_ai(
        self, profiles: List[Dict], search_query: str
    ) -> List[Dict]:
        """検索クエリの関連性に基づいてAIで社内AI人材候補プロフィールをランク付けします"""
        try:
            # Prepare profiles for AI ranking
            profile_summaries = []
            for profile in profiles:
                summary = {
                    "profile_id": profile["profile_id"],
                    "business_title": profile.get("business_title", ""),
                    "skills": [skill["name"] for skill in profile.get("skills", [])],
                    "experience_summary": self._get_experience_summary(profile),
                    "departments": [
                        exp["department"] for exp in profile.get("experiences", [])
                    ],
                }
                profile_summaries.append(summary)

            # Generate AI ranking prompt
            ranking_prompt = self._create_ranking_prompt(
                profile_summaries, search_query
            )

            # Get AI ranking
            ranking_response = self.bedrock_client.generate_text(
                prompt=ranking_prompt, max_tokens=1000, temperature=0.1
            )

            # Parse ranking results
            ranked_profile_ids = self._parse_ranking_response(ranking_response)

            # Reorder profiles based on AI ranking
            ranked_profiles = []
            profile_dict = {p["profile_id"]: p for p in profiles}

            for profile_id in ranked_profile_ids:
                if profile_id in profile_dict:
                    ranked_profiles.append(profile_dict[profile_id])

            # Add any profiles not ranked by AI at the end
            for profile in profiles:
                if profile["profile_id"] not in ranked_profile_ids:
                    ranked_profiles.append(profile)

            return ranked_profiles

        except Exception as e:
            logger.error(f"Error in AI ranking: {str(e)}")
            # Return original order if AI ranking fails
            return profiles

    def _create_ranking_prompt(self, profiles: List[Dict], search_query: str) -> str:
        """社内AI人材候補プロフィールのAIランキング用プロンプトを作成します"""
        profiles_text = ""
        for i, profile in enumerate(profiles, 1):
            skills_text = ", ".join(profile["skills"][:5])  # 上位5スキル
            profiles_text += f"{i}. ID: {profile['profile_id']}\n"
            profiles_text += f"   Title: {profile['business_title']}\n"
            profiles_text += f"   Skills: {skills_text}\n"
            profiles_text += f"   Experience: {profile['experience_summary']}\n\n"

        return f"""
あなたは双日テックイノベーション：AI人材発掘・配置マッチングMVP（AI CoE支援）の
社内AI人材候補プロフィールを検索クエリに基づいてランク付けするアシスタントです。
プロフィールを分析し、検索要件への関連性でランク付けしてください。

検索クエリ: "{search_query}"

社内AI人材候補プロフィール:
{profiles_text}

指示:
1. 検索クエリにどの程度マッチするかでプロフィールをランク付けしてください
2. スキル、経験、職種を考慮してください
3. 関連性の高い順にプロフィールIDのみを返してください
4. プロフィールIDをカンマ区切りのリストで出力してください

出力例: profile_1, profile_3, profile_2

ランク付けされたプロフィールID:
"""

    def _parse_ranking_response(self, response: str) -> List[str]:
        """AIランキングレスポンスを解析してプロフィールIDを抽出します"""
        try:
            # Extract profile IDs from response
            lines = response.strip().split("\n")
            for line in lines:
                if "," in line and "profile_" in line:
                    profile_ids = [pid.strip() for pid in line.split(",")]
                    return [pid for pid in profile_ids if pid.startswith("profile_")]

            # Fallback: try to extract from any line containing profile IDs
            import re

            profile_ids = re.findall(r"profile_[a-zA-Z0-9_-]+", response)
            return list(
                dict.fromkeys(profile_ids)
            )  # Remove duplicates while preserving order

        except Exception as e:
            logger.error(f"Error parsing ranking response: {str(e)}")
            return []

    def _get_experience_summary(self, profile: Dict) -> str:
        """社内AI人材候補の経験概要を生成します"""
        experiences = profile.get("experiences", [])
        if not experiences:
            return "経験なし"

        total_years = sum(exp.get("duration", 0) for exp in experiences)
        departments = list(set(exp.get("department", "") for exp in experiences))

        return f"{total_years}年の経験 ({', '.join(departments[:3])})"

    def _paginate_results(
        self, profiles: List[Dict], page: int, limit: int
    ) -> List[Dict]:
        """社内AI人材候補検索結果にページネーションを適用します"""
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        return profiles[start_idx:end_idx]

    def _format_public_profile(self, profile: Dict) -> Dict:
        """社内AI人材候補検索結果用にプロフィールをフォーマットします"""
        return {
            "profile_id": profile["profile_id"],
            "business_title": profile.get("business_title", ""),
            "skills": profile.get("skills", [])[:10],  # Top 10 skills
            "experience_years": sum(
                exp.get("duration", 0) for exp in profile.get("experiences", [])
            ),
            "departments": list(
                set(exp.get("department", "") for exp in profile.get("experiences", []))
            ),
            "location": profile.get("location", ""),
            "availability": profile.get("availability", ""),
            "last_updated": profile.get("last_updated", ""),
        }

    def _format_detailed_profile(self, profile: Dict) -> Dict:
        """社内AI人材候補の個別プロフィール表示用に詳細プロフィールをフォーマットします"""
        return {
            "profile_id": profile["profile_id"],
            "business_title": profile.get("business_title", ""),
            "skills": profile.get("skills", []),
            "experiences": profile.get("experiences", []),
            "certifications": profile.get("certifications", []),
            "achievements": profile.get("achievements", []),
            "location": profile.get("location", ""),
            "availability": profile.get("availability", ""),
            "preferred_roles": profile.get("preferred_roles", []),
            "work_style": profile.get("work_style", ""),
            "contact_preferences": profile.get("contact_preferences", {}),
            "last_updated": profile.get("last_updated", ""),
        }

    def _increment_profile_views(self, user_id: str) -> None:
        """
        社内AI人材候補プロフィールの閲覧数をインクリメントします。
        非ブロッキング操作 - エラーはログに記録されますがレスポンスには影響しません。
        """
        try:
            self.veteran_profile_repo.increment_profile_views(user_id)
        except Exception as e:
            logger.warning(f"Failed to increment profile views for user {user_id}: {str(e)}")
            # Don't raise - profile view tracking is non-critical

    def _get_cors_headers(self) -> Dict:
        """外部API（社内AI人材候補検索）アクセス用CORSヘッダーを取得します"""
        return {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
            "Access-Control-Allow-Methods": "GET,OPTIONS",
        }


# Lambda function handlers
def handler(event, context):
    """社内AI人材候補検索操作のメインLambdaハンドラー"""
    try:
        path = event.get("path", "")
        http_method = event.get("httpMethod", "")
        
        search_handler = PublicSearchHandler()
        
        # Route based on path
        if "/public/talents/search" in path and http_method == "GET":
            return search_handler.search_veterans(event, context)
        elif "/public/talents/" in path and http_method == "GET":
            return search_handler.get_veteran_profile(event, context)
        elif "/public/categories" in path and http_method == "GET":
            return search_handler.get_search_categories(event, context)
        else:
            return {
                "statusCode": 404,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps({"error": "見つかりません"}),
            }
    except Exception as e:
        logger.error(f"Error in public search handler: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"error": message_config.get_error_message('internal_error')}),
        }


def search_veterans(event, context):
    """社内AI人材候補検索のLambdaハンドラー"""
    handler_instance = PublicSearchHandler()
    return handler_instance.search_veterans(event, context)


def get_veteran_profile(event, context):
    """社内AI人材候補プロフィール取得のLambdaハンドラー"""
    handler_instance = PublicSearchHandler()
    return handler_instance.get_veteran_profile(event, context)


def get_search_categories(event, context):
    """社内AI人材候補検索カテゴリ取得のLambdaハンドラー"""
    handler_instance = PublicSearchHandler()
    return handler_instance.get_search_categories(event, context)
