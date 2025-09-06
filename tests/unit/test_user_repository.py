"""
Unit tests for UserRepository
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import boto3
from moto import mock_dynamodb

from src.repositories.user_repository import UserRepository
from src.models.user import User


@mock_dynamodb
class TestUserRepository:
    """Test cases for UserRepository"""
    
    def setup_method(self, method):
        """Set up test fixtures"""
        # Create mock DynamoDB table
        self.dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        
        # Create table
        self.table = self.dynamodb.create_table(
            TableName='Users',
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
                    'KeySchema': [
                        {'AttributeName': 'email', 'KeyType': 'HASH'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
                }
            ],
            BillingMode='PROVISIONED',
            ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
        )
        
        # Initialize repository with mocked table
        self.repo = UserRepository()
        self.repo.table = self.table
        
        # Sample user data
        self.sample_user = User(
            user_id='user123',
            employee_id='emp123',
            email='test@honda.com',
            name='Test User',
            department='Engineering',
            join_date='2020-01-01',
            role='veteran',
            is_active=True
        )
    
    def test_create_user_success(self):
        """Test successful user creation"""
        result = self.repo.create_user(self.sample_user)
        
        assert result is True
        
        # Verify user was stored
        response = self.table.get_item(Key={'user_id': 'user123'})
        assert 'Item' in response
        assert response['Item']['email'] == 'test@honda.com'
        assert response['Item']['is_active'] is True
    
    def test_create_user_failure(self):
        """Test user creation failure"""
        with patch.object(self.repo.table, 'put_item', side_effect=Exception("DynamoDB error")):
            result = self.repo.create_user(self.sample_user)
            assert result is False
    
    def test_get_user_success(self):
        """Test successful user retrieval"""
        # First create the user
        self.repo.create_user(self.sample_user)
        
        # Then retrieve it
        result = self.repo.get_user('user123')
        
        assert result is not None
        assert result.user_id == 'user123'
        assert result.email == 'test@honda.com'
        assert result.role == 'veteran'
    
    def test_get_user_not_found(self):
        """Test user retrieval when not found"""
        result = self.repo.get_user('nonexistent')
        assert result is None
    
    def test_get_user_exception(self):
        """Test user retrieval with exception"""
        with patch.object(self.repo.table, 'get_item', side_effect=Exception("DynamoDB error")):
            result = self.repo.get_user('user123')
            assert result is None
    
    def test_get_user_by_email_success(self):
        """Test successful user retrieval by email"""
        # First create the user
        self.repo.create_user(self.sample_user)
        
        # Then retrieve by email
        result = self.repo.get_user_by_email('test@honda.com')
        
        assert result is not None
        assert result.email == 'test@honda.com'
        assert result.user_id == 'user123'
    
    def test_get_user_by_email_not_found(self):
        """Test user retrieval by email when not found"""
        result = self.repo.get_user_by_email('nonexistent@honda.com')
        assert result is None
    
    def test_get_user_by_email_exception(self):
        """Test user retrieval by email with exception"""
        with patch.object(self.repo.table, 'query', side_effect=Exception("DynamoDB error")):
            result = self.repo.get_user_by_email('test@honda.com')
            assert result is None
    
    def test_update_user_success(self):
        """Test successful user update"""
        # First create the user
        self.repo.create_user(self.sample_user)
        
        # Update the user
        self.sample_user.name = 'Updated User'
        self.sample_user.department = 'Product'
        
        result = self.repo.update_user(self.sample_user)
        assert result is True
        
        # Verify update
        updated_user = self.repo.get_user('user123')
        assert updated_user.name == 'Updated User'
        assert updated_user.department == 'Product'
    
    def test_update_user_failure(self):
        """Test user update failure"""
        with patch.object(self.repo.table, 'put_item', side_effect=Exception("DynamoDB error")):
            result = self.repo.update_user(self.sample_user)
            assert result is False
    
    def test_delete_user_success(self):
        """Test successful user deletion"""
        # First create the user
        self.repo.create_user(self.sample_user)
        
        # Delete it
        result = self.repo.delete_user('user123')
        assert result is True
        
        # Verify deletion
        deleted_user = self.repo.get_user('user123')
        assert deleted_user is None
    
    def test_delete_user_failure(self):
        """Test user deletion failure"""
        with patch.object(self.repo.table, 'delete_item', side_effect=Exception("DynamoDB error")):
            result = self.repo.delete_user('user123')
            assert result is False
    
    def test_list_users_success(self):
        """Test successful user listing"""
        # Create multiple users
        user1 = User(
            user_id='user1',
            employee_id='emp1',
            email='user1@honda.com',
            name='User 1',
            role='veteran',
            is_active=True
        )
        user2 = User(
            user_id='user2',
            employee_id='emp2',
            email='user2@honda.com',
            name='User 2',
            role='admin',
            is_active=True
        )
        
        self.repo.create_user(user1)
        self.repo.create_user(user2)
        
        # List users
        result = self.repo.list_users()
        
        assert len(result) == 2
        assert all(user.is_active for user in result)
    
    def test_list_users_with_role_filter(self):
        """Test user listing with role filter"""
        # Create users with different roles
        user1 = User(
            user_id='user1',
            employee_id='emp1',
            email='user1@honda.com',
            name='User 1',
            role='veteran',
            is_active=True
        )
        user2 = User(
            user_id='user2',
            employee_id='emp2',
            email='user2@honda.com',
            name='User 2',
            role='admin',
            is_active=True
        )
        
        self.repo.create_user(user1)
        self.repo.create_user(user2)
        
        # List veterans only
        result = self.repo.list_users(role='veteran')
        
        assert len(result) == 1
        assert result[0].role == 'veteran'
    
    def test_list_users_exception(self):
        """Test user listing with exception"""
        with patch.object(self.repo.table, 'scan', side_effect=Exception("DynamoDB error")):
            result = self.repo.list_users()
            assert result == []
    
    def test_user_exists_true(self):
        """Test user existence check when exists"""
        self.repo.create_user(self.sample_user)
        
        result = self.repo.user_exists('user123')
        assert result is True
    
    def test_user_exists_false(self):
        """Test user existence check when doesn't exist"""
        result = self.repo.user_exists('nonexistent')
        assert result is False
    
    def test_user_exists_exception(self):
        """Test user existence check with exception"""
        with patch.object(self.repo.table, 'get_item', side_effect=Exception("DynamoDB error")):
            result = self.repo.user_exists('user123')
            assert result is False
    
    def test_activate_user_success(self):
        """Test successful user activation"""
        # Create inactive user
        self.sample_user.is_active = False
        self.repo.create_user(self.sample_user)
        
        # Activate user
        result = self.repo.activate_user('user123')
        assert result is True
        
        # Verify activation
        user = self.repo.get_user('user123')
        assert user.is_active is True
    
    def test_activate_user_not_found(self):
        """Test user activation when user not found"""
        result = self.repo.activate_user('nonexistent')
        assert result is False
    
    def test_deactivate_user_success(self):
        """Test successful user deactivation"""
        # Create active user
        self.repo.create_user(self.sample_user)
        
        # Deactivate user
        result = self.repo.deactivate_user('user123')
        assert result is True
        
        # Verify deactivation
        user = self.repo.get_user('user123')
        assert user.is_active is False
    
    def test_deactivate_user_not_found(self):
        """Test user deactivation when user not found"""
        result = self.repo.deactivate_user('nonexistent')
        assert result is False