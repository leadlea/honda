"""
Unit tests for the matching handler Lambda function.
"""

import pytest
import json
from unittest.mock import Mock, patch, AsyncMock

from src.handlers.matching_handler import (
    lambda_handler, handle_get_recommendations, handle_generate_recommendations,
    handle_get_match_analysis, handle_analyze_match, handle_batch_generate_recommendations
)
from src.models.recommendation import Recommendation
from src.services.matching_engine import MatchResult


class TestMatchingHandler:
    """Test cases for matching handler functions."""
    
    @pytest.fixture
    def mock_event_base(self):
        """Base event structure for testing."""
        return {
            'httpMethod': 'GET',
            'path': '/recommendations/veteran123',
            'headers': {
                'Authorization': 'Bearer valid_token'
            },
            'pathParameters': {
                'user_id': 'veteran123'
            },
            'queryStringParameters': None
        }
    
    @pytest.fixture
    def mock_context(self):
        """Mock Lambda context."""
        return Mock()
    
    @pytest.fixture
    def mock_user_data(self):
        """Mock user data from JWT token."""
        return {
            'user_id': 'veteran123',
            'role': 'veteran',
            'email': 'veteran@honda.com'
        }
    
    def test_lambda_handler_routing_get_recommendations(self, mock_event_base, mock_context):
        """Test Lambda handler routing to get recommendations."""
        with patch('src.handlers.matching_handler.handle_get_recommendations') as mock_handler:
            mock_handler.return_value = {'statusCode': 200, 'body': '{}'}
            
            result = lambda_handler(mock_event_base, mock_context)
            
            mock_handler.assert_called_once_with(mock_event_base, mock_context)
            assert result['statusCode'] == 200
    
    def test_lambda_handler_routing_generate_recommendations(self, mock_context):
        """Test Lambda handler routing to generate recommendations."""
        event = {
            'httpMethod': 'POST',
            'path': '/recommendations/veteran123/generate',
            'headers': {'Authorization': 'Bearer token'},
            'pathParameters': {'user_id': 'veteran123'}
        }
        
        with patch('src.handlers.matching_handler.handle_generate_recommendations') as mock_handler:
            mock_handler.return_value = {'statusCode': 201, 'body': '{}'}
            
            result = lambda_handler(event, mock_context)
            
            mock_handler.assert_called_once_with(event, mock_context)
            assert result['statusCode'] == 201
    
    def test_lambda_handler_routing_match_analysis(self, mock_context):
        """Test Lambda handler routing to match analysis."""
        event = {
            'httpMethod': 'GET',
            'path': '/match-analysis/veteran123/opp123',
            'headers': {'Authorization': 'Bearer token'},
            'pathParameters': {'user_id': 'veteran123', 'opportunity_id': 'opp123'}
        }
        
        with patch('src.handlers.matching_handler.handle_get_match_analysis') as mock_handler:
            mock_handler.return_value = {'statusCode': 200, 'body': '{}'}
            
            result = lambda_handler(event, mock_context)
            
            mock_handler.assert_called_once_with(event, mock_context)
            assert result['statusCode'] == 200
    
    def test_lambda_handler_unknown_endpoint(self, mock_context):
        """Test Lambda handler with unknown endpoint."""
        event = {
            'httpMethod': 'GET',
            'path': '/unknown/endpoint',
            'headers': {}
        }
        
        result = lambda_handler(event, mock_context)
        
        assert result['statusCode'] == 404
        body = json.loads(result['body'])
        assert 'Endpoint not found' in body['error']
    
    def test_lambda_handler_exception_handling(self, mock_context):
        """Test Lambda handler exception handling."""
        event = {
            'httpMethod': 'GET',
            'path': '/recommendations/veteran123'
        }
        
        with patch('src.handlers.matching_handler.handle_get_recommendations') as mock_handler:
            mock_handler.side_effect = Exception("Test error")
            
            result = lambda_handler(event, mock_context)
            
            assert result['statusCode'] == 500
            body = json.loads(result['body'])
            assert 'Internal server error' in body['error']


