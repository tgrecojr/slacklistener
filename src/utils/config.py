"""Configuration loading and validation."""

import logging
import os
import re
from pathlib import Path
from typing import List, Optional, Any, Dict

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

logger = logging.getLogger(__name__)


def expand_env_vars(config_dict: Any) -> Any:
    """
    Recursively expand environment variables in config dictionary.

    Supports ${VAR_NAME} syntax.

    Args:
        config_dict: Configuration dictionary or value

    Returns:
        Config with environment variables expanded
    """
    if isinstance(config_dict, dict):
        return {key: expand_env_vars(value) for key, value in config_dict.items()}
    elif isinstance(config_dict, list):
        return [expand_env_vars(item) for item in config_dict]
    elif isinstance(config_dict, str):
        # Replace ${VAR_NAME} with environment variable value
        pattern = re.compile(r"\$\{([^}]+)\}")

        def replace_var(match):
            var_name = match.group(1)
            return os.getenv(var_name, match.group(0))  # Keep original if not found

        return pattern.sub(replace_var, config_dict)
    else:
        return config_dict


class LLMConfig(BaseModel):
    """OpenRouter LLM configuration."""

    model_config = ConfigDict(extra="forbid")

    # OpenRouter parameters
    api_key: str = Field(..., description="OpenRouter API key")
    model: str = Field(
        default="anthropic/claude-3.5-sonnet",
        description="Model identifier (e.g., anthropic/claude-3.5-sonnet, openai/gpt-4)",
    )
    max_tokens: int = Field(default=1024, ge=1, le=100000)
    temperature: float = Field(default=0.7, ge=0.0, le=1.0)
    base_url: str = Field(
        default="https://openrouter.ai/api/v1", description="OpenRouter API base URL"
    )

    # App attribution headers
    site_url: str = Field(
        default="https://github.com/tgrecojr/slacklistener",
        description="App URL for OpenRouter attribution (shown in rankings)",
    )
    site_name: str = Field(
        default="slacklistener",
        description="App name for OpenRouter attribution (shown in console)",
    )


class ResponseConfig(BaseModel):
    """Response behavior configuration."""

    thread_reply: bool = Field(default=True, description="Reply in thread")
    add_reaction: Optional[str] = Field(
        default=None, description="Reaction emoji to add"
    )


class ChannelConfig(BaseModel):
    """Channel listener configuration."""

    channel_id: str = Field(..., description="Slack channel ID")
    channel_name: str = Field(..., description="Human-readable channel name")
    enabled: bool = Field(default=True, description="Whether this channel is enabled")
    keywords: List[str] = Field(
        default_factory=list, description="Keywords to trigger on"
    )
    case_sensitive: bool = Field(
        default=False, description="Case-sensitive keyword matching"
    )
    require_image: bool = Field(
        default=False, description="Only respond to messages with images"
    )
    llm: Optional[LLMConfig] = Field(None, description="LLM configuration")
    system_prompt: str = Field(..., description="System prompt for LLM")
    tools: List[Dict[str, Any]] = Field(
        default_factory=list, description="Tools to execute before LLM invocation"
    )
    response: ResponseConfig = Field(
        default_factory=ResponseConfig, description="Response settings"
    )

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
    llm: Optional[LLMConfig] = Field(None, description="LLM configuration")
    system_prompt: str = Field(..., description="System prompt for LLM")
    tools: List[Dict[str, Any]] = Field(
        default_factory=list, description="Tools to execute before LLM invocation"
    )

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
    max_message_length: int = Field(
        default=10000, ge=1, description="Max message length to process"
    )
    llm_timeout: int = Field(
        default=30, ge=1, le=300, description="LLM API timeout in seconds"
    )
    ignore_bot_messages: bool = Field(
        default=True, description="Ignore messages from bots"
    )
    ignore_self: bool = Field(default=True, description="Ignore own messages")
    prompt_guard_enabled: bool = Field(
        default=True, description="Enable prompt injection scanning"
    )
    prompt_injection_threshold: float = Field(
        default=0.92,
        ge=0.0,
        le=1.0,
        description="Prompt injection detection threshold (0-1, higher = stricter)",
    )


class AppConfig(BaseModel):
    """Main application configuration."""

    channels: List[ChannelConfig] = Field(
        default_factory=list, description="Channel configurations"
    )
    slash_commands: List[SlashCommandConfig] = Field(
        default_factory=list, description="Slash command configurations"
    )
    settings: GlobalSettings = Field(
        default_factory=GlobalSettings, description="Global settings"
    )


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

    # Expand environment variables
    config_dict = expand_env_vars(config_dict)

    try:
        config = AppConfig(**config_dict)
        logger.info(
            f"Configuration loaded: {len(config.channels)} channels, "
            f"{len(config.slash_commands)} slash commands"
        )
        return config
    except Exception as e:
        raise ValueError(f"Invalid configuration: {e}")
