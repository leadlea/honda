"""
Unit tests for AI utilities and prompt templates.
"""

import json
import pytest
from unittest.mock import Mock, patch, AsyncMock

from src.services.ai_utils import (
    PromptTemplate,
    AIPrompts,
    AIService,
    get_ai_service
)
from src.services.bedrock_client import BedrockResponse


class TestPromptTemplate:
    """Test cases for PromptTemplate class."""
    
    def test_format_with_required_variables(self):
        """Test formatting template with all required variables."""
        template = PromptTemplate(
            template="Hello {name}, you work in {department}",
            required_variables=["name", "department"]
        )
        
        result = template.format(name="John", department="Engineering")
        assert result == "Hello John, you work in Engineering"
    
    def test_format_with_optional_variables(self):
        """Test formatting template with optional variables."""
        template = PromptTemplate(
            template="Hello {name}, you work in {department}. {greeting}",
            required_variables=["name", "department"],
            optional_variables=["greeting"]
        )
        
        result = template.format(
            name="John", 
            department="Engineering", 
            greeting="Welcome!"
        )
        assert result == "Hello John, you work in Engineering. Welcome!"
    
    def test_format_missing_required_variable(self):
        """Test formatting template with missing required variable."""
        template = PromptTemplate(
            template="Hello {name}, you work in {department}",
            required_variables=["name", "department"]
        )
        
        with pytest.raises(ValueError) as exc_info:
            template.format(name="John")
        
        assert "Missing required variables: ['department']" in str(exc_info.value)
    
    def test_format_extra_variables(self):
        """Test formatting template with extra variables."""
        template = PromptTemplate(
            template="Hello {name}",
            required_variables=["name"]
        )
        
        # Should not raise error with extra variables
        result = template.format(name="John", extra="value")
        assert result == "Hello John"


class TestAIPrompts:
    """Test cases for AIPrompts class."""
    
    def test_questionnaire_generation_template(self):
        """Test questionnaire generation template formatting."""
        result = AIPrompts.QUESTIONNAIRE_GENERATION.format(
            name="John Doe",
            department="Engineering",
            years_experience=10,
            current_role="Senior Engineer",
            previous_responses="[]"
        )
        
        assert "John Doe" in result
        assert "Engineering" in result
        assert "10" in result
        assert "Senior Engineer" in result
        assert "questionnaire" in result.lower()
    
    def test_business_title_generation_template(self):
        """Test business title generation template formatting."""
        result = AIPrompts.BUSINESS_TITLE_GENERATION.format(
            name="Jane Smith",
            department="Marketing",
            skills='[{"name": "Digital Marketing", "level": "Expert"}]',
            experience='[{"title": "Marketing Manager", "years": 5}]',
            career_interests='["Leadership", "Strategy"]',
            current_role="Senior Marketing Specialist"
        )
        
        assert "Jane Smith" in result
        assert "Marketing" in result
        assert "Digital Marketing" in result
        assert "business titles" in result.lower()
    
    def test_profile_analysis_template(self):
        """Test profile analysis template formatting."""
        profile_data = {"name": "John", "skills": ["Python", "Leadership"]}
        questionnaire_responses = [{"question": "Q1", "answer": "A1"}]
        
        result = AIPrompts.PROFILE_ANALYSIS.format(
            profile_data=json.dumps(profile_data),
            questionnaire_responses=json.dumps(questionnaire_responses)
        )
        
        assert "Python" in result
        assert "Leadership" in result
        assert "analysis" in result.lower()
    
    def test_opportunity_matching_template(self):
        """Test opportunity matching template formatting."""
        veteran_profile = {"name": "John", "skills": ["Python"]}
        opportunity_details = {"title": "Software Engineer", "requirements": ["Python"]}
        
        result = AIPrompts.OPPORTUNITY_MATCHING.format(
            veteran_profile=json.dumps(veteran_profile),
            opportunity_details=json.dumps(opportunity_details)
        )
        
        assert "Software Engineer" in result
        assert "match" in result.lower()


