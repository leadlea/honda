"""
Unit tests for the matching engine service.
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.models.opportunity import Opportunity
from src.models.recommendation import Recommendation
from src.models.veteran_profile import VeteranProfile
from src.services.matching_engine import (
    MatchingCriteria,
    MatchingEngine,
    MatchResult,
    get_matching_engine,
)


class TestMatchingEngine:
    """Test cases for MatchingEngine class."""

    @pytest.fixture
    def matching_engine(self):
        """Create a matching engine instance for testing."""
        engine = MatchingEngine()
        # Mock the repositories and services
        engine.ai_service = Mock()
        engine.bedrock_client = Mock()
        engine.veteran_repo = Mock()
        engine.opportunity_repo = Mock()
        engine.recommendation_repo = Mock()
        return engine

    @pytest.fixture
    def sample_veteran_profile(self):
        """Create a sample veteran profile for testing."""
        return VeteranProfile(
            user_id="veteran123",
            business_title="Senior Software Engineer",
            skills=[
                {"name": "Python", "level": "Expert", "years": 8, "certifications": []},
                {
                    "name": "AWS",
                    "level": "Advanced",
                    "years": 5,
                    "certifications": ["AWS Solutions Architect"],
                },
                {
                    "name": "Machine Learning",
                    "level": "Intermediate",
                    "years": 3,
                    "certifications": [],
                },
            ],
            experiences=[
                {
                    "title": "Senior Software Engineer",
                    "department": "Engineering",
                    "duration": 36,
                    "achievements": [
                        "Led team of 5 developers",
                        "Reduced deployment time by 50%",
                    ],
                },
                {
                    "title": "Software Engineer",
                    "department": "Engineering",
                    "duration": 24,
                    "achievements": [
                        "Implemented CI/CD pipeline",
                        "Mentored junior developers",
                    ],
                },
            ],
            preferences={
                "preferred_roles": [
                    "Technical Lead",
                    "Engineering Manager",
                    "Solutions Architect",
                ],
                "work_style": "hybrid",
                "locations": ["Tokyo", "Remote"],
            },
            questionnaire_responses=[
                {
                    "question": "Leadership experience",
                    "answer": "5+ years managing teams",
                },
                {
                    "question": "Career goals",
                    "answer": "Transition to technical leadership role",
                },
            ],
        )

    @pytest.fixture
    def sample_opportunity(self):
        """Create a sample opportunity for testing."""
        return Opportunity(
            opportunity_id="opp123",
            title="Technical Lead - Cloud Platform",
            description="Lead a team of engineers building cloud infrastructure solutions",
            required_skills=["Python", "AWS", "Leadership", "Kubernetes"],
            location="Tokyo",
            type="internal_transfer",
            source="internal",
            company="Honda",
            salary_range={"min": 8000000, "max": 12000000, "currency": "JPY"},
            is_active=True,
        )

    @pytest.fixture
    def sample_ai_match_response(self):
        """Create a sample AI match analysis response."""
        return {
            "overall_match_score": 0.85,
            "match_analysis": {
                "skills_alignment": {
                    "score": 0.9,
                    "matching_skills": ["Python", "AWS"],
                    "missing_skills": ["Kubernetes"],
                    "transferable_skills": ["Leadership"],
                },
                "experience_relevance": {
                    "score": 0.8,
                    "relevant_experience": [
                        "Senior Software Engineer",
                        "Team Leadership",
                    ],
                    "experience_gaps": ["Kubernetes management"],
                },
                "career_fit": {
                    "score": 0.85,
                    "alignment_factors": [
                        "Leadership aspirations",
                        "Technical background",
                    ],
                    "potential_concerns": ["New to Kubernetes"],
                },
                "growth_potential": {
                    "score": 0.9,
                    "development_opportunities": [
                        "Technical leadership",
                        "Cloud architecture",
                    ],
                },
            },
            "recommendation": {
                "action": "strongly_recommend",
                "reasoning": "Excellent match for technical leadership transition",
                "success_factors": [
                    "Strong technical background",
                    "Leadership experience",
                ],
                "risk_factors": ["Kubernetes learning curve"],
            },
            "match_summary": "Strong candidate for technical lead role with excellent growth potential",
        }

    @pytest.mark.asyncio
    async def test_analyze_match_success(
        self,
        matching_engine,
        sample_veteran_profile,
        sample_opportunity,
        sample_ai_match_response,
    ):
        """Test successful match analysis."""
        # Mock AI service response
        matching_engine.ai_service.match_opportunity = AsyncMock(
            return_value=sample_ai_match_response
        )

        # Perform match analysis
        result = await matching_engine.analyze_match(
            sample_veteran_profile, sample_opportunity
        )

        # Verify result
        assert isinstance(result, MatchResult)
        assert result.veteran_id == "veteran123"
        assert result.opportunity_id == "opp123"
        assert result.overall_score == 0.85
        assert result.recommendation_action == "strongly_recommend"
        assert len(result.match_reasons) == 4  # skills, experience, career, growth
        assert "Strong candidate for technical lead role" in result.match_summary

        # Verify AI service was called correctly
        matching_engine.ai_service.match_opportunity.assert_called_once()
        call_args = matching_engine.ai_service.match_opportunity.call_args[1]
        assert call_args["veteran_profile"]["user_id"] == "veteran123"
        assert call_args["opportunity_details"]["opportunity_id"] == "opp123"

    @pytest.mark.asyncio
    async def test_analyze_match_ai_failure(
        self, matching_engine, sample_veteran_profile, sample_opportunity
    ):
        """Test match analysis when AI service fails."""
        # Mock AI service to raise exception
        matching_engine.ai_service.match_opportunity = AsyncMock(
            side_effect=Exception("AI service unavailable")
        )

        # Perform match analysis
        result = await matching_engine.analyze_match(
            sample_veteran_profile, sample_opportunity
        )

        # Verify error handling
        assert isinstance(result, MatchResult)
        assert result.overall_score == 0.0
        assert result.recommendation_action == "not_recommend"
        assert len(result.match_reasons) == 1
        assert result.match_reasons[0]["category"] == "error"
        assert "Analysis failed" in result.match_reasons[0]["description"]

    @pytest.mark.asyncio
    async def test_generate_recommendations_for_veteran(
        self, matching_engine, sample_veteran_profile, sample_opportunity
    ):
        """Test generating recommendations for a veteran."""
        # Mock repository responses
        matching_engine.veteran_repo.get_profile.return_value = sample_veteran_profile
        matching_engine.opportunity_repo.get_active_opportunities.return_value = [
            sample_opportunity
        ]

        # Mock AI service response
        matching_engine.ai_service.match_opportunity = AsyncMock(
            return_value={
                "overall_match_score": 0.75,
                "match_analysis": {
                    "skills_alignment": {"score": 0.8},
                    "experience_relevance": {"score": 0.7},
                    "career_fit": {"score": 0.8},
                    "growth_potential": {"score": 0.7},
                },
                "recommendation": {
                    "action": "recommend",
                    "reasoning": "Good match",
                    "success_factors": ["Technical skills"],
                    "risk_factors": [],
                },
                "match_summary": "Good match for the role",
            }
        )

        # Generate recommendations
        recommendations = await matching_engine.generate_recommendations_for_veteran(
            "veteran123"
        )

        # Verify results
        assert len(recommendations) == 1
        assert isinstance(recommendations[0], Recommendation)
        assert recommendations[0].user_id == "veteran123"
        assert recommendations[0].opportunity_id == "opp123"
        assert recommendations[0].match_score == 0.75
        assert recommendations[0].status == "generated"

    @pytest.mark.asyncio
    async def test_generate_recommendations_with_criteria(
        self, matching_engine, sample_veteran_profile
    ):
        """Test generating recommendations with filtering criteria."""
        # Create multiple opportunities
        opportunities = [
            Opportunity(
                opportunity_id="opp1",
                title="Internal Role",
                source="internal",
                type="internal_transfer",
                location="Tokyo",
                required_skills=["Python"],
                is_active=True,
            ),
            Opportunity(
                opportunity_id="opp2",
                title="External Role",
                source="external",
                type="external_position",
                location="Osaka",
                required_skills=["Java"],
                is_active=True,
            ),
        ]

        # Mock repository responses
        matching_engine.veteran_repo.get_profile.return_value = sample_veteran_profile
        matching_engine.opportunity_repo.get_active_opportunities.return_value = (
            opportunities
        )

        # Mock AI service to return different scores
        def mock_ai_response(*args, **kwargs):
            opp_id = kwargs["opportunity_details"]["opportunity_id"]
            score = 0.8 if opp_id == "opp1" else 0.4
            return {
                "overall_match_score": score,
                "match_analysis": {},
                "recommendation": {"action": "recommend"},
                "match_summary": f"Match for {opp_id}",
            }

        matching_engine.ai_service.match_opportunity = AsyncMock(
            side_effect=mock_ai_response
        )

        # Test with criteria for internal only
        criteria = MatchingCriteria(include_internal_only=True, min_score_threshold=0.5)

        recommendations = await matching_engine.generate_recommendations_for_veteran(
            "veteran123", criteria
        )

        # Should only get internal opportunity
        assert len(recommendations) == 1
        assert recommendations[0].opportunity_id == "opp1"

    @pytest.mark.asyncio
    async def test_batch_generate_recommendations(self, matching_engine):
        """Test batch recommendation generation."""
        user_ids = ["user1", "user2"]

        # Mock individual recommendation generation
        async def mock_generate_recommendations(user_id, criteria=None):
            return [
                Recommendation(user_id=user_id, opportunity_id="opp1", match_score=0.8)
            ]

        matching_engine.generate_recommendations_for_veteran = AsyncMock(
            side_effect=mock_generate_recommendations
        )

        # Generate batch recommendations
        results = await matching_engine.batch_generate_recommendations(user_ids)

        # Verify results
        assert len(results) == 2
        assert "user1" in results
        assert "user2" in results
        assert len(results["user1"]) == 1
        assert len(results["user2"]) == 1

    @pytest.mark.asyncio
    async def test_save_recommendations(self, matching_engine):
        """Test saving recommendations to database."""
        recommendations = [
            Recommendation(user_id="user1", opportunity_id="opp1", match_score=0.8),
            Recommendation(user_id="user2", opportunity_id="opp2", match_score=0.7),
        ]

        # Mock repository response
        matching_engine.recommendation_repo.batch_create_recommendations.return_value = (
            True
        )

        # Save recommendations
        result = await matching_engine.save_recommendations(recommendations)

        # Verify
        assert result is True
        matching_engine.recommendation_repo.batch_create_recommendations.assert_called_once_with(
            recommendations
        )

    @pytest.mark.asyncio
    async def test_refresh_recommendations_for_veteran(self, matching_engine):
        """Test refreshing recommendations for a veteran."""
        # Mock generate and save methods
        mock_recommendations = [
            Recommendation(user_id="veteran123", opportunity_id="opp1", match_score=0.8)
        ]

        matching_engine.generate_recommendations_for_veteran = AsyncMock(
            return_value=mock_recommendations
        )
        matching_engine.save_recommendations = AsyncMock(return_value=True)

        # Refresh recommendations
        result = await matching_engine.refresh_recommendations_for_veteran("veteran123")

        # Verify
        assert result == mock_recommendations
        matching_engine.generate_recommendations_for_veteran.assert_called_once_with(
            "veteran123", None
        )
        matching_engine.save_recommendations.assert_called_once_with(
            mock_recommendations
        )

    def test_calculate_match_score_breakdown(self, matching_engine):
        """Test calculating match score breakdown by category."""
        match_reasons = [
            {"category": "skills_alignment", "weight": 0.4},
            {"category": "experience_relevance", "weight": 0.3},
            {"category": "career_fit", "weight": 0.2},
            {"category": "growth_potential", "weight": 0.1},
        ]

        breakdown = matching_engine.calculate_match_score_breakdown(match_reasons)

        assert breakdown["skills_alignment"] == 0.4
        assert breakdown["experience_relevance"] == 0.3
        assert breakdown["career_fit"] == 0.2
        assert breakdown["growth_potential"] == 0.1

    @pytest.mark.asyncio
    async def test_get_match_explanation(
        self, matching_engine, sample_veteran_profile, sample_opportunity
    ):
        """Test getting detailed match explanation."""
        # Create sample recommendation
        recommendation = Recommendation(
            user_id="veteran123",
            recommendation_id="rec123",
            opportunity_id="opp123",
            match_score=0.85,
            match_reasons=[
                {"category": "skills_alignment", "weight": 0.4},
                {"category": "experience_relevance", "weight": 0.3},
            ],
        )

        # Mock repository responses
        matching_engine.recommendation_repo.get_recommendation.return_value = (
            recommendation
        )
        matching_engine.veteran_repo.get_profile.return_value = sample_veteran_profile
        matching_engine.opportunity_repo.get_opportunity.return_value = (
            sample_opportunity
        )

        # Get match explanation
        explanation = await matching_engine.get_match_explanation(
            "veteran123", "opp123"
        )

        # Verify explanation structure
        assert explanation["overall_score"] == 0.85
        assert "score_breakdown" in explanation
        assert "match_reasons" in explanation
        assert "veteran_profile" in explanation
        assert "opportunity" in explanation
        assert (
            explanation["veteran_profile"]["business_title"]
            == "Senior Software Engineer"
        )
        assert explanation["opportunity"]["title"] == "Technical Lead - Cloud Platform"


class TestMatchingCriteria:
    """Test cases for MatchingCriteria class."""

    def test_default_criteria(self):
        """Test default matching criteria values."""
        criteria = MatchingCriteria()

        assert criteria.min_score_threshold == 0.3
        assert criteria.max_recommendations_per_user == 10
        assert criteria.include_internal_only is False
        assert criteria.include_external_only is False
        assert criteria.preferred_locations is None
        assert criteria.required_skills is None
        assert criteria.opportunity_types is None

    def test_custom_criteria(self):
        """Test custom matching criteria values."""
        criteria = MatchingCriteria(
            min_score_threshold=0.5,
            max_recommendations_per_user=5,
            include_internal_only=True,
            preferred_locations=["Tokyo", "Osaka"],
            required_skills=["Python", "AWS"],
            opportunity_types=["internal_transfer"],
        )

        assert criteria.min_score_threshold == 0.5
        assert criteria.max_recommendations_per_user == 5
        assert criteria.include_internal_only is True
        assert criteria.preferred_locations == ["Tokyo", "Osaka"]
        assert criteria.required_skills == ["Python", "AWS"]
        assert criteria.opportunity_types == ["internal_transfer"]


class TestMatchResult:
    """Test cases for MatchResult class."""

    def test_match_result_creation(self):
        """Test creating a MatchResult instance."""
        result = MatchResult(
            veteran_id="veteran123",
            opportunity_id="opp123",
            overall_score=0.85,
            match_reasons=[{"category": "skills", "weight": 0.4}],
            recommendation_action="recommend",
            success_factors=["Technical skills"],
            risk_factors=["Learning curve"],
            match_summary="Good match",
        )

        assert result.veteran_id == "veteran123"
        assert result.opportunity_id == "opp123"
        assert result.overall_score == 0.85
        assert len(result.match_reasons) == 1
        assert result.recommendation_action == "recommend"
        assert result.success_factors == ["Technical skills"]
        assert result.risk_factors == ["Learning curve"]
        assert result.match_summary == "Good match"


def test_get_matching_engine():
    """Test getting global matching engine instance."""
    engine1 = get_matching_engine()
    engine2 = get_matching_engine()

    # Should return the same instance (singleton pattern)
    assert engine1 is engine2
    assert isinstance(engine1, MatchingEngine)


if __name__ == "__main__":
    pytest.main([__file__])