class TestGetRecommendations:
    """Test cases for get recommendations handler."""
    
    @pytest.fixture
    def mock_recommendations(self):
        """Mock recommendation objects."""
        return [
            Recommendation(
                user_id="veteran123",
                recommendation_id="rec1",
                opportunity_id="opp1",
                match_score=0.85,
                match_reasons=[{"category": "skills", "weight": 0.4}],
                status="generated"
            ),
            Recommendation(
                user_id="veteran123",
                recommendation_id="rec2",
                opportunity_id="opp2",
                match_score=0.75,
                match_reasons=[{"category": "experience", "weight": 0.3}],
                status="viewed"
            )
        ]
    
    @patch('src.handlers.matching_handler.verify_jwt_token')
    @patch('src.handlers.matching_handler.require_permission')
    @patch('src.handlers.matching_handler.get_matching_engine')
    def test_get_recommendations_success(self, mock_get_engine, mock_require_permission, 
                                       mock_verify_token, mock_recommendations):
        """Test successful get recommendations."""
        # Setup mocks
        mock_verify_token.return_value = {'user_id': 'veteran123', 'role': 'veteran'}
        mock_require_permission.return_value = True
        
        mock_engine = Mock()
        mock_engine.recommendation_repo.get_user_recommendations.return_value = mock_recommendations
        mock_get_engine.return_value = mock_engine
        
        # Create event
        event = {
            'headers': {'Authorization': 'Bearer valid_token'},
            'pathParameters': {'user_id': 'veteran123'},
            'queryStringParameters': None
        }
        
        # Call handler
        result = handle_get_recommendations(event, Mock())
        
        # Verify response
        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        assert 'recommendations' in body
        assert len(body['recommendations']) == 2
        assert body['count'] == 2
        
        # Verify recommendation data
        rec_data = body['recommendations'][0]
        assert rec_data['recommendation_id'] == 'rec1'
        assert rec_data['opportunity_id'] == 'opp1'
        assert rec_data['match_score'] == 0.85
        assert rec_data['status'] == 'generated'
    
    @patch('src.handlers.matching_handler.verify_jwt_token')
    def test_get_recommendations_no_token(self, mock_verify_token):
        """Test get recommendations without authorization token."""
        event = {
            'headers': {},
            'pathParameters': {'user_id': 'veteran123'}
        }
        
        result = handle_get_recommendations(event, Mock())
        
        assert result['statusCode'] == 401
        body = json.loads(result['body'])
        assert 'Authorization token required' in body['error']
    
    @patch('src.handlers.matching_handler.verify_jwt_token')
    def test_get_recommendations_invalid_token(self, mock_verify_token):
        """Test get recommendations with invalid token."""
        mock_verify_token.return_value = None
        
        event = {
            'headers': {'Authorization': 'Bearer invalid_token'},
            'pathParameters': {'user_id': 'veteran123'}
        }
        
        result = handle_get_recommendations(event, Mock())
        
        assert result['statusCode'] == 401
        body = json.loads(result['body'])
        assert 'Invalid or expired token' in body['error']
    
    @patch('src.handlers.matching_handler.verify_jwt_token')
    @patch('src.handlers.matching_handler.require_permission')
    def test_get_recommendations_insufficient_permissions(self, mock_require_permission, 
                                                        mock_verify_token):
        """Test get recommendations with insufficient permissions."""
        mock_verify_token.return_value = {'user_id': 'veteran123', 'role': 'veteran'}
        mock_require_permission.return_value = False
        
        event = {
            'headers': {'Authorization': 'Bearer valid_token'},
            'pathParameters': {'user_id': 'veteran123'}
        }
        
        result = handle_get_recommendations(event, Mock())
        
        assert result['statusCode'] == 403
        body = json.loads(result['body'])
        assert 'Insufficient permissions' in body['error']
    
    @patch('src.handlers.matching_handler.verify_jwt_token')
    @patch('src.handlers.matching_handler.require_permission')
    def test_get_recommendations_missing_user_id(self, mock_require_permission, 
                                                mock_verify_token):
        """Test get recommendations without user_id parameter."""
        mock_verify_token.return_value = {'user_id': 'veteran123', 'role': 'veteran'}
        mock_require_permission.return_value = True
        
        event = {
            'headers': {'Authorization': 'Bearer valid_token'},
            'pathParameters': {}
        }
        
        result = handle_get_recommendations(event, Mock())
        
        assert result['statusCode'] == 400
        body = json.loads(result['body'])
        assert 'user_id is required' in body['error']


