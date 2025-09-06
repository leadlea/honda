"""
Unit tests for Public Search Handler
"""

import json
from unittest.mock import Mock, patch

from src.handlers.public_search_handler import PublicSearchHandler


class TestPublicSearchHandler:
    def setup_method(self):
        """Set up test fixtures"""
        self.handler = PublicSearchHandler()

        # Mock profile data
        self.mock_profile = {
            "profile_id": "profile_123",
            "user_id": "user_123",
            "display_name": "John Doe",
            "business_title": "Senior Software Engineer",
            "summary": "Experienced software engineer with cloud expertise",
            "skills": [
                {"name": "Python", "level": "Expert", "years": 8},
                {"name": "AWS", "level": "Advanced", "years": 5},
            ],
            "experiences": [
                {
                    "title": "Senior Engineer",
                    "department": "Engineering",
                    "duration": 5,
                    "achievements": ["Led team of 5 developers"],
                }
            ],
            "certifications": ["AWS Solutions Architect"],
            "achievements": ["Led team of 5 developers"],
            "experience_years": 8,
            "location": "Tokyo, Japan",
            "availability": "available",
            "preferred_roles": ["Technical Lead", "Architect"],
            "work_style": "Remote",
            "contact_preferences": {"allow_contact": True},
            "is_active": True,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
            "last_updated": "2024-01-01T00:00:00",
        }

    @patch("src.handlers.public_search_handler.PublicProfileRepository")
    def test_search_veterans_success(self, mock_repo_class):
        """Test successful veteran search"""
        # Setup
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        mock_repo.search_public_profiles.return_value = [self.mock_profile]

        event = {
            "queryStringParameters": {
                "skills": "Python,AWS",
                "location": "Tokyo",
                "page": "1",
                "limit": "20",
            }
        }

        # Execute
        handler = PublicSearchHandler()
        result = handler.search_veterans(event, {})

        # Verify
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert "veterans" in body
        assert body["total_count"] == 1
        assert body["page"] == 1
        assert body["limit"] == 20

        # Verify CORS headers
        assert "Access-Control-Allow-Origin" in result["headers"]

        # Verify repository was called with correct filters
        expected_filters = {"skills": ["Python", "AWS"], "location": "Tokyo"}
        mock_repo.search_public_profiles.assert_called_once_with(expected_filters)

    @patch("src.handlers.public_search_handler.PublicProfileRepository")
    def test_search_veterans_no_results(self, mock_repo_class):
        """Test search with no results"""
        # Setup
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        mock_repo.search_public_profiles.return_value = []

        event = {"queryStringParameters": {"skills": "NonexistentSkill"}}

        # Execute
        handler = PublicSearchHandler()
        result = handler.search_veterans(event, {})

        # Verify
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["veterans"] == []
        assert body["total_count"] == 0
        assert "No veterans found" in body["message"]

    @patch("src.handlers.public_search_handler.BedrockClient")
    @patch("src.handlers.public_search_handler.PublicProfileRepository")
    def test_search_veterans_with_ai_ranking(self, mock_repo_class, mock_bedrock_class):
        """Test search with AI ranking"""
        # Setup
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        mock_repo.search_public_profiles.return_value = [self.mock_profile]

        mock_bedrock = Mock()
        mock_bedrock_class.return_value = mock_bedrock
        mock_bedrock.generate_text.return_value = "profile_123"

        event = {"queryStringParameters": {"q": "Python developer", "skills": "Python"}}

        # Execute
        handler = PublicSearchHandler()
        result = handler.search_veterans(event, {})

        # Verify
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert len(body["veterans"]) == 1

        # Verify AI ranking was called
        mock_bedrock.generate_text.assert_called_once()

    @patch("src.handlers.public_search_handler.PublicProfileRepository")
    def test_get_veteran_profile_success(self, mock_repo_class):
        """Test successful profile retrieval"""
        # Setup
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        mock_repo.get_public_profile.return_value = self.mock_profile

        event = {"pathParameters": {"profileId": "profile_123"}}

        # Execute
        handler = PublicSearchHandler()
        result = handler.get_veteran_profile(event, {})

        # Verify
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert "veteran" in body
        assert body["veteran"]["profile_id"] == "profile_123"

        mock_repo.get_public_profile.assert_called_once_with("profile_123")

    @patch("src.handlers.public_search_handler.PublicProfileRepository")
    def test_get_veteran_profile_not_found(self, mock_repo_class):
        """Test profile not found"""
        # Setup
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        mock_repo.get_public_profile.return_value = None

        event = {"pathParameters": {"profileId": "nonexistent"}}

        # Execute
        handler = PublicSearchHandler()
        result = handler.get_veteran_profile(event, {})

        # Verify
        assert result["statusCode"] == 404
        body = json.loads(result["body"])
        assert "Profile not found" in body["error"]

    @patch("src.handlers.public_search_handler.PublicProfileRepository")
    def test_get_search_categories_success(self, mock_repo_class):
        """Test successful categories retrieval"""
        # Setup
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        mock_categories = {
            "skills": ["Python", "AWS", "Java"],
            "departments": ["Engineering", "Sales"],
            "locations": ["Tokyo", "Osaka"],
            "availability_options": ["available", "limited"],
            "experience_levels": ["junior", "mid", "senior", "expert"],
        }
        mock_repo.get_available_categories.return_value = mock_categories

        event = {}

        # Execute
        handler = PublicSearchHandler()
        result = handler.get_search_categories(event, {})

        # Verify
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert "categories" in body
        assert body["categories"] == mock_categories

    def test_extract_search_filters(self):
        """Test filter extraction from query parameters"""
        query_params = {
            "skills": "Python,AWS,Java",
            "experience_level": "senior",
            "department": "Engineering",
            "location": "Tokyo",
            "availability": "available",
            "min_years": "5",
            "max_years": "15",
        }

        filters = self.handler._extract_search_filters(query_params)

        assert filters["skills"] == ["Python", "AWS", "Java"]
        assert filters["experience_level"] == "senior"
        assert filters["department"] == "Engineering"
        assert filters["location"] == "Tokyo"
        assert filters["availability"] == "available"
        assert filters["min_years"] == 5
        assert filters["max_years"] == 15

    def test_extract_search_filters_invalid_numbers(self):
        """Test filter extraction with invalid numbers"""
        query_params = {"min_years": "invalid", "max_years": "also_invalid"}

        filters = self.handler._extract_search_filters(query_params)

        # Invalid numbers should be ignored
        assert "min_years" not in filters
        assert "max_years" not in filters

    def test_format_public_profile(self):
        """Test public profile formatting"""
        formatted = self.handler._format_public_profile(self.mock_profile)

        assert formatted["profile_id"] == "profile_123"
        assert formatted["business_title"] == "Senior Software Engineer"
        assert len(formatted["skills"]) <= 10  # Should limit to top 10
        assert formatted["experience_years"] == 5  # Based on experiences duration
        assert "Engineering" in formatted["departments"]
        assert formatted["location"] == "Tokyo, Japan"
        assert formatted["availability"] == "available"

    def test_format_detailed_profile(self):
        """Test detailed profile formatting"""
        formatted = self.handler._format_detailed_profile(self.mock_profile)

        assert formatted["profile_id"] == "profile_123"
        assert formatted["business_title"] == "Senior Software Engineer"
        assert formatted["skills"] == self.mock_profile["skills"]
        assert formatted["experiences"] == self.mock_profile["experiences"]
        assert formatted["certifications"] == self.mock_profile["certifications"]
        assert formatted["achievements"] == self.mock_profile["achievements"]

    def test_paginate_results(self):
        """Test result pagination"""
        profiles = [{"id": i} for i in range(25)]  # 25 profiles

        # First page
        page1 = self.handler._paginate_results(profiles, 1, 10)
        assert len(page1) == 10
        assert page1[0]["id"] == 0
        assert page1[9]["id"] == 9

        # Second page
        page2 = self.handler._paginate_results(profiles, 2, 10)
        assert len(page2) == 10
        assert page2[0]["id"] == 10
        assert page2[9]["id"] == 19

        # Third page (partial)
        page3 = self.handler._paginate_results(profiles, 3, 10)
        assert len(page3) == 5
        assert page3[0]["id"] == 20
        assert page3[4]["id"] == 24

    def test_get_experience_summary(self):
        """Test experience summary generation"""
        profile = {
            "experiences": [
                {"department": "Engineering", "duration": 5},
                {"department": "Sales", "duration": 3},
                {"department": "Engineering", "duration": 2},
            ]
        }

        summary = self.handler._get_experience_summary(profile)

        assert "10 years" in summary
        assert "Engineering" in summary
        assert "Sales" in summary

    def test_get_experience_summary_no_experience(self):
        """Test experience summary with no experience"""
        profile = {"experiences": []}

        summary = self.handler._get_experience_summary(profile)

        assert summary == "No experience listed"

    def test_create_ranking_prompt(self):
        """Test AI ranking prompt creation"""
        profiles = [
            {
                "profile_id": "profile_1",
                "business_title": "Senior Engineer",
                "skills": ["Python", "AWS"],
                "experience_summary": "5 years in Engineering",
                "departments": ["Engineering"],
            }
        ]

        prompt = self.handler._create_ranking_prompt(profiles, "Python developer")

        assert "Python developer" in prompt
        assert "profile_1" in prompt
        assert "Senior Engineer" in prompt
        assert "Python, AWS" in prompt

    def test_parse_ranking_response(self):
        """Test parsing AI ranking response"""
        # Test successful parsing
        response = "profile_1, profile_3, profile_2"
        result = self.handler._parse_ranking_response(response)
        assert result == ["profile_1", "profile_3", "profile_2"]

        # Test with extra text
        response = (
            "Here are the rankings:\nprofile_2, profile_1\nThese are the best matches."
        )
        result = self.handler._parse_ranking_response(response)
        assert result == ["profile_2", "profile_1"]

        # Test with no valid profile IDs
        response = "No valid profiles found"
        result = self.handler._parse_ranking_response(response)
        assert result == []

    def test_get_cors_headers(self):
        """Test CORS headers"""
        headers = self.handler._get_cors_headers()

        assert headers["Content-Type"] == "application/json"
        assert headers["Access-Control-Allow-Origin"] == "*"
        assert "Access-Control-Allow-Headers" in headers
        assert "Access-Control-Allow-Methods" in headers

    @patch("src.handlers.public_search_handler.PublicProfileRepository")
    def test_search_veterans_error_handling(self, mock_repo_class):
        """Test error handling in search"""
        # Setup
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        mock_repo.search_public_profiles.side_effect = Exception("Database error")

        event = {"queryStringParameters": {}}

        # Execute
        handler = PublicSearchHandler()
        result = handler.search_veterans(event, {})

        # Verify
        assert result["statusCode"] == 500
        body = json.loads(result["body"])
        assert "Internal server error" in body["error"]

    @patch("src.handlers.public_search_handler.PublicProfileRepository")
    def test_get_veteran_profile_error_handling(self, mock_repo_class):
        """Test error handling in profile retrieval"""
        # Setup
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        mock_repo.get_public_profile.side_effect = Exception("Database error")

        event = {"pathParameters": {"profileId": "profile_123"}}

        # Execute
        handler = PublicSearchHandler()
        result = handler.get_veteran_profile(event, {})

        # Verify
        assert result["statusCode"] == 500
        body = json.loads(result["body"])
        assert "Internal server error" in body["error"]


