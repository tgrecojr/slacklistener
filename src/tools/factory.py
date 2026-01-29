"""Factory for creating tool instances based on configuration."""

import logging
from typing import Dict, Any

from .tool import Tool

logger = logging.getLogger(__name__)


def create_tool(tool_config: Dict[str, Any]) -> Tool:
    """
    Create a tool instance based on configuration.

    Args:
        tool_config: Tool configuration dictionary containing:
            - type: Tool type identifier (e.g., "openweathermap")
            - Additional tool-specific parameters

    Returns:
        Tool instance

    Raises:
        ValueError: If tool type is invalid or required parameters are missing
    """
    tool_type = tool_config.get("type")

    if not tool_type:
        raise ValueError("Tool configuration must specify 'type'")

    if tool_type == "openweathermap":
        from .implementations.openweathermap import OpenWeatherMapTool

        # Validate required parameters
        api_key = tool_config.get("api_key")
        if not api_key:
            raise ValueError("OpenWeatherMap tool requires 'api_key' parameter")

        # Optional parameters
        location = tool_config.get("location")
        latitude = tool_config.get("latitude")
        longitude = tool_config.get("longitude")

        # Must have either location or lat/lon
        if not location and (latitude is None or longitude is None):
            raise ValueError(
                "OpenWeatherMap tool requires either 'location' or both 'latitude' and 'longitude'"
            )

        return OpenWeatherMapTool(
            api_key=api_key,
            location=location,
            latitude=latitude,
            longitude=longitude,
            units=tool_config.get("units", "imperial"),
            language=tool_config.get("language", "en"),
        )

    elif tool_type == "rssfeed":
        from .implementations.rssfeed import RSSFeedTool

        # Validate required parameters
        feed_urls = tool_config.get("feed_urls")
        if not feed_urls or not isinstance(feed_urls, list) or len(feed_urls) == 0:
            raise ValueError(
                "RSSFeed tool requires 'feed_urls' parameter with at least one URL"
            )

        return RSSFeedTool(
            feed_urls=feed_urls,
            data_file=tool_config.get("data_file", "data/seen_articles.json"),
            max_stories=tool_config.get("max_stories", 10),
        )

    else:
        raise ValueError(f"Unknown tool type: {tool_type}")