class TestGenerateRecommendations:
    """Test cases for generate recommendations handler."""
    
    @patch('src.handlers.matching_handler.verify_jwt_token')
    @patch('src.handlers.matching_handler.require_permission')
    @patch('src.handlers.matching_handler.get_matching_engine')
    @patch('src.handlers.matching_handler.asyncio')
    def test_generate_recommendations_success(self, mock_asyncio, mock_get_engine, 
                                            mock_require_permission, mock_verify_token):
        """Test successful recommendation generation."""
        # Setup mocks
        mock_verify_token.return_value = {'user_id': 'veteran123', 'role': 'veteran'}
        mock_require_permission.return_value = True
        
        mock_recommendations = [
            Recommendation(
                user_id="veteran123",
                recommendation_id="rec1",
                opportunity_id="opp1",
                match_score=0.85
            )
        ]
        
        mock_engine = Mock()
        mock_engine.refresh_recommendations_for_veteran = AsyncMock(
            return_value=mock_recommendations
        )
        mock_get_engine.return_value = mock_engine
        
        # Mock asyncio event loop
        mock_loop = Mock()
        mock_loop.run_until_complete.return_value = mock_recommendations
        mock_asyncio.new_event_loop.return_value = mock_loop
        mock_asyncio.set_event_loop = Mock()
        
        # Create event
        event = {
            'headers': {'Authorization': 'Bearer valid_token'},
            'pathParameters': {'user_id': 'veteran123'},
            'body': json.dumps({
                'min_score_threshold': 0.5,
                'max_recommendations': 5
            })
        }
        
        # Call handler
        result = handle_generate_recommendations(event, Mock())
        
        # Verify response
        assert result['statusCode'] == 201
        body = json.loads(result['body'])
        assert 'Recommendations generated successfully' in body['message']
        assert 'recommendations' in body
        assert body['count'] == 1
    
    @patch('src.handlers.matching_handler.verify_jwt_token')
    @patch('src.handlers.matching_handler.require_permission')
    @patch('src.handlers.matching_handler.get_matching_engine')
    @patch('src.handlers.matching_handler.asyncio')
    def test_generate_recommendations_with_criteria(self, mock_asyncio, mock_get_engine, 
                                                  mock_require_permission, mock_verify_token):
        """Test recommendation generation with custom criteria."""
        # Setup mocks
        mock_verify_token.return_value = {'user_id': 'veteran123', 'role': 'veteran'}
        mock_require_permission.return_value = True
        
        mock_engine = Mock()
        mock_engine.refresh_recommendations_for_veteran = AsyncMock(return_value=[])
        mock_get_engine.return_value = mock_engine
        
        # Mock asyncio
        mock_loop = Mock()
        mock_loop.run_until_complete.return_value = []
        mock_asyncio.new_event_loop.return_value = mock_loop
        mock_asyncio.set_event_loop = Mock()
        
        # Create event with criteria
        event = {
            'headers': {'Authorization': 'Bearer valid_token'},
            'pathParameters': {'user_id': 'veteran123'},
            'body': json.dumps({
                'min_score_threshold': 0.7,
                'max_recommendations': 3,
                'include_internal_only': True,
                'preferred_locations': ['Tokyo'],
                'required_skills': ['Python', 'AWS']
            })
        }
        
        # Call handler
        result = handle_generate_recommendations(event, Mock())
        
        # Verify response
        assert result['statusCode'] == 201
        
        # Verify criteria was passed correctly
        mock_engine.refresh_recommendations_for_veteran.assert_called_once()
        call_args = mock_engine.refresh_recommendations_for_veteran.call_args
        criteria = call_args[0][1]  # Second argument is criteria
        assert criteria.min_score_threshold == 0.7
        assert criteria.max_recommendations_per_user == 3
        assert criteria.include_internal_only is True
        assert criteria.preferred_locations == ['Tokyo']
        assert criteria.required_skills == ['Python', 'AWS']


