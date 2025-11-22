"""OpenAI API LLM provider implementation."""

import logging
from typing import List, Dict, Any, Optional

from ..provider import LLMProvider

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    """OpenAI API LLM provider."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
    ):
        """
        Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key
            model: Model name
        """
        try:
            import openai
        except ImportError:
            raise ImportError(
                "openai is required for OpenAIProvider. "
                "Install it with: pip install openai"
            )

        self.api_key = api_key
        self.model = model
        self.client = openai.OpenAI(api_key=api_key)
        logger.info(f"Initialized OpenAI provider with model {model}")

    def generate_response(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> Optional[str]:
        """
        Generate a response using OpenAI API.

        Args:
            messages: List of message dicts with "role" and "content"
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0-1)

        Returns:
            Generated text response or None on error
        """
        try:
            logger.debug(f"Invoking OpenAI model: {self.model}")

            # Prepare messages - add system prompt if provided
            api_messages = []
            if system_prompt:
                api_messages.append({"role": "system", "content": system_prompt})

            # Add user messages
            api_messages.extend(messages)

            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=api_messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )

            # Extract and return the response text
            if response.choices and len(response.choices) > 0:
                return response.choices[0].message.content
            else:
                logger.error(f"Unexpected response format: {response}")
                return None

        except Exception as e:
            logger.error(f"OpenAI API error: {e}", exc_info=True)
            return None
