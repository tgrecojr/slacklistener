"""Tests for slash command handler."""

from unittest.mock import Mock, patch

import pytest

from src.handlers.command_handler import CommandHandler


@pytest.fixture
def command_handler(mock_slack_app, sample_app_config):
    """Create a command handler instance."""
    return CommandHandler(app=mock_slack_app, config=sample_app_config)


@pytest.fixture
def command_handler_with_guard(mock_slack_app, sample_app_config):
    """Create a command handler with an input guard."""
    mock_guard = Mock()
    mock_guard.scan.return_value = (True, 0.05)
    return CommandHandler(
        app=mock_slack_app, config=sample_app_config, input_guard=mock_guard
    )


class TestCommandHandler:
    """Tests for CommandHandler class."""

    def test_initialization(self, command_handler):
        """Test handler initialization."""
        assert command_handler.app is not None
        assert command_handler.config is not None

    @patch("src.handlers.command_handler.OpenRouterClient")
    def test_handle_command_success(
        self, mock_client_class, command_handler, sample_slack_command
    ):
        """Test successful command handling."""
        # Mock LLM client
        mock_client = Mock()
        mock_client.generate_response.return_value = (
            "This is a test response from Claude."
        )
        mock_client_class.return_value = mock_client

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

    @patch("src.handlers.command_handler.OpenRouterClient")
    def test_handle_command_llm_error(
        self, mock_client_class, command_handler, sample_slack_command
    ):
        """Test handling LLM client errors."""
        # Mock LLM client to raise exception
        mock_client_class.side_effect = Exception("LLM error")

        ack = Mock()
        say = Mock()

        command_handler.handle_command(ack, sample_slack_command, say)

        # Should acknowledge
        ack.assert_called_once()

        # Should report error
        say.assert_called_once()
        response_text = say.call_args.args[0]
        assert "error" in response_text.lower()

    @patch("src.handlers.command_handler.OpenRouterClient")
    def test_handle_command_exception(
        self, mock_client_class, command_handler, sample_slack_command
    ):
        """Test handling unexpected exceptions."""
        # Mock LLM client to raise exception
        mock_client_class.side_effect = Exception("Test error")

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

    @patch("src.handlers.command_handler.OpenRouterClient")
    def test_generate_response(
        self, mock_client_class, command_handler, sample_command_config
    ):
        """Test response generation."""
        # Mock LLM client
        mock_client = Mock()
        mock_client.generate_response.return_value = (
            "This is a test response from Claude."
        )
        mock_client_class.return_value = mock_client

        command = {"user_id": "U123", "channel_id": "C123"}
        response = command_handler._generate_response(
            "Test question", sample_command_config, command
        )

        assert response == "This is a test response from Claude."
        mock_client.generate_response.assert_called_once()

    @patch("src.handlers.command_handler.OpenRouterClient")
    def test_generate_response_passes_timeout(
        self, mock_client_class, command_handler, sample_command_config
    ):
        """Test that timeout from settings is passed to OpenRouterClient."""
        mock_client = Mock()
        mock_client.generate_response.return_value = "Test response"
        mock_client_class.return_value = mock_client

        command = {"user_id": "U123", "channel_id": "C123"}
        command_handler._generate_response("Test", sample_command_config, command)

        # Verify timeout was passed to OpenRouterClient constructor
        mock_client_class.assert_called_once()
        call_kwargs = mock_client_class.call_args.kwargs
        assert call_kwargs["timeout"] == command_handler.config.settings.llm_timeout

    @patch("src.handlers.command_handler.OpenRouterClient")
    def test_client_is_cached_across_commands(
        self, mock_client_class, command_handler, sample_slack_command
    ):
        """Test that the same OpenRouterClient is reused for the same command config."""
        mock_client = Mock()
        mock_client.generate_response.return_value = "response"
        mock_client_class.return_value = mock_client

        ack = Mock()
        say = Mock()

        # Run command twice
        command_handler.handle_command(ack, sample_slack_command, say)
        command_handler.handle_command(ack, sample_slack_command, say)

        # Client should only be created once
        assert mock_client_class.call_count == 1

    @patch("src.handlers.command_handler.OpenRouterClient")
    def test_generate_response_uses_correct_params(
        self, mock_client_class, command_handler, sample_command_config
    ):
        """Test that response generation uses correct parameters."""
        # Mock LLM client
        mock_client = Mock()
        mock_client.generate_response.return_value = "Test response"
        mock_client_class.return_value = mock_client

        command = {"user_id": "U123", "channel_id": "C123"}
        command_handler._generate_response("Test", sample_command_config, command)

        # Verify client was called with correct parameters
        mock_client.generate_response.assert_called_once()
        call_kwargs = mock_client.generate_response.call_args.kwargs

        assert call_kwargs["max_tokens"] == sample_command_config.llm.max_tokens
        assert call_kwargs["temperature"] == sample_command_config.llm.temperature
        assert call_kwargs["system_prompt"] == sample_command_config.system_prompt

    @patch("src.handlers.command_handler.OpenRouterClient")
    def test_input_guard_allows_safe_command(
        self, mock_client_class, command_handler_with_guard, sample_slack_command
    ):
        """Test that handler calls input_guard.scan() and proceeds when safe."""
        mock_client = Mock()
        mock_client.generate_response.return_value = "test response"
        mock_client_class.return_value = mock_client

        ack = Mock()
        say = Mock()

        command_handler_with_guard.handle_command(ack, sample_slack_command, say)

        # Guard should have been called with the command text
        command_handler_with_guard.input_guard.scan.assert_called_once_with(
            "What is AI?"
        )

        # Should send response (command was safe)
        say.assert_called_once()
        assert "test response" in say.call_args.args[0]

    def test_input_guard_blocks_injection(
        self, command_handler_with_guard, sample_slack_command
    ):
        """Test that detected injection sends generic error via say()."""
        # Configure guard to detect injection
        command_handler_with_guard.input_guard.scan.return_value = (False, 0.98)

        ack = Mock()
        say = Mock()

        command_handler_with_guard.handle_command(ack, sample_slack_command, say)

        # Should acknowledge
        ack.assert_called_once()

        # Guard should have been called
        command_handler_with_guard.input_guard.scan.assert_called_once()

        # Should send generic error message
        say.assert_called_once()
        response_text = say.call_args.args[0]
        assert "could not be processed" in response_text.lower()

    @patch("src.handlers.command_handler.OpenRouterClient")
    def test_no_guard_skips_scan(
        self, mock_client_class, command_handler, sample_slack_command
    ):
        """Test that handler works normally when input_guard is None."""
        mock_client = Mock()
        mock_client.generate_response.return_value = "test response"
        mock_client_class.return_value = mock_client

        ack = Mock()
        say = Mock()

        # command_handler has no input_guard (None)
        assert command_handler.input_guard is None
        command_handler.handle_command(ack, sample_slack_command, say)

        # Should still send response
        say.assert_called_once()
