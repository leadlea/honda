"""
Configuration settings for AWS Bedrock Claude integration.
"""

import os
from typing import List

from src.services.bedrock_client import BedrockRegion, ClaudeModel


class BedrockConfig:
    """Configuration class for Bedrock settings."""

    # Default regions in order of preference
    DEFAULT_PRIMARY_REGION = BedrockRegion.AP_NORTHEAST_1
    DEFAULT_FALLBACK_REGIONS = [BedrockRegion.US_WEST_2, BedrockRegion.US_EAST_1]

    # Default model settings
    DEFAULT_MODEL = ClaudeModel.CLAUDE_3_5_SONNET
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_RETRY_DELAY = 1.0
    DEFAULT_TIMEOUT = 300

    # Default request parameters
    DEFAULT_MAX_TOKENS = 4000
    DEFAULT_TEMPERATURE = 0.7
    DEFAULT_TOP_P = 0.9

    @classmethod
    def get_primary_region(cls) -> BedrockRegion:
        """Get primary region from environment or default."""
        region_name = os.getenv(
            "BEDROCK_PRIMARY_REGION", cls.DEFAULT_PRIMARY_REGION.value
        )
        try:
            return BedrockRegion(region_name)
        except ValueError:
            return cls.DEFAULT_PRIMARY_REGION

    @classmethod
    def get_fallback_regions(cls) -> List[BedrockRegion]:
        """Get fallback regions from environment or default."""
        regions_str = os.getenv("BEDROCK_FALLBACK_REGIONS")
        if not regions_str:
            return cls.DEFAULT_FALLBACK_REGIONS

        regions = []
        for region_name in regions_str.split(","):
            region_name = region_name.strip()
            try:
                regions.append(BedrockRegion(region_name))
            except ValueError:
                continue

        return regions if regions else cls.DEFAULT_FALLBACK_REGIONS

    @classmethod
    def get_model(cls) -> ClaudeModel:
        """Get Claude model from environment or default."""
        model_id = os.getenv("BEDROCK_MODEL_ID", cls.DEFAULT_MODEL.value)
        try:
            return ClaudeModel(model_id)
        except ValueError:
            return cls.DEFAULT_MODEL

    @classmethod
    def get_max_retries(cls) -> int:
        """Get max retries from environment or default."""
        try:
            return int(os.getenv("BEDROCK_MAX_RETRIES", cls.DEFAULT_MAX_RETRIES))
        except (ValueError, TypeError):
            return cls.DEFAULT_MAX_RETRIES

    @classmethod
    def get_retry_delay(cls) -> float:
        """Get retry delay from environment or default."""
        try:
            return float(os.getenv("BEDROCK_RETRY_DELAY", cls.DEFAULT_RETRY_DELAY))
        except (ValueError, TypeError):
            return cls.DEFAULT_RETRY_DELAY

    @classmethod
    def get_timeout(cls) -> int:
        """Get timeout from environment or default."""
        try:
            return int(os.getenv("BEDROCK_TIMEOUT", cls.DEFAULT_TIMEOUT))
        except (ValueError, TypeError):
            return cls.DEFAULT_TIMEOUT

    @classmethod
    def get_max_tokens(cls) -> int:
        """Get default max tokens from environment or default."""
        try:
            return int(os.getenv("BEDROCK_MAX_TOKENS", cls.DEFAULT_MAX_TOKENS))
        except (ValueError, TypeError):
            return cls.DEFAULT_MAX_TOKENS

    @classmethod
    def get_temperature(cls) -> float:
        """Get default temperature from environment or default."""
        try:
            return float(os.getenv("BEDROCK_TEMPERATURE", cls.DEFAULT_TEMPERATURE))
        except (ValueError, TypeError):
            return cls.DEFAULT_TEMPERATURE

    @classmethod
    def get_top_p(cls) -> float:
        """Get default top_p from environment or default."""
        try:
            return float(os.getenv("BEDROCK_TOP_P", cls.DEFAULT_TOP_P))
        except (ValueError, TypeError):
            return cls.DEFAULT_TOP_P

    @classmethod
    def is_enabled(cls) -> bool:
        """Check if Bedrock is enabled."""
        return os.getenv("BEDROCK_ENABLED", "true").lower() in (
            "true",
            "1",
            "yes",
            "on",
        )

    @classmethod
    def get_log_level(cls) -> str:
        """Get logging level for Bedrock operations."""
        return os.getenv("BEDROCK_LOG_LEVEL", "INFO").upper()


# Environment variable documentation
BEDROCK_ENV_VARS = {
    "BEDROCK_ENABLED": "Enable/disable Bedrock integration (true/false)",
    "BEDROCK_PRIMARY_REGION": "Primary AWS region for Bedrock (us-west-2, us-east-1, eu-west-1)",
    "BEDROCK_FALLBACK_REGIONS": "Comma-separated list of fallback regions",
    "BEDROCK_MODEL_ID": "Claude model ID to use",
    "BEDROCK_MAX_RETRIES": "Maximum number of retry attempts (integer)",
    "BEDROCK_RETRY_DELAY": "Base delay between retries in seconds (float)",
    "BEDROCK_TIMEOUT": "Request timeout in seconds (integer)",
    "BEDROCK_MAX_TOKENS": "Default maximum tokens for requests (integer)",
    "BEDROCK_TEMPERATURE": "Default temperature for AI generation (0.0-1.0)",
    "BEDROCK_TOP_P": "Default top_p for AI generation (0.0-1.0)",
    "BEDROCK_LOG_LEVEL": "Logging level (DEBUG, INFO, WARNING, ERROR)",
}