class TestAIService:
    """Test cases for AIService class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.ai_service = AIService()
    
    @patch('src.services.ai_utils.get_bedrock_client')
    @pytest.mark.asyncio
    async def test_generate_questionnaire_success(self, mock_get_client):
        """Test successful questionnaire generation."""
        # Mock successful response
        mock_response = BedrockResponse(
            content=json.dumps({
                "questionnaire_id": "q123",
                "title": "Test Questionnaire",
                "description": "Test description",
                "questions": [
                    {
                        "id": "q1",
                        "type": "multiple_choice",
                        "question": "What is your primary skill?",
                        "options": ["Python", "Java", "JavaScript"]
                    }
                ]
            }),
            usage={"input_tokens": 100, "output_tokens": 200},
            model="claude-3-5-sonnet",
            stop_reason="end_turn",
            success=True
        )
        
        mock_client = Mock()
        mock_client.invoke_claude = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_client
        
        # Create new AI service instance with mocked client
        ai_service = AIService()
        ai_service.client = mock_client
        
        result = await ai_service.generate_questionnaire(
            name="John Doe",
            department="Engineering",
            years_experience=5,
            current_role="Developer"
        )
        
        assert result["questionnaire_id"] == "q123"
        assert result["title"] == "Test Questionnaire"
        assert len(result["questions"]) == 1
        assert result["questions"][0]["question"] == "What is your primary skill?"
    
    @patch('src.services.ai_utils.get_bedrock_client')
    @pytest.mark.asyncio
    async def test_generate_questionnaire_ai_failure(self, mock_get_client):
        """Test questionnaire generation with AI failure."""
        # Mock failed response
        mock_response = BedrockResponse(
            content="",
            usage={},
            model="claude-3-5-sonnet",
            stop_reason="error",
            success=False,
            error_message="AI service unavailable"
        )
        
        mock_client = Mock()
        mock_client.invoke_claude = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_client
        
        # Create new AI service instance with mocked client
        ai_service = AIService()
        ai_service.client = mock_client
        
        with pytest.raises(Exception) as exc_info:
            await ai_service.generate_questionnaire(
                name="John Doe",
                department="Engineering",
                years_experience=5,
                current_role="Developer"
            )
        
        assert "AI generation failed" in str(exc_info.value)
    
    @patch('src.services.ai_utils.get_bedrock_client')
    @pytest.mark.asyncio
    async def test_generate_questionnaire_invalid_json(self, mock_get_client):
        """Test questionnaire generation with invalid JSON response."""
        # Mock response with invalid JSON
        mock_response = BedrockResponse(
            content="Invalid JSON content",
            usage={"input_tokens": 100, "output_tokens": 50},
            model="claude-3-5-sonnet",
            stop_reason="end_turn",
            success=True
        )
        
        mock_client = Mock()
        mock_client.invoke_claude = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_client
        
        # Create new AI service instance with mocked client
        ai_service = AIService()
        ai_service.client = mock_client
        
        with pytest.raises(Exception) as exc_info:
            await ai_service.generate_questionnaire(
                name="John Doe",
                department="Engineering",
                years_experience=5,
                current_role="Developer"
            )
        
        assert "Failed to generate valid questionnaire format" in str(exc_info.value)
    
    @patch('src.services.ai_utils.get_bedrock_client')
    @pytest.mark.asyncio
    async def test_generate_business_titles_success(self, mock_get_client):
        """Test successful business title generation."""
        # Mock successful response
        mock_response = BedrockResponse(
            content=json.dumps({
                "titles": [
                    {
                        "title": "Senior Software Architect",
                        "description": "Combines technical expertise with leadership",
                        "focus_areas": ["Architecture", "Leadership", "Innovation"],
                        "market_appeal": "high"
                    }
                ],
                "recommended_title": "Senior Software Architect",
                "reasoning": "Best reflects technical and leadership skills"
            }),
            usage={"input_tokens": 150, "output_tokens": 100},
            model="claude-3-5-sonnet",
            stop_reason="end_turn",
            success=True
        )
        
        mock_client = Mock()
        mock_client.invoke_claude = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_client
        
        # Create new AI service instance with mocked client
        ai_service = AIService()
        ai_service.client = mock_client
        
        result = await ai_service.generate_business_titles(
            name="John Doe",
            department="Engineering",
            skills=[{"name": "Python", "level": "Expert"}],
            experience=[{"title": "Senior Developer", "years": 5}],
            career_interests=["Architecture", "Leadership"],
            current_role="Senior Developer"
        )
        
        assert len(result["titles"]) == 1
        assert result["titles"][0]["title"] == "Senior Software Architect"
        assert result["recommended_title"] == "Senior Software Architect"
    
    @patch('src.services.ai_utils.get_bedrock_client')
    @pytest.mark.asyncio
    async def test_analyze_profile_success(self, mock_get_client):
        """Test successful profile analysis."""
        # Mock successful response
        mock_response = BedrockResponse(
            content=json.dumps({
                "strengths": [
                    {
                        "strength": "Technical Leadership",
                        "evidence": "Led multiple development teams",
                        "market_relevance": "high"
                    }
                ],
                "career_paths": [
                    {
                        "path": "Engineering Manager",
                        "probability": "high",
                        "required_development": ["People Management"]
                    }
                ],
                "skill_gaps": [],
                "market_assessment": {
                    "overall_marketability": "high",
                    "unique_value_proposition": "Strong technical and leadership combination",
                    "target_industries": ["Technology", "Finance"]
                },
                "opportunity_types": [
                    {
                        "type": "Leadership Role",
                        "fit_score": 0.9,
                        "reasoning": "Strong leadership background"
                    }
                ]
            }),
            usage={"input_tokens": 200, "output_tokens": 300},
            model="claude-3-5-sonnet",
            stop_reason="end_turn",
            success=True
        )
        
        mock_client = Mock()
        mock_client.invoke_claude = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_client
        
        # Create new AI service instance with mocked client
        ai_service = AIService()
        ai_service.client = mock_client
        
        result = await ai_service.analyze_profile(
            profile_data={"name": "John", "skills": ["Python", "Leadership"]},
            questionnaire_responses=[{"question": "Q1", "answer": "A1"}]
        )
        
        assert len(result["strengths"]) == 1
        assert result["strengths"][0]["strength"] == "Technical Leadership"
        assert result["market_assessment"]["overall_marketability"] == "high"
    
    @patch('src.services.ai_utils.get_bedrock_client')
    @pytest.mark.asyncio
    async def test_match_opportunity_success(self, mock_get_client):
        """Test successful opportunity matching."""
        # Mock successful response
        mock_response = BedrockResponse(
            content=json.dumps({
                "overall_match_score": 0.85,
                "match_analysis": {
                    "skills_alignment": {
                        "score": 0.9,
                        "matching_skills": ["Python", "Leadership"],
                        "missing_skills": ["Kubernetes"],
                        "transferable_skills": ["Project Management"]
                    },
                    "experience_relevance": {
                        "score": 0.8,
                        "relevant_experience": ["Team Leadership", "Software Development"],
                        "experience_gaps": ["Cloud Architecture"]
                    },
                    "career_fit": {
                        "score": 0.85,
                        "alignment_factors": ["Leadership opportunity", "Technical growth"],
                        "potential_concerns": ["Learning curve for new technologies"]
                    },
                    "growth_potential": {
                        "score": 0.9,
                        "development_opportunities": ["Cloud expertise", "Team scaling"]
                    }
                },
                "recommendation": {
                    "action": "strongly_recommend",
                    "reasoning": "Excellent fit with high growth potential",
                    "success_factors": ["Strong technical foundation", "Leadership experience"],
                    "risk_factors": ["Need to learn cloud technologies"]
                },
                "match_summary": "Strong candidate with excellent leadership and technical skills"
            }),
            usage={"input_tokens": 250, "output_tokens": 400},
            model="claude-3-5-sonnet",
            stop_reason="end_turn",
            success=True
        )
        
        mock_client = Mock()
        mock_client.invoke_claude = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_client
        
        # Create new AI service instance with mocked client
        ai_service = AIService()
        ai_service.client = mock_client
        
        result = await ai_service.match_opportunity(
            veteran_profile={"name": "John", "skills": ["Python", "Leadership"]},
            opportunity_details={"title": "Engineering Manager", "requirements": ["Python", "Leadership"]}
        )
        
        assert result["overall_match_score"] == 0.85
        assert result["recommendation"]["action"] == "strongly_recommend"
        assert len(result["match_analysis"]["skills_alignment"]["matching_skills"]) == 2


class TestGlobalFunctions:
    """Test cases for global utility functions."""
    
    def test_get_ai_service_singleton(self):
        """Test that get_ai_service returns singleton."""
        service1 = get_ai_service()
        service2 = get_ai_service()
        
        assert service1 is service2