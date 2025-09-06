"""
Unit tests for the recommendation service.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from src.services.recommendation_service import (
    RecommendationService, RecommendationFeedback, RecommendationStats,
    get_recommendation_service
)
from src.models.recommendation import Recommendation
from src.models.opportunity import Opportunity
from src.services.matching_engine import MatchingCriteria


class TestRecommendationService:
    """Test cases for RecommendationService class."""
    
    @pytest.fixture
    def recommendation_service(self):
        """Create a recommendation service instance for testing."""
        service = RecommendationService()
        # Mock the dependencies
        service.matching_engine = Mock()
        service.recommendation_repo = Mock()
        service.veteran_repo = Mock()
        service.opportunity_repo = Mock()
        return service
    
    @pytest.fixture
    def sample_recommendations(self):
        """Create sample recommendations for testing."""
        return [
            Recommendation(
                user_id="user123",
                recommendation_id="rec1",
                opportunity_id="opp1",
                match_score=0.85,
                status="generated"
            ),
            Recommendation(
                user_id="user123",
                recommendation_id="rec2",
                opportunity_id="opp2",
                match_score=0.75,
                status="viewed"
            ),
            Recommendation(
                user_id="user123",
                recommendation_id="rec3",
                opportunity_id="opp3",
                match_score=0.65,
                status="applied"
            )
        ]
    
    @pytest.fixture
    def sample_opportunity(self):
        """Create a sample opportunity for testing."""
        return Opportunity(
            opportunity_id="opp1",
            title="Software Engineer",
            company="Honda",
            type="internal_transfer",
            location="Tokyo"
        )
    
    @pytest.mark.asyncio
    async def test_generate_personalized_recommendations_no_duplicates(
        self, recommendation_service, sample_recommendations
    ):
        """Test generating personalized recommendations without duplicates."""
        # Mock matching engine response
        recommendation_service.matching_engine.generate_recommendations_for_veteran = AsyncMock(
            return_value=sample_recommendations
        )
        
        # Mock no existing recommendations (no duplicates)
        recommendation_service.recommendation_repo.get_user_recommendations.return_value = []
        
        # Mock personalization (no adjustment)
        recommendation_service._get_user_feedback_patterns = AsyncMock(return_value={})
        
        # Generate recommendations
        result = await recommendation_service.generate_personalized_recommendations("user123")
        
        # Verify
        assert len(result) == 3
        assert all(isinstance(rec, Recommendation) for rec in result)
        recommendation_service.matching_engine.generate_recommendations_for_veteran.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_personalized_recommendations_with_duplicates(
        self, recommendation_service, sample_recommendations
    ):
        """Test generating personalized recommendations with duplicate prevention."""
        # Mock matching engine response
        recommendation_service.matching_engine.generate_recommendations_for_veteran = AsyncMock(
            return_value=sample_recommendations
        )
        
        # Mock existing recommendations (opp1 already recommended)
        existing_rec = Recommendation(
            user_id="user123",
            opportunity_id="opp1",
            match_score=0.8,
            generated_at=(datetime.utcnow() - timedelta(days=5)).isoformat()
        )
        recommendation_service.recommendation_repo.get_user_recommendations.return_value = [existing_rec]
        
        # Mock personalization
        recommendation_service._get_user_feedback_patterns = AsyncMock(return_value={})
        
        # Generate recommendations
        result = await recommendation_service.generate_personalized_recommendations("user123")
        
        # Verify duplicate was filtered out
        assert len(result) == 2  # opp1 should be filtered out
        opportunity_ids = [rec.opportunity_id for rec in result]
        assert "opp1" not in opportunity_ids
        assert "opp2" in opportunity_ids
        assert "opp3" in opportunity_ids
    
    @pytest.mark.asyncio
    async def test_apply_personalization(self, recommendation_service, sample_recommendations):
        """Test applying personalization based on user feedback."""
        # Mock feedback patterns showing preference for internal transfers
        feedback_patterns = {
            "preferred_opportunity_types": {"internal_transfer": 5, "external_position": 1},
            "preferred_companies": {"Honda": 3},
            "preferred_locations": {"Tokyo": 4},
            "dismissed_patterns": {"consulting": 2},
            "average_applied_score": 0.8,
            "average_dismissed_score": 0.4
        }
        
        # Mock the _get_user_feedback_patterns method
        recommendation_service._get_user_feedback_patterns = AsyncMock(return_value=feedback_patterns)
        
        # Mock opportunity details
        opportunity = Opportunity(
            opportunity_id="opp1",
            type="internal_transfer",
            company="Honda",
            location="Tokyo"
        )
        recommendation_service.opportunity_repo.get_opportunity.return_value = opportunity
        
        # Apply personalization
        result = await recommendation_service._apply_personalization("user123", sample_recommendations[:1])
        
        # Verify personalization was applied
        assert len(result) == 1
        rec = result[0]
        assert rec.match_score > 0.85  # Should be boosted
        
        # Check if personalization reason was added
        personalization_reasons = [
            reason for reason in rec.match_reasons 
            if reason.get("category") == "personalization"
        ]
        assert len(personalization_reasons) > 0
    
    @pytest.mark.asyncio
    async def test_record_recommendation_feedback(self, recommendation_service, sample_opportunity):
        """Test recording recommendation feedback."""
        # Create sample recommendation
        recommendation = Recommendation(
            user_id="user123",
            recommendation_id="rec1",
            opportunity_id="opp1",
            match_score=0.85,
            status="generated"
        )
        
        # Mock repository responses
        recommendation_service.recommendation_repo.get_recommendation.return_value = recommendation
        recommendation_service.recommendation_repo.update_recommendation.return_value = True
        
        # Create feedback
        feedback = RecommendationFeedback(
            recommendation_id="rec1",
            user_id="user123",
            feedback_type="positive",
            feedback_score=4.0,
            feedback_comment="Great match!"
        )
        
        # Record feedback
        result = await recommendation_service.record_recommendation_feedback(feedback)
        
        # Verify
        assert result is True
        assert recommendation.status == "viewed"  # Should be marked as viewed
        
        # Check if feedback was added to match_reasons
        feedback_reasons = [
            reason for reason in recommendation.match_reasons 
            if reason.get("category") == "user_feedback"
        ]
        assert len(feedback_reasons) == 1
        assert feedback_reasons[0]["details"]["feedback_type"] == "positive"
        assert feedback_reasons[0]["details"]["feedback_score"] == 4.0
    
    @pytest.mark.asyncio
    async def test_record_feedback_applied(self, recommendation_service):
        """Test recording applied feedback."""
        # Create sample recommendation
        recommendation = Recommendation(
            user_id="user123",
            recommendation_id="rec1",
            opportunity_id="opp1",
            match_score=0.85,
            status="generated"
        )
        
        # Mock repository responses
        recommendation_service.recommendation_repo.get_recommendation.return_value = recommendation
        recommendation_service.recommendation_repo.update_recommendation.return_value = True
        
        # Create applied feedback
        feedback = RecommendationFeedback(
            recommendation_id="rec1",
            user_id="user123",
            feedback_type="applied"
        )
        
        # Record feedback
        result = await recommendation_service.record_recommendation_feedback(feedback)
        
        # Verify
        assert result is True
        assert recommendation.status == "applied"
        assert recommendation.applied_at is not None
    
    @pytest.mark.asyncio
    async def test_get_recommendation_statistics(self, recommendation_service):
        """Test getting recommendation statistics."""
        # Create sample recommendations with different statuses
        recommendations = [
            Recommendation(user_id="user123", opportunity_id="opp1", match_score=0.9, status="applied"),
            Recommendation(user_id="user123", opportunity_id="opp2", match_score=0.8, status="viewed"),
            Recommendation(user_id="user123", opportunity_id="opp3", match_score=0.7, status="dismissed"),
            Recommendation(user_id="user123", opportunity_id="opp4", match_score=0.6, status="generated")
        ]
        
        # Add feedback to one recommendation
        recommendations[0].match_reasons.append({
            "category": "user_feedback",
            "details": {"feedback_score": 5.0}
        })
        
        # Mock repository response
        recommendation_service.recommendation_repo.get_user_recommendations.return_value = recommendations
        
        # Get statistics
        stats = await recommendation_service.get_recommendation_statistics("user123")
        
        # Verify statistics
        assert isinstance(stats, RecommendationStats)
        assert stats.total_recommendations == 4
        assert stats.viewed_count == 3  # viewed, applied, dismissed
        assert stats.applied_count == 1
        assert stats.dismissed_count == 1
        assert stats.average_match_score == 0.75  # (0.9 + 0.8 + 0.7 + 0.6) / 4
        assert stats.feedback_count == 1
        assert stats.average_feedback_score == 5.0
        assert stats.conversion_rate == 0.25  # 1/4
        assert stats.engagement_rate == 0.75  # 3/4
    
    @pytest.mark.asyncio
    async def test_get_recommendation_history(self, recommendation_service, sample_recommendations):
        """Test getting recommendation history with opportunity details."""
        # Mock repository responses
        recommendation_service.recommendation_repo.get_user_recommendations.return_value = sample_recommendations
        
        # Mock opportunity details
        opportunity = Opportunity(
            opportunity_id="opp1",
            title="Software Engineer",
            company="Honda",
            type="internal_transfer",
            location="Tokyo"
        )
        recommendation_service.opportunity_repo.get_opportunity.return_value = opportunity
        
        # Get history
        history = await recommendation_service.get_recommendation_history("user123")
        
        # Verify
        assert len(history) == 3
        assert all("opportunity" in item for item in history)
        assert history[0]["opportunity"]["title"] == "Software Engineer"
        assert history[0]["opportunity"]["company"] == "Honda"
    
    @pytest.mark.asyncio
    async def test_refresh_recommendations_with_feedback_learning(self, recommendation_service):
        """Test refreshing recommendations with feedback learning."""
        # Mock generate_personalized_recommendations
        new_recommendations = [
            Recommendation(user_id="user123", opportunity_id="opp_new", match_score=0.9)
        ]
        recommendation_service.generate_personalized_recommendations = AsyncMock(
            return_value=new_recommendations
        )
        
        # Mock save_recommendations
        recommendation_service.matching_engine.save_recommendations = AsyncMock(return_value=True)
        
        # Refresh recommendations
        result = await recommendation_service.refresh_recommendations_with_feedback_learning("user123")
        
        # Verify
        assert result == new_recommendations
        recommendation_service.generate_personalized_recommendations.assert_called_once_with(
            "user123", None, prevent_duplicates=True
        )
        recommendation_service.matching_engine.save_recommendations.assert_called_once_with(
            new_recommendations
        )
    
    @pytest.mark.asyncio
    async def test_get_recommendation_insights(self, recommendation_service):
        """Test getting recommendation insights."""
        # Mock statistics
        stats = RecommendationStats(
            total_recommendations=10,
            viewed_count=6,
            applied_count=2,
            dismissed_count=1,
            average_match_score=0.75,
            feedback_count=3,
            average_feedback_score=4.2
        )
        recommendation_service.get_recommendation_statistics = AsyncMock(return_value=stats)
        
        # Mock feedback patterns
        feedback_patterns = {
            "preferred_opportunity_types": {"internal_transfer": 5, "external_position": 2},
            "preferred_companies": {"Honda": 4, "Toyota": 1},
            "preferred_locations": {"Tokyo": 3, "Osaka": 2}
        }
        recommendation_service._get_user_feedback_patterns = AsyncMock(return_value=feedback_patterns)
        
        # Get insights
        insights = await recommendation_service.get_recommendation_insights("user123")
        
        # Verify
        assert "statistics" in insights
        assert "preferences" in insights
        assert "recommendations" in insights
        
        # Check preferences
        assert insights["preferences"]["top_opportunity_types"]["internal_transfer"] == 5
        assert insights["preferences"]["top_companies"]["Honda"] == 4
        assert insights["preferences"]["top_locations"]["Tokyo"] == 3
        
        # Should have actionable recommendations since conversion rate is 20% (2/10)
        assert len(insights["recommendations"]) > 0


class TestRecommendationFeedback:
    """Test cases for RecommendationFeedback class."""
    
    def test_feedback_creation(self):
        """Test creating recommendation feedback."""
        feedback = RecommendationFeedback(
            recommendation_id="rec123",
            user_id="user123",
            feedback_type="positive",
            feedback_score=4.5,
            feedback_comment="Great recommendation!"
        )
        
        assert feedback.recommendation_id == "rec123"
        assert feedback.user_id == "user123"
        assert feedback.feedback_type == "positive"
        assert feedback.feedback_score == 4.5
        assert feedback.feedback_comment == "Great recommendation!"
        assert feedback.created_at is not None
    
    def test_feedback_auto_timestamp(self):
        """Test automatic timestamp creation."""
        feedback = RecommendationFeedback(
            recommendation_id="rec123",
            user_id="user123",
            feedback_type="negative"
        )
        
        # Should have created_at timestamp
        assert feedback.created_at is not None
        
        # Should be recent (within last minute)
        created_time = datetime.fromisoformat(feedback.created_at.replace('Z', '+00:00'))
        now = datetime.utcnow()
        time_diff = now - created_time.replace(tzinfo=None)
        assert time_diff.total_seconds() < 60


class TestRecommendationStats:
    """Test cases for RecommendationStats class."""
    
    def test_stats_calculation(self):
        """Test recommendation statistics calculation."""
        stats = RecommendationStats(
            total_recommendations=10,
            viewed_count=7,
            applied_count=3,
            dismissed_count=2,
            average_match_score=0.75,
            feedback_count=5,
            average_feedback_score=4.2
        )
        
        assert stats.conversion_rate == 0.3  # 3/10
        assert stats.engagement_rate == 0.7  # 7/10
    
    def test_stats_zero_division(self):
        """Test statistics with zero recommendations."""
        stats = RecommendationStats(
            total_recommendations=0,
            viewed_count=0,
            applied_count=0,
            dismissed_count=0,
            average_match_score=0.0,
            feedback_count=0
        )
        
        assert stats.conversion_rate == 0.0
        assert stats.engagement_rate == 0.0


def test_get_recommendation_service():
    """Test getting global recommendation service instance."""
    service1 = get_recommendation_service()
    service2 = get_recommendation_service()
    
    # Should return the same instance (singleton pattern)
    assert service1 is service2
    assert isinstance(service1, RecommendationService)


if __name__ == '__main__':
    pytest.main([__file__])