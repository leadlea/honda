"""
Recommendation service for managing personalized recommendations and feedback.
Builds on the matching engine to provide advanced recommendation features.
"""

import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from ..config.ai_content_config import ai_content_config
from ..models.recommendation import Recommendation
from ..repositories.opportunity_repository import OpportunityRepository
from ..repositories.recommendation_repository import RecommendationRepository
from ..repositories.veteran_profile_repository import VeteranProfileRepository
from .matching_engine import MatchingCriteria, get_matching_engine
from ..utils.branding_logger import get_branding_logger

logger = logging.getLogger(__name__)

# Initialize branding logger
branding_logger = get_branding_logger('recommendation_service')


@dataclass
class RecommendationFeedback:
    """Feedback data for recommendation accuracy."""

    recommendation_id: str
    user_id: str
    feedback_type: str  # 'positive', 'negative', 'applied', 'dismissed'
    feedback_score: Optional[float] = None  # 1-5 rating
    feedback_comment: Optional[str] = None
    created_at: str = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()


@dataclass
class RecommendationStats:
    """Statistics for recommendation performance."""

    total_recommendations: int
    viewed_count: int
    applied_count: int
    dismissed_count: int
    average_match_score: float
    feedback_count: int
    average_feedback_score: Optional[float] = None
    conversion_rate: float = 0.0  # applied / total
    engagement_rate: float = 0.0  # viewed / total

    def __post_init__(self):
        if self.total_recommendations > 0:
            self.conversion_rate = self.applied_count / self.total_recommendations
            self.engagement_rate = self.viewed_count / self.total_recommendations


class RecommendationService:
    """
    Advanced recommendation service with history management,
    duplicate prevention, and feedback collection.
    """

    def __init__(self):
        self.matching_engine = get_matching_engine()
        self.recommendation_repo = RecommendationRepository()
        self.veteran_repo = VeteranProfileRepository()
        self.opportunity_repo = OpportunityRepository()

        # Configuration
        self.duplicate_prevention_days = 30  # Days to prevent duplicate recommendations
        self.max_recommendations_per_batch = 20
        self.min_feedback_for_learning = 5

    async def generate_personalized_recommendations(
        self,
        user_id: str,
        criteria: Optional[MatchingCriteria] = None,
        prevent_duplicates: bool = True,
    ) -> List[Recommendation]:
        """
        Generate personalized recommendations with duplicate prevention.

        Args:
            user_id: The veteran's user ID
            criteria: Optional matching criteria
            prevent_duplicates: Whether to prevent duplicate recommendations

        Returns:
            List of new recommendations
        """
        try:
            # Get existing recommendations for duplicate prevention
            existing_opportunity_ids = set()
            if prevent_duplicates:
                existing_opportunity_ids = (
                    await self._get_recent_recommendation_opportunity_ids(
                        user_id, self.duplicate_prevention_days
                    )
                )

            # Generate new recommendations using matching engine
            new_recommendations = (
                await self.matching_engine.generate_recommendations_for_veteran(
                    user_id, criteria
                )
            )

            # Filter out duplicates
            filtered_recommendations = []
            for rec in new_recommendations:
                if rec.opportunity_id not in existing_opportunity_ids:
                    filtered_recommendations.append(rec)
                else:
                    logger.info(
                        f"Filtered duplicate recommendation for opportunity {rec.opportunity_id}"
                    )

            # Apply personalization based on user history and feedback
            personalized_recommendations = await self._apply_personalization(
                user_id, filtered_recommendations
            )
            
            # Enhance recommendation reasons with branding context
            enhanced_recommendations = await self._enhance_recommendation_reasons(
                user_id, personalized_recommendations
            )

            # Limit the number of recommendations
            if len(enhanced_recommendations) > self.max_recommendations_per_batch:
                enhanced_recommendations = enhanced_recommendations[
                    : self.max_recommendations_per_batch
                ]

            logger.info(
                f"Generated {len(enhanced_recommendations)} personalized recommendations for user {user_id}"
            )
            branding_logger.log_recommendation_generated(user_id)
            return enhanced_recommendations

        except Exception as e:
            logger.error(
                f"Error generating personalized recommendations for user {user_id}: {e}"
            )
            raise

    async def _get_recent_recommendation_opportunity_ids(
        self, user_id: str, days: int
    ) -> set:
        """Get opportunity IDs from recent recommendations to prevent duplicates."""
        try:
            # Get all recommendations for the user
            all_recommendations = self.recommendation_repo.get_user_recommendations(
                user_id
            )

            # Filter by date
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            cutoff_iso = cutoff_date.isoformat()

            recent_opportunity_ids = set()
            for rec in all_recommendations:
                if rec.generated_at >= cutoff_iso:
                    recent_opportunity_ids.add(rec.opportunity_id)

            return recent_opportunity_ids

        except Exception as e:
            logger.error(f"Error getting recent recommendation opportunity IDs: {e}")
            return set()

    async def _apply_personalization(
        self, user_id: str, recommendations: List[Recommendation]
    ) -> List[Recommendation]:
        """Apply personalization based on user feedback and behavior."""
        try:
            # Get user's feedback history
            feedback_data = await self._get_user_feedback_patterns(user_id)

            # Adjust recommendation scores based on feedback patterns
            for rec in recommendations:
                # Apply feedback-based adjustments
                adjustment_factor = self._calculate_personalization_factor(
                    rec, feedback_data
                )
                rec.match_score *= adjustment_factor

                # Add personalization reason to match_reasons
                if adjustment_factor != 1.0:
                    rec.match_reasons.append(
                        {
                            "category": "personalization",
                            "description": f"Adjusted based on user preferences (factor: {adjustment_factor:.2f})",
                            "weight": abs(adjustment_factor - 1.0) * 0.1,
                            "details": {"adjustment_factor": adjustment_factor},
                        }
                    )

            # Re-sort by adjusted scores
            recommendations.sort(key=lambda x: x.match_score, reverse=True)

            return recommendations

        except Exception as e:
            logger.error(f"Error applying personalization: {e}")
            return recommendations

    async def _enhance_recommendation_reasons(
        self, user_id: str, recommendations: List[Recommendation]
    ) -> List[Recommendation]:
        """Enhance recommendation reasons with branding context and detailed explanations."""
        try:
            # Get user profile for context
            user_profile = self.veteran_repo.get_profile(user_id)
            if not user_profile:
                return recommendations

            for rec in recommendations:
                # Get opportunity details
                opportunity = self.opportunity_repo.get_opportunity(rec.opportunity_id)
                if not opportunity:
                    continue

                # Calculate detailed match metrics
                skill_match_score = self._calculate_skill_match_score(user_profile, opportunity)
                experience_match_score = self._calculate_experience_match_score(user_profile, opportunity)
                growth_potential = self._assess_growth_potential(user_profile, opportunity)
                ecosystem_contribution = self._assess_ecosystem_contribution(user_profile, opportunity)

                # Generate personalized message using AI content config
                personalized_message = self._generate_personalized_message(
                    user_profile, opportunity, rec.match_score
                )

                # Create enhanced match reason using template
                enhanced_reason = ai_content_config.get_recommendation_template(
                    'match_reason_template',
                    skill_match_score=int(skill_match_score * 100),
                    skill_match_details=self._format_skill_match_details(user_profile, opportunity),
                    experience_match_score=int(experience_match_score * 100),
                    experience_match_details=self._format_experience_match_details(user_profile, opportunity),
                    growth_potential=growth_potential,
                    growth_details=self._format_growth_details(user_profile, opportunity),
                    ecosystem_contribution=ecosystem_contribution,
                    contribution_details=self._format_contribution_details(user_profile, opportunity),
                    personalized_message=personalized_message
                )

                # Add enhanced reason to match_reasons
                rec.match_reasons.append({
                    "category": "detailed_analysis",
                    "description": "製造業プラチナアドバイザリー詳細分析",
                    "weight": 1.0,
                    "details": {
                        "enhanced_reason": enhanced_reason,
                        "skill_match_score": skill_match_score,
                        "experience_match_score": experience_match_score,
                        "growth_potential": growth_potential,
                        "ecosystem_contribution": ecosystem_contribution
                    }
                })

            return recommendations

        except Exception as e:
            logger.error(f"Error enhancing recommendation reasons: {e}")
            return recommendations

    def _calculate_skill_match_score(self, user_profile, opportunity) -> float:
        """Calculate skill match score between user and opportunity."""
        try:
            user_skills = set(skill.get('name', '').lower() for skill in user_profile.skills)
            required_skills = set(skill.lower() for skill in opportunity.required_skills)
            
            if not required_skills:
                return 0.8  # Default score if no specific skills required
            
            matched_skills = user_skills.intersection(required_skills)
            return len(matched_skills) / len(required_skills)
        except:
            return 0.7  # Default score on error

    def _calculate_experience_match_score(self, user_profile, opportunity) -> float:
        """Calculate experience match score between user and opportunity."""
        try:
            # Simple experience matching based on years and domain
            user_years = sum(exp.get('duration', 0) for exp in user_profile.experiences)
            required_years = opportunity.required_experience_years or 0
            
            if required_years == 0:
                return 0.8
            
            experience_ratio = min(user_years / required_years, 1.0)
            return experience_ratio
        except:
            return 0.7

    def _assess_growth_potential(self, user_profile, opportunity) -> str:
        """Assess growth potential for the user in this opportunity."""
        try:
            # Assess based on skill gaps and opportunity requirements
            user_skills = set(skill.get('name', '').lower() for skill in user_profile.skills)
            opportunity_skills = set(skill.lower() for skill in opportunity.required_skills)
            
            skill_gaps = opportunity_skills - user_skills
            if len(skill_gaps) <= 2:
                return "高い成長可能性"
            elif len(skill_gaps) <= 4:
                return "中程度の成長可能性"
            else:
                return "新分野への挑戦機会"
        except:
            return "成長機会あり"

    def _assess_ecosystem_contribution(self, user_profile, opportunity) -> str:
        """Assess potential contribution to manufacturing ecosystem."""
        try:
            # Assess based on experience and opportunity type
            total_experience = sum(exp.get('duration', 0) for exp in user_profile.experiences)
            
            if total_experience >= 15:
                return "シニアエキスパートとしての指導・メンタリング"
            elif total_experience >= 10:
                return "専門知識の共有と技術伝承"
            elif total_experience >= 5:
                return "実践的スキルの活用と改善提案"
            else:
                return "新しい視点での価値創造"
        except:
            return "製造業生態系への貢献"

    def _generate_personalized_message(self, user_profile, opportunity, match_score) -> str:
        """Generate personalized message for the recommendation."""
        try:
            user_name = user_profile.basic_info.get('name', '登録人材')
            
            if match_score >= 0.8:
                return f"{user_name}さんの豊富な経験と専門スキルが、この参画機会で大いに活かされることが期待されます。製造業の新しい生態系において、あなたの価値創造力を存分に発揮していただけるでしょう。"
            elif match_score >= 0.6:
                return f"{user_name}さんの持つスキルと経験が、この参画機会での成功につながります。新たな挑戦を通じて、さらなる専門性の向上と製造業への貢献が期待できます。"
            else:
                return f"{user_name}さんにとって新しい分野への挑戦となりますが、これまでの経験を活かしながら新たなスキルを習得し、製造業の多様性に貢献する絶好の機会です。"
        except:
            return "あなたの専門性を活かし、製造業の新しい生態系で価値創造に貢献する機会です。"

    def _format_skill_match_details(self, user_profile, opportunity) -> str:
        """Format skill match details."""
        try:
            user_skills = [skill.get('name', '') for skill in user_profile.skills[:5]]
            return f"主要スキル: {', '.join(user_skills)}"
        except:
            return "スキル情報を分析中"

    def _format_experience_match_details(self, user_profile, opportunity) -> str:
        """Format experience match details."""
        try:
            total_years = sum(exp.get('duration', 0) for exp in user_profile.experiences)
            departments = list(set(exp.get('department', '') for exp in user_profile.experiences))[:3]
            return f"{total_years}年の経験 ({', '.join(departments)})"
        except:
            return "経験情報を分析中"

    def _format_growth_details(self, user_profile, opportunity) -> str:
        """Format growth potential details."""
        return "新しい技術習得と専門性向上の機会"

    def _format_contribution_details(self, user_profile, opportunity) -> str:
        """Format ecosystem contribution details."""
        return "製造業の持続的発展と人材育成への貢献"

        except Exception as e:
            logger.error(f"Error applying personalization: {e}")
            return recommendations

    async def _get_user_feedback_patterns(self, user_id: str) -> Dict[str, Any]:
        """Analyze user's feedback patterns to understand preferences."""
        try:
            # Get user's recommendation history
            user_recommendations = self.recommendation_repo.get_user_recommendations(
                user_id, limit=100
            )

            patterns = {
                "preferred_opportunity_types": defaultdict(int),
                "preferred_companies": defaultdict(int),
                "preferred_locations": defaultdict(int),
                "dismissed_patterns": defaultdict(int),
                "applied_patterns": defaultdict(int),
                "average_applied_score": 0.0,
                "average_dismissed_score": 0.0,
            }

            applied_scores = []
            dismissed_scores = []

            for rec in user_recommendations:
                # Get opportunity details
                opportunity = self.opportunity_repo.get_opportunity(rec.opportunity_id)
                if not opportunity:
                    continue

                if rec.status == "applied":
                    patterns["applied_patterns"][opportunity.type] += 1
                    patterns["preferred_opportunity_types"][
                        opportunity.type
                    ] += 2  # Higher weight
                    patterns["preferred_companies"][opportunity.company] += 2
                    patterns["preferred_locations"][opportunity.location] += 2
                    applied_scores.append(rec.match_score)

                elif rec.status == "dismissed":
                    patterns["dismissed_patterns"][opportunity.type] += 1
                    dismissed_scores.append(rec.match_score)

                elif rec.status == "viewed":
                    patterns["preferred_opportunity_types"][opportunity.type] += 1
                    patterns["preferred_companies"][opportunity.company] += 1
                    patterns["preferred_locations"][opportunity.location] += 1

            # Calculate average scores
            if applied_scores:
                patterns["average_applied_score"] = sum(applied_scores) / len(
                    applied_scores
                )
            if dismissed_scores:
                patterns["average_dismissed_score"] = sum(dismissed_scores) / len(
                    dismissed_scores
                )

            return patterns

        except Exception as e:
            logger.error(f"Error analyzing user feedback patterns: {e}")
            return {}

    def _calculate_personalization_factor(
        self, recommendation: Recommendation, feedback_patterns: Dict[str, Any]
    ) -> float:
        """Calculate personalization adjustment factor based on feedback patterns."""
        try:
            # Get opportunity details
            opportunity = self.opportunity_repo.get_opportunity(
                recommendation.opportunity_id
            )
            if not opportunity:
                return 1.0

            factor = 1.0

            # Adjust based on opportunity type preferences
            type_preference = feedback_patterns.get("preferred_opportunity_types", {})
            if opportunity.type in type_preference:
                preference_strength = type_preference[opportunity.type]
                factor *= 1.0 + (preference_strength * 0.1)  # Up to 20% boost

            # Adjust based on company preferences
            company_preference = feedback_patterns.get("preferred_companies", {})
            if opportunity.company in company_preference:
                preference_strength = company_preference[opportunity.company]
                factor *= 1.0 + (preference_strength * 0.05)  # Up to 10% boost

            # Adjust based on location preferences
            location_preference = feedback_patterns.get("preferred_locations", {})
            if opportunity.location in location_preference:
                preference_strength = location_preference[opportunity.location]
                factor *= 1.0 + (preference_strength * 0.05)  # Up to 10% boost

            # Penalize if similar opportunities were frequently dismissed
            dismissed_patterns = feedback_patterns.get("dismissed_patterns", {})
            if opportunity.type in dismissed_patterns:
                dismissal_count = dismissed_patterns[opportunity.type]
                factor *= max(0.5, 1.0 - (dismissal_count * 0.1))  # Up to 50% penalty

            # Ensure factor stays within reasonable bounds
            factor = max(0.3, min(2.0, factor))

            return factor

        except Exception as e:
            logger.error(f"Error calculating personalization factor: {e}")
            return 1.0

    async def record_recommendation_feedback(
        self, feedback: RecommendationFeedback
    ) -> bool:
        """
        Record feedback for a recommendation to improve future recommendations.

        Args:
            feedback: Feedback data

        Returns:
            True if feedback was recorded successfully
        """
        try:
            # Get the recommendation
            recommendation = self.recommendation_repo.get_recommendation(
                feedback.user_id, feedback.recommendation_id
            )

            if not recommendation:
                raise ValueError(
                    f"Recommendation {feedback.recommendation_id} not found"
                )

            # Update recommendation status based on feedback
            if feedback.feedback_type == "applied":
                recommendation.mark_applied()
            elif feedback.feedback_type == "dismissed":
                recommendation.mark_dismissed()
            elif feedback.feedback_type in ["positive", "negative"]:
                if recommendation.status == "generated":
                    recommendation.mark_viewed()

            # Store feedback in recommendation match_reasons for future analysis
            feedback_reason = {
                "category": "user_feedback",
                "description": f"User feedback: {feedback.feedback_type}",
                "weight": feedback.feedback_score or 0.0,
                "details": {
                    "feedback_type": feedback.feedback_type,
                    "feedback_score": feedback.feedback_score,
                    "feedback_comment": feedback.feedback_comment,
                    "feedback_date": feedback.created_at,
                },
            }

            recommendation.match_reasons.append(feedback_reason)

            # Update the recommendation
            success = self.recommendation_repo.update_recommendation(recommendation)

            if success:
                logger.info(
                    f"Recorded feedback for recommendation {feedback.recommendation_id}"
                )

                # Trigger learning update if we have enough feedback
                await self._update_learning_model(feedback.user_id)

            return success

        except Exception as e:
            logger.error(f"Error recording recommendation feedback: {e}")
            raise

    async def _update_learning_model(self, user_id: str) -> None:
        """Update learning model based on accumulated feedback."""
        try:
            # Get recent feedback count
            user_recommendations = self.recommendation_repo.get_user_recommendations(
                user_id, limit=50
            )

            feedback_count = sum(
                1
                for rec in user_recommendations
                if any(
                    reason.get("category") == "user_feedback"
                    for reason in rec.match_reasons
                )
            )

            if feedback_count >= self.min_feedback_for_learning:
                logger.info(
                    f"Updating learning model for user {user_id} with {feedback_count} feedback items"
                )
                # Here you could implement more sophisticated ML model updates
                # For now, we rely on the pattern analysis in _get_user_feedback_patterns

        except Exception as e:
            logger.error(f"Error updating learning model: {e}")

    async def get_recommendation_statistics(
        self, user_id: str, days: Optional[int] = 30
    ) -> RecommendationStats:
        """
        Get recommendation statistics for a user.

        Args:
            user_id: The user's ID
            days: Number of days to analyze (None for all time)

        Returns:
            RecommendationStats object
        """
        try:
            # Get user recommendations
            all_recommendations = self.recommendation_repo.get_user_recommendations(
                user_id
            )

            # Filter by date if specified
            if days:
                cutoff_date = datetime.utcnow() - timedelta(days=days)
                cutoff_iso = cutoff_date.isoformat()
                recommendations = [
                    rec for rec in all_recommendations if rec.generated_at >= cutoff_iso
                ]
            else:
                recommendations = all_recommendations

            if not recommendations:
                return RecommendationStats(
                    total_recommendations=0,
                    viewed_count=0,
                    applied_count=0,
                    dismissed_count=0,
                    average_match_score=0.0,
                    feedback_count=0,
                )

            # Calculate statistics
            total_count = len(recommendations)
            viewed_count = sum(
                1
                for rec in recommendations
                if rec.status in ["viewed", "applied", "dismissed"]
            )
            applied_count = sum(1 for rec in recommendations if rec.status == "applied")
            dismissed_count = sum(
                1 for rec in recommendations if rec.status == "dismissed"
            )

            # Calculate average match score
            total_score = sum(rec.match_score for rec in recommendations)
            average_match_score = total_score / total_count if total_count > 0 else 0.0

            # Count feedback items
            feedback_count = sum(
                1
                for rec in recommendations
                if any(
                    reason.get("category") == "user_feedback"
                    for reason in rec.match_reasons
                )
            )

            # Calculate average feedback score
            feedback_scores = []
            for rec in recommendations:
                for reason in rec.match_reasons:
                    if reason.get("category") == "user_feedback":
                        score = reason.get("details", {}).get("feedback_score")
                        if score is not None:
                            feedback_scores.append(score)

            average_feedback_score = (
                sum(feedback_scores) / len(feedback_scores) if feedback_scores else None
            )

            return RecommendationStats(
                total_recommendations=total_count,
                viewed_count=viewed_count,
                applied_count=applied_count,
                dismissed_count=dismissed_count,
                average_match_score=average_match_score,
                feedback_count=feedback_count,
                average_feedback_score=average_feedback_score,
            )

        except Exception as e:
            logger.error(f"Error getting recommendation statistics: {e}")
            raise

    async def get_recommendation_history(
        self,
        user_id: str,
        limit: Optional[int] = 50,
        status_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get detailed recommendation history for a user.

        Args:
            user_id: The user's ID
            limit: Maximum number of recommendations to return
            status_filter: Optional status filter

        Returns:
            List of recommendation history items with opportunity details
        """
        try:
            # Get recommendations
            if status_filter:
                recommendations = (
                    self.recommendation_repo.get_user_recommendations_by_status(
                        user_id, status_filter, limit
                    )
                )
            else:
                recommendations = self.recommendation_repo.get_user_recommendations(
                    user_id, limit
                )

            # Enrich with opportunity details
            history = []
            for rec in recommendations:
                opportunity = self.opportunity_repo.get_opportunity(rec.opportunity_id)

                history_item = {
                    "recommendation_id": rec.recommendation_id,
                    "opportunity_id": rec.opportunity_id,
                    "match_score": rec.match_score,
                    "status": rec.status,
                    "generated_at": rec.generated_at,
                    "viewed_at": rec.viewed_at,
                    "applied_at": rec.applied_at,
                    "dismissed_at": rec.dismissed_at,
                    "match_reasons": rec.match_reasons,
                    "opportunity": {
                        "title": opportunity.title if opportunity else "Unknown",
                        "company": opportunity.company if opportunity else "Unknown",
                        "type": opportunity.type if opportunity else "Unknown",
                        "location": opportunity.location if opportunity else "Unknown",
                    }
                    if opportunity
                    else None,
                }

                # Extract feedback if available
                feedback_reasons = [
                    reason
                    for reason in rec.match_reasons
                    if reason.get("category") == "user_feedback"
                ]
                if feedback_reasons:
                    latest_feedback = feedback_reasons[-1]  # Get most recent feedback
                    history_item["feedback"] = latest_feedback.get("details", {})

                history.append(history_item)

            return history

        except Exception as e:
            logger.error(f"Error getting recommendation history: {e}")
            raise

    async def refresh_recommendations_with_feedback_learning(
        self, user_id: str, criteria: Optional[MatchingCriteria] = None
    ) -> List[Recommendation]:
        """
        Refresh recommendations incorporating feedback learning.

        Args:
            user_id: The user's ID
            criteria: Optional matching criteria

        Returns:
            List of new recommendations
        """
        try:
            # Generate new personalized recommendations
            new_recommendations = await self.generate_personalized_recommendations(
                user_id, criteria, prevent_duplicates=True
            )

            # Save the recommendations
            if new_recommendations:
                await self.matching_engine.save_recommendations(new_recommendations)
                logger.info(
                    f"Refreshed {len(new_recommendations)} recommendations for user {user_id}"
                )

            return new_recommendations

        except Exception as e:
            logger.error(
                f"Error refreshing recommendations with feedback learning: {e}"
            )
            raise

    async def get_recommendation_insights(self, user_id: str) -> Dict[str, Any]:
        """
        Get insights about user's recommendation patterns and preferences.

        Args:
            user_id: The user's ID

        Returns:
            Dictionary with insights and recommendations
        """
        try:
            # Get statistics
            stats = await self.get_recommendation_statistics(user_id)

            # Get feedback patterns
            feedback_patterns = await self._get_user_feedback_patterns(user_id)

            # Generate insights
            insights = {
                "statistics": stats.__dict__,
                "preferences": {
                    "top_opportunity_types": dict(
                        sorted(
                            feedback_patterns.get(
                                "preferred_opportunity_types", {}
                            ).items(),
                            key=lambda x: x[1],
                            reverse=True,
                        )[:5]
                    ),
                    "top_companies": dict(
                        sorted(
                            feedback_patterns.get("preferred_companies", {}).items(),
                            key=lambda x: x[1],
                            reverse=True,
                        )[:5]
                    ),
                    "top_locations": dict(
                        sorted(
                            feedback_patterns.get("preferred_locations", {}).items(),
                            key=lambda x: x[1],
                            reverse=True,
                        )[:5]
                    ),
                },
                "recommendations": [],
            }

            # Generate actionable recommendations
            if stats.conversion_rate < 0.1:  # Less than 10% conversion
                insights["recommendations"].append(
                    "Consider updating your profile or preferences to get more relevant recommendations"
                )

            if stats.engagement_rate < 0.3:  # Less than 30% engagement
                insights["recommendations"].append(
                    "Try reviewing recommendations more frequently to improve matching accuracy"
                )

            if stats.feedback_count < 5:
                insights["recommendations"].append(
                    "Provide more feedback on recommendations to improve future suggestions"
                )

            return insights

        except Exception as e:
            logger.error(f"Error getting recommendation insights: {e}")
            raise


# Global service instance
_recommendation_service: Optional[RecommendationService] = None


def get_recommendation_service() -> RecommendationService:
    """
    Get or create global recommendation service instance.

    Returns:
        RecommendationService instance
    """
    global _recommendation_service

    if _recommendation_service is None:
        _recommendation_service = RecommendationService()

    return _recommendation_service
