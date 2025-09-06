"""
Unit tests for Bedrock Claude client.
"""

import json
from unittest.mock import MagicMock, Mock, patch

import pytest
from botocore.exceptions import ClientError

from src.services.bedrock_client import (
    BedrockClient,
    BedrockClientError,
    BedrockRegion,
    BedrockRequest,
    BedrockResponse,
    ClaudeModel,
    create_bedrock_client,
    get_bedrock_client,
)


class TestBedrockClient:
    """Test cases for BedrockClient class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.client = BedrockClient(
            primary_region=BedrockRegion.US_WEST_2,
            fallback_regions=[BedrockRegion.US_EAST_1],
            max_retries=2,
            retry_delay=0.1,  # Fast retries for testing
        )

    def test_initialization(self):
        """Test client initialization."""
        assert self.client.primary_region == BedrockRegion.US_WEST_2
        assert self.client.fallback_regions == [BedrockRegion.US_EAST_1]
        assert self.client.model == ClaudeModel.CLAUDE_3_5_SONNET
        assert self.client.max_retries == 2
        assert self.client.retry_delay == 0.1

    def test_prepare_claude_payload(self):
        """Test Claude payload preparation."""
        request = BedrockRequest(
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=1000,
            temperature=0.7,
            system_prompt="You are a helpful assistant",
        )

        payload = self.client._prepare_claude_payload(request)

        expected_payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "temperature": 0.7,
            "top_p": 0.9,
            "messages": [{"role": "user", "content": "Hello"}],
            "system": "You are a helpful assistant",
        }

        assert payload == expected_payload

    def test_prepare_claude_payload_without_system(self):
        """Test Claude payload preparation without system prompt."""
        request = BedrockRequest(
            messages=[{"role": "user", "content": "Hello"}], max_tokens=1000
        )

        payload = self.client._prepare_claude_payload(request)

        assert "system" not in payload
        assert payload["messages"] == [{"role": "user", "content": "Hello"}]

    def test_parse_claude_response_success(self):
        """Test successful Claude response parsing."""
        response_body = {
            "content": [{"text": "Hello! How can I help you?"}],
            "usage": {"input_tokens": 10, "output_tokens": 8},
            "stop_reason": "end_turn",
        }

        result = self.client._parse_claude_response(response_body)

        assert result.success is True
        assert result.content == "Hello! How can I help you?"
        assert result.usage == {"input_tokens": 10, "output_tokens": 8}
        assert result.stop_reason == "end_turn"
        assert result.model == ClaudeModel.CLAUDE_3_5_SONNET.value

    def test_parse_claude_response_empty_content(self):
        """Test Claude response parsing with empty content."""
        response_body = {
            "content": [],
            "usage": {"input_tokens": 10, "output_tokens": 0},
            "stop_reason": "max_tokens",
        }

        result = self.client._parse_claude_response(response_body)

        assert result.success is True
        assert result.content == ""
        assert result.stop_reason == "max_tokens"

    def test_parse_claude_response_malformed(self):
        """Test Claude response parsing with malformed data."""
        response_body = {"invalid": "response"}

        result = self.client._parse_claude_response(response_body)

        assert result.success is False
        assert result.content == ""
        assert "parse_error" in result.stop_reason
        assert result.error_message is not None

    def test_should_retry_throttling(self):
        """Test retry logic for throttling errors."""
        error = ClientError(
            error_response={"Error": {"Code": "ThrottlingException"}},
            operation_name="InvokeModel",
        )

        assert self.client._should_retry(error, 0) is True
        assert self.client._should_retry(error, 1) is True
        assert self.client._should_retry(error, 2) is False  # max_retries = 2

    def test_should_retry_non_retryable_error(self):
        """Test retry logic for non-retryable errors."""
        error = ClientError(
            error_response={"Error": {"Code": "ValidationException"}},
            operation_name="InvokeModel",
        )

        assert self.client._should_retry(error, 0) is False

    def test_calculate_retry_delay(self):
        """Test exponential backoff calculation."""
        assert self.client._calculate_retry_delay(0) == 0.1
        assert self.client._calculate_retry_delay(1) == 0.2
        assert self.client._calculate_retry_delay(2) == 0.4

    @patch("boto3.client")
    def test_invoke_claude_success(self, mock_boto_client):
        """Test successful Claude invocation."""
        # Mock successful response
        mock_response = {"body": Mock()}
        mock_response["body"].read.return_value = json.dumps(
            {
                "content": [{"text": "Test response"}],
                "usage": {"input_tokens": 5, "output_tokens": 2},
                "stop_reason": "end_turn",
            }
        ).encode()

        mock_client = Mock()
        mock_client.invoke_model.return_value = mock_response
        mock_boto_client.return_value = mock_client

        # Reinitialize client to use mocked boto3
        client = BedrockClient(max_retries=1)
        client.clients[BedrockRegion.US_WEST_2] = mock_client

        request = BedrockRequest(messages=[{"role": "user", "content": "Hello"}])

        result = client.invoke_claude_sync(request)

        assert result.success is True
        assert result.content == "Test response"
        assert result.retry_count == 0

    @patch("boto3.client")
    def test_invoke_claude_with_retry(self, mock_boto_client):
        """Test Claude invocation with retry on throttling."""
        # Mock throttling error then success
        throttling_error = ClientError(
            error_response={"Error": {"Code": "ThrottlingException"}},
            operation_name="InvokeModel",
        )

        mock_response = {"body": Mock()}
        mock_response["body"].read.return_value = json.dumps(
            {
                "content": [{"text": "Success after retry"}],
                "usage": {"input_tokens": 5, "output_tokens": 3},
                "stop_reason": "end_turn",
            }
        ).encode()

        mock_client = Mock()
        mock_client.invoke_model.side_effect = [throttling_error, mock_response]
        mock_boto_client.return_value = mock_client

        # Reinitialize client to use mocked boto3
        client = BedrockClient(max_retries=2, retry_delay=0.01)
        client.clients[BedrockRegion.US_WEST_2] = mock_client

        request = BedrockRequest(messages=[{"role": "user", "content": "Hello"}])

        result = client.invoke_claude_sync(request)

        assert result.success is True
        assert result.content == "Success after retry"
        assert result.retry_count == 1

    @patch("boto3.client")
    def test_invoke_claude_all_retries_failed(self, mock_boto_client):
        """Test Claude invocation when all retries fail."""
        # Mock persistent throttling error
        throttling_error = ClientError(
            error_response={"Error": {"Code": "ThrottlingException"}},
            operation_name="InvokeModel",
        )

        mock_client = Mock()
        mock_client.invoke_model.side_effect = throttling_error
        mock_boto_client.return_value = mock_client

        # Reinitialize client to use mocked boto3
        client = BedrockClient(max_retries=1, retry_delay=0.01)
        client.clients[BedrockRegion.US_WEST_2] = mock_client
        client.clients[BedrockRegion.US_EAST_1] = mock_client

        request = BedrockRequest(messages=[{"role": "user", "content": "Hello"}])

        result = client.invoke_claude_sync(request)

        assert result.success is False
        assert result.error_message is not None
        assert "failed" in result.error_message.lower()

    def test_health_check(self):
        """Test health check functionality."""
        with patch.object(self.client, "invoke_claude_sync") as mock_invoke:
            # Mock successful health check
            mock_invoke.return_value = BedrockResponse(
                content="Hello",
                usage={},
                model="test",
                stop_reason="end_turn",
                success=True,
            )

            health_status = self.client.health_check()

            assert BedrockRegion.US_WEST_2.value in health_status
            assert health_status[BedrockRegion.US_WEST_2.value]["status"] == "healthy"


class TestBedrockRequest:
    """Test cases for BedrockRequest class."""

    def test_default_values(self):
        """Test default values in BedrockRequest."""
        request = BedrockRequest(messages=[{"role": "user", "content": "Hello"}])

        assert request.max_tokens == 4000
        assert request.temperature == 0.7
        assert request.top_p == 0.9
        assert request.system_prompt is None

    def test_custom_values(self):
        """Test custom values in BedrockRequest."""
        request = BedrockRequest(
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=2000,
            temperature=0.5,
            top_p=0.8,
            system_prompt="Custom system prompt",
        )

        assert request.max_tokens == 2000
        assert request.temperature == 0.5
        assert request.top_p == 0.8
        assert request.system_prompt == "Custom system prompt"


class TestBedrockResponse:
    """Test cases for BedrockResponse class."""

    def test_successful_response(self):
        """Test successful response creation."""
        response = BedrockResponse(
            content="Test content",
            usage={"input_tokens": 10, "output_tokens": 5},
            model="claude-3-5-sonnet",
            stop_reason="end_turn",
            success=True,
        )

        assert response.content == "Test content"
        assert response.usage == {"input_tokens": 10, "output_tokens": 5}
        assert response.success is True
        assert response.error_message is None
        assert response.retry_count == 0

    def test_error_response(self):
        """Test error response creation."""
        response = BedrockResponse(
            content="",
            usage={},
            model="claude-3-5-sonnet",
            stop_reason="error",
            success=False,
            error_message="Test error",
            retry_count=2,
        )

        assert response.success is False
        assert response.error_message == "Test error"
        assert response.retry_count == 2


class TestGlobalFunctions:
    """Test cases for global utility functions."""

    def test_get_bedrock_client_singleton(self):
        """Test that get_bedrock_client returns singleton."""
        client1 = get_bedrock_client()
        client2 = get_bedrock_client()

        assert client1 is client2

    def test_create_bedrock_client_new_instance(self):
        """Test that create_bedrock_client creates new instances."""
        client1 = create_bedrock_client()
        client2 = create_bedrock_client()

        assert client1 is not client2

    def test_create_bedrock_client_with_params(self):
        """Test create_bedrock_client with custom parameters."""
        client = create_bedrock_client(
            primary_region=BedrockRegion.EU_WEST_1, max_retries=5
        )

        assert client.primary_region == BedrockRegion.EU_WEST_1
        assert client.max_retries == 5
