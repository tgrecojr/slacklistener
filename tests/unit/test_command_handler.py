"""Tests for slash command handler."""

from unittest.mock import Mock, patch

import pytest

from src.handlers.command_handler import CommandHandler


@pytest.fixture
def command_handler(mock_slack_app, sample_app_config):
    """Create a command handler instance."""
    return CommandHandler(
        app=mock_slack_app, config=sample_app_config
    )


class TestCommandHandler:
    """Tests for CommandHandler class."""

    def test_initialization(self, command_handler):
        """Test handler initialization."""
        assert command_handler.app is not None
        assert command_handler.config is not None

    @patch("src.handlers.command_handler.create_llm_provider")
    def test_handle_command_success(self, mock_create_provider, command_handler, sample_slack_command):
        """Test successful command handling."""
        # Mock LLM provider
        mock_provider = Mock()
        mock_provider.generate_response.return_value = "This is a test response from Claude."
        mock_create_provider.return_value = mock_provider

        ack = Mock()
        say = Mock()

        command_handler.handle_command(ack, sample_slack_command, say)

        # Should acknowledge immediately
        ack.assert_called_once()

        # Should send response
        say.assert_called_once()
        call_args = say.call_args
        assert "test response from Claude" in call_args.args[0]

    def test_handle_command_no_text(self, command_handler):
        """Test command with no text provided."""
        command = {
            "command": "/analyze",
            "text": "",  # Empty text
            "user_id": "U67890",
        }

        ack = Mock()
        say = Mock()

        command_handler.handle_command(ack, command, say)

        # Should acknowledge
        ack.assert_called_once()

        # Should ask for text
        say.assert_called_once()
        response_text = say.call_args.args[0]
        assert "provide text" in response_text.lower()

    def test_handle_command_too_long(self, command_handler):
        """Test command with text that's too long."""
        command = {
            "command": "/analyze",
            "text": "A" * 20000,  # Very long text
            "user_id": "U67890",
        }

        ack = Mock()
        say = Mock()

        command_handler.handle_command(ack, command, say)

        # Should acknowledge
        ack.assert_called_once()

        # Should report error
        say.assert_called_once()
        response_text = say.call_args.args[0]
        assert "too long" in response_text.lower()

    def test_handle_command_unconfigured(self, command_handler):
        """Test unconfigured command."""
        command = {
            "command": "/unknown",
            "text": "test",
            "user_id": "U67890",
        }

        ack = Mock()
        say = Mock()

        command_handler.handle_command(ack, command, say)

        # Should acknowledge
        ack.assert_called_once()

        # Should report not configured
        say.assert_called_once()
        response_text = say.call_args.args[0]
        assert "not configured" in response_text.lower()

    @patch("src.handlers.command_handler.create_llm_provider")
    def test_handle_command_bedrock_error(self, mock_create_provider, command_handler, sample_slack_command):
        """Test handling LLM provider errors."""
        # Mock LLM provider to return None (error)
        mock_provider = Mock()
        mock_provider.generate_response.return_value = None
        mock_create_provider.return_value = mock_provider

        ack = Mock()
        say = Mock()

        command_handler.handle_command(ack, sample_slack_command, say)

        # Should acknowledge
        ack.assert_called_once()

        # Should report error
        say.assert_called_once()
        response_text = say.call_args.args[0]
        assert "error" in response_text.lower()

    @patch("src.handlers.command_handler.create_llm_provider")
    def test_handle_command_exception(self, mock_create_provider, command_handler, sample_slack_command):
        """Test handling unexpected exceptions."""
        # Mock LLM provider to raise exception
        mock_provider = Mock()
        mock_provider.generate_response.side_effect = Exception("Test error")
        mock_create_provider.return_value = mock_provider

        ack = Mock()
        say = Mock()

        command_handler.handle_command(ack, sample_slack_command, say)

        # Should still acknowledge
        ack.assert_called_once()

        # Should report error gracefully
        say.assert_called_once()
        response_text = say.call_args.args[0]
        assert "error" in response_text.lower()

    def test_get_command_config(self, command_handler):
        """Test getting command configuration."""
        config = command_handler._get_command_config("/analyze")
        assert config is not None
        assert config.description == "Analyze text with AI"

        config = command_handler._get_command_config("/nonexistent")
        assert config is None

    @patch("src.handlers.command_handler.create_llm_provider")
    def test_generate_response(self, mock_create_provider, command_handler, sample_command_config):
        """Test response generation."""
        # Mock LLM provider
        mock_provider = Mock()
        mock_provider.generate_response.return_value = "This is a test response from Claude."
        mock_create_provider.return_value = mock_provider

        command = {"user_id": "U123", "channel_id": "C123"}
        response = command_handler._generate_response(
            "Test question", sample_command_config, command
        )

        assert response == "This is a test response from Claude."
        mock_provider.generate_response.assert_called_once()

    @patch("src.handlers.command_handler.create_llm_provider")
    def test_generate_response_uses_correct_params(
        self, mock_create_provider, command_handler, sample_command_config
    ):
        """Test that response generation uses correct parameters."""
        # Mock LLM provider
        mock_provider = Mock()
        mock_provider.generate_response.return_value = "Test response"
        mock_create_provider.return_value = mock_provider

        command = {"user_id": "U123", "channel_id": "C123"}
        command_handler._generate_response("Test", sample_command_config, command)

        # Verify provider was called with correct parameters
        mock_provider.generate_response.assert_called_once()
        call_kwargs = mock_provider.generate_response.call_args.kwargs

        assert call_kwargs["max_tokens"] == sample_command_config.llm.max_tokens
        assert call_kwargs["temperature"] == sample_command_config.llm.temperature
        assert call_kwargs["system_prompt"] == sample_command_config.system_prompt