class TestMatchAnalysis:
    """Test cases for match analysis handlers."""
    
    @patch('src.handlers.matching_handler.verify_jwt_token')
    @patch('src.handlers.matching_handler.require_permission')
    @patch('src.handlers.matching_handler.get_matching_engine')
    @patch('src.handlers.matching_handler.asyncio')
    def test_get_match_analysis_success(self, mock_asyncio, mock_get_engine, 
                                      mock_require_permission, mock_verify_token):
        """Test successful match analysis retrieval."""
        # Setup mocks
        mock_verify_token.return_value = {'user_id': 'veteran123', 'role': 'veteran'}
        mock_require_permission.return_value = True
        
        mock_explanation = {
            'overall_score': 0.85,
            'score_breakdown': {'skills': 0.4, 'experience': 0.3},
            'match_reasons': [{'category': 'skills', 'weight': 0.4}],
            'veteran_profile': {'business_title': 'Senior Engineer'},
            'opportunity': {'title': 'Tech Lead'}
        }
        
        mock_engine = Mock()
        mock_engine.get_match_explanation = AsyncMock(return_value=mock_explanation)
        mock_get_engine.return_value = mock_engine
        
        # Mock asyncio
        mock_loop = Mock()
        mock_loop.run_until_complete.return_value = mock_explanation
        mock_asyncio.new_event_loop.return_value = mock_loop
        mock_asyncio.set_event_loop = Mock()
        
        # Create event
        event = {
            'headers': {'Authorization': 'Bearer valid_token'},
            'pathParameters': {'user_id': 'veteran123', 'opportunity_id': 'opp123'}
        }
        
        # Call handler
        result = handle_get_match_analysis(event, Mock())
        
        # Verify response
        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        assert body['overall_score'] == 0.85
        assert 'score_breakdown' in body
        assert 'match_reasons' in body
    
    @patch('src.handlers.matching_handler.verify_jwt_token')
    @patch('src.handlers.matching_handler.require_permission')
    @patch('src.handlers.matching_handler.get_matching_engine')
    @patch('src.handlers.matching_handler.asyncio')
    def test_analyze_match_success(self, mock_asyncio, mock_get_engine, 
                                 mock_require_permission, mock_verify_token):
        """Test successful match analysis."""
        # Setup mocks
        mock_verify_token.return_value = {'user_id': 'admin123', 'role': 'admin'}
        mock_require_permission.return_value = True
        
        mock_match_result = MatchResult(
            veteran_id="veteran123",
            opportunity_id="opp123",
            overall_score=0.85,
            match_reasons=[{'category': 'skills', 'weight': 0.4}],
            recommendation_action="recommend",
            success_factors=["Technical skills"],
            risk_factors=["Learning curve"],
            match_summary="Good match"
        )
        
        mock_engine = Mock()
        mock_engine.veteran_repo.get_profile.return_value = Mock()  # Mock profile
        mock_engine.opportunity_repo.get_opportunity.return_value = Mock()  # Mock opportunity
        mock_engine.analyze_match = AsyncMock(return_value=mock_match_result)
        mock_get_engine.return_value = mock_engine
        
        # Mock asyncio
        mock_loop = Mock()
        mock_loop.run_until_complete.return_value = mock_match_result
        mock_asyncio.new_event_loop.return_value = mock_loop
        mock_asyncio.set_event_loop = Mock()
        
        # Create event
        event = {
            'headers': {'Authorization': 'Bearer valid_token'},
            'body': json.dumps({
                'user_id': 'veteran123',
                'opportunity_id': 'opp123'
            })
        }
        
        # Call handler
        result = handle_analyze_match(event, Mock())
        
        # Verify response
        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        assert body['veteran_id'] == 'veteran123'
        assert body['opportunity_id'] == 'opp123'
        assert body['overall_score'] == 0.85
        assert body['recommendation_action'] == 'recommend'
    
    @patch('src.handlers.matching_handler.verify_jwt_token')
    @patch('src.handlers.matching_handler.require_permission')
    @patch('src.handlers.matching_handler.get_matching_engine')
    def test_analyze_match_profile_not_found(self, mock_get_engine, 
                                           mock_require_permission, mock_verify_token):
        """Test match analysis when profile is not found."""
        # Setup mocks
        mock_verify_token.return_value = {'user_id': 'admin123', 'role': 'admin'}
        mock_require_permission.return_value = True
        
        mock_engine = Mock()
        mock_engine.veteran_repo.get_profile.return_value = None  # Profile not found
        mock_get_engine.return_value = mock_engine
        
        # Create event
        event = {
            'headers': {'Authorization': 'Bearer valid_token'},
            'body': json.dumps({
                'user_id': 'veteran123',
                'opportunity_id': 'opp123'
            })
        }
        
        # Call handler
        result = handle_analyze_match(event, Mock())
        
        # Verify response
        assert result['statusCode'] == 404
        body = json.loads(result['body'])
        assert 'Veteran profile not found' in body['error']


