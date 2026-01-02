"""Tests for tools and tool factory."""

import json
from unittest.mock import Mock, patch

import pytest
import responses

from src.tools.factory import create_tool
from src.tools.implementations.openweathermap import OpenWeatherMapTool


class TestOpenWeatherMapTool:
    """Tests for OpenWeatherMap tool."""

    def test_initialization_with_location(self):
        """Test tool initialization with location string."""
        tool = OpenWeatherMapTool(
            api_key="test_key", location="Boston,MA,US", units="imperial"
        )

        assert tool.api_key == "test_key"
        assert tool.location == "Boston,MA,US"
        assert tool.units == "imperial"
        assert tool.language == "en"
        assert tool.get_name() == "OpenWeatherMap"

    def test_initialization_with_coordinates(self):
        """Test tool initialization with lat/lon coordinates."""
        tool = OpenWeatherMapTool(
            api_key="test_key", latitude=42.3601, longitude=-71.0589, units="metric"
        )

        assert tool.api_key == "test_key"
        assert tool.latitude == 42.3601
        assert tool.longitude == -71.0589
        assert tool.units == "metric"

    @responses.activate
    def test_execute_success(self):
        """Test successful weather data fetch."""
        # Mock current weather response
        current_response = {
            "name": "Boston",
            "main": {"temp": 45.5, "feels_like": 42.0, "humidity": 65},
            "weather": [{"description": "partly cloudy"}],
            "wind": {"speed": 10.5},
        }

        # Mock forecast response
        forecast_response = {
            "list": [
                {
                    "dt": 1640000000,
                    "main": {"temp": 44.0},
                    "weather": [{"description": "clear sky"}],
                },
                {
                    "dt": 1640010800,
                    "main": {"temp": 43.5},
                    "weather": [{"description": "few clouds"}],
                },
            ]
        }

        responses.add(
            responses.GET,
            "https://api.openweathermap.org/data/2.5/weather",
            json=current_response,
            status=200,
        )

        responses.add(
            responses.GET,
            "https://api.openweathermap.org/data/2.5/forecast",
            json=forecast_response,
            status=200,
        )

        tool = OpenWeatherMapTool(
            api_key="test_key", location="Boston,MA,US", units="imperial"
        )

        context = {"user_input": "test", "timestamp": "2024-01-01T00:00:00"}
        result = tool.execute(context)

        # Verify result contains expected data
        assert "Boston" in result
        assert "45.5" in result
        assert "partly cloudy" in result
        assert "65%" in result
        assert "10.5" in result

    @responses.activate
    def test_execute_api_error(self):
        """Test handling of API errors."""
        responses.add(
            responses.GET,
            "https://api.openweathermap.org/data/2.5/weather",
            json={"error": "Invalid API key"},
            status=401,
        )

        tool = OpenWeatherMapTool(
            api_key="invalid_key", location="Boston,MA,US", units="imperial"
        )

        context = {"user_input": "test"}

        # Should return error message
        result = tool.execute(context)
        assert "Error:" in result
        assert "Could not fetch weather data" in result

    def test_execute_no_location(self):
        """Test error when no location is provided."""
        tool = OpenWeatherMapTool(api_key="test_key")

        context = {"user_input": "test"}

        # Should return error message
        result = tool.execute(context)
        assert "Error:" in result
        assert "location or latitude/longitude" in result


