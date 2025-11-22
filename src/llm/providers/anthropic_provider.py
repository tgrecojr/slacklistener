"""Anthropic direct API LLM provider implementation."""

import logging
from typing import List, Dict, Any, Optional

from ..provider import LLMProvider

logger = logging.getLogger(__name__)


class AnthropicProvider(LLMProvider):
    """Anthropic direct API LLM provider."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-5-sonnet-20241022",
    ):
        """
        Initialize Anthropic provider.

        Args:
            api_key: Anthropic API key
            model: Model name
        """
        try:
            import anthropic
        except ImportError:
            raise ImportError(
                "anthropic is required for AnthropicProvider. "
                "Install it with: pip install anthropic"
            )

        self.api_key = api_key
        self.model = model
        self.client = anthropic.Anthropic(api_key=api_key)
        logger.info(f"Initialized Anthropic provider with model {model}")

    def generate_response(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> Optional[str]:
        """
        Generate a response using Anthropic API.

        Args:
            messages: List of message dicts with "role" and "content"
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0-1)

        Returns:
            Generated text response or None on error
        """
        try:
            logger.debug(f"Invoking Anthropic model: {self.model}")

            # Build the API call arguments
            api_args = {
                "model": self.model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": messages,
            }

            if system_prompt:
                api_args["system"] = system_prompt

            # Call Anthropic API
            response = self.client.messages.create(**api_args)

            # Extract and return the response text
            if response.content and len(response.content) > 0:
                return response.content[0].text
            else:
                logger.error(f"Unexpected response format: {response}")
                return None

        except Exception as e:
            logger.error(f"Anthropic API error: {e}", exc_info=True)
            return None
