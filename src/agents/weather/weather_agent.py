"""
Weather Agent - Test Data Implementation

This agent provides basic weather information using test data.
It follows the same structure as other agents in the system.
"""

import logging
from typing import Dict, List, Any, Optional
from ...interfaces.agent import AgentInterface
from uuid import UUID
import json
from datetime import datetime, timedelta
import random

logger = logging.getLogger(__name__)


class WeatherAgent(AgentInterface):
    """Weather agent that returns test weather data"""

    def __init__(self):
        self._agent_id_str = "weather"
        self._uuid = None
        self.agent_id = "weather"
        self._name = "Weather Agent"
        self._description = "Provides weather information using test data"
        self._initialized = False
        self.category = "weather_information"
        self.status = "initialized"

        # Test weather data
        self._test_weather_data = self._generate_test_weather_data()

    def _generate_test_weather_data(self) -> Dict[str, Any]:
        """Generate sample weather data for testing"""
        cities = [
            "New York",
            "Los Angeles",
            "Chicago",
            "Houston",
            "Phoenix",
            "Philadelphia",
            "San Antonio",
            "San Diego",
            "Dallas",
            "San Jose",
        ]

        weather_conditions = [
            "sunny",
            "cloudy",
            "partly cloudy",
            "rainy",
            "snowy",
            "foggy",
        ]

        test_data = {}
        for city in cities:
            test_data[city.lower()] = {
                "city": city,
                "temperature": random.randint(-10, 35),
                "condition": random.choice(weather_conditions),
                "humidity": random.randint(30, 90),
                "wind_speed": random.randint(0, 25),
                "pressure": random.randint(950, 1050),
                "last_updated": datetime.now().isoformat(),
            }

        return test_data

    @property
    def agent_id_str(self) -> str:
        return self._agent_id_str

    @property
    def uuid(self) -> UUID:
        if self._uuid is None:
            raise ValueError("UUID has not been set yet.")
        return self._uuid

    @uuid.setter
    def uuid(self, value: UUID):
        if self._uuid is not None:
            raise ValueError("UUID can only be set once.")
        self._uuid = value

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the agent with configuration."""
        try:
            self._initialized = True
            logger.info("WeatherAgent initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing WeatherAgent: {str(e)}")
            raise e

    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming requests through the agent."""
        if not self._initialized:
            return {"error": "Agent not initialized"}

        command = request.get("command", "")

        if command == "get_weather":
            return await self._get_weather(request)
        elif command == "get_forecast":
            return await self._get_forecast(request)
        elif command == "list_cities":
            return await self._list_cities(request)
        else:
            return {
                "error": f"Unknown command: {command}",
                "available_commands": ["get_weather", "get_forecast", "list_cities"],
            }

    async def _get_weather(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Get current weather for a specified city."""
        try:
            city = request.get("city", "").lower().strip()

            if not city:
                return {"error": "Missing city parameter"}

            weather_data = self._test_weather_data.get(city)

            if not weather_data:
                # Return a default response for unknown cities
                available_cities = list(self._test_weather_data.keys())
                return {
                    "error": f"Weather data not available for '{city}'",
                    "available_cities": available_cities,
                }

            return {
                "status": "success",
                "data": {
                    "success": True,
                    "weather": weather_data,
                    "timestamp": datetime.now().isoformat(),
                },
            }

        except Exception as e:
            logger.error(f"Error getting weather: {str(e)}")
            return {"status": "error", "message": f"Error getting weather: {str(e)}"}

    async def _get_forecast(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Get weather forecast for a specified city."""
        try:
            city = request.get("city", "").lower().strip()
            days = request.get("days", 5)

            if not city:
                return {"error": "Missing city parameter"}

            if city not in self._test_weather_data:
                available_cities = list(self._test_weather_data.keys())
                return {
                    "error": f"Forecast data not available for '{city}'",
                    "available_cities": available_cities,
                }

            # Generate forecast based on current weather
            current_weather = self._test_weather_data[city]
            forecast = []

            for i in range(days):
                forecast_date = datetime.now() + timedelta(days=i)
                # Vary temperature slightly from current
                temp_variation = random.randint(-5, 5)
                forecast_temp = current_weather["temperature"] + temp_variation

                forecast.append(
                    {
                        "date": forecast_date.strftime("%Y-%m-%d"),
                        "temperature": forecast_temp,
                        "condition": random.choice(
                            ["sunny", "cloudy", "partly cloudy", "rainy"]
                        ),
                        "humidity": random.randint(30, 90),
                        "wind_speed": random.randint(0, 25),
                    }
                )

            return {
                "status": "success",
                "data": {
                    "success": True,
                    "city": current_weather["city"],
                    "forecast": forecast,
                    "days": days,
                    "timestamp": datetime.now().isoformat(),
                },
            }

        except Exception as e:
            logger.error(f"Error getting forecast: {str(e)}")
            return {"status": "error", "message": f"Error getting forecast: {str(e)}"}

    async def _list_cities(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """List all available cities."""
        try:
            cities = [data["city"] for data in self._test_weather_data.values()]

            return {
                "status": "success",
                "data": {
                    "success": True,
                    "cities": sorted(cities),
                    "count": len(cities),
                    "timestamp": datetime.now().isoformat(),
                },
            }

        except Exception as e:
            logger.error(f"Error listing cities: {str(e)}")
            return {"status": "error", "message": f"Error listing cities: {str(e)}"}

    async def shutdown(self) -> None:
        """Shutdown the agent."""
        self._initialized = False
        logger.info("WeatherAgent shutting down")

    def get_tools(self) -> List[Dict[str, Any]]:
        """Get agent capabilities."""
        return [
            {
                "name": "get_weather",
                "description": "Get current weather information for a specified city",
                "parameters": {
                    "city": {
                        "type": "string",
                        "description": "Name of the city to get weather for (required)",
                    }
                },
                "returnValues": {
                    "weather": "object - Current weather data including temperature, condition, humidity, wind speed, and pressure",
                    "timestamp": "string - When the data was retrieved",
                },
            },
            {
                "name": "get_forecast",
                "description": "Get weather forecast for a specified city",
                "parameters": {
                    "city": {
                        "type": "string",
                        "description": "Name of the city to get forecast for (required)",
                    },
                    "days": {
                        "type": "integer",
                        "description": "Number of days to forecast (default: 5)",
                    },
                },
                "returnValues": {
                    "forecast": "array - List of forecast data for specified number of days",
                    "city": "string - Name of the city",
                    "days": "number - Number of forecast days",
                    "timestamp": "string - When the forecast was generated",
                },
            },
            {
                "name": "list_cities",
                "description": "Get list of all available cities for weather data",
                "parameters": {},
                "returnValues": {
                    "cities": "array - List of available city names",
                    "count": "number - Total number of cities available",
                    "timestamp": "string - When the list was generated",
                },
            },
        ]

    def get_status(self) -> Dict[str, Any]:
        """Get current agent status."""
        return {
            "initialized": self._initialized,
            "healthy": self._initialized,
            "cities_available": len(self._test_weather_data),
            "capabilities_count": len(self.get_tools()),
            "test_data_generated": datetime.now().isoformat(),
        }
