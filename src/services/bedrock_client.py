"""
AWS Bedrock Claude client for AI inference operations.
Provides cross-region inference, error handling, and retry functionality.
"""

import hashlib
import json
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from src.utils.performance import BedrockOptimizer, performance_timer

logger = logging.getLogger(__name__)


class BedrockRegion(Enum):
    """Supported Bedrock regions for cross-region inference."""

    US_WEST_2 = "us-west-2"
    US_EAST_1 = "us-east-1"
    EU_WEST_1 = "eu-west-1"
    AP_NORTHEAST_1 = "ap-northeast-1"


class ClaudeModel(Enum):
    """Supported Claude models."""

    CLAUDE_3_5_SONNET = "anthropic.claude-3-5-sonnet-20240620-v1:0"
    CLAUDE_3_HAIKU = "anthropic.claude-3-haiku-20240307-v1:0"


@dataclass
class BedrockResponse:
    """Standardized response from Bedrock API."""

    content: str
    usage: Dict[str, int]
    model: str
    stop_reason: str
    success: bool
    error_message: Optional[str] = None
    retry_count: int = 0


@dataclass
class BedrockRequest:
    """Standardized request to Bedrock API."""

    messages: List[Dict[str, str]]
    max_tokens: int = 4000
    temperature: float = 0.7
    top_p: float = 0.9
    system_prompt: Optional[str] = None


class BedrockClientError(Exception):
    """Custom exception for Bedrock client errors."""


