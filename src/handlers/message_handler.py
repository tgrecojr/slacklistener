"""Handler for channel message events."""

import base64
import logging
from typing import Optional, List, Dict, Any

from slack_bolt import App

from ..llm import OpenRouterClient
from ..utils.config import AppConfig, ChannelConfig
from ..utils.slack_helpers import (
    matches_keywords,
    extract_message_images,
    should_ignore_message,
    format_slack_text,
)

logger = logging.getLogger(__name__)


class MessageHandler:
    """Handles incoming Slack messages."""

    def __init__(
        self,
        app: App,
        config: AppConfig,
        bot_user_id: str,
        bot_token: str,
    ):
        """
        Initialize message handler.

        Args:
            app: Slack Bolt app
            config: Application configuration
            bot_user_id: Bot's user ID
            bot_token: Bot token for file downloads
        """
        self.app = app
        self.config = config
        self.bot_user_id = bot_user_id
        self.bot_token = bot_token
        self._client_cache: Dict[tuple, Any] = {}

    def handle_message(self, event: dict, say, client) -> None:
        """
        Handle a message event.

        Args:
            event: Slack message event
            say: Slack say function
            client: Slack client
        """
        try:
            # Check if we should ignore this message
            if should_ignore_message(
                event,
                self.bot_user_id,
                self.config.settings.ignore_bot_messages,
                self.config.settings.ignore_self,
            ):
                return

            # Get channel configuration
            channel_id = event.get("channel")
            channel_config = self._get_channel_config(channel_id)

            if not channel_config:
                # Not configured for this channel
                return

            # Get message text
            text = event.get("text", "")

            # Check message length
            if len(text) > self.config.settings.max_message_length:
                logger.warning(
                    f"Message too long ({len(text)} chars) in channel {channel_config.channel_name}"
                )
                return

            # Check if message has images
            images = extract_message_images(event, client, self.bot_token)
            # Validate that images have actual data, not just that files were detected
            valid_images = [img for img in images if img.get("data")]
            has_images = len(valid_images) > 0

            # Check if we should respond to this message
            if channel_config.require_image and not has_images:
                logger.debug(
                    "Message has no images with valid data, skipping (require_image=True)"
                )
                return

            # Check keywords
            if not matches_keywords(
                text, channel_config.keywords, channel_config.case_sensitive
            ):
                logger.debug(
                    f"No keyword match in channel {channel_config.channel_name}"
                )
                return

            # Add reaction if configured
            if channel_config.response.add_reaction:
                try:
                    client.reactions_add(
                        channel=channel_id,
                        timestamp=event.get("ts"),
                        name=channel_config.response.add_reaction,
                    )
                except Exception as e:
                    logger.error(f"Error adding reaction: {e}")

            # Generate response
            logger.info(
                f"Processing message in {channel_config.channel_name} "
                f"(images: {len(valid_images)}, keywords matched)"
            )

            response_text = self._generate_response(text, valid_images, channel_config)

            if response_text:
                # Send response
                self._send_response(
                    say,
                    response_text,
                    event.get("ts"),
                    channel_config.response.thread_reply,
                )
            else:
                logger.error("Failed to generate response")

        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)

    def _get_channel_config(self, channel_id: str) -> Optional[ChannelConfig]:
        """Get configuration for a channel."""
        for channel in self.config.channels:
            if channel.channel_id == channel_id and channel.enabled:
                return channel
        return None

    def _get_client(self, channel_config: ChannelConfig) -> OpenRouterClient:
        """Get or create a cached OpenRouter client for the given config."""
        cache_key = (
            channel_config.llm.api_key,
            channel_config.llm.model,
            channel_config.llm.base_url,
            channel_config.llm.site_url,
            channel_config.llm.site_name,
            self.config.settings.llm_timeout,
        )
        if cache_key not in self._client_cache:
            self._client_cache[cache_key] = OpenRouterClient(
                api_key=channel_config.llm.api_key,
                model=channel_config.llm.model,
                base_url=channel_config.llm.base_url,
                site_url=channel_config.llm.site_url,
                site_name=channel_config.llm.site_name,
                timeout=self.config.settings.llm_timeout,
            )
        return self._client_cache[cache_key]

    def _format_message(
        self, text: str, images: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Format a message with text and optional images for LLM providers.

        Args:
            text: Message text
            images: List of image dicts with 'data' (bytes), 'mimetype' (str), and 'filename' (str)

        Returns:
            Formatted message dict
        """
        content = []

        # Add images if provided
        if images:
            for image_info in images:
                image_data = image_info.get("data")
                mimetype = image_info.get("mimetype", "image/jpeg")

                if image_data:
                    # Format for OpenAI API (used by OpenRouter)
                    base64_data = base64.b64encode(image_data).decode("utf-8")
                    content.append(
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mimetype};base64,{base64_data}"
                            },
                        }
                    )

        # Add text content
        # If there's no text but we have images, add a placeholder
        if text:
            content.append({"type": "text", "text": text})
        elif images:
            # Images present but no text - add placeholder for LLM to analyze
            content.append({"type": "text", "text": "Please analyze this image."})
        else:
            # No images and no text - add minimal content to avoid API error
            content.append({"type": "text", "text": "Hello"})

        return {"role": "user", "content": content}

    def _generate_response(
        self,
        text: str,
        images: list,
        channel_config: ChannelConfig,
    ) -> Optional[str]:
        """
        Generate LLM response using OpenRouter.

        Args:
            text: Message text
            images: List of image dicts with 'data' (bytes), 'mimetype' (str), and 'filename' (str)
            channel_config: Channel configuration

        Returns:
            Response text or None on error
        """
        try:
            # Get or create OpenRouter client from config
            client = self._get_client(channel_config)

            # Format message
            message = self._format_message(text, images)

            # Generate response
            response = client.generate_response(
                messages=[message],
                system_prompt=channel_config.system_prompt,
                max_tokens=channel_config.llm.max_tokens,
                temperature=channel_config.llm.temperature,
            )

            return response

        except Exception as e:
            logger.error(f"Error generating response: {e}", exc_info=True)
            return None

    def _send_response(
        self,
        say,
        text: str,
        thread_ts: Optional[str],
        thread_reply: bool,
    ) -> None:
        """
        Send response to Slack.

        Args:
            say: Slack say function
            text: Response text
            thread_ts: Thread timestamp
            thread_reply: Whether to reply in thread
        """
        # Format text
        formatted_text = format_slack_text(text)

        # Send message
        if thread_reply and thread_ts:
            say(text=formatted_text, thread_ts=thread_ts)
        else:
            say(text=formatted_text)

        logger.info("Response sent successfully")
