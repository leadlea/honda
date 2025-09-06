"""
AI-powered matching engine for veteran talent matching.
Analyzes veteran profiles against opportunities and generates match scores and recommendations.
"""

import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime

from .ai_utils import get_ai_service
from .bedrock_client import BedrockRequest, get_bedrock_client
from ..models.veteran_profile import VeteranProfile
from ..models.opportunity import Opportunity
from ..models.recommendation import Recommendation
from ..repositories.veteran_profile_repository import VeteranProfileRepository
from ..repositories.opportunity_repository import OpportunityRepository
from ..repositories.recommendation_repository import RecommendationRepository


logger = logging.getLogger(__name__)


@dataclass
class MatchResult:
    """Result of matching analysis between a veteran and opportunity."""
    veteran_id: str
    opportunity_id: str
    overall_score: float
    match_reasons: List[Dict[str, Any]]
    recommendation_action: str
    success_factors: List[str]
    risk_factors: List[str]
    match_summary: str


@dataclass
class MatchingCriteria:
    """Criteria for filtering and ranking matches."""
    min_score_threshold: float = 0.3
    max_recommendations_per_user: int = 10
    include_internal_only: bool = False
    include_external_only: bool = False
    preferred_locations: Optional[List[str]] = None
    required_skills: Optional[List[str]] = None
    opportunity_types: Optional[List[str]] = None


