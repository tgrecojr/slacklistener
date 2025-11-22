"""Configuration loading and validation."""

import logging
from pathlib import Path
from typing import List, Optional

import yaml
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


class BedrockConfig(BaseModel):
    """Bedrock model configuration."""

    model_id: str = Field(..., description="Bedrock model ID")
    region: str = Field(default="us-east-1", description="AWS region")
    max_tokens: int = Field(default=1024, ge=1, le=100000)
    temperature: float = Field(default=0.7, ge=0.0, le=1.0)

    class Config:
        extra = "allow"  # Allow additional fields


class ResponseConfig(BaseModel):
    """Response behavior configuration."""

    thread_reply: bool = Field(default=True, description="Reply in thread")
    add_reaction: Optional[str] = Field(default=None, description="Reaction emoji to add")


class ChannelConfig(BaseModel):
    """Channel listener configuration."""

    channel_id: str = Field(..., description="Slack channel ID")
    channel_name: str = Field(..., description="Human-readable channel name")
    enabled: bool = Field(default=True, description="Whether this channel is enabled")
    keywords: List[str] = Field(default_factory=list, description="Keywords to trigger on")
    case_sensitive: bool = Field(default=False, description="Case-sensitive keyword matching")
    require_image: bool = Field(default=False, description="Only respond to messages with images")
    bedrock: BedrockConfig = Field(..., description="Bedrock configuration")
    system_prompt: str = Field(..., description="System prompt for LLM")
    response: ResponseConfig = Field(default_factory=ResponseConfig, description="Response settings")

    @field_validator("keywords")
    @classmethod
    def keywords_or_empty(cls, v: List[str]) -> List[str]:
        """Allow empty keywords list to match all messages."""
        return v


class SlashCommandConfig(BaseModel):
    """Slash command configuration."""

    command: str = Field(..., description="Command name (e.g., /analyze)")
    description: str = Field(..., description="Command description")
    enabled: bool = Field(default=True, description="Whether this command is enabled")
    bedrock: BedrockConfig = Field(..., description="Bedrock configuration")
    system_prompt: str = Field(..., description="System prompt for LLM")

    @field_validator("command")
    @classmethod
    def validate_command_format(cls, v: str) -> str:
        """Ensure command starts with /."""
        if not v.startswith("/"):
            return f"/{v}"
        return v


class GlobalSettings(BaseModel):
    """Global application settings."""

    log_level: str = Field(default="INFO", description="Logging level")
    max_message_length: int = Field(default=10000, ge=1, description="Max message length to process")
    bedrock_timeout: int = Field(default=30, ge=1, le=300, description="Bedrock API timeout")
    ignore_bot_messages: bool = Field(default=True, description="Ignore messages from bots")
    ignore_self: bool = Field(default=True, description="Ignore own messages")


class AppConfig(BaseModel):
    """Main application configuration."""

    channels: List[ChannelConfig] = Field(default_factory=list, description="Channel configurations")
    slash_commands: List[SlashCommandConfig] = Field(
        default_factory=list, description="Slash command configurations"
    )
    settings: GlobalSettings = Field(default_factory=GlobalSettings, description="Global settings")


def load_config(config_path: str = "config/config.yaml") -> AppConfig:
    """
    Load and validate configuration from YAML file.

    Args:
        config_path: Path to config YAML file

    Returns:
        Validated AppConfig object

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config is invalid
    """
    path = Path(config_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {config_path}\n"
            f"Please copy config/config.example.yaml to config/config.yaml and configure it."
        )

    logger.info(f"Loading configuration from {config_path}")

    with open(path, "r") as f:
        config_dict = yaml.safe_load(f)

    try:
        config = AppConfig(**config_dict)
        logger.info(
            f"Configuration loaded: {len(config.channels)} channels, "
            f"{len(config.slash_commands)} slash commands"
        )
        return config
    except Exception as e:
        raise ValueError(f"Invalid configuration: {e}")


def get_channel_config(config: AppConfig, channel_id: str) -> Optional[ChannelConfig]:
    """
    Get configuration for a specific channel.

    Args:
        config: Application configuration
        channel_id: Slack channel ID

    Returns:
        ChannelConfig if found and enabled, None otherwise
    """
    for channel in config.channels:
        if channel.channel_id == channel_id and channel.enabled:
            return channel
    return None


def get_command_config(config: AppConfig, command: str) -> Optional[SlashCommandConfig]:
    """
    Get configuration for a specific slash command.

    Args:
        config: Application configuration
        command: Command name (with or without /)

    Returns:
        SlashCommandConfig if found and enabled, None otherwise
    """
    if not command.startswith("/"):
        command = f"/{command}"

    for cmd_config in config.slash_commands:
        if cmd_config.command == command and cmd_config.enabled:
            return cmd_config
    return None
