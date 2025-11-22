"""Factory for creating LLM provider instances."""

import logging
from typing import Dict, Any

from .provider import LLMProvider
from .providers.bedrock_provider import BedrockProvider
from .providers.anthropic_provider import AnthropicProvider
from .providers.openai_provider import OpenAIProvider

logger = logging.getLogger(__name__)


def create_llm_provider(provider_config: Dict[str, Any]) -> LLMProvider:
    """
    Factory function to create LLM provider instances based on configuration.

    Args:
        provider_config: Dictionary with provider configuration containing:
            - provider: Provider type ("bedrock", "anthropic", "openai")
            - Additional provider-specific config

    Returns:
        LLMProvider instance

    Raises:
        ValueError: If provider type is unknown or required config is missing
    """
    provider_type = provider_config.get("provider", "bedrock").lower()

    logger.info(f"Creating LLM provider: {provider_type}")

    if provider_type == "bedrock":
        return BedrockProvider(
            region=provider_config.get("region", "us-east-1"),
            model_id=provider_config.get("model_id", "anthropic.claude-3-5-haiku-20241022-v1:0"),
            aws_access_key_id=provider_config.get("aws_access_key_id"),
            aws_secret_access_key=provider_config.get("aws_secret_access_key"),
        )

    elif provider_type == "anthropic":
        api_key = provider_config.get("api_key")
        if not api_key:
            raise ValueError("api_key is required for Anthropic provider")

        return AnthropicProvider(
            api_key=api_key,
            model=provider_config.get("model", "claude-3-5-sonnet-20241022"),
        )

    elif provider_type == "openai":
        api_key = provider_config.get("api_key")
        if not api_key:
            raise ValueError("api_key is required for OpenAI provider")

        return OpenAIProvider(
            api_key=api_key,
            model=provider_config.get("model", "gpt-4o"),
        )

    else:
        raise ValueError(
            f"Unknown LLM provider: {provider_type}. "
            f"Supported providers: bedrock, anthropic, openai"
        )