class TestToolFactory:
    """Tests for tool factory."""

    def test_create_openweathermap_tool_with_location(self):
        """Test creating OpenWeatherMap tool with location."""
        config = {
            "type": "openweathermap",
            "api_key": "test_key",
            "location": "Boston,MA,US",
            "units": "imperial",
        }

        tool = create_tool(config)

        assert isinstance(tool, OpenWeatherMapTool)
        assert tool.api_key == "test_key"
        assert tool.location == "Boston,MA,US"

    def test_create_openweathermap_tool_with_coordinates(self):
        """Test creating OpenWeatherMap tool with coordinates."""
        config = {
            "type": "openweathermap",
            "api_key": "test_key",
            "latitude": 42.3601,
            "longitude": -71.0589,
            "units": "metric",
        }

        tool = create_tool(config)

        assert isinstance(tool, OpenWeatherMapTool)
        assert tool.latitude == 42.3601
        assert tool.longitude == -71.0589

    def test_create_tool_missing_type(self):
        """Test error when tool type is missing."""
        config = {"api_key": "test_key"}

        with pytest.raises(ValueError, match="must specify 'type'"):
            create_tool(config)

    def test_create_tool_invalid_type(self):
        """Test error when tool type is invalid."""
        config = {"type": "nonexistent_tool"}

        with pytest.raises(ValueError, match="Unknown tool type"):
            create_tool(config)

    def test_create_tool_missing_api_key(self):
        """Test error when API key is missing."""
        config = {"type": "openweathermap", "location": "Boston,MA,US"}

        with pytest.raises(ValueError, match="requires 'api_key'"):
            create_tool(config)

    def test_create_tool_missing_location(self):
        """Test error when location is missing."""
        config = {"type": "openweathermap", "api_key": "test_key"}

        with pytest.raises(ValueError, match="requires either 'location'"):
            create_tool(config)


class TestCommandHandlerWithTools:
    """Tests for command handler with tool integration."""

    @responses.activate
    @patch("src.handlers.command_handler.OpenRouterClient")
    def test_command_with_tool_execution(self, mock_client_class):
        """Test that tools are executed before LLM invocation."""
        # Import here to avoid circular imports in tests
        from src.handlers.command_handler import CommandHandler
        from src.utils.config import AppConfig, SlashCommandConfig, LLMConfig

        # Mock current weather response
        current_response = {
            "name": "Boston",
            "main": {"temp": 45.5, "feels_like": 42.0, "humidity": 65},
            "weather": [{"description": "partly cloudy"}],
            "wind": {"speed": 10.5},
        }

        # Mock forecast response
        forecast_response = {
            "list": [
                {
                    "dt": 1640000000,
                    "main": {"temp": 44.0},
                    "weather": [{"description": "clear sky"}],
                }
            ]
        }

        responses.add(
            responses.GET,
            "https://api.openweathermap.org/data/2.5/weather",
            json=current_response,
            status=200,
        )

        responses.add(
            responses.GET,
            "https://api.openweathermap.org/data/2.5/forecast",
            json=forecast_response,
            status=200,
        )

        # Create mock LLM client
        mock_client = Mock()
        mock_client.generate_response.return_value = "Wear layers and stay hydrated!"
        mock_client_class.return_value = mock_client

        # Create config with tool
        command_config = SlashCommandConfig(
            command="/run",
            description="Running advice",
            llm=LLMConfig(
                api_key="test_key",
                model="anthropic/claude-3.5-sonnet",
            ),
            system_prompt="You are a running coach.",
            tools=[
                {
                    "type": "openweathermap",
                    "api_key": "weather_key",
                    "location": "Boston,MA,US",
                    "units": "imperial",
                }
            ],
        )

        app_config = AppConfig(slash_commands=[command_config])

        # Create handler
        app = Mock()
        handler = CommandHandler(app=app, config=app_config)

        # Handle command
        ack = Mock()
        say = Mock()
        command = {
            "command": "/run",
            "text": "I want to run 5 miles",
            "user_id": "U123",
            "channel_id": "C123",
        }

        handler.handle_command(ack, command, say)

        # Verify ack was called
        ack.assert_called_once()

        # Verify LLM client was called with enriched system prompt
        mock_client.generate_response.assert_called_once()
        call_kwargs = mock_client.generate_response.call_args.kwargs

        # System prompt should include weather data
        system_prompt = call_kwargs["system_prompt"]
        assert "You are a running coach" in system_prompt
        assert "OpenWeatherMap Data" in system_prompt
        assert "Boston" in system_prompt
        assert "45.5" in system_prompt

        # Verify response was sent
        say.assert_called_once()
        assert "Wear layers" in say.call_args.args[0]
