"""
Unit tests for BaseRepository.
"""

import pytest
from unittest.mock import Mock, patch
from src.repositories.base_repository import BaseRepository


class TestBaseRepository:
    """Test cases for BaseRepository."""
    
    @patch('src.repositories.base_repository.boto3')
    def test_base_repository_initialization(self, mock_boto3):
        """Test BaseRepository initialization."""
        mock_dynamodb = Mock()
        mock_table = Mock()
        mock_boto3.resource.return_value = mock_dynamodb
        mock_dynamodb.Table.return_value = mock_table
        
        repo = BaseRepository("test-table")
        
        assert repo.table_name == "test-table"
        assert repo.dynamodb == mock_dynamodb
        assert repo.table == mock_table
        mock_boto3.resource.assert_called_once_with('dynamodb', region_name='us-west-2')
    
    @patch('src.repositories.base_repository.boto3')
    def test_get_item_success(self, mock_boto3):
        """Test successful get_item operation."""
        mock_table = Mock()
        mock_boto3.resource.return_value.Table.return_value = mock_table
        mock_table.get_item.return_value = {'Item': {'id': '123', 'name': 'test'}}
        
        repo = BaseRepository("test-table")
        result = repo.get_item({'id': '123'})
        
        assert result == {'id': '123', 'name': 'test'}
        mock_table.get_item.assert_called_once_with(Key={'id': '123'})
    
    @patch('src.repositories.base_repository.boto3')
    def test_get_item_not_found(self, mock_boto3):
        """Test get_item when item not found."""
        mock_table = Mock()
        mock_boto3.resource.return_value.Table.return_value = mock_table
        mock_table.get_item.return_value = {}
        
        repo = BaseRepository("test-table")
        result = repo.get_item({'id': '123'})
        
        assert result is None
    
    @patch('src.repositories.base_repository.boto3')
    def test_put_item_success(self, mock_boto3):
        """Test successful put_item operation."""
        mock_table = Mock()
        mock_boto3.resource.return_value.Table.return_value = mock_table
        
        repo = BaseRepository("test-table")
        result = repo.put_item({'id': '123', 'name': 'test'})
        
        assert result is True
        mock_table.put_item.assert_called_once_with(Item={'id': '123', 'name': 'test'})
    
    @patch('src.repositories.base_repository.boto3')
    def test_item_exists_true(self, mock_boto3):
        """Test item_exists when item exists."""
        mock_table = Mock()
        mock_boto3.resource.return_value.Table.return_value = mock_table
        mock_table.get_item.return_value = {'Item': {'id': '123'}}
        
        repo = BaseRepository("test-table")
        result = repo.item_exists({'id': '123'})
        
        assert result is True
    
    @patch('src.repositories.base_repository.boto3')
    def test_item_exists_false(self, mock_boto3):
        """Test item_exists when item doesn't exist."""
        mock_table = Mock()
        mock_boto3.resource.return_value.Table.return_value = mock_table
        mock_table.get_item.return_value = {}
        
        repo = BaseRepository("test-table")
        result = repo.item_exists({'id': '123'})
        
        assert result is False