class TestBatchRecommendations:
    """Test cases for batch recommendation generation."""
    
    @patch('src.handlers.matching_handler.verify_jwt_token')
    @patch('src.handlers.matching_handler.require_permission')
    @patch('src.handlers.matching_handler.get_matching_engine')
    @patch('src.handlers.matching_handler.asyncio')
    def test_batch_generate_recommendations_success(self, mock_asyncio, mock_get_engine, 
                                                  mock_require_permission, mock_verify_token):
        """Test successful batch recommendation generation."""
        # Setup mocks
        mock_verify_token.return_value = {'user_id': 'admin123', 'role': 'admin'}
        mock_require_permission.return_value = True
        
        mock_batch_results = {
            'user1': [Recommendation(user_id='user1', opportunity_id='opp1', match_score=0.8)],
            'user2': [Recommendation(user_id='user2', opportunity_id='opp2', match_score=0.7)]
        }
        
        mock_engine = Mock()
        mock_engine.batch_generate_recommendations = AsyncMock(return_value=mock_batch_results)
        mock_engine.save_recommendations = AsyncMock(return_value=True)
        mock_get_engine.return_value = mock_engine
        
        # Mock asyncio
        mock_loop = Mock()
        mock_loop.run_until_complete.side_effect = [mock_batch_results, True]
        mock_asyncio.new_event_loop.return_value = mock_loop
        mock_asyncio.set_event_loop = Mock()
        
        # Create event
        event = {
            'headers': {'Authorization': 'Bearer valid_token'},
            'body': json.dumps({
                'user_ids': ['user1', 'user2'],
                'criteria': {
                    'min_score_threshold': 0.5,
                    'max_recommendations': 5
                }
            })
        }
        
        # Call handler
        result = handle_batch_generate_recommendations(event, Mock())
        
        # Verify response
        assert result['statusCode'] == 201
        body = json.loads(result['body'])
        assert 'Batch recommendations generated successfully' in body['message']
        assert 'results' in body
        assert body['total_recommendations'] == 2
        assert 'user1' in body['results']
        assert 'user2' in body['results']
    
    @patch('src.handlers.matching_handler.verify_jwt_token')
    @patch('src.handlers.matching_handler.require_permission')
    def test_batch_generate_recommendations_non_admin(self, mock_require_permission, 
                                                    mock_verify_token):
        """Test batch recommendation generation with non-admin user."""
        # Setup mocks
        mock_verify_token.return_value = {'user_id': 'veteran123', 'role': 'veteran'}
        mock_require_permission.return_value = False  # Non-admin user
        
        # Create event
        event = {
            'headers': {'Authorization': 'Bearer valid_token'},
            'body': json.dumps({'user_ids': ['user1', 'user2']})
        }
        
        # Call handler
        result = handle_batch_generate_recommendations(event, Mock())
        
        # Verify response
        assert result['statusCode'] == 403
        body = json.loads(result['body'])
        assert 'Admin access required for batch operations' in body['error']


if __name__ == '__main__':
    pytest.main([__file__])