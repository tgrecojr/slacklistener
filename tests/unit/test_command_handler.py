"""Tests for slash command handler."""

from unittest.mock import Mock

import pytest

from src.handlers.command_handler import CommandHandler


@pytest.fixture
def command_handler(mock_slack_app, sample_app_config, mock_bedrock_client):
    """Create a command handler instance."""
    return CommandHandler(
        app=mock_slack_app, config=sample_app_config, bedrock_client=mock_bedrock_client
    )


class TestCommandHandler:
    """Tests for CommandHandler class."""

    def test_initialization(self, command_handler):
        """Test handler initialization."""
        assert command_handler.app is not None
        assert command_handler.config is not None
        assert command_handler.bedrock_client is not None

    def test_handle_command_success(self, command_handler, sample_slack_command):
        """Test successful command handling."""
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

    def test_handle_command_bedrock_error(self, command_handler, sample_slack_command):
        """Test handling Bedrock errors."""
        # Make bedrock return None (error)
        command_handler.bedrock_client.invoke_claude.return_value = None

        ack = Mock()
        say = Mock()

        command_handler.handle_command(ack, sample_slack_command, say)

        # Should acknowledge
        ack.assert_called_once()

        # Should report error
        say.assert_called_once()
        response_text = say.call_args.args[0]
        assert "error" in response_text.lower()

    def test_handle_command_exception(self, command_handler, sample_slack_command):
        """Test handling unexpected exceptions."""
        # Make bedrock raise exception
        command_handler.bedrock_client.invoke_claude.side_effect = Exception("Test error")

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

    def test_generate_response(self, command_handler, sample_command_config):
        """Test response generation."""
        response = command_handler._generate_response("Test question", sample_command_config)

        assert response == "This is a test response from Claude."
        command_handler.bedrock_client.invoke_claude.assert_called_once()

    def test_generate_response_uses_correct_params(self, command_handler, sample_command_config):
        """Test that response generation uses correct parameters."""
        command_handler._generate_response("Test", sample_command_config)

        call_args = command_handler.bedrock_client.invoke_claude.call_args

        assert call_args.kwargs["model_id"] == sample_command_config.bedrock.model_id
        assert call_args.kwargs["max_tokens"] == sample_command_config.bedrock.max_tokens
        assert call_args.kwargs["temperature"] == sample_command_config.bedrock.temperature
        assert call_args.kwargs["system_prompt"] == sample_command_config.system_prompt
