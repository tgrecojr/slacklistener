"""OpenWeatherMap API tool for weather data enrichment."""

import logging
from typing import Dict, Any, Optional
import requests

from ..tool import Tool

logger = logging.getLogger(__name__)


class OpenWeatherMapTool(Tool):
    """Tool to fetch current and forecast weather from OpenWeatherMap API."""

    def __init__(
        self,
        api_key: str,
        location: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        units: str = "imperial",
        language: str = "en",
    ):
        """
        Initialize OpenWeatherMap tool.

        Args:
            api_key: OpenWeatherMap API key
            location: Location string (e.g., "Boston,MA,US")
            latitude: Latitude for location (alternative to location string)
            longitude: Longitude for location (alternative to location string)
            units: Units system (imperial, metric, or standard)
            language: Language for descriptions
        """
        self.api_key = api_key
        self.location = location
        self.latitude = latitude
        self.longitude = longitude
        self.units = units
        self.language = language
        self.base_url = "https://api.openweathermap.org/data/2.5"

    def get_name(self) -> str:
        """Get tool name."""
        return "OpenWeatherMap"

    def execute(self, context: Dict[str, Any]) -> str:
        """
        Fetch weather data and format for LLM consumption.

        Args:
            context: Execution context (not used for this tool)

        Returns:
            Formatted weather data string
        """
        try:
            # Get current weather
            current_weather = self._fetch_current_weather()

            # Get forecast
            forecast = self._fetch_forecast()

            # Format the data for LLM
            weather_report = self._format_weather_data(current_weather, forecast)

            logger.info("Successfully fetched weather data from OpenWeatherMap")
            return weather_report

        except Exception as e:
            logger.error(f"Error fetching weather data: {e}")
            return f"Error: Could not fetch weather data - {str(e)}"

    def _fetch_current_weather(self) -> Dict[str, Any]:
        """Fetch current weather from OpenWeatherMap API."""
        url = f"{self.base_url}/weather"
        params = {
            "appid": self.api_key,
            "units": self.units,
            "lang": self.language,
        }

        # Add location parameters
        if self.latitude is not None and self.longitude is not None:
            params["lat"] = self.latitude
            params["lon"] = self.longitude
        elif self.location:
            params["q"] = self.location
        else:
            raise ValueError("Either location or latitude/longitude must be provided")

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        return response.json()

    def _fetch_forecast(self) -> Dict[str, Any]:
        """Fetch 5-day/3-hour forecast from OpenWeatherMap API."""
        url = f"{self.base_url}/forecast"
        params = {
            "appid": self.api_key,
            "units": self.units,
            "lang": self.language,
        }

        # Add location parameters
        if self.latitude is not None and self.longitude is not None:
            params["lat"] = self.latitude
            params["lon"] = self.longitude
        elif self.location:
            params["q"] = self.location
        else:
            raise ValueError("Either location or latitude/longitude must be provided")

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        return response.json()

    def _format_weather_data(
        self, current: Dict[str, Any], forecast: Dict[str, Any]
    ) -> str:
        """
        Format weather data into a readable string for LLM.

        Args:
            current: Current weather data from API
            forecast: Forecast data from API

        Returns:
            Formatted weather report string
        """
        # Extract current weather info
        temp_unit = "°F" if self.units == "imperial" else "°C"
        speed_unit = "mph" if self.units == "imperial" else "m/s"

        current_temp = current["main"]["temp"]
        feels_like = current["main"]["feels_like"]
        humidity = current["main"]["humidity"]
        weather_desc = current["weather"][0]["description"]
        wind_speed = current["wind"]["speed"]
        location_name = current["name"]

        # Build current weather section
        report = f"CURRENT WEATHER for {location_name}:\n"
        report += f"- Temperature: {current_temp:.1f}{temp_unit} (feels like {feels_like:.1f}{temp_unit})\n"
        report += f"- Conditions: {weather_desc}\n"
        report += f"- Humidity: {humidity}%\n"
        report += f"- Wind Speed: {wind_speed:.1f} {speed_unit}\n"

        # Add forecast (next 24 hours - 8 data points at 3-hour intervals)
        report += "\nFORECAST (Next 24 hours):\n"
        for i, item in enumerate(forecast["list"][:8]):
            from datetime import datetime

            dt = datetime.fromtimestamp(item["dt"])
            temp = item["main"]["temp"]
            desc = item["weather"][0]["description"]
            time_str = dt.strftime("%I:%M %p")

            report += f"- {time_str}: {temp:.1f}{temp_unit}, {desc}\n"

        return report