class BedrockClient:
    """
    AWS Bedrock Claude client with cross-region inference and retry logic.
    """

    def __init__(
        self,
        primary_region: BedrockRegion = BedrockRegion.US_WEST_2,
        fallback_regions: Optional[List[BedrockRegion]] = None,
        model: ClaudeModel = ClaudeModel.CLAUDE_3_5_SONNET,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        timeout: int = 300,
    ):
        """
        Initialize Bedrock client with cross-region support.

        Args:
            primary_region: Primary region for Bedrock inference
            fallback_regions: List of fallback regions if primary fails
            model: Claude model to use for inference
            max_retries: Maximum number of retry attempts
            retry_delay: Base delay between retries (exponential backoff)
            timeout: Request timeout in seconds
        """
        self.primary_region = primary_region
        self.fallback_regions = fallback_regions or [
            BedrockRegion.US_EAST_1,
            BedrockRegion.EU_WEST_1,
        ]
        self.model = model
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Configure boto3 with timeout and retry settings
        self.config = Config(
            read_timeout=timeout,
            connect_timeout=30,
            retries={"max_attempts": 0},  # We handle retries manually
        )

        # Initialize clients for all regions using connection pool
        self.clients = {}
        self._initialize_clients()

        # Initialize performance optimizer
        self.optimizer = BedrockOptimizer()

        logger.info(f"Bedrock client initialized with model {model.value}")

    def _initialize_clients(self) -> None:
        """Initialize Bedrock clients for all configured regions."""
        regions = [self.primary_region] + self.fallback_regions

        for region in regions:
            try:
                client = boto3.client(
                    "bedrock-runtime", region_name=region.value, config=self.config
                )
                self.clients[region] = client
                logger.debug(f"Initialized Bedrock client for region {region.value}")
            except Exception as e:
                logger.warning(
                    f"Failed to initialize client for region {region.value}: {e}"
                )

    def _prepare_claude_payload(self, request: BedrockRequest) -> Dict[str, Any]:
        """
        Prepare the payload for Claude API call.

        Args:
            request: Bedrock request object

        Returns:
            Formatted payload for Claude API
        """
        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p,
            "messages": request.messages,
        }

        if request.system_prompt:
            payload["system"] = request.system_prompt

        return payload

    def _parse_claude_response(self, response_body: Dict[str, Any]) -> BedrockResponse:
        """
        Parse Claude API response into standardized format.

        Args:
            response_body: Raw response from Claude API

        Returns:
            Parsed BedrockResponse object
        """
        try:
            # Check if response has expected structure
            if "content" not in response_body:
                raise KeyError("Missing 'content' field in response")

            content = ""
            if response_body["content"]:
                if (
                    isinstance(response_body["content"], list)
                    and len(response_body["content"]) > 0
                ):
                    content = response_body["content"][0].get("text", "")
                else:
                    raise TypeError("Invalid content structure")

            usage = response_body.get("usage", {})
            stop_reason = response_body.get("stop_reason", "unknown")

            return BedrockResponse(
                content=content,
                usage=usage,
                model=self.model.value,
                stop_reason=stop_reason,
                success=True,
            )
        except (KeyError, IndexError, TypeError) as e:
            logger.error(f"Failed to parse Claude response: {e}")
            return BedrockResponse(
                content="",
                usage={},
                model=self.model.value,
                stop_reason="parse_error",
                success=False,
                error_message=f"Response parsing failed: {str(e)}",
            )

    def _should_retry(self, error: Exception, attempt: int) -> bool:
        """
        Determine if an error should trigger a retry.

        Args:
            error: The exception that occurred
            attempt: Current attempt number

        Returns:
            True if should retry, False otherwise
        """
        if attempt >= self.max_retries:
            return False

        # Retry on throttling, service unavailable, and timeout errors
        if isinstance(error, ClientError):
            error_code = error.response.get("Error", {}).get("Code", "")
            retry_codes = [
                "ThrottlingException",
                "ServiceUnavailableException",
                "InternalServerException",
                "ModelTimeoutException",
            ]
            return error_code in retry_codes

        # Retry on network-related errors
        if isinstance(error, (BotoCoreError, ConnectionError, TimeoutError)):
            return True

        return False

    def _calculate_retry_delay(self, attempt: int) -> float:
        """
        Calculate delay for exponential backoff.

        Args:
            attempt: Current attempt number

        Returns:
            Delay in seconds
        """
        return self.retry_delay * (2**attempt)

    @performance_timer("bedrock_invoke_claude")
    async def invoke_claude(
        self, request: BedrockRequest, region_override: Optional[BedrockRegion] = None
    ) -> BedrockResponse:
        """
        Invoke Claude model with cross-region fallback and retry logic.

        Args:
            request: Bedrock request object
            region_override: Override region selection

        Returns:
            BedrockResponse object with results or error information
        """
        regions_to_try = (
            [region_override]
            if region_override
            else [self.primary_region] + self.fallback_regions
        )

        # Check cache first (using messages content for hash)
        messages_str = json.dumps(request.messages, sort_keys=True)
        prompt_hash = hashlib.md5(
            messages_str.encode(), usedforsecurity=False
        ).hexdigest()
        cached_response = self.optimizer.get_cached_response(
            prompt_hash, self.model.value
        )
        if cached_response:
            return BedrockResponse(
                success=True,
                content=cached_response,
                model=self.model.value,
                region=self.primary_region.value,
                usage={"cached": True},
            )

        # Use the request as-is (no prompt optimization for messages format)
        optimized_request = request

        payload = self._prepare_claude_payload(optimized_request)

        last_error = None
        total_attempts = 0

        for region in regions_to_try:
            if region not in self.clients:
                logger.warning(f"No client available for region {region.value}")
                continue

            client = self.clients[region]

            for attempt in range(self.max_retries + 1):
                total_attempts += 1

                try:
                    logger.debug(
                        f"Invoking Claude in {region.value}, attempt {attempt + 1}"
                    )

                    response = client.invoke_model(
                        modelId=self.model.value,
                        body=json.dumps(payload),
                        contentType="application/json",
                        accept="application/json",
                    )

                    response_body = json.loads(response["body"].read())
                    result = self._parse_claude_response(response_body)
                    result.retry_count = total_attempts - 1
                    result.region = region.value

                    # Cache successful response
                    if result.success and result.content:
                        self.optimizer.cache_response(
                            prompt_hash, self.model.value, result.content
                        )

                    logger.info(f"Claude invocation successful in {region.value}")
                    return result

                except Exception as e:
                    last_error = e
                    logger.warning(
                        f"Claude invocation failed in {region.value}, attempt {attempt + 1}: {e}"
                    )

                    if self._should_retry(e, attempt):
                        delay = self._calculate_retry_delay(attempt)
                        logger.info(f"Retrying in {delay} seconds...")
                        time.sleep(delay)
                    else:
                        break

        # All regions and retries failed
        error_msg = f"All Claude invocation attempts failed. Last error: {last_error}"
        logger.error(error_msg)

        return BedrockResponse(
            content="",
            usage={},
            model=self.model.value,
            stop_reason="error",
            success=False,
            error_message=error_msg,
            retry_count=total_attempts - 1,
        )

    def invoke_claude_sync(
        self, request: BedrockRequest, region_override: Optional[BedrockRegion] = None
    ) -> BedrockResponse:
        """
        Synchronous version of Claude invocation.

        Args:
            request: Bedrock request object
            region_override: Override region selection

        Returns:
            BedrockResponse object with results or error information
        """
        import asyncio

        # Create new event loop if none exists or if current loop is running
        try:
            asyncio.get_running_loop()
            # If we're in a running loop, we need to create a new one in a thread
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    lambda: asyncio.run(self.invoke_claude(request, region_override))
                )
                return future.result()
        except RuntimeError:
            # No running loop, safe to create and run
            return asyncio.run(self.invoke_claude(request, region_override))

    def health_check(self) -> Dict[str, Any]:
        """
        Check health of Bedrock clients across all regions.

        Returns:
            Dictionary with health status for each region
        """
        health_status = {}

        for region, client in self.clients.items():
            try:
                # Simple test request to check connectivity
                test_request = BedrockRequest(
                    messages=[{"role": "user", "content": "Hello"}], max_tokens=10
                )

                response = self.invoke_claude_sync(test_request, region)
                health_status[region.value] = {
                    "status": "healthy" if response.success else "unhealthy",
                    "error": response.error_message,
                }
            except Exception as e:
                health_status[region.value] = {"status": "unhealthy", "error": str(e)}

        return health_status


# Global client instance
_bedrock_client: Optional[BedrockClient] = None


def get_bedrock_client() -> BedrockClient:
    """
    Get or create global Bedrock client instance with configuration.

    Returns:
        BedrockClient instance
    """
    global _bedrock_client

    if _bedrock_client is None:
        from src.config.bedrock_config import BedrockConfig

        _bedrock_client = BedrockClient(
            primary_region=BedrockConfig.get_primary_region(),
            fallback_regions=BedrockConfig.get_fallback_regions(),
            model=BedrockConfig.get_model(),
            max_retries=BedrockConfig.get_max_retries(),
            retry_delay=BedrockConfig.get_retry_delay(),
            timeout=BedrockConfig.get_timeout(),
        )

    return _bedrock_client


def create_bedrock_client(**kwargs) -> BedrockClient:
    """
    Create a new Bedrock client with custom configuration.

    Args:
        **kwargs: Configuration parameters for BedrockClient

    Returns:
        New BedrockClient instance
    """
    return BedrockClient(**kwargs)