# Test Lambda function handlers
class TestLambdaHandlers:
    @patch("src.handlers.public_search_handler.PublicSearchHandler")
    def test_search_veterans_lambda(self, mock_handler_class):
        """Test search veterans Lambda handler"""
        from src.handlers.public_search_handler import search_veterans

        mock_handler = Mock()
        mock_handler_class.return_value = mock_handler
        mock_handler.search_veterans.return_value = {"statusCode": 200}

        event = {}
        context = {}

        result = search_veterans(event, context)

        assert result["statusCode"] == 200
        mock_handler.search_veterans.assert_called_once_with(event, context)

    @patch("src.handlers.public_search_handler.PublicSearchHandler")
    def test_get_veteran_profile_lambda(self, mock_handler_class):
        """Test get veteran profile Lambda handler"""
        from src.handlers.public_search_handler import get_veteran_profile

        mock_handler = Mock()
        mock_handler_class.return_value = mock_handler
        mock_handler.get_veteran_profile.return_value = {"statusCode": 200}

        event = {}
        context = {}

        result = get_veteran_profile(event, context)

        assert result["statusCode"] == 200
        mock_handler.get_veteran_profile.assert_called_once_with(event, context)

    @patch("src.handlers.public_search_handler.PublicSearchHandler")
    def test_get_search_categories_lambda(self, mock_handler_class):
        """Test get search categories Lambda handler"""
        from src.handlers.public_search_handler import get_search_categories

        mock_handler = Mock()
        mock_handler_class.return_value = mock_handler
        mock_handler.get_search_categories.return_value = {"statusCode": 200}

        event = {}
        context = {}

        result = get_search_categories(event, context)

        assert result["statusCode"] == 200
        mock_handler.get_search_categories.assert_called_once_with(event, context)
