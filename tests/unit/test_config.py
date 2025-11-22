"""Tests for configuration loading and validation."""

import tempfile
from pathlib import Path

import pytest
import yaml

from src.utils.config import (
    load_config,
    get_channel_config,
    get_command_config,
    BedrockConfig,
    ChannelConfig,
    AppConfig,
)


def test_bedrock_config_validation():
    """Test Bedrock configuration validation."""
    # Valid config
    config = BedrockConfig(
        model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
        region="us-east-1",
        max_tokens=1024,
        temperature=0.7,
    )
    assert config.model_id == "anthropic.claude-3-5-sonnet-20241022-v2:0"
    assert config.max_tokens == 1024

    # Invalid temperature
    with pytest.raises(ValueError):
        BedrockConfig(
            model_id="test-model",
            temperature=1.5,  # > 1.0
        )

    # Invalid max_tokens
    with pytest.raises(ValueError):
        BedrockConfig(
            model_id="test-model",
            max_tokens=0,  # < 1
        )


def test_channel_config_validation():
    """Test channel configuration validation."""
    bedrock = BedrockConfig(model_id="test-model")

    config = ChannelConfig(
        channel_id="C12345",
        channel_name="test",
        bedrock=bedrock,
        system_prompt="Test prompt",
    )

    assert config.channel_id == "C12345"
    assert config.enabled is True  # Default
    assert config.keywords == []  # Default


def test_load_config_file_not_found():
    """Test loading non-existent config file."""
    with pytest.raises(FileNotFoundError):
        load_config("nonexistent.yaml")


def test_load_config_valid(tmp_path):
    """Test loading valid configuration file."""
    config_data = {
        "channels": [
            {
                "channel_id": "C12345",
                "channel_name": "test",
                "bedrock": {"model_id": "test-model"},
                "system_prompt": "Test prompt",
            }
        ],
        "slash_commands": [
            {
                "command": "/test",
                "description": "Test command",
                "bedrock": {"model_id": "test-model"},
                "system_prompt": "Test prompt",
            }
        ],
        "settings": {},
    }

    config_file = tmp_path / "config.yaml"
    with open(config_file, "w") as f:
        yaml.dump(config_data, f)

    config = load_config(str(config_file))

    assert isinstance(config, AppConfig)
    assert len(config.channels) == 1
    assert len(config.slash_commands) == 1
    assert config.channels[0].channel_id == "C12345"


def test_get_channel_config(sample_app_config):
    """Test getting channel configuration by ID."""
    # Existing channel
    config = get_channel_config(sample_app_config, "C12345")
    assert config is not None
    assert config.channel_name == "test-channel"

    # Non-existent channel
    config = get_channel_config(sample_app_config, "C99999")
    assert config is None


def test_get_command_config(sample_app_config):
    """Test getting command configuration."""
    # With leading slash
    config = get_command_config(sample_app_config, "/analyze")
    assert config is not None
    assert config.description == "Analyze text with AI"

    # Without leading slash
    config = get_command_config(sample_app_config, "analyze")
    assert config is not None

    # Non-existent command
    config = get_command_config(sample_app_config, "/nonexistent")
    assert config is None


def test_disabled_channel_not_returned(sample_channel_config):
    """Test that disabled channels are not returned."""
    sample_channel_config.enabled = False
    config = AppConfig(
        channels=[sample_channel_config],
        slash_commands=[],
    )

    result = get_channel_config(config, "C12345")
    assert result is None


def test_slash_command_auto_adds_slash():
    """Test that slash commands automatically get / prefix."""
    bedrock = BedrockConfig(model_id="test-model")

    config = {
        "command": "analyze",  # No leading slash
        "description": "Test",
        "bedrock": bedrock,
        "system_prompt": "Test",
    }

    from src.utils.config import SlashCommandConfig

    cmd = SlashCommandConfig(**config)
    assert cmd.command == "/analyze"
