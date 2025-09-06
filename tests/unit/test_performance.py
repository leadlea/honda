"""
Unit tests for performance optimization utilities.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from src.utils.performance import (
    PerformanceMonitor, ConnectionPool, DynamoDBOptimizer,
    BedrockOptimizer, LambdaColdStartOptimizer, MemoryOptimizer,
    performance_timer, optimize_lambda_handler
)


class TestPerformanceMonitor:
    """Test performance monitoring functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.monitor = PerformanceMonitor()
    
    def test_record_metric(self):
        """Test recording performance metrics."""
        self.monitor.record_metric('test_metric', 100.5, 'ms')
        
        assert 'test_metric' in self.monitor.metrics
        assert len(self.monitor.metrics['test_metric']) == 1
        assert self.monitor.metrics['test_metric'][0]['value'] == 100.5
        assert self.monitor.metrics['test_metric'][0]['unit'] == 'ms'
    
    def test_get_average(self):
        """Test getting average metric value."""
        self.monitor.record_metric('test_metric', 100)
        self.monitor.record_metric('test_metric', 200)
        self.monitor.record_metric('test_metric', 300)
        
        average = self.monitor.get_average('test_metric')
        assert average == 200.0
    
    def test_get_average_no_data(self):
        """Test getting average for non-existent metric."""
        average = self.monitor.get_average('nonexistent')
        assert average is None
    
    def test_metrics_summary(self):
        """Test getting metrics summary."""
        self.monitor.record_metric('metric1', 100)
        self.monitor.record_metric('metric1', 200)
        self.monitor.record_metric('metric2', 50)
        
        summary = self.monitor.get_metrics_summary()
        
        assert 'metric1' in summary
        assert 'metric2' in summary
        assert summary['metric1']['count'] == 2
        assert summary['metric1']['average'] == 150.0
        assert summary['metric1']['min'] == 100
        assert summary['metric1']['max'] == 200
    
    def test_metric_limit(self):
        """Test metric storage limit."""
        # Add more than 100 metrics
        for i in range(150):
            self.monitor.record_metric('test_metric', i)
        
        # Should keep only last 100
        assert len(self.monitor.metrics['test_metric']) == 100
        assert self.monitor.metrics['test_metric'][0]['value'] == 50  # First kept value


class TestPerformanceTimer:
    """Test performance timer decorator."""
    
    def test_performance_timer_decorator(self):
        """Test performance timer decorator functionality."""
        monitor = PerformanceMonitor()
        
        @performance_timer('test_function')
        def test_function():
            time.sleep(0.01)  # 10ms
            return 'result'
        
        # Mock the global performance monitor
        with patch('src.utils.performance.performance_monitor', monitor):
            result = test_function()
        
        assert result == 'result'
        assert 'test_function' in monitor.metrics
        assert len(monitor.metrics['test_function']) == 1
        # Should be around 10ms, allow some variance
        assert 5 < monitor.metrics['test_function'][0]['value'] < 50


