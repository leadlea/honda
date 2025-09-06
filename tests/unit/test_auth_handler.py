"""
Unit tests for authentication handler.
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from moto import mock_dynamodb, mock_cognitoidp
import boto3
import os

# Set environment variables for testing
os.environ['COGNITO_USER_POOL_ID'] = 'test-pool-id'
os.environ['COGNITO_CLIENT_ID'] = 'test-client-id'
os.environ['DYNAMODB_TABLE_PREFIX'] = 'test'
os.environ['REGION'] = 'us-west-2'

from src.handlers.auth_handler import (
    handler, register_user, login_user, logout_user, 
    get_user_profile, verify_token, refresh_token
)


class TestAuthHandler:
    """Test cases for authentication handler."""
    
    @mock_dynamodb
    @mock_cognitoidp
    def setup_method(self, method):
        """Set up test environment."""
        # Create mock DynamoDB table
        dynamodb = boto3.resource('dynamodb', region_name='us-west-2')
        
        table = dynamodb.create_table(
            TableName='test-users',
            KeySchema=[
                {'AttributeName': 'user_id', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'user_id', 'AttributeType': 'S'},
                {'AttributeName': 'email', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'EmailIndex',
                    'KeySchema': [{'AttributeName': 'email', 'KeyType': 'HASH'}],
                    'Projection': {'ProjectionType': 'ALL'}
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Create mock Cognito User Pool
        cognito = boto3.client('cognito-idp', region_name='us-west-2')
        cognito.create_user_pool(
            PoolName='test-pool',
            Policies={
                'PasswordPolicy': {
                    'MinimumLength': 8,
                    'RequireUppercase': True,
                    'RequireLowercase': True,
                    'RequireNumbers': True,
                    'RequireSymbols': True
                }
            }
        )
    
    def test_handler_routing_register(self):
        """Test handler routing for registration."""
        event = {
            'httpMethod': 'POST',
            'path': '/auth/register',
            'pathParameters': {'proxy': 'register'},
            'body': json.dumps({
                'email': 'test@example.com',
                'password': 'TestPass123!',
                'name': 'Test User',
                'employee_id': 'EMP001',
                'department': 'Engineering'
            })
        }
        
        with patch('src.handlers.auth_handler.register_user') as mock_register:
            mock_register.return_value = {'statusCode': 201, 'body': '{"message": "success"}'}
            
            result = handler(event, {})
            
            mock_register.assert_called_once_with(event)
            assert result['statusCode'] == 201
    
    def test_handler_routing_login(self):
        """Test handler routing for login."""
        event = {
            'httpMethod': 'POST',
            'path': '/auth/login',
            'pathParameters': {'proxy': 'login'},
            'body': json.dumps({
                'email': 'test@example.com',
                'password': 'TestPass123!'
            })
        }
        
        with patch('src.handlers.auth_handler.login_user') as mock_login:
            mock_login.return_value = {'statusCode': 200, 'body': '{"message": "success"}'}
            
            result = handler(event, {})
            
            mock_login.assert_called_once_with(event)
            assert result['statusCode'] == 200
    
    def test_handler_invalid_action(self):
        """Test handler with invalid action."""
        event = {
            'httpMethod': 'POST',
            'path': '/auth/invalid',
            'pathParameters': {'proxy': 'invalid'},
            'body': '{}'
        }
        
        result = handler(event, {})
        
        assert result['statusCode'] == 400
        body = json.loads(result['body'])
        assert 'error' in body
    
    @mock_dynamodb
    @mock_cognitoidp
    def test_register_user_success(self):
        """Test successful user registration."""
        # Setup mocks
        with patch('src.handlers.auth_handler.cognito_client') as mock_cognito, \
             patch('src.handlers.auth_handler.users_table') as mock_table:
            
            mock_cognito.admin_create_user.return_value = {
                'User': {'Username': 'test-user-id'}
            }
            mock_cognito.admin_set_user_password.return_value = {}
            mock_table.put_item.return_value = {}
            
            event = {
                'body': json.dumps({
                    'email': 'test@example.com',
                    'password': 'TestPass123!',
                    'name': 'Test User',
                    'employee_id': 'EMP001',
                    'department': 'Engineering',
                    'role': 'veteran'
                })
            }
            
            result = register_user(event)
            
            assert result['statusCode'] == 201
            body = json.loads(result['body'])
            assert body['message'] == 'User registered successfully'
            assert body['user_id'] == 'test-user-id'
            assert body['email'] == 'test@example.com'
            assert body['role'] == 'veteran'
    
    def test_register_user_missing_fields(self):
        """Test registration with missing required fields."""
        event = {
            'body': json.dumps({
                'email': 'test@example.com',
                'password': 'TestPass123!'
                # Missing name, employee_id, department
            })
        }
        
        result = register_user(event)
        
        assert result['statusCode'] == 400
        body = json.loads(result['body'])
        assert 'Missing required field' in body['error']
    
    def test_register_user_invalid_role(self):
        """Test registration with invalid role."""
        event = {
            'body': json.dumps({
                'email': 'test@example.com',
                'password': 'TestPass123!',
                'name': 'Test User',
                'employee_id': 'EMP001',
                'department': 'Engineering',
                'role': 'invalid_role'
            })
        }
        
        result = register_user(event)
        
        assert result['statusCode'] == 400
        body = json.loads(result['body'])
        assert 'Invalid role' in body['error']
    
    @mock_cognitoidp
    def test_login_user_success(self):
        """Test successful user login."""
        with patch('src.handlers.auth_handler.cognito_client') as mock_cognito, \
             patch('src.handlers.auth_handler.users_table') as mock_table, \
             patch('src.handlers.auth_handler.get_user_id_from_token') as mock_get_user_id:
            
            mock_cognito.admin_initiate_auth.return_value = {
                'AuthenticationResult': {
                    'AccessToken': 'access-token',
                    'IdToken': 'id-token',
                    'RefreshToken': 'refresh-token',
                    'ExpiresIn': 3600
                }
            }
            
            mock_get_user_id.return_value = 'test-user-id'
            
            mock_table.get_item.return_value = {
                'Item': {
                    'user_id': 'test-user-id',
                    'email': 'test@example.com',
                    'name': 'Test User',
                    'role': 'veteran',
                    'department': 'Engineering'
                }
            }
            
            event = {
                'body': json.dumps({
                    'email': 'test@example.com',
                    'password': 'TestPass123!'
                })
            }
            
            result = login_user(event)
            
            assert result['statusCode'] == 200
            body = json.loads(result['body'])
            assert body['message'] == 'Login successful'
            assert 'tokens' in body
            assert 'user' in body
            assert body['tokens']['access_token'] == 'access-token'
    
    def test_login_user_missing_credentials(self):
        """Test login with missing credentials."""
        event = {
            'body': json.dumps({
                'email': 'test@example.com'
                # Missing password
            })
        }
        
        result = login_user(event)
        
        assert result['statusCode'] == 400
        body = json.loads(result['body'])
        assert 'Email and password are required' in body['error']
    
    @mock_cognitoidp
    def test_logout_user_success(self):
        """Test successful user logout."""
        with patch('src.handlers.auth_handler.cognito_client') as mock_cognito, \
             patch('src.handlers.auth_handler.extract_token_from_header') as mock_extract:
            
            mock_extract.return_value = 'access-token'
            mock_cognito.global_sign_out.return_value = {}
            
            event = {
                'headers': {
                    'Authorization': 'Bearer access-token'
                }
            }
            
            result = logout_user(event)
            
            assert result['statusCode'] == 200
            body = json.loads(result['body'])
            assert body['message'] == 'Logout successful'
    
    def test_logout_user_no_token(self):
        """Test logout without access token."""
        event = {
            'headers': {}
        }
        
        result = logout_user(event)
        
        assert result['statusCode'] == 401
        body = json.loads(result['body'])
        assert 'Access token required' in body['error']
    
    @mock_cognitoidp
    def test_refresh_token_success(self):
        """Test successful token refresh."""
        with patch('src.handlers.auth_handler.cognito_client') as mock_cognito:
            
            mock_cognito.admin_initiate_auth.return_value = {
                'AuthenticationResult': {
                    'AccessToken': 'new-access-token',
                    'IdToken': 'new-id-token',
                    'ExpiresIn': 3600
                }
            }
            
            event = {
                'body': json.dumps({
                    'refresh_token': 'refresh-token'
                })
            }
            
            result = refresh_token(event)
            
            assert result['statusCode'] == 200
            body = json.loads(result['body'])
            assert body['message'] == 'Token refreshed successfully'
            assert body['tokens']['access_token'] == 'new-access-token'
    
    def test_refresh_token_missing_token(self):
        """Test token refresh without refresh token."""
        event = {
            'body': json.dumps({})
        }
        
        result = refresh_token(event)
        
        assert result['statusCode'] == 400
        body = json.loads(result['body'])
        assert 'Refresh token required' in body['error']
    
    @mock_dynamodb
    def test_get_user_profile_success(self):
        """Test successful user profile retrieval."""
        with patch('src.handlers.auth_handler.get_user_id_from_event') as mock_get_user_id, \
             patch('src.handlers.auth_handler.users_table') as mock_table:
            
            mock_get_user_id.return_value = 'test-user-id'
            
            mock_table.get_item.return_value = {
                'Item': {
                    'user_id': 'test-user-id',
                    'employee_id': 'EMP001',
                    'email': 'test@example.com',
                    'name': 'Test User',
                    'department': 'Engineering',
                    'role': 'veteran',
                    'is_active': True,
                    'created_at': '2023-01-01T00:00:00Z'
                }
            }
            
            event = {
                'headers': {
                    'Authorization': 'Bearer access-token'
                }
            }
            
            result = get_user_profile(event)
            
            assert result['statusCode'] == 200
            body = json.loads(result['body'])
            assert 'user' in body
            assert body['user']['user_id'] == 'test-user-id'
            assert body['user']['email'] == 'test@example.com'
    
    def test_get_user_profile_invalid_token(self):
        """Test profile retrieval with invalid token."""
        with patch('src.handlers.auth_handler.get_user_id_from_event') as mock_get_user_id:
            
            mock_get_user_id.return_value = None
            
            event = {
                'headers': {}
            }
            
            result = get_user_profile(event)
            
            assert result['statusCode'] == 401
            body = json.loads(result['body'])
            assert 'Invalid token' in body['error']
    
    @mock_cognitoidp
    def test_verify_token_success(self):
        """Test successful token verification."""
        with patch('src.handlers.auth_handler.cognito_client') as mock_cognito, \
             patch('src.handlers.auth_handler.extract_token_from_header') as mock_extract:
            
            mock_extract.return_value = 'access-token'
            
            mock_cognito.get_user.return_value = {
                'Username': 'test-user-id',
                'UserAttributes': [
                    {'Name': 'email', 'Value': 'test@example.com'},
                    {'Name': 'name', 'Value': 'Test User'},
                    {'Name': 'custom:role', 'Value': 'veteran'},
                    {'Name': 'custom:department', 'Value': 'Engineering'}
                ]
            }
            
            event = {
                'headers': {
                    'Authorization': 'Bearer access-token'
                }
            }
            
            result = verify_token(event)
            
            assert result['statusCode'] == 200
            body = json.loads(result['body'])
            assert body['valid'] is True
            assert 'user' in body
            assert body['user']['user_id'] == 'test-user-id'
    
    def test_verify_token_no_token(self):
        """Test token verification without token."""
        event = {
            'headers': {}
        }
        
        result = verify_token(event)
        
        assert result['statusCode'] == 401
        body = json.loads(result['body'])
        assert 'Access token required' in body['error']