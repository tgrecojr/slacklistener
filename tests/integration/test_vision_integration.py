"""Integration tests for vision/image processing capabilities."""

from unittest.mock import Mock, patch, MagicMock

import pytest
import responses

from src.handlers.message_handler import MessageHandler
from src.utils.config import (
    AppConfig,
    ChannelConfig,
    LLMConfig,
    ResponseConfig,
    GlobalSettings,
)


@pytest.fixture
def vision_channel_config():
    """Configuration for vision-enabled channel."""
    return ChannelConfig(
        channel_id="C_VISION",
        channel_name="design-review",
        enabled=True,
        keywords=[],
        require_image=True,
        llm=LLMConfig(
            api_key="test-api-key",
            model="anthropic/claude-3.5-sonnet",
            max_tokens=2048,
            temperature=0.7,
        ),
        system_prompt="You are a design review expert. Analyze the provided image in detail.",
        response=ResponseConfig(thread_reply=True, add_reaction="eyes"),
    )


@pytest.fixture
def vision_app_config(vision_channel_config):
    """App config with vision channel."""
    return AppConfig(
        channels=[vision_channel_config],
        slash_commands=[],
        settings=GlobalSettings(),
    )


class TestVisionIntegration:
    """Integration tests for vision capabilities."""

    @responses.activate
    @patch("src.handlers.message_handler.OpenRouterClient")
    def test_complete_image_workflow(
        self,
        mock_client_class,
        vision_app_config,
        sample_image_bytes,
    ):
        """Test complete workflow: Slack image -> OpenRouter vision -> Response."""
        # Mock LLM client
        mock_client = MagicMock()
        mock_client.generate_response.return_value = (
            "This is a detailed design review response"
        )
        mock_client_class.return_value = mock_client

        # Mock Slack app
        app = MagicMock()
        app.client = MagicMock()

        # Create message handler
        handler = MessageHandler(
            app=app,
            config=vision_app_config,
            bot_user_id="U_BOT",
            bot_token="xoxb-test-token",
        )

        # Create Slack event with image
        image_url = "https://files.slack.com/files-pri/T12345/screenshot.png"
        event = {
            "type": "message",
            "user": "U_USER",
            "text": "Please review this design",
            "channel": "C_VISION",
            "ts": "1234567890.123456",
            "files": [
                {
                    "id": "F12345",
                    "name": "design.png",
                    "mimetype": "image/png",
                    "url_private": image_url,
                }
            ],
        }

        # Mock file download
        responses.add(responses.GET, image_url, body=sample_image_bytes, status=200)

        # Mock Slack client methods
        say = Mock()
        client = Mock()
        client.reactions_add = Mock()

        # Handle the message
        handler.handle_message(event, say, client)

        # Verify reaction was added
        client.reactions_add.assert_called_once_with(
            channel="C_VISION", timestamp="1234567890.123456", name="eyes"
        )

        # Verify client was called
        assert mock_client.generate_response.called
        provider_call = mock_client.generate_response.call_args

        # Verify message has both image and text content
        messages = provider_call.kwargs["messages"]
        assert len(messages) == 1
        content = messages[0]["content"]
        # Should have image_url and text (OpenRouter/OpenAI format)
        assert len([c for c in content if c["type"] == "image_url"]) >= 1
        assert len([c for c in content if c["type"] == "text"]) >= 1

        # Verify response was sent
        say.assert_called_once()
        assert say.call_args.kwargs["thread_ts"] == "1234567890.123456"

    @responses.activate
    @patch("src.handlers.message_handler.OpenRouterClient")
    def test_multiple_images_workflow(
        self,
        mock_client_class,
        vision_app_config,
        sample_image_bytes,
    ):
        """Test handling multiple images in one message."""
        # Mock LLM client
        mock_client = MagicMock()
        mock_client.generate_response.return_value = "Multi-image comparison response"
        mock_client_class.return_value = mock_client

        app = MagicMock()
        handler = MessageHandler(
            app=app,
            config=vision_app_config,
            bot_user_id="U_BOT",
            bot_token="xoxb-test-token",
        )

        # Event with multiple images
        event = {
            "type": "message",
            "user": "U_USER",
            "text": "Compare these designs",
            "channel": "C_VISION",
            "ts": "1234567890.123456",
            "files": [
                {
                    "name": "design1.png",
                    "mimetype": "image/png",
                    "url_private": "https://files.slack.com/design1.png",
                },
                {
                    "name": "design2.jpg",
                    "mimetype": "image/jpeg",
                    "url_private": "https://files.slack.com/design2.jpg",
                },
            ],
        }

        # Mock downloads
        for file in event["files"]:
            responses.add(
                responses.GET, file["url_private"], body=sample_image_bytes, status=200
            )

        say = Mock()
        client = Mock()
        client.reactions_add = Mock()

        handler.handle_message(event, say, client)

        # Verify client was called
        provider_call = mock_client.generate_response.call_args
        messages = provider_call.kwargs["messages"]

        # Should have 2 images + 1 text = 3 content blocks
        assert len(messages[0]["content"]) == 3

        # Verify we have 2 images (image_url format for OpenRouter/OpenAI)
        images = [c for c in messages[0]["content"] if c["type"] == "image_url"]
        assert len(images) == 2

    @responses.activate
    @patch("src.handlers.message_handler.OpenRouterClient")
    def test_vision_error_handling(
        self,
        mock_client_class,
        vision_app_config,
        sample_image_bytes,
    ):
        """Test error handling in vision workflow."""
        # Setup LLM client to fail
        mock_client = MagicMock()
        mock_client.generate_response.side_effect = Exception("API error")
        mock_client_class.return_value = mock_client

        app = MagicMock()
        handler = MessageHandler(
            app=app,
            config=vision_app_config,
            bot_user_id="U_BOT",
            bot_token="xoxb-test-token",
        )

        # Mock file download
        responses.add(
            responses.GET,
            "https://files.slack.com/image.png",
            body=sample_image_bytes,
            status=200,
        )

        event = {
            "type": "message",
            "user": "U_USER",
            "text": "Review this",
            "channel": "C_VISION",
            "ts": "123",
            "files": [
                {
                    "name": "image.png",
                    "mimetype": "image/png",
                    "url_private": "https://files.slack.com/image.png",
                }
            ],
        }

        say = Mock()
        client = Mock()
        client.reactions_add = Mock()

        handler.handle_message(event, say, client)

        # Should handle error gracefully (not crash)
        # Reaction should still be added before LLM call
        client.reactions_add.assert_called_once()
        # Should not send response on error
        say.assert_not_called()
