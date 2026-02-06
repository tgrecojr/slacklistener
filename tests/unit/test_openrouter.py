"""Tests for OpenRouter LLM client."""

from unittest.mock import Mock, patch, MagicMock

import pytest

from src.llm.openrouter import OpenRouterClient


class TestOpenRouterClientTimeout:
    """Tests for OpenRouterClient timeout support."""

    @patch("src.llm.openrouter.OpenAI")
    def test_default_timeout_when_not_specified(self, mock_openai_class):
        """Test that no timeout is set when not specified."""
        client = OpenRouterClient(api_key="test-key")

        mock_openai_class.assert_called_once()
        call_kwargs = mock_openai_class.call_args.kwargs
        assert "timeout" not in call_kwargs

    @patch("src.llm.openrouter.OpenAI")
    def test_timeout_passed_to_openai_client(self, mock_openai_class):
        """Test that timeout is passed to the OpenAI client."""
        client = OpenRouterClient(api_key="test-key", timeout=45)

        mock_openai_class.assert_called_once()
        call_kwargs = mock_openai_class.call_args.kwargs
        assert call_kwargs["timeout"] == 45

    @patch("src.llm.openrouter.OpenAI")
    def test_custom_timeout_value(self, mock_openai_class):
        """Test various timeout values."""
        for timeout_val in [10, 60, 300]:
            mock_openai_class.reset_mock()
            client = OpenRouterClient(api_key="test-key", timeout=timeout_val)

            call_kwargs = mock_openai_class.call_args.kwargs
            assert call_kwargs["timeout"] == timeout_val
