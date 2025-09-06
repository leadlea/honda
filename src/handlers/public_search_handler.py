"""
Public Search Handler for Honda Veteran Bank
Provides external access to veteran profiles with filtering and AI ranking
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.repositories.public_profile_repository import PublicProfileRepository
from src.services.ai_utils import get_ai_service
from src.services.bedrock_client import BedrockClient

# Public API - no authentication required for external access

logger = logging.getLogger(__name__)


class PublicSearchHandler:
    def __init__(self):
        self.public_profile_repo = PublicProfileRepository()
        self.bedrock_client = BedrockClient()
        self.ai_service = get_ai_service()

    def search_veterans(self, event: Dict, context: Any) -> Dict:
        """
        External API for searching veteran profiles
        Supports filtering by skills, experience, and availability
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
                            "veterans": [],
                            "total_count": 0,
                            "message": "No veterans found matching the criteria",
                        }
                    ),
                }

            # Apply AI ranking if search query provided
            search_query = query_params.get("q", "")
            if search_query:
                ranked_profiles = self._rank_profiles_with_ai(profiles, search_query)
            else:
                ranked_profiles = profiles

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
                        "veterans": formatted_profiles,
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
                        "error": "Internal server error",
                        "message": "Failed to search veterans",
                    }
                ),
            }

    def get_veteran_profile(self, event: Dict, context: Any) -> Dict:
        """
        Get detailed public profile of a specific veteran
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
                            "error": "Profile not found",
                            "message": "The requested veteran profile is not available",
                        }
                    ),
                }

            # Format detailed profile
            formatted_profile = self._format_detailed_profile(profile)

            return {
                "statusCode": 200,
                "headers": self._get_cors_headers(),
                "body": json.dumps({"veteran": formatted_profile}),
            }

        except Exception as e:
            logger.error(f"Error in get_veteran_profile: {str(e)}")
            return {
                "statusCode": 500,
                "headers": self._get_cors_headers(),
                "body": json.dumps(
                    {
                        "error": "Internal server error",
                        "message": "Failed to retrieve veteran profile",
                    }
                ),
            }

    def get_search_categories(self, event: Dict, context: Any) -> Dict:
        """
        Get available categories for filtering (skills, departments, etc.)
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
                        "error": "Internal server error",
                        "message": "Failed to retrieve categories",
                    }
                ),
            }

    def _extract_search_filters(self, query_params: Dict) -> Dict:
        """Extract and validate search filters from query parameters"""
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
        """Use AI to rank profiles based on search query relevance"""
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
        """Create prompt for AI-based profile ranking"""
        profiles_text = ""
        for i, profile in enumerate(profiles, 1):
            skills_text = ", ".join(profile["skills"][:5])  # Top 5 skills
            profiles_text += f"{i}. ID: {profile['profile_id']}\n"
            profiles_text += f"   Title: {profile['business_title']}\n"
            profiles_text += f"   Skills: {skills_text}\n"
            profiles_text += f"   Experience: {profile['experience_summary']}\n\n"

        return f"""
You are helping rank veteran profiles based on a search query. 
Analyze the profiles and rank them by relevance to the search requirements.

Search Query: "{search_query}"

Veteran Profiles:
{profiles_text}

Instructions:
1. Rank profiles by how well they match the search query
2. Consider skills, experience, and job titles
3. Return only the profile IDs in ranked order (most relevant first)
4. Format as a simple comma-separated list of profile IDs

Example output: profile_1, profile_3, profile_2

Ranked Profile IDs:
"""

    def _parse_ranking_response(self, response: str) -> List[str]:
        """Parse AI ranking response to extract profile IDs"""
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
        """Generate a brief experience summary"""
        experiences = profile.get("experiences", [])
        if not experiences:
            return "No experience listed"

        total_years = sum(exp.get("duration", 0) for exp in experiences)
        departments = list(set(exp.get("department", "") for exp in experiences))

        return f"{total_years} years across {', '.join(departments[:3])}"

    def _paginate_results(
        self, profiles: List[Dict], page: int, limit: int
    ) -> List[Dict]:
        """Apply pagination to results"""
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        return profiles[start_idx:end_idx]

    def _format_public_profile(self, profile: Dict) -> Dict:
        """Format profile for public search results"""
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
        """Format detailed profile for individual profile view"""
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

    def _get_cors_headers(self) -> Dict:
        """Get CORS headers for external API access"""
        return {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
            "Access-Control-Allow-Methods": "GET,OPTIONS",
        }


# Lambda function handlers
def search_veterans(event, context):
    """Lambda handler for veteran search"""
    handler = PublicSearchHandler()
    return handler.search_veterans(event, context)


def get_veteran_profile(event, context):
    """Lambda handler for getting veteran profile"""
    handler = PublicSearchHandler()
    return handler.get_veteran_profile(event, context)


def get_search_categories(event, context):
    """Lambda handler for getting search categories"""
    handler = PublicSearchHandler()
    return handler.get_search_categories(event, context)
