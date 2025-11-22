"""Pytest configuration and shared fixtures."""

import base64
import json
from typing import Dict, Any
from unittest.mock import MagicMock, Mock

import pytest
from slack_bolt import App

from src.services.bedrock_client import BedrockClient
from src.utils.config import (
    AppConfig,
    ChannelConfig,
    SlashCommandConfig,
    BedrockConfig,
    ResponseConfig,
    GlobalSettings,
)


@pytest.fixture
def sample_bedrock_config():
    """Sample Bedrock configuration."""
    return BedrockConfig(
        model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
        region="us-east-1",
        max_tokens=1024,
        temperature=0.7,
    )


@pytest.fixture
def sample_channel_config(sample_bedrock_config):
    """Sample channel configuration."""
    return ChannelConfig(
        channel_id="C12345",
        channel_name="test-channel",
        enabled=True,
        keywords=["help", "issue"],
        case_sensitive=False,
        require_image=False,
        bedrock=sample_bedrock_config,
        system_prompt="You are a helpful assistant.",
        response=ResponseConfig(thread_reply=True, add_reaction="eyes"),
    )


@pytest.fixture
def sample_image_channel_config(sample_bedrock_config):
    """Sample image analysis channel configuration."""
    return ChannelConfig(
        channel_id="C54321",
        channel_name="image-analysis",
        enabled=True,
        keywords=[],
        case_sensitive=False,
        require_image=True,
        bedrock=sample_bedrock_config,
        system_prompt="You are an image analysis expert.",
        response=ResponseConfig(thread_reply=True, add_reaction="camera"),
    )


@pytest.fixture
def sample_command_config(sample_bedrock_config):
    """Sample slash command configuration."""
    return SlashCommandConfig(
        command="/analyze",
        description="Analyze text with AI",
        enabled=True,
        bedrock=sample_bedrock_config,
        system_prompt="You are an analytical assistant.",
    )


@pytest.fixture
def sample_app_config(sample_channel_config, sample_command_config):
    """Sample application configuration."""
    return AppConfig(
        channels=[sample_channel_config],
        slash_commands=[sample_command_config],
        settings=GlobalSettings(),
    )


@pytest.fixture
def mock_slack_app():
    """Mock Slack Bolt app."""
    app = MagicMock(spec=App)
    app.client = MagicMock()
    app.client.auth_test.return_value = {"user_id": "U12345"}
    return app


@pytest.fixture
def mock_bedrock_client():
    """Mock Bedrock client."""
    client = MagicMock(spec=BedrockClient)
    client.invoke_claude.return_value = "This is a test response from Claude."
    return client


@pytest.fixture
def sample_slack_message_event():
    """Sample Slack message event."""
    return {
        "type": "message",
        "user": "U67890",
        "text": "I need help with an issue",
        "channel": "C12345",
        "ts": "1234567890.123456",
    }


@pytest.fixture
def sample_slack_image_event():
    """Sample Slack message event with an image."""
    return {
        "type": "message",
        "user": "U67890",
        "text": "Check out this screenshot",
        "channel": "C54321",
        "ts": "1234567890.123456",
        "files": [
            {
                "id": "F12345",
                "name": "screenshot.png",
                "mimetype": "image/png",
                "url_private": "https://files.slack.com/files-pri/T12345/screenshot.png",
                "size": 12345,
            }
        ],
    }


@pytest.fixture
def sample_slack_command():
    """Sample Slack slash command payload."""
    return {
        "command": "/analyze",
        "text": "What is AI?",
        "user_id": "U67890",
        "channel_id": "C12345",
        "response_url": "https://hooks.slack.com/commands/1234/5678",
    }


@pytest.fixture
def sample_image_bytes():
    """Sample image as bytes (1x1 red pixel PNG)."""
    # Minimal valid PNG file
    return base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="
    )


@pytest.fixture
def sample_image_info(sample_image_bytes):
    """Sample image info dict."""
    return {
        "data": sample_image_bytes,
        "mimetype": "image/png",
        "filename": "test.png",
    }


@pytest.fixture
def mock_bedrock_response():
    """Mock successful Bedrock API response."""
    return {
        "body": Mock(
            read=Mock(
                return_value=json.dumps(
                    {
                        "content": [
                            {
                                "type": "text",
                                "text": "This is a test response from Claude.",
                            }
                        ],
                        "stop_reason": "end_turn",
                    }
                ).encode()
            )
        )
    }


@pytest.fixture
def mock_bedrock_vision_response():
    """Mock successful Bedrock vision API response."""
    return {
        "body": Mock(
            read=Mock(
                return_value=json.dumps(
                    {
                        "content": [
                            {
                                "type": "text",
                                "text": "This image shows a red pixel. It appears to be a test image.",
                            }
                        ],
                        "stop_reason": "end_turn",
                    }
                ).encode()
            )
        )
    }