class TestConnectionPool:
    """Test connection pool functionality."""
    
    @patch('src.utils.performance.boto3.client')
    def test_get_client_caching(self, mock_boto_client):
        """Test client caching in connection pool."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        # First call should create client
        client1 = ConnectionPool.get_client('dynamodb', 'us-west-2')
        assert client1 == mock_client
        assert mock_boto_client.call_count == 1
        
        # Second call should return cached client
        client2 = ConnectionPool.get_client('dynamodb', 'us-west-2')
        assert client2 == mock_client
        assert mock_boto_client.call_count == 1  # No additional calls
    
    @patch('src.utils.performance.boto3.resource')
    def test_get_resource_caching(self, mock_boto_resource):
        """Test resource caching in connection pool."""
        mock_resource = Mock()
        mock_boto_resource.return_value = mock_resource
        
        # First call should create resource
        resource1 = ConnectionPool.get_resource('dynamodb', 'us-west-2')
        assert resource1 == mock_resource
        assert mock_boto_resource.call_count == 1
        
        # Second call should return cached resource
        resource2 = ConnectionPool.get_resource('dynamodb', 'us-west-2')
        assert resource2 == mock_resource
        assert mock_boto_resource.call_count == 1  # No additional calls


class TestDynamoDBOptimizer:
    """Test DynamoDB optimization utilities."""
    
    def test_build_optimized_query(self):
        """Test building optimized query parameters."""
        query_params = DynamoDBOptimizer.build_optimized_query(
            'test_table',
            'user_id = :user_id',
            'attribute_exists(active)',
            'GSI1',
            50,
            False
        )
        
        assert query_params['KeyConditionExpression'] == 'user_id = :user_id'
        assert query_params['FilterExpression'] == 'attribute_exists(active)'
        assert query_params['IndexName'] == 'GSI1'
        assert query_params['Limit'] == 50
        assert query_params['ScanIndexForward'] is False
    
    def test_optimize_batch_operations(self):
        """Test batch operation optimization."""
        items = [{'id': i} for i in range(60)]  # 60 items
        
        batches = DynamoDBOptimizer.optimize_batch_operations(items, 25)
        
        assert len(batches) == 3  # 25 + 25 + 10
        assert len(batches[0]) == 25
        assert len(batches[1]) == 25
        assert len(batches[2]) == 10
    
    def test_calculate_read_capacity(self):
        """Test read capacity calculation."""
        # 4KB item, 10 reads/sec, eventual consistency
        rcu = DynamoDBOptimizer.calculate_read_capacity(4.0, 10.0, 'eventual')
        assert rcu == 6  # (10 * 1) / 2 * 1.2 = 6
        
        # 4KB item, 10 reads/sec, strong consistency
        rcu = DynamoDBOptimizer.calculate_read_capacity(4.0, 10.0, 'strong')
        assert rcu == 12  # 10 * 1 * 1.2 = 12
    
    def test_calculate_write_capacity(self):
        """Test write capacity calculation."""
        # 2KB item, 5 writes/sec
        wcu = DynamoDBOptimizer.calculate_write_capacity(2.0, 5.0)
        assert wcu == 12  # 5 * 2 * 1.2 = 12


class TestBedrockOptimizer:
    """Test Bedrock optimization utilities."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.optimizer = BedrockOptimizer()
    
    def test_optimize_prompt(self):
        """Test prompt optimization."""
        long_prompt = "This is a test prompt with    excessive    whitespace"
        optimized = self.optimizer.optimize_prompt(long_prompt)
        
        assert optimized == "This is a test prompt with excessive whitespace"
    
    def test_optimize_prompt_truncation(self):
        """Test prompt truncation for long prompts."""
        long_prompt = "A" * 20000  # Very long prompt
        optimized = self.optimizer.optimize_prompt(long_prompt, max_tokens=1000)
        
        # Should be truncated (1000 tokens * 4 chars = 4000 chars)
        assert len(optimized) <= 4003  # 4000 + "..."
        assert optimized.endswith("...")
    
    def test_get_optimal_inference_params(self):
        """Test getting optimal inference parameters."""
        params = self.optimizer.get_optimal_inference_params('questionnaire_generation')
        
        assert params['max_tokens'] == 2000
        assert params['temperature'] == 0.8
        assert params['top_p'] == 0.9
    
    def test_cache_response(self):
        """Test response caching."""
        prompt_hash = 'test_hash'
        model_id = 'claude-3'
        response = 'test response'
        
        # Cache response
        self.optimizer.cache_response(prompt_hash, model_id, response)
        
        # Should be able to retrieve it
        cached = self.optimizer.get_cached_response(prompt_hash, model_id)
        assert cached == response
    
    @patch('time.time')
    def test_cache_expiration(self, mock_time):
        """Test cache expiration."""
        mock_time.return_value = 1000
        
        prompt_hash = 'test_hash'
        model_id = 'claude-3'
        response = 'test response'
        
        # Cache response
        self.optimizer.cache_response(prompt_hash, model_id, response)
        
        # Move time forward past TTL
        mock_time.return_value = 1400  # 400 seconds later (> 300 TTL)
        
        # Should return None (expired)
        cached = self.optimizer.get_cached_response(prompt_hash, model_id)
        assert cached is None


class TestMemoryOptimizer:
    """Test memory optimization utilities."""
    
    def test_optimize_response_size(self):
        """Test response size optimization."""
        large_data = {
            'items': [{'id': i, 'data': 'x' * 1000} for i in range(100)],
            'total': 100
        }
        
        optimized = MemoryOptimizer.optimize_response_size(large_data, max_size_kb=10)
        
        # Should be truncated
        assert optimized['truncated'] is True
        assert optimized['original_count'] == 100
        assert len(optimized['items']) == 50
    
    def test_optimize_json_parsing(self):
        """Test JSON parsing optimization."""
        test_data = '{"key": "value", "number": 123}'
        
        parsed = MemoryOptimizer.optimize_json_parsing(test_data)
        
        assert parsed == {"key": "value", "number": 123}


class TestLambdaOptimizer:
    """Test Lambda optimization decorator."""
    
    def test_optimize_lambda_handler(self):
        """Test Lambda handler optimization decorator."""
        @optimize_lambda_handler
        def test_handler(event, context):
            return {
                'statusCode': 200,
                'body': '{"message": "success"}'
            }
        
        event = {'body': '{"input": "test"}'}
        context = Mock()
        context.aws_request_id = 'test-request-id'
        
        result = test_handler(event, context)
        
        assert result['statusCode'] == 200
        assert 'body' in result
    
    def test_optimize_lambda_handler_with_large_response(self):
        """Test Lambda handler with large response optimization."""
        @optimize_lambda_handler
        def test_handler(event, context):
            large_items = [{'id': i, 'data': 'x' * 1000} for i in range(100)]
            return {
                'statusCode': 200,
                'body': json.dumps({'items': large_items})
            }
        
        event = {}
        context = Mock()
        context.aws_request_id = 'test-request-id'
        
        result = test_handler(event, context)
        
        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        # Should be optimized if too large
        assert len(body['items']) <= 100


if __name__ == '__main__':
    pytest.main([__file__])