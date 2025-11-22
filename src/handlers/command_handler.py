"""Handler for slash commands."""

import logging
from typing import Optional

from slack_bolt import App

from ..llm import create_llm_provider
from ..llm.provider import LLMProvider
from ..utils.config import AppConfig, SlashCommandConfig
from ..utils.slack_helpers import format_slack_text

logger = logging.getLogger(__name__)


class CommandHandler:
    """Handles slash commands."""

    def __init__(
        self,
        app: App,
        config: AppConfig,
    ):
        """
        Initialize command handler.

        Args:
            app: Slack Bolt app
            config: Application configuration
        """
        self.app = app
        self.config = config

    def handle_command(self, ack, command: dict, say) -> None:
        """
        Handle a slash command.

        Args:
            ack: Slack acknowledgment function
            command: Command payload
            say: Slack say function
        """
        # Acknowledge command immediately
        ack()

        try:
            command_text = command.get("command")
            command_config = self._get_command_config(command_text)

            if not command_config:
                logger.warning(f"Unconfigured command: {command_text}")
                say("Sorry, this command is not configured.")
                return

            # Get the text passed with the command
            user_text = command.get("text", "")

            if not user_text:
                say(
                    f"Please provide text after the command. "
                    f"Usage: `{command_text} <your text>`"
                )
                return

            # Check message length
            if len(user_text) > self.config.settings.max_message_length:
                say(
                    f"Your message is too long ({len(user_text)} characters). "
                    f"Maximum is {self.config.settings.max_message_length} characters."
                )
                return

            logger.info(f"Processing command: {command_text}")

            # Generate response
            response_text = self._generate_response(user_text, command_config)

            if response_text:
                formatted_text = format_slack_text(response_text)
                say(formatted_text)
                logger.info(f"Command {command_text} completed successfully")
            else:
                say("Sorry, I encountered an error processing your request.")
                logger.error(f"Failed to generate response for command {command_text}")

        except Exception as e:
            logger.error(f"Error handling command: {e}", exc_info=True)
            say("Sorry, an error occurred while processing your command.")

    def _get_command_config(self, command: str) -> Optional[SlashCommandConfig]:
        """Get configuration for a command."""
        for cmd_config in self.config.slash_commands:
            if cmd_config.command == command and cmd_config.enabled:
                return cmd_config
        return None

    def _generate_response(
        self,
        text: str,
        command_config: SlashCommandConfig,
    ) -> Optional[str]:
        """
        Generate LLM response for command.

        Args:
            text: User's text
            command_config: Command configuration

        Returns:
            Response text or None on error
        """
        try:
            # Create LLM provider from config
            provider = create_llm_provider(command_config.llm.to_provider_config())

            # Create simple text message
            message = {"role": "user", "content": [{"type": "text", "text": text}]}

            # Generate response
            response = provider.generate_response(
                messages=[message],
                system_prompt=command_config.system_prompt,
                max_tokens=command_config.llm.max_tokens,
                temperature=command_config.llm.temperature,
            )

            return response

        except Exception as e:
            logger.error(f"Error generating response: {e}", exc_info=True)
            return None