class MatchingEngine:
    """
    AI-powered matching engine that analyzes veteran profiles against opportunities
    and generates intelligent recommendations with explanations.
    """
    
    def __init__(self):
        self.ai_service = get_ai_service()
        self.bedrock_client = get_bedrock_client()
        self.veteran_repo = VeteranProfileRepository()
        self.opportunity_repo = OpportunityRepository()
        self.recommendation_repo = RecommendationRepository()
    
    async def analyze_match(
        self,
        veteran_profile: VeteranProfile,
        opportunity: Opportunity
    ) -> MatchResult:
        """
        Analyze how well a veteran profile matches an opportunity using AI.
        
        Args:
            veteran_profile: The veteran's profile data
            opportunity: The opportunity to match against
            
        Returns:
            MatchResult with detailed analysis
        """
        try:
            # Prepare data for AI analysis
            veteran_data = {
                "user_id": veteran_profile.user_id,
                "business_title": veteran_profile.business_title,
                "skills": veteran_profile.skills,
                "experiences": veteran_profile.experiences,
                "preferences": veteran_profile.preferences,
                "questionnaire_responses": veteran_profile.questionnaire_responses
            }
            
            opportunity_data = {
                "opportunity_id": opportunity.opportunity_id,
                "title": opportunity.title,
                "description": opportunity.description,
                "required_skills": opportunity.required_skills,
                "location": opportunity.location,
                "type": opportunity.type,
                "source": opportunity.source,
                "company": opportunity.company,
                "salary_range": opportunity.salary_range
            }
            
            # Use AI service to analyze the match
            match_analysis = await self.ai_service.match_opportunity(
                veteran_profile=veteran_data,
                opportunity_details=opportunity_data
            )
            
            # Extract match reasons with proper structure
            match_reasons = []
            if "match_analysis" in match_analysis:
                analysis = match_analysis["match_analysis"]
                
                # Skills alignment
                if "skills_alignment" in analysis:
                    skills_data = analysis["skills_alignment"]
                    match_reasons.append({
                        "category": "skills_alignment",
                        "description": f"Skills match score: {skills_data.get('score', 0):.2f}",
                        "weight": skills_data.get("score", 0) * 0.4,  # 40% weight for skills
                        "details": {
                            "matching_skills": skills_data.get("matching_skills", []),
                            "missing_skills": skills_data.get("missing_skills", []),
                            "transferable_skills": skills_data.get("transferable_skills", [])
                        }
                    })
                
                # Experience relevance
                if "experience_relevance" in analysis:
                    exp_data = analysis["experience_relevance"]
                    match_reasons.append({
                        "category": "experience_relevance",
                        "description": f"Experience relevance: {exp_data.get('score', 0):.2f}",
                        "weight": exp_data.get("score", 0) * 0.3,  # 30% weight for experience
                        "details": {
                            "relevant_experience": exp_data.get("relevant_experience", []),
                            "experience_gaps": exp_data.get("experience_gaps", [])
                        }
                    })
                
                # Career fit
                if "career_fit" in analysis:
                    career_data = analysis["career_fit"]
                    match_reasons.append({
                        "category": "career_fit",
                        "description": f"Career alignment: {career_data.get('score', 0):.2f}",
                        "weight": career_data.get("score", 0) * 0.2,  # 20% weight for career fit
                        "details": {
                            "alignment_factors": career_data.get("alignment_factors", []),
                            "potential_concerns": career_data.get("potential_concerns", [])
                        }
                    })
                
                # Growth potential
                if "growth_potential" in analysis:
                    growth_data = analysis["growth_potential"]
                    match_reasons.append({
                        "category": "growth_potential",
                        "description": f"Growth opportunities: {growth_data.get('score', 0):.2f}",
                        "weight": growth_data.get("score", 0) * 0.1,  # 10% weight for growth
                        "details": {
                            "development_opportunities": growth_data.get("development_opportunities", [])
                        }
                    })
            
            # Extract recommendation details
            recommendation = match_analysis.get("recommendation", {})
            
            return MatchResult(
                veteran_id=veteran_profile.user_id,
                opportunity_id=opportunity.opportunity_id,
                overall_score=match_analysis.get("overall_match_score", 0.0),
                match_reasons=match_reasons,
                recommendation_action=recommendation.get("action", "not_recommend"),
                success_factors=recommendation.get("success_factors", []),
                risk_factors=recommendation.get("risk_factors", []),
                match_summary=match_analysis.get("match_summary", "No summary available")
            )
            
        except Exception as e:
            logger.error(f"Error analyzing match for veteran {veteran_profile.user_id} and opportunity {opportunity.opportunity_id}: {e}")
            # Return a default low-score match result on error
            return MatchResult(
                veteran_id=veteran_profile.user_id,
                opportunity_id=opportunity.opportunity_id,
                overall_score=0.0,
                match_reasons=[{
                    "category": "error",
                    "description": f"Analysis failed: {str(e)}",
                    "weight": 0.0,
                    "details": {}
                }],
                recommendation_action="not_recommend",
                success_factors=[],
                risk_factors=["Analysis error occurred"],
                match_summary="Unable to analyze match due to technical error"
            )
    
    async def generate_recommendations_for_veteran(
        self,
        user_id: str,
        criteria: Optional[MatchingCriteria] = None
    ) -> List[Recommendation]:
        """
        Generate personalized recommendations for a veteran based on their profile.
        
        Args:
            user_id: The veteran's user ID
            criteria: Optional criteria for filtering opportunities
            
        Returns:
            List of Recommendation objects sorted by match score
        """
        try:
            # Get veteran profile
            veteran_profile = self.veteran_repo.get_profile(user_id)
            if not veteran_profile:
                raise ValueError(f"Veteran profile not found for user {user_id}")
            
            # Get available opportunities
            opportunities = await self._get_filtered_opportunities(criteria)
            
            if not opportunities:
                logger.warning(f"No opportunities found for matching criteria")
                return []
            
            # Analyze matches for all opportunities
            match_results = []
            for opportunity in opportunities:
                try:
                    match_result = await self.analyze_match(veteran_profile, opportunity)
                    match_results.append(match_result)
                except Exception as e:
                    logger.warning(f"Failed to analyze match for opportunity {opportunity.opportunity_id}: {e}")
                    continue
            
            # Filter by minimum score threshold
            min_threshold = criteria.min_score_threshold if criteria else 0.3
            qualified_matches = [
                match for match in match_results 
                if match.overall_score >= min_threshold
            ]
            
            # Sort by match score (highest first)
            qualified_matches.sort(key=lambda x: x.overall_score, reverse=True)
            
            # Limit number of recommendations
            max_recommendations = criteria.max_recommendations_per_user if criteria else 10
            top_matches = qualified_matches[:max_recommendations]
            
            # Convert to Recommendation objects
            recommendations = []
            for match in top_matches:
                recommendation = Recommendation(
                    user_id=user_id,
                    opportunity_id=match.opportunity_id,
                    match_score=match.overall_score,
                    match_reasons=match.match_reasons,
                    status="generated"
                )
                recommendations.append(recommendation)
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating recommendations for veteran {user_id}: {e}")
            raise
    
    async def _get_filtered_opportunities(
        self,
        criteria: Optional[MatchingCriteria] = None
    ) -> List[Opportunity]:
        """
        Get opportunities filtered by the given criteria.
        
        Args:
            criteria: Optional filtering criteria
            
        Returns:
            List of filtered opportunities
        """
        try:
            # Start with all active opportunities
            opportunities = self.opportunity_repo.get_active_opportunities()
            
            if not criteria:
                return opportunities
            
            filtered_opportunities = []
            
            for opportunity in opportunities:
                # Filter by source (internal/external)
                if criteria.include_internal_only and opportunity.source != "internal":
                    continue
                if criteria.include_external_only and opportunity.source != "external":
                    continue
                
                # Filter by opportunity types
                if criteria.opportunity_types and opportunity.type not in criteria.opportunity_types:
                    continue
                
                # Filter by location (if specified)
                if criteria.preferred_locations:
                    location_match = any(
                        loc.lower() in opportunity.location.lower() 
                        for loc in criteria.preferred_locations
                    )
                    if not location_match:
                        continue
                
                # Filter by required skills (if specified)
                if criteria.required_skills:
                    skill_match = any(
                        skill.lower() in [req_skill.lower() for req_skill in opportunity.required_skills]
                        for skill in criteria.required_skills
                    )
                    if not skill_match:
                        continue
                
                filtered_opportunities.append(opportunity)
            
            return filtered_opportunities
            
        except Exception as e:
            logger.error(f"Error filtering opportunities: {e}")
            raise
    
    async def batch_generate_recommendations(
        self,
        user_ids: List[str],
        criteria: Optional[MatchingCriteria] = None
    ) -> Dict[str, List[Recommendation]]:
        """
        Generate recommendations for multiple veterans in batch.
        
        Args:
            user_ids: List of veteran user IDs
            criteria: Optional criteria for filtering opportunities
            
        Returns:
            Dictionary mapping user_id to list of recommendations
        """
        try:
            results = {}
            
            for user_id in user_ids:
                try:
                    recommendations = await self.generate_recommendations_for_veteran(
                        user_id, criteria
                    )
                    results[user_id] = recommendations
                    logger.info(f"Generated {len(recommendations)} recommendations for user {user_id}")
                except Exception as e:
                    logger.error(f"Failed to generate recommendations for user {user_id}: {e}")
                    results[user_id] = []
            
            return results
            
        except Exception as e:
            logger.error(f"Error in batch recommendation generation: {e}")
            raise
    
    async def save_recommendations(
        self,
        recommendations: List[Recommendation]
    ) -> bool:
        """
        Save recommendations to the database.
        
        Args:
            recommendations: List of recommendations to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not recommendations:
                return True
            
            return self.recommendation_repo.batch_create_recommendations(recommendations)
            
        except Exception as e:
            logger.error(f"Error saving recommendations: {e}")
            raise
    
    async def refresh_recommendations_for_veteran(
        self,
        user_id: str,
        criteria: Optional[MatchingCriteria] = None
    ) -> List[Recommendation]:
        """
        Refresh recommendations for a veteran by generating new ones and saving them.
        
        Args:
            user_id: The veteran's user ID
            criteria: Optional criteria for filtering opportunities
            
        Returns:
            List of newly generated recommendations
        """
        try:
            # Generate new recommendations
            new_recommendations = await self.generate_recommendations_for_veteran(
                user_id, criteria
            )
            
            if new_recommendations:
                # Save to database
                await self.save_recommendations(new_recommendations)
                logger.info(f"Refreshed {len(new_recommendations)} recommendations for user {user_id}")
            
            return new_recommendations
            
        except Exception as e:
            logger.error(f"Error refreshing recommendations for user {user_id}: {e}")
            raise
    
    def calculate_match_score_breakdown(
        self,
        match_reasons: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """
        Calculate a breakdown of match scores by category.
        
        Args:
            match_reasons: List of match reason dictionaries
            
        Returns:
            Dictionary with score breakdown by category
        """
        breakdown = {}
        
        for reason in match_reasons:
            category = reason.get("category", "unknown")
            weight = reason.get("weight", 0.0)
            breakdown[category] = weight
        
        return breakdown
    
    async def get_match_explanation(
        self,
        user_id: str,
        opportunity_id: str
    ) -> Dict[str, Any]:
        """
        Get detailed explanation for why a specific opportunity was recommended.
        
        Args:
            user_id: The veteran's user ID
            opportunity_id: The opportunity ID
            
        Returns:
            Detailed match explanation
        """
        try:
            # Get the recommendation
            recommendation = self.recommendation_repo.get_recommendation(user_id, opportunity_id)
            if not recommendation:
                raise ValueError(f"Recommendation not found for user {user_id} and opportunity {opportunity_id}")
            
            # Get the veteran profile and opportunity for additional context
            veteran_profile = self.veteran_repo.get_profile(user_id)
            opportunity = self.opportunity_repo.get_opportunity(opportunity_id)
            
            if not veteran_profile or not opportunity:
                raise ValueError("Profile or opportunity not found")
            
            # Calculate score breakdown
            score_breakdown = self.calculate_match_score_breakdown(recommendation.match_reasons)
            
            return {
                "overall_score": recommendation.match_score,
                "score_breakdown": score_breakdown,
                "match_reasons": recommendation.match_reasons,
                "veteran_profile": {
                    "business_title": veteran_profile.business_title,
                    "key_skills": [skill.get("name") for skill in veteran_profile.skills[:5]],
                    "experience_years": sum(exp.get("duration", 0) for exp in veteran_profile.experiences)
                },
                "opportunity": {
                    "title": opportunity.title,
                    "company": opportunity.company,
                    "type": opportunity.type,
                    "required_skills": opportunity.required_skills
                },
                "recommendation_status": recommendation.status,
                "generated_at": recommendation.generated_at
            }
            
        except Exception as e:
            logger.error(f"Error getting match explanation: {e}")
            raise


# Global matching engine instance
_matching_engine: Optional[MatchingEngine] = None


def get_matching_engine() -> MatchingEngine:
    """
    Get or create global matching engine instance.
    
    Returns:
        MatchingEngine instance
    """
    global _matching_engine
    
    if _matching_engine is None:
        _matching_engine = MatchingEngine()
    
    return _matching_engine