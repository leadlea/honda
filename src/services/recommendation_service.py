"""
Recommendation service for managing personalized recommendations and feedback.
Builds on the matching engine to provide advanced recommendation features.
"""

import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from ..models.opportunity import Opportunity
from ..models.recommendation import Recommendation
from ..models.veteran_profile import VeteranProfile
from ..repositories.opportunity_repository import OpportunityRepository
from ..repositories.recommendation_repository import RecommendationRepository
from ..repositories.veteran_profile_repository import VeteranProfileRepository
from .matching_engine import MatchingCriteria, get_matching_engine

logger = logging.getLogger(__name__)


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

            # Limit the number of recommendations
            if len(personalized_recommendations) > self.max_recommendations_per_batch:
                personalized_recommendations = personalized_recommendations[
                    : self.max_recommendations_per_batch
                ]

            logger.info(
                f"Generated {len(personalized_recommendations)} personalized recommendations for user {user_id}"
            )
            return personalized_recommendations

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
