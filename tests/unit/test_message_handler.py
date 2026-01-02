"""Tests for message handler."""

from unittest.mock import Mock, MagicMock, patch

import pytest

from src.handlers.message_handler import MessageHandler


@pytest.fixture
def message_handler(mock_slack_app, sample_app_config):
    """Create a message handler instance."""
    return MessageHandler(
        app=mock_slack_app,
        config=sample_app_config,
        bot_user_id="U12345",
        bot_token="xoxb-test-token",
    )


class TestMessageHandler:
    """Tests for MessageHandler class."""

    def test_initialization(self, message_handler):
        """Test handler initialization."""
        assert message_handler.bot_user_id == "U12345"
        assert message_handler.bot_token == "xoxb-test-token"

    @patch("src.handlers.message_handler.OpenRouterClient")
    def test_handle_message_with_keyword(
        self, mock_client_class, message_handler, sample_slack_message_event
    ):
        """Test handling message with matching keyword."""
        # Mock LLM client
        mock_client = Mock()
        mock_client.generate_response.return_value = "test response from Claude"
        mock_client_class.return_value = mock_client

        say = Mock()
        client = Mock()
        client.reactions_add = Mock()

        message_handler.handle_message(sample_slack_message_event, say, client)

        # Should add reaction
        client.reactions_add.assert_called_once()

        # Should send response
        say.assert_called_once()
        call_args = say.call_args
        assert "test response from Claude" in call_args.kwargs["text"]

    def test_handle_message_no_keyword_match(self, message_handler):
        """Test handling message without matching keyword."""
        event = {
            "type": "message",
            "user": "U67890",
            "text": "Random message without keywords",
            "channel": "C12345",
            "ts": "1234567890.123456",
        }

        say = Mock()
        client = Mock()

        message_handler.handle_message(event, say, client)

        # Should not send response
        say.assert_not_called()

    def test_handle_message_bot_message(self, message_handler):
        """Test ignoring bot messages."""
        event = {
            "type": "message",
            "bot_id": "B12345",
            "text": "Bot message",
            "channel": "C12345",
        }

        say = Mock()
        client = Mock()

        message_handler.handle_message(event, say, client)

        # Should be ignored
        say.assert_not_called()

    def test_handle_message_self_message(self, message_handler):
        """Test ignoring own messages."""
        event = {
            "type": "message",
            "user": "U12345",  # Same as bot_user_id
            "text": "My own message",
            "channel": "C12345",
        }

        say = Mock()
        client = Mock()

        message_handler.handle_message(event, say, client)

        # Should be ignored
        say.assert_not_called()

    def test_handle_message_unconfigured_channel(self, message_handler):
        """Test message in unconfigured channel."""
        event = {
            "type": "message",
            "user": "U67890",
            "text": "help needed",
            "channel": "C99999",  # Not in config
        }

        say = Mock()
        client = Mock()

        message_handler.handle_message(event, say, client)

        # Should be ignored
        say.assert_not_called()

    @patch("src.handlers.message_handler.OpenRouterClient")
    def test_handle_message_thread_reply(
        self, mock_client_class, message_handler, sample_slack_message_event
    ):
        """Test replying in thread."""
        # Mock LLM client
        mock_client = Mock()
        mock_client.generate_response.return_value = "test response"
        mock_client_class.return_value = mock_client

        say = Mock()
        client = Mock()
        client.reactions_add = Mock()

        message_handler.handle_message(sample_slack_message_event, say, client)

        # Should reply in thread
        call_args = say.call_args
        assert call_args.kwargs["thread_ts"] == "1234567890.123456"

    def test_handle_message_too_long(self, message_handler):
        """Test handling very long messages."""
        event = {
            "type": "message",
            "user": "U67890",
            "text": "help " + ("A" * 20000),  # Very long message
            "channel": "C12345",
        }

        say = Mock()
        client = Mock()

        message_handler.handle_message(event, say, client)

        # Should be ignored due to length
        say.assert_not_called()

    @patch("src.handlers.message_handler.OpenRouterClient")
    @patch("src.handlers.message_handler.extract_message_images")
    def test_handle_message_with_image(
        self,
        mock_extract_images,
        mock_client_class,
        message_handler,
        sample_slack_image_event,
        sample_image_info,
    ):
        """Test handling message with image."""
        # Mock LLM client
        mock_client = Mock()
        mock_client.generate_response.return_value = "image analysis response"
        mock_client_class.return_value = mock_client

        # Mock image extraction
        mock_extract_images.return_value = [sample_image_info]

        # Use image analysis channel
        event = sample_slack_image_event.copy()
        event["channel"] = "C54321"  # Image analysis channel from fixture

        # Need to add the image channel to config
        from src.utils.config import ChannelConfig, LLMConfig, ResponseConfig

        image_channel = ChannelConfig(
            channel_id="C54321",
            channel_name="image-analysis",
            enabled=True,
            keywords=[],
            require_image=True,
            llm=LLMConfig(api_key="test-key", model="test-model"),
            system_prompt="Analyze images",
            response=ResponseConfig(),
        )
        message_handler.config.channels.append(image_channel)

        say = Mock()
        client = Mock()
        client.reactions_add = Mock()

        message_handler.handle_message(event, say, client)

        # Should process with images and send response
        say.assert_called_once()

    @patch("src.handlers.message_handler.extract_message_images")
    def test_handle_message_require_image_no_image(
        self, mock_extract_images, message_handler, sample_slack_message_event
    ):
        """Test channel requiring images rejects messages without images."""
        # Mock no images
        mock_extract_images.return_value = []

        # Create image-required channel
        from src.utils.config import ChannelConfig, LLMConfig, ResponseConfig

        image_channel = ChannelConfig(
            channel_id="C12345",
            channel_name="image-only",
            enabled=True,
            keywords=[],
            require_image=True,
            llm=LLMConfig(api_key="test-key", model="test-model"),
            system_prompt="Test",
            response=ResponseConfig(),
        )

        # Replace channel in config
        message_handler.config.channels = [image_channel]

        say = Mock()
        client = Mock()

        message_handler.handle_message(sample_slack_message_event, say, client)

        # Should not respond (no image)
        say.assert_not_called()

    @patch("src.handlers.message_handler.OpenRouterClient")
    def test_generate_response_error_handling(
        self, mock_client_class, message_handler
    ):
        """Test error handling in response generation."""
        # Make client raise exception (error case)
        mock_client_class.side_effect = Exception("LLM error")

        say = Mock()
        client = Mock()
        client.reactions_add = Mock()

        message_handler.handle_message(
            {
                "type": "message",
                "user": "U67890",
                "text": "help",
                "channel": "C12345",
                "ts": "123",
            },
            say,
            client,
        )

        # Should not send response on error
        say.assert_not_called()
