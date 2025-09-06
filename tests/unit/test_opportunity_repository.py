"""
Unit tests for OpportunityRepository
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import boto3
from moto import mock_dynamodb

from src.repositories.opportunity_repository import OpportunityRepository
from src.models.opportunity import Opportunity


@mock_dynamodb
class TestOpportunityRepository:
    """Test cases for OpportunityRepository"""
    
    def setup_method(self, method):
        """Set up test fixtures"""
        # Create mock DynamoDB table
        self.dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        
        # Create table
        self.table = self.dynamodb.create_table(
            TableName='Opportunities',
            KeySchema=[
                {'AttributeName': 'opportunity_id', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'opportunity_id', 'AttributeType': 'S'},
                {'AttributeName': 'type', 'AttributeType': 'S'},
                {'AttributeName': 'posted_date', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'TypeDateIndex',
                    'KeySchema': [
                        {'AttributeName': 'type', 'KeyType': 'HASH'},
                        {'AttributeName': 'posted_date', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
                }
            ],
            BillingMode='PROVISIONED',
            ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
        )
        
        # Initialize repository with mocked table
        self.repo = OpportunityRepository()
        self.repo.table = self.table
        
        # Sample opportunity data
        self.sample_opportunity = Opportunity(
            opportunity_id='opp123',
            title='Senior Engineer',
            description='Great opportunity',
            required_skills=['Python', 'AWS'],
            location='Remote',
            type='internal_transfer',
            source='internal',
            company='Honda',
            salary_range={'min': 80000, 'max': 120000, 'currency': 'USD'},
            is_active=True,
            posted_date='2024-01-01T00:00:00',
            expiry_date='2024-12-31T23:59:59'
        )
    
    def test_create_opportunity_success(self):
        """Test successful opportunity creation"""
        result = self.repo.create_opportunity(self.sample_opportunity)
        
        assert result is True
        
        # Verify opportunity was stored
        response = self.table.get_item(Key={'opportunity_id': 'opp123'})
        assert 'Item' in response
        assert response['Item']['title'] == 'Senior Engineer'
        assert response['Item']['is_active'] is True
    
    def test_create_opportunity_failure(self):
        """Test opportunity creation failure"""
        with patch.object(self.repo.table, 'put_item', side_effect=Exception("DynamoDB error")):
            result = self.repo.create_opportunity(self.sample_opportunity)
            assert result is False
    
    def test_get_opportunity_success(self):
        """Test successful opportunity retrieval"""
        # First create the opportunity
        self.repo.create_opportunity(self.sample_opportunity)
        
        # Then retrieve it
        result = self.repo.get_opportunity('opp123')
        
        assert result is not None
        assert result.opportunity_id == 'opp123'
        assert result.title == 'Senior Engineer'
        assert result.is_active is True
    
    def test_get_opportunity_not_found(self):
        """Test opportunity retrieval when not found"""
        result = self.repo.get_opportunity('nonexistent')
        assert result is None
    
    def test_get_opportunity_exception(self):
        """Test opportunity retrieval with exception"""
        with patch.object(self.repo.table, 'get_item', side_effect=Exception("DynamoDB error")):
            result = self.repo.get_opportunity('opp123')
            assert result is None
    
    def test_update_opportunity_success(self):
        """Test successful opportunity update"""
        # First create the opportunity
        self.repo.create_opportunity(self.sample_opportunity)
        
        # Update the opportunity
        self.sample_opportunity.title = 'Lead Engineer'
        self.sample_opportunity.is_active = False
        
        result = self.repo.update_opportunity(self.sample_opportunity)
        assert result is True
        
        # Verify update
        updated_opp = self.repo.get_opportunity('opp123')
        assert updated_opp.title == 'Lead Engineer'
        assert updated_opp.is_active is False
    
    def test_update_opportunity_failure(self):
        """Test opportunity update failure"""
        with patch.object(self.repo.table, 'put_item', side_effect=Exception("DynamoDB error")):
            result = self.repo.update_opportunity(self.sample_opportunity)
            assert result is False
    
    def test_delete_opportunity_success(self):
        """Test successful opportunity deletion"""
        # First create the opportunity
        self.repo.create_opportunity(self.sample_opportunity)
        
        # Delete it
        result = self.repo.delete_opportunity('opp123')
        assert result is True
        
        # Verify deletion
        deleted_opp = self.repo.get_opportunity('opp123')
        assert deleted_opp is None
    
    def test_delete_opportunity_failure(self):
        """Test opportunity deletion failure"""
        with patch.object(self.repo.table, 'delete_item', side_effect=Exception("DynamoDB error")):
            result = self.repo.delete_opportunity('opp123')
            assert result is False
    
    def test_list_opportunities_success(self):
        """Test successful opportunity listing"""
        # Create multiple opportunities
        opp1 = Opportunity(
            opportunity_id='opp1',
            title='Engineer 1',
            type='internal_transfer',
            is_active=True
        )
        opp2 = Opportunity(
            opportunity_id='opp2',
            title='Engineer 2',
            type='external_position',
            is_active=True
        )
        
        self.repo.create_opportunity(opp1)
        self.repo.create_opportunity(opp2)
        
        # List opportunities
        result = self.repo.list_opportunities()
        
        assert len(result) == 2
        assert all(opp.is_active for opp in result)
    
    def test_list_opportunities_with_filters(self):
        """Test opportunity listing with filters"""
        # Create opportunities with different types
        opp1 = Opportunity(
            opportunity_id='opp1',
            title='Engineer 1',
            type='internal_transfer',
            is_active=True
        )
        opp2 = Opportunity(
            opportunity_id='opp2',
            title='Engineer 2',
            type='external_position',
            is_active=True
        )
        
        self.repo.create_opportunity(opp1)
        self.repo.create_opportunity(opp2)
        
        # List with type filter
        result = self.repo.list_opportunities(filters={'type': 'internal_transfer'})
        
        assert len(result) == 1
        assert result[0].type == 'internal_transfer'
    
    def test_list_opportunities_exception(self):
        """Test opportunity listing with exception"""
        with patch.object(self.repo.table, 'scan', side_effect=Exception("DynamoDB error")):
            result = self.repo.list_opportunities()
            assert result == []
    
    def test_search_opportunities_success(self):
        """Test successful opportunity search"""
        # Create opportunities
        opp1 = Opportunity(
            opportunity_id='opp1',
            title='Python Engineer',
            description='Python development role',
            required_skills=['Python', 'Django'],
            is_active=True
        )
        opp2 = Opportunity(
            opportunity_id='opp2',
            title='Java Engineer',
            description='Java development role',
            required_skills=['Java', 'Spring'],
            is_active=True
        )
        
        self.repo.create_opportunity(opp1)
        self.repo.create_opportunity(opp2)
        
        # Search for Python opportunities
        result = self.repo.search_opportunities('Python')
        
        assert len(result) >= 1
        # Should find the Python engineer opportunity
        python_opp = next((opp for opp in result if 'Python' in opp.title), None)
        assert python_opp is not None
    
    def test_search_opportunities_exception(self):
        """Test opportunity search with exception"""
        with patch.object(self.repo.table, 'scan', side_effect=Exception("DynamoDB error")):
            result = self.repo.search_opportunities('Python')
            assert result == []
    
    def test_get_opportunities_by_type_success(self):
        """Test successful retrieval of opportunities by type"""
        # Create opportunities of different types
        opp1 = Opportunity(
            opportunity_id='opp1',
            title='Internal Role',
            type='internal_transfer',
            posted_date='2024-01-01T00:00:00',
            is_active=True
        )
        opp2 = Opportunity(
            opportunity_id='opp2',
            title='External Role',
            type='external_position',
            posted_date='2024-01-02T00:00:00',
            is_active=True
        )
        
        self.repo.create_opportunity(opp1)
        self.repo.create_opportunity(opp2)
        
        # Get internal opportunities
        result = self.repo.get_opportunities_by_type('internal_transfer')
        
        assert len(result) == 1
        assert result[0].type == 'internal_transfer'
    
    def test_get_opportunities_by_type_exception(self):
        """Test opportunities by type retrieval with exception"""
        with patch.object(self.repo.table, 'query', side_effect=Exception("DynamoDB error")):
            result = self.repo.get_opportunities_by_type('internal_transfer')
            assert result == []