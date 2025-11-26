"""OpenRouter LLM client."""

import logging
from typing import List, Dict, Any, Optional

from openai import OpenAI

logger = logging.getLogger(__name__)


class OpenRouterClient:
    """OpenRouter LLM client using OpenAI SDK."""

    def __init__(
        self,
        api_key: str,
        model: str = "anthropic/claude-3.5-sonnet",
        base_url: str = "https://openrouter.ai/api/v1",
    ):
        """
        Initialize OpenRouter client.

        Args:
            api_key: OpenRouter API key
            model: Model identifier (e.g., "anthropic/claude-3.5-sonnet")
            base_url: OpenRouter API base URL
        """
        self.model = model
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
        )
        logger.info(f"Initialized OpenRouter client with model: {model}")

    def generate_response(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> Optional[str]:
        """
        Generate a response from the LLM.

        Args:
            messages: List of message dicts with "role" and "content"
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0-1)

        Returns:
            Generated text response or None on error
        """
        try:
            # Prepare messages
            api_messages = []

            # Add system prompt if provided
            if system_prompt:
                api_messages.append({"role": "system", "content": system_prompt})

            # Add conversation messages
            api_messages.extend(messages)

            logger.debug(f"Sending request to OpenRouter with {len(api_messages)} messages")

            # Call OpenRouter API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=api_messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )

            # Extract response text
            if response.choices and len(response.choices) > 0:
                content = response.choices[0].message.content
                logger.debug(f"Received response: {len(content) if content else 0} characters")
                return content
            else:
                logger.warning("No response choices returned from OpenRouter")
                return None

        except Exception as e:
            logger.error(f"Error calling OpenRouter API: {e}", exc_info=True)
            return None
