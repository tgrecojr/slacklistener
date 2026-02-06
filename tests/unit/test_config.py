"""Tests for configuration loading and validation."""

import tempfile
from pathlib import Path

import pytest
import yaml

from src.utils.config import (
    load_config,
    LLMConfig,
    ChannelConfig,
    AppConfig,
)


def test_llm_config_validation():
    """Test LLM configuration validation."""
    # Valid config
    config = LLMConfig(
        api_key="test-api-key",
        model="anthropic/claude-3.5-sonnet",
        max_tokens=1024,
        temperature=0.7,
    )
    assert config.model == "anthropic/claude-3.5-sonnet"
    assert config.max_tokens == 1024

    # Invalid temperature
    with pytest.raises(ValueError):
        LLMConfig(
            api_key="test-api-key",
            temperature=1.5,  # > 1.0
        )

    # Invalid max_tokens
    with pytest.raises(ValueError):
        LLMConfig(
            api_key="test-api-key",
            max_tokens=0,  # < 1
        )


def test_channel_config_validation():
    """Test channel configuration validation."""
    llm = LLMConfig(api_key="test-api-key", model="test-model")

    config = ChannelConfig(
        channel_id="C12345",
        channel_name="test",
        llm=llm,
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
                "llm": {"api_key": "test-key", "model": "test-model"},
                "system_prompt": "Test prompt",
            }
        ],
        "slash_commands": [
            {
                "command": "/test",
                "description": "Test command",
                "llm": {"api_key": "test-key", "model": "test-model"},
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


def test_disabled_channel_config(sample_channel_config):
    """Test that disabled channels can be configured."""
    sample_channel_config.enabled = False
    config = AppConfig(
        channels=[sample_channel_config],
        slash_commands=[],
    )

    assert config.channels[0].enabled is False


def test_slash_command_auto_adds_slash():
    """Test that slash commands automatically get / prefix."""
    llm = LLMConfig(api_key="test-key", model="test-model")

    config = {
        "command": "analyze",  # No leading slash
        "description": "Test",
        "llm": llm,
        "system_prompt": "Test",
    }

    from src.utils.config import SlashCommandConfig

    cmd = SlashCommandConfig(**config)
    assert cmd.command == "/analyze"
