"""Abstract base class for tools/helpers."""

from abc import ABC, abstractmethod
from typing import Dict, Any


class Tool(ABC):
    """Abstract base class for tools that enrich context before LLM invocation."""

    @abstractmethod
    def execute(self, context: Dict[str, Any]) -> str:
        """
        Execute the tool and return enrichment data.

        Args:
            context: Execution context including:
                - user_input: The user's message/command text
                - channel_id: Slack channel ID (if applicable)
                - user_id: Slack user ID (if applicable)
                - timestamp: Current timestamp
                - Any other relevant context

        Returns:
            String containing the enrichment data to be added to the prompt

        Raises:
            Exception: If tool execution fails
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """
        Get the tool name for logging/debugging.

        Returns:
            Tool name
        """
        pass
