"""Handler for slash commands."""

import logging
from datetime import datetime
from typing import Optional

from slack_bolt import App

from ..llm import OpenRouterClient
from ..tools.factory import create_tool
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
        self._client_cache: dict[tuple, any] = {}

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

            # Generate response with context
            response_text = self._generate_response(user_text, command_config, command)

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

    def _get_client(self, command_config: SlashCommandConfig) -> OpenRouterClient:
        """Get or create a cached OpenRouter client for the given config."""
        cache_key = (
            command_config.llm.api_key,
            command_config.llm.model,
            command_config.llm.base_url,
            command_config.llm.site_url,
            command_config.llm.site_name,
            self.config.settings.llm_timeout,
        )
        if cache_key not in self._client_cache:
            self._client_cache[cache_key] = OpenRouterClient(
                api_key=command_config.llm.api_key,
                model=command_config.llm.model,
                base_url=command_config.llm.base_url,
                site_url=command_config.llm.site_url,
                site_name=command_config.llm.site_name,
                timeout=self.config.settings.llm_timeout,
            )
        return self._client_cache[cache_key]

    def _generate_response(
        self,
        text: str,
        command_config: SlashCommandConfig,
        command: dict,
    ) -> Optional[str]:
        """
        Generate LLM response for command using OpenRouter.

        Args:
            text: User's text
            command_config: Command configuration
            command: Full command payload for context

        Returns:
            Response text or None on error
        """
        try:
            # Execute tools and collect enrichment data
            tool_results = []
            if command_config.tools:
                logger.info(f"Executing {len(command_config.tools)} tool(s)")

                # Build context for tools
                tool_context = {
                    "user_input": text,
                    "user_id": command.get("user_id"),
                    "channel_id": command.get("channel_id"),
                    "timestamp": datetime.now().isoformat(),
                }

                for tool_config in command_config.tools:
                    try:
                        tool = create_tool(tool_config)
                        logger.info(f"Executing tool: {tool.get_name()}")
                        result = tool.execute(tool_context)
                        tool_results.append(
                            f"\n--- {tool.get_name()} Data ---\n{result}"
                        )
                        logger.info(f"Tool {tool.get_name()} completed successfully")
                    except Exception as e:
                        logger.error(
                            f"Error executing tool {tool_config.get('type')}: {e}",
                            exc_info=True,
                        )
                        # Continue with other tools even if one fails

            # Build system prompt with tool enrichment
            system_prompt = command_config.system_prompt
            if tool_results:
                enrichment = "\n".join(tool_results)
                system_prompt = f"{command_config.system_prompt}\n\n{enrichment}"
                logger.debug(
                    f"Enriched system prompt with {len(tool_results)} tool result(s)"
                )

            # Get or create OpenRouter client from config
            client = self._get_client(command_config)

            # Create simple text message
            message = {"role": "user", "content": [{"type": "text", "text": text}]}

            # Generate response
            response = client.generate_response(
                messages=[message],
                system_prompt=system_prompt,
                max_tokens=command_config.llm.max_tokens,
                temperature=command_config.llm.temperature,
            )

            return response

        except Exception as e:
            logger.error(f"Error generating response: {e}", exc_info=True)
            return None
