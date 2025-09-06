"""
Unit tests for profile handler
"""
import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.handlers.profile_handler import (
    handler, create_profile, get_profile, update_profile, 
    delete_profile, list_profiles, update_privacy_settings,
    generate_business_title
)
from src.models.veteran_profile import VeteranProfile
from src.models.user import User


class TestProfileHandler:
    """Test cases for profile handler"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.mock_user = {
            'user_id': 'test-user-123',
            'role': 'veteran',
            'email': 'test@example.com'
        }
        
        self.mock_profile_data = {
            'business_title': 'Senior Software Engineer',
            'skills': [
                {'name': 'Python', 'level': 'Expert', 'years': 5, 'certifications': []},
                {'name': 'AWS', 'level': 'Advanced', 'years': 3, 'certifications': ['AWS Solutions Architect']}
            ],
            'experiences': [
                {
                    'title': 'Software Engineer',
                    'department': 'Engineering',
                    'duration': 36,
                    'achievements': ['Led team of 5 developers']
                }
            ],
            'preferences': {
                'preferred_roles': ['Senior Engineer', 'Tech Lead'],
                'work_style': 'Remote',
                'locations': ['Tokyo', 'Remote']
            },
            'privacy_settings': {
                'is_publicly_visible': False,
                'external_contact': True
            }
        }
        
        self.base_event = {
            'httpMethod': 'GET',
            'path': '/profiles/test-user-123',
            'pathParameters': {'proxy': 'test-user-123'},
            'queryStringParameters': None,
            'headers': {'Authorization': 'Bearer token'},
            'body': None,
            'user': self.mock_user
        }

    @patch('src.handlers.profile_handler.extract_user_from_event')
    def test_handler_routing_get_profile(self, mock_extract_user):
        """Test handler routes GET request to get_profile"""
        mock_extract_user.return_value = self.mock_user
        
        with patch('src.handlers.profile_handler.get_profile') as mock_get_profile:
            mock_get_profile.return_value = {'statusCode': 200, 'body': '{}'}
            
            event = self.base_event.copy()
            result = handler(event, {})
            
            mock_get_profile.assert_called_once()
            assert result['statusCode'] == 200

    @patch('src.handlers.profile_handler.extract_user_from_event')
    def test_handler_routing_create_profile(self, mock_extract_user):
        """Test handler routes POST request to create_profile"""
        mock_extract_user.return_value = self.mock_user
        
        with patch('src.handlers.profile_handler.create_profile') as mock_create_profile:
            mock_create_profile.return_value = {'statusCode': 201, 'body': '{}'}
            
            event = self.base_event.copy()
            event['httpMethod'] = 'POST'
            event['path'] = '/profiles'
            
            result = handler(event, {})
            
            mock_create_profile.assert_called_once()
            assert result['statusCode'] == 201

    @patch('src.handlers.profile_handler.VeteranProfileRepository')
    def test_create_profile_success(self, mock_repo_class):
        """Test successful profile creation"""
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        mock_repo.profile_exists.return_value = False
        mock_repo.create_profile.return_value = True
        
        event = {
            'user': self.mock_user,
            'body': json.dumps(self.mock_profile_data)
        }
        
        with patch('src.handlers.profile_handler.security_auditor') as mock_auditor, \
             patch('src.handlers.profile_handler.extract_request_info') as mock_extract_info:
            
            mock_extract_info.return_value = {'source_ip': '127.0.0.1'}
            
            result = create_profile(event)
            
            assert result['statusCode'] == 201
            response_body = json.loads(result['body'])
            assert response_body['message'] == 'Profile created successfully'
            assert 'profile' in response_body
            
            mock_repo.profile_exists.assert_called_once_with('test-user-123')
            mock_repo.create_profile.assert_called_once()
            mock_auditor.log_profile_access.assert_called_once()

    @patch('src.handlers.profile_handler.VeteranProfileRepository')
    def test_create_profile_already_exists(self, mock_repo_class):
        """Test profile creation when profile already exists"""
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        mock_repo.profile_exists.return_value = True
        
        event = {
            'user': self.mock_user,
            'body': json.dumps(self.mock_profile_data)
        }
        
        result = create_profile(event)
        
        assert result['statusCode'] == 409
        response_body = json.loads(result['body'])
        assert response_body['error'] == 'Profile already exists for this user'

    @patch('src.handlers.profile_handler.VeteranProfileRepository')
    def test_create_profile_validation_error(self, mock_repo_class):
        """Test profile creation with validation errors"""
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        mock_repo.profile_exists.return_value = False
        
        # Invalid profile data - missing required skill fields
        invalid_data = {
            'skills': [{'name': 'Python'}]  # Missing level and years
        }
        
        event = {
            'user': self.mock_user,
            'body': json.dumps(invalid_data)
        }
        
        result = create_profile(event)
        
        assert result['statusCode'] == 400
        response_body = json.loads(result['body'])
        assert response_body['error'] == 'Profile validation failed'
        assert 'details' in response_body

    @patch('src.handlers.profile_handler.VeteranProfileRepository')
    @patch('src.handlers.profile_handler.check_resource_access')
    def test_get_profile_success(self, mock_check_access, mock_repo_class):
        """Test successful profile retrieval"""
        mock_check_access.return_value = True
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        
        mock_profile = VeteranProfile(
            user_id='test-user-123',
            **self.mock_profile_data
        )
        mock_repo.get_profile.return_value = mock_profile
        
        event = {
            'user': self.mock_user,
            'path': '/profiles/test-user-123'
        }
        
        with patch('src.handlers.profile_handler.security_auditor') as mock_auditor, \
             patch('src.handlers.profile_handler.extract_request_info') as mock_extract_info:
            
            mock_extract_info.return_value = {'source_ip': '127.0.0.1'}
            
            result = get_profile(event, {})
            
            assert result['statusCode'] == 200
            response_body = json.loads(result['body'])
            assert 'profile' in response_body
            assert response_body['profile']['user_id'] == 'test-user-123'
            
            mock_repo.get_profile.assert_called_once_with('test-user-123')
            mock_auditor.log_profile_access.assert_called_once()

    @patch('src.handlers.profile_handler.VeteranProfileRepository')
    @patch('src.handlers.profile_handler.check_resource_access')
    def test_get_profile_not_found(self, mock_check_access, mock_repo_class):
        """Test profile retrieval when profile doesn't exist"""
        mock_check_access.return_value = True
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        mock_repo.get_profile.return_value = None
        
        event = {
            'user': self.mock_user,
            'path': '/profiles/test-user-123'
        }
        
        result = get_profile(event, {})
        
        assert result['statusCode'] == 404
        response_body = json.loads(result['body'])
        assert response_body['error'] == 'Profile not found'

    @patch('src.handlers.profile_handler.VeteranProfileRepository')
    @patch('src.handlers.profile_handler.check_resource_access')
    def test_get_profile_access_denied(self, mock_check_access, mock_repo_class):
        """Test profile retrieval with access denied"""
        mock_check_access.return_value = False
        
        event = {
            'user': self.mock_user,
            'path': '/profiles/other-user-456'
        }
        
        with patch('src.handlers.profile_handler.security_auditor') as mock_auditor, \
             patch('src.handlers.profile_handler.extract_request_info') as mock_extract_info:
            
            mock_extract_info.return_value = {'source_ip': '127.0.0.1'}
            
            result = get_profile(event, {})
            
            assert result['statusCode'] == 403
            response_body = json.loads(result['body'])
            assert response_body['error'] == 'Access denied'
            
            mock_auditor.log_profile_access.assert_called_once()

    @patch('src.handlers.profile_handler.VeteranProfileRepository')
    def test_update_profile_success(self, mock_repo_class):
        """Test successful profile update"""
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        
        existing_profile = VeteranProfile(
            user_id='test-user-123',
            **self.mock_profile_data
        )
        mock_repo.get_profile.return_value = existing_profile
        mock_repo.update_profile.return_value = True
        
        update_data = {
            'business_title': 'Lead Software Engineer',
            'skills': [{'name': 'Python', 'level': 'Expert', 'years': 6, 'certifications': []}]
        }
        
        event = {
            'user': self.mock_user,
            'path': '/profiles/test-user-123',
            'body': json.dumps(update_data),
            'profile_user_id': 'test-user-123'
        }
        
        with patch('src.handlers.profile_handler.security_auditor') as mock_auditor, \
             patch('src.handlers.profile_handler.extract_request_info') as mock_extract_info:
            
            mock_extract_info.return_value = {'source_ip': '127.0.0.1'}
            
            result = update_profile(event, {})
            
            assert result['statusCode'] == 200
            response_body = json.loads(result['body'])
            assert response_body['message'] == 'Profile updated successfully'
            assert 'updated_fields' in response_body
            assert 'profile' in response_body
            
            mock_repo.get_profile.assert_called_once_with('test-user-123')
            mock_repo.update_profile.assert_called_once()
            mock_auditor.log_profile_access.assert_called_once()

    @patch('src.handlers.profile_handler.VeteranProfileRepository')
    def test_update_profile_not_found(self, mock_repo_class):
        """Test profile update when profile doesn't exist"""
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        mock_repo.get_profile.return_value = None
        
        event = {
            'user': self.mock_user,
            'path': '/profiles/test-user-123',
            'body': json.dumps({'business_title': 'New Title'}),
            'profile_user_id': 'test-user-123'
        }
        
        result = update_profile(event, {})
        
        assert result['statusCode'] == 404
        response_body = json.loads(result['body'])
        assert response_body['error'] == 'Profile not found'

    @patch('src.handlers.profile_handler.VeteranProfileRepository')
    def test_delete_profile_success(self, mock_repo_class):
        """Test successful profile deletion"""
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        mock_repo.profile_exists.return_value = True
        mock_repo.delete_profile.return_value = True
        
        admin_user = {'user_id': 'admin-123', 'role': 'admin'}
        
        event = {
            'user': admin_user,
            'path': '/profiles/test-user-123'
        }
        
        with patch('src.handlers.profile_handler.security_auditor') as mock_auditor, \
             patch('src.handlers.profile_handler.extract_request_info') as mock_extract_info:
            
            mock_extract_info.return_value = {'source_ip': '127.0.0.1'}
            
            result = delete_profile(event, {})
            
            assert result['statusCode'] == 200
            response_body = json.loads(result['body'])
            assert response_body['message'] == 'Profile deleted successfully'
            
            mock_repo.profile_exists.assert_called_once_with('test-user-123')
            mock_repo.delete_profile.assert_called_once_with('test-user-123')
            mock_auditor.log_admin_action.assert_called_once()

    @patch('src.handlers.profile_handler.VeteranProfileRepository')
    def test_delete_profile_not_found(self, mock_repo_class):
        """Test profile deletion when profile doesn't exist"""
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        mock_repo.profile_exists.return_value = False
        
        admin_user = {'user_id': 'admin-123', 'role': 'admin'}
        
        event = {
            'user': admin_user,
            'path': '/profiles/test-user-123'
        }
        
        result = delete_profile(event, {})
        
        assert result['statusCode'] == 404
        response_body = json.loads(result['body'])
        assert response_body['error'] == 'Profile not found'

    @patch('src.handlers.profile_handler.VeteranProfileRepository')
    @patch('src.handlers.profile_handler.UserRepository')
    @patch('src.handlers.profile_handler.rbac_manager')
    def test_list_profiles_admin(self, mock_rbac_manager, mock_user_repo_class, mock_profile_repo_class):
        """Test profile listing for admin user"""
        mock_profile_repo = Mock()
        mock_user_repo = Mock()
        mock_profile_repo_class.return_value = mock_profile_repo
        mock_user_repo_class.return_value = mock_user_repo
        
        # Mock RBAC to allow admin to view any profile
        mock_rbac_manager.has_permission.return_value = True
        
        mock_profiles = [
            VeteranProfile(user_id='user1', business_title='Engineer'),
            VeteranProfile(user_id='user2', business_title='Designer')
        ]
        
        mock_profile_repo.scan.return_value = [p.to_dynamodb_item() for p in mock_profiles]
        mock_user_repo.get_user_by_id.side_effect = [
            User(user_id='user1', name='John Doe', department='Engineering', email='john@example.com', employee_id='E001', join_date='2020-01-01', role='veteran', is_active=True),
            User(user_id='user2', name='Jane Smith', department='Design', email='jane@example.com', employee_id='E002', join_date='2020-01-01', role='veteran', is_active=True)
        ]
        
        admin_user = {'user_id': 'admin-123', 'role': 'admin'}
        
        event = {
            'user': admin_user,
            'path': '/profiles',
            'queryStringParameters': None
        }
        
        result = list_profiles(event, {})
        
        assert result['statusCode'] == 200
        response_body = json.loads(result['body'])
        assert 'profiles' in response_body
        assert len(response_body['profiles']) == 2
        assert response_body['count'] == 2

    @patch('src.handlers.profile_handler.VeteranProfileRepository')
    @patch('src.handlers.profile_handler.UserRepository')
    @patch('src.handlers.profile_handler.rbac_manager')
    def test_list_profiles_external_recruiter(self, mock_rbac_manager, mock_user_repo_class, mock_repo_class):
        """Test profile listing for external recruiter (public profiles only)"""
        mock_repo = Mock()
        mock_user_repo = Mock()
        mock_repo_class.return_value = mock_repo
        mock_user_repo_class.return_value = mock_user_repo
        
        # Mock RBAC to allow external recruiter to view public profiles
        mock_rbac_manager.has_permission.return_value = True
        
        public_profile = VeteranProfile(
            user_id='user1',
            business_title='Engineer',
            is_publicly_visible='true'
        )
        mock_repo.get_public_profiles.return_value = [public_profile]
        mock_user_repo.get_user_by_id.return_value = None  # External recruiters don't get user data
        
        recruiter_user = {'user_id': 'recruiter-123', 'role': 'external_recruiter'}
        
        event = {
            'user': recruiter_user,
            'path': '/profiles',
            'queryStringParameters': None
        }
        
        result = list_profiles(event, {})
        
        assert result['statusCode'] == 200
        response_body = json.loads(result['body'])
        assert 'profiles' in response_body
        assert len(response_body['profiles']) == 1
        # External recruiters should only see limited data
        profile_data = response_body['profiles'][0]
        assert 'name' not in profile_data  # User data not included for external recruiters

    @patch('src.handlers.profile_handler.privacy_manager')
    def test_update_privacy_settings_success(self, mock_privacy_manager):
        """Test successful privacy settings update"""
        mock_privacy_manager.validate_privacy_settings.return_value = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        mock_privacy_manager.update_privacy_settings.return_value = {
            'success': True,
            'updated_settings': {'is_publicly_visible': True, 'external_contact': False},
            'sync_result': {'sync_performed': True, 'actions': []},
            'profile_updated_at': '2023-01-01T00:00:00'
        }
        
        privacy_data = {
            'is_publicly_visible': True,
            'external_contact': False
        }
        
        event = {
            'user': self.mock_user,
            'path': '/profiles/test-user-123/privacy',
            'body': json.dumps(privacy_data),
            'profile_user_id': 'test-user-123'
        }
        
        with patch('src.handlers.profile_handler.security_auditor') as mock_auditor, \
             patch('src.handlers.profile_handler.extract_request_info') as mock_extract_info:
            
            mock_extract_info.return_value = {'source_ip': '127.0.0.1'}
            
            result = update_privacy_settings(event, {})
            
            assert result['statusCode'] == 200
            response_body = json.loads(result['body'])
            assert response_body['message'] == 'Privacy settings updated successfully'
            assert 'updated_settings' in response_body
            assert 'sync_result' in response_body
            
            mock_privacy_manager.validate_privacy_settings.assert_called_once_with(privacy_data)
            mock_privacy_manager.update_privacy_settings.assert_called_once_with('test-user-123', privacy_data)
            mock_auditor.log_profile_access.assert_called_once()

    @patch('src.handlers.profile_handler.privacy_manager')
    def test_update_privacy_settings_invalid_data(self, mock_privacy_manager):
        """Test privacy settings update with invalid data types"""
        mock_privacy_manager.validate_privacy_settings.return_value = {
            'valid': False,
            'errors': ['is_publicly_visible must be a boolean value'],
            'warnings': []
        }
        
        privacy_data = {
            'is_publicly_visible': 'true',  # Should be boolean, not string
            'external_contact': False
        }
        
        event = {
            'user': self.mock_user,
            'path': '/profiles/test-user-123/privacy',
            'body': json.dumps(privacy_data),
            'profile_user_id': 'test-user-123'
        }
        
        result = update_privacy_settings(event, {})
        
        assert result['statusCode'] == 400
        response_body = json.loads(result['body'])
        assert 'Privacy settings validation failed' in response_body['error']

    def test_invalid_json_body(self):
        """Test handlers with invalid JSON in request body"""
        event = {
            'user': self.mock_user,
            'body': 'invalid json'
        }
        
        result = create_profile(event)
        assert result['statusCode'] == 400
        
        result = update_profile(event, {})
        assert result['statusCode'] == 400
        
        result = update_privacy_settings(event, {})
        assert result['statusCode'] == 400

    def test_missing_authentication(self):
        """Test handlers without user authentication"""
        event = {'body': json.dumps({})}
        
        result = create_profile(event)
        assert result['statusCode'] == 401
        response_body = json.loads(result['body'])
        assert response_body['error'] == 'Authentication required'