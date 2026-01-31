"""
AI utility functions and prompt templates for Bedrock Claude integration.
"""

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .bedrock_client import BedrockRequest, get_bedrock_client

logger = logging.getLogger(__name__)


@dataclass
class PromptTemplate:
    """Template for AI prompts with variable substitution."""

    template: str
    required_variables: List[str]
    optional_variables: List[str] = None

    def format(self, **kwargs) -> str:
        """
        Format template with provided variables.

        Args:
            **kwargs: Variables to substitute in template

        Returns:
            Formatted prompt string

        Raises:
            ValueError: If required variables are missing
        """
        missing_vars = [var for var in self.required_variables if var not in kwargs]
        if missing_vars:
            raise ValueError(f"Missing required variables: {missing_vars}")

        return self.template.format(**kwargs)


class AIPrompts:
    """Collection of AI prompt templates for various use cases."""

    # Questionnaire generation prompt
    QUESTIONNAIRE_GENERATION = PromptTemplate(
        template="""You are an expert HR consultant creating a personalized questionnaire for a veteran employee to assess their skills, experience, and career interests.

Employee Profile:
- Name: {name}
- Department: {department}
- Years of Experience: {years_experience}
- Current Role: {current_role}
- Previous Questionnaire Responses: {previous_responses}

Create a dynamic questionnaire with 8-12 questions that will help understand:
1. Technical skills and expertise levels
2. Leadership and management experience
3. Career interests and aspirations
4. Preferred work environments and styles
5. Areas for growth and development

Guidelines:
- Make questions specific and actionable
- Avoid generic questions if we already have similar information
- Include both multiple choice and open-ended questions
- Focus on uncovering unique strengths and interests
- Consider the employee's background and department

Return the questionnaire as a JSON object with this structure:
{{
  "questionnaire_id": "unique_id",
  "title": "Personalized Career Assessment",
  "description": "Brief description of the questionnaire purpose",
  "questions": [
    {{
      "id": "q1",
      "type": "multiple_choice|open_ended|rating_scale",
      "question": "Question text",
      "options": ["option1", "option2"] // only for multiple_choice
      "scale": {{"min": 1, "max": 5, "labels": {{"1": "Beginner", "5": "Expert"}}}} // only for rating_scale
    }}
  ]
}}""",
        required_variables=["name", "department", "years_experience", "current_role"],
        optional_variables=["previous_responses"],
    )

    # Business title generation prompt
    BUSINESS_TITLE_GENERATION = PromptTemplate(
        template="""あなたは、退役軍人の従業員のスキルと経験に基づいて、ユニークなビジネスタイトルを作成する専門のキャリアコンサルタントです。

従業員プロフィール:
名前: {name}
部署: {department}
スキル: {skills}
経験: {experience}
キャリア興味: {career_interests}
現在の役職: {current_role}

以下の条件を満たす5つのユニークで専門的な日本語のビジネスタイトルを生成してください:
1. 従業員のスキルと経験のユニークな組み合わせを反映する
2. 市場性があり、潜在的な機会に魅力的である
3. 一般的な職種名とは差別化されている
4. 価値提案を強調する
5. 社内外の両方で使用するのに適している

考慮事項:
- 業界固有の専門知識
- リーダーシップ能力
- 技術的専門性
- 部門横断的な経験
- イノベーションと問題解決能力

タイトルは必ず日本語で生成し、以下のJSON形式で返してください:
{{
  "titles": [
    {{
      "title": "プロフェッショナルなビジネスタイトル（日本語）",
      "description": "このタイトルが適している理由の簡単な説明（日本語）",
      "focus_areas": ["分野1", "分野2", "分野3"],
      "market_appeal": "high|medium|low"
    }}
  ],
  "recommended_title": "リストから最も推奨されるタイトル（日本語）",
  "reasoning": "推奨タイトルが最適である理由の説明（日本語）"
}}""",
        required_variables=[
            "name",
            "department",
            "skills",
            "experience",
            "career_interests",
            "current_role",
        ],
    )

    # Profile analysis prompt
    PROFILE_ANALYSIS = PromptTemplate(
        template="""Analyze the following veteran employee profile and provide insights for career matching and recommendations.

Profile Data:
{profile_data}

Questionnaire Responses:
{questionnaire_responses}

Provide analysis in the following areas:
1. Key Strengths: Top 5 strengths based on skills and experience
2. Career Trajectory: Likely career progression paths
3. Skill Gaps: Areas for potential development
4. Market Value: Assessment of marketability
5. Opportunity Types: Types of roles/projects that would be good fits

Return analysis as JSON:
{{
  "strengths": [
    {{
      "strength": "Strength name",
      "evidence": "Supporting evidence from profile",
      "market_relevance": "high|medium|low"
    }}
  ],
  "career_paths": [
    {{
      "path": "Career path name",
      "probability": "high|medium|low",
      "required_development": ["skill1", "skill2"]
    }}
  ],
  "skill_gaps": [
    {{
      "skill": "Skill name",
      "importance": "high|medium|low",
      "development_suggestion": "How to develop this skill"
    }}
  ],
  "market_assessment": {{
    "overall_marketability": "high|medium|low",
    "unique_value_proposition": "What makes this person unique",
    "target_industries": ["industry1", "industry2"]
  }},
  "opportunity_types": [
    {{
      "type": "Opportunity type",
      "fit_score": 0.0-1.0,
      "reasoning": "Why this is a good fit"
    }}
  ]
}}""",
        required_variables=["profile_data", "questionnaire_responses"],
    )

    # Opportunity matching prompt
    OPPORTUNITY_MATCHING = PromptTemplate(
        template="""Analyze how well a veteran employee profile matches a specific opportunity and provide detailed matching insights.

Veteran Profile:
{veteran_profile}

Opportunity Details:
{opportunity_details}

Analyze the match across these dimensions:
1. Skills Alignment: How well do skills match requirements
2. Experience Relevance: Relevance of past experience
3. Career Fit: Alignment with career interests and goals
4. Growth Potential: Opportunity for professional development
5. Cultural Fit: Alignment with work style preferences

Provide a detailed matching analysis as JSON:
{{
  "overall_match_score": 0.0-1.0,
  "match_analysis": {{
    "skills_alignment": {{
      "score": 0.0-1.0,
      "matching_skills": ["skill1", "skill2"],
      "missing_skills": ["skill1", "skill2"],
      "transferable_skills": ["skill1", "skill2"]
    }},
    "experience_relevance": {{
      "score": 0.0-1.0,
      "relevant_experience": ["experience1", "experience2"],
      "experience_gaps": ["gap1", "gap2"]
    }},
    "career_fit": {{
      "score": 0.0-1.0,
      "alignment_factors": ["factor1", "factor2"],
      "potential_concerns": ["concern1", "concern2"]
    }},
    "growth_potential": {{
      "score": 0.0-1.0,
      "development_opportunities": ["opportunity1", "opportunity2"]
    }}
  }},
  "recommendation": {{
    "action": "strongly_recommend|recommend|consider|not_recommend",
    "reasoning": "Detailed explanation of recommendation",
    "success_factors": ["factor1", "factor2"],
    "risk_factors": ["risk1", "risk2"]
  }},
  "match_summary": "Brief summary of why this is/isn't a good match"
}}""",
        required_variables=["veteran_profile", "opportunity_details"],
    )


class AIService:
    """Service class for AI operations using Bedrock Claude."""

    def __init__(self):
        self.client = get_bedrock_client()

    async def generate_questionnaire(
        self,
        name: str,
        department: str,
        years_experience: int,
        current_role: str,
        previous_responses: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """
        Generate a personalized questionnaire for a veteran employee.

        Args:
            name: Employee name
            department: Employee department
            years_experience: Years of experience
            current_role: Current job role
            previous_responses: Previous questionnaire responses

        Returns:
            Generated questionnaire as dictionary
        """
        try:
            prompt = AIPrompts.QUESTIONNAIRE_GENERATION.format(
                name=name,
                department=department,
                years_experience=years_experience,
                current_role=current_role,
                previous_responses=json.dumps(previous_responses or []),
            )

            request = BedrockRequest(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=3000,
                temperature=0.7,
            )

            response = await self.client.invoke_claude(request)

            if not response.success:
                raise Exception(f"AI generation failed: {response.error_message}")

            # Parse JSON response
            questionnaire_data = json.loads(response.content)
            return questionnaire_data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse questionnaire JSON: {e}")
            raise Exception("Failed to generate valid questionnaire format")
        except Exception as e:
            logger.error(f"Questionnaire generation failed: {e}")
            raise

    async def generate_business_titles(
        self,
        name: str,
        department: str,
        skills: List[Dict],
        experience: List[Dict],
        career_interests: List[str],
        current_role: str,
        branding_context: str = "",
        platform_name: str = "製造業プラチナアドバイザリー",
    ) -> Dict[str, Any]:
        """
        Generate business titles for a registered talent.

        Args:
            name: Employee name
            department: Employee department
            skills: List of skills with details
            experience: List of experience entries
            career_interests: List of career interests
            current_role: Current job role
            branding_context: Branding context for title generation
            platform_name: Platform name for context

        Returns:
            Generated business titles as dictionary
        """
        try:
            # Use branding context if provided, otherwise use default
            if branding_context:
                context_prompt = branding_context
            else:
                context_prompt = f"""
{platform_name}のビジネスタイトル生成：

【プラットフォームの特徴】
- 製造業に特化した人材プラットフォーム
- 登録人材の専門性と経験を重視
- 「人を活かす、新しい製造業の生態系」の実現

【タイトル生成の方針】
1. 製造業の専門性を反映
2. 登録人材の経験レベルを適切に表現
3. 市場価値と成長可能性を示唆
4. 企業にとって魅力的で理解しやすい表現
5. 日本の製造業文化に適合した表現
"""

            prompt = f"""{context_prompt}

登録人材情報：
名前: {name}
部署: {department}
現在の役職: {current_role}
スキル: {json.dumps(skills, ensure_ascii=False)}
経験: {json.dumps(experience, ensure_ascii=False)}
キャリア志向: {json.dumps(career_interests, ensure_ascii=False)}

上記の情報を基に、この登録人材に適した複数のビジネスタイトルを生成してください。
製造業の専門性を活かし、企業にとって魅力的で理解しやすいタイトルを提案してください。

以下のJSON形式で回答してください：
{{
    "titles": [
        {{
            "title": "提案タイトル1",
            "reasoning": "このタイトルを提案する理由",
            "market_appeal": "市場での魅力度（1-5）",
            "specialization": "専門分野"
        }}
    ],
    "recommended_title": "最も推奨するタイトル",
    "reasoning": "推奨理由の詳細説明"
}}"""

            request = BedrockRequest(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
                temperature=0.8,
            )

            response = await self.client.invoke_claude(request)

            if not response.success:
                raise Exception(f"AI generation failed: {response.error_message}")

            # Parse JSON response
            titles_data = json.loads(response.content)
            
            # Apply branding to titles if needed
            if "titles" in titles_data:
                for title_info in titles_data["titles"]:
                    if "title" in title_info:
                        # Apply any additional branding transformations
                        title_info["title"] = title_info["title"].replace("ベテラン", "登録人材")
            
            return titles_data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse business titles JSON: {e}")
            raise Exception("Failed to generate valid business titles format")
        except Exception as e:
            logger.error(f"Business title generation failed: {e}")
            raise

    async def analyze_profile(
        self, profile_data: Dict[str, Any], questionnaire_responses: List[Dict]
    ) -> Dict[str, Any]:
        """
        Analyze a veteran profile for insights and recommendations.

        Args:
            profile_data: Complete profile data
            questionnaire_responses: Questionnaire responses

        Returns:
            Profile analysis as dictionary
        """
        try:
            prompt = AIPrompts.PROFILE_ANALYSIS.format(
                profile_data=json.dumps(profile_data),
                questionnaire_responses=json.dumps(questionnaire_responses),
            )

            request = BedrockRequest(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4000,
                temperature=0.6,
            )

            response = await self.client.invoke_claude(request)

            if not response.success:
                raise Exception(f"AI analysis failed: {response.error_message}")

            # Parse JSON response
            analysis_data = json.loads(response.content)
            return analysis_data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse profile analysis JSON: {e}")
            raise Exception("Failed to generate valid profile analysis format")
        except Exception as e:
            logger.error(f"Profile analysis failed: {e}")
            raise

    async def match_opportunity(
        self, veteran_profile: Dict[str, Any], opportunity_details: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze how well a veteran matches an opportunity.

        Args:
            veteran_profile: Complete veteran profile
            opportunity_details: Opportunity details

        Returns:
            Matching analysis as dictionary
        """
        try:
            prompt = AIPrompts.OPPORTUNITY_MATCHING.format(
                veteran_profile=json.dumps(veteran_profile),
                opportunity_details=json.dumps(opportunity_details),
            )

            request = BedrockRequest(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=3000,
                temperature=0.5,
            )

            response = await self.client.invoke_claude(request)

            if not response.success:
                raise Exception(f"AI matching failed: {response.error_message}")

            # Parse JSON response
            matching_data = json.loads(response.content)
            return matching_data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse opportunity matching JSON: {e}")
            raise Exception("Failed to generate valid matching analysis format")
        except Exception as e:
            logger.error(f"Opportunity matching failed: {e}")
            raise


# Global service instance
_ai_service: Optional[AIService] = None


def get_ai_service() -> AIService:
    """
    Get or create global AI service instance.

    Returns:
        AIService instance
    """
    global _ai_service

    if _ai_service is None:
        _ai_service = AIService()

    return _ai_service
