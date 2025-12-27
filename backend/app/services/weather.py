"""
Weather API Service
Handles communication with Open-Meteo API for weather data.

Version: 1.0.0
"""

import requests
from datetime import datetime, timedelta
from typing import Dict, Any, Optional


class WeatherAPI:
    """Client for interacting with the Open-Meteo weather API."""

    def __init__(self):
        """Initialize the Weather API client."""
        self.forecast_url = "https://api.open-meteo.com/v1/forecast"
        self.archive_url = "https://archive-api.open-meteo.com/v1/archive"

    def get_current_weather(
        self,
        lat: float,
        lon: float,
        city_name: str = ""
    ) -> Optional[Dict[str, Any]]:
        """
        Get current weather for a location using Open-Meteo API.
        No API key required - completely free.

        Args:
            lat: Latitude
            lon: Longitude
            city_name: Optional city name for display

        Returns:
            Dictionary containing current weather data
        """
        try:
            url = self.forecast_url
            params = {
                'latitude': lat,
                'longitude': lon,
                'current': 'temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,pressure_msl,wind_speed_10m',
                'temperature_unit': 'fahrenheit',
                'wind_speed_unit': 'mph',
                'precipitation_unit': 'inch'
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if 'current' in data:
                current = data['current']

                # Map weather codes to descriptions
                weather_code = current.get('weather_code', 0)
                description = self._get_weather_description(weather_code)

                return {
                    'temp': current.get('temperature_2m'),
                    'feels_like': current.get('apparent_temperature'),
                    'humidity': current.get('relative_humidity_2m'),
                    'pressure': current.get('pressure_msl'),
                    'wind_speed': current.get('wind_speed_10m'),
                    'description': description,
                    'precipitation': current.get('precipitation'),
                    'city_name': city_name,
                    'latitude': lat,
                    'longitude': lon
                }

            return None

        except Exception as e:
            print(f"Error fetching current weather: {e}")
            return None

    def get_historical_weather(
        self,
        lat: float,
        lon: float,
        date: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get historical weather for a specific location and date using Open-Meteo Archive API.
        Date format: 'YYYY-MM-DD'
        Free API - no key required, data back to 1940.

        Args:
            lat: Latitude
            lon: Longitude
            date: Date in 'YYYY-MM-DD' format

        Returns:
            Dictionary containing historical weather data
        """
        try:
            url = self.archive_url
            params = {
                'latitude': lat,
                'longitude': lon,
                'start_date': date,
                'end_date': date,
                'daily': 'temperature_2m_max,temperature_2m_min,temperature_2m_mean,relative_humidity_2m_mean,precipitation_sum,wind_speed_10m_max,pressure_msl_mean,weather_code',
                'temperature_unit': 'fahrenheit',
                'wind_speed_unit': 'mph',
                'precipitation_unit': 'inch'
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if 'daily' in data and len(data['daily'].get('time', [])) > 0:
                daily = data['daily']

                # Get weather description from weather code
                weather_code = daily.get('weather_code', [0])[0] if daily.get('weather_code') else 0
                description = self._get_weather_description(weather_code)

                return {
                    'temp_max': daily.get('temperature_2m_max', [None])[0],
                    'temp_min': daily.get('temperature_2m_min', [None])[0],
                    'temp_avg': daily.get('temperature_2m_mean', [None])[0],
                    'humidity': daily.get('relative_humidity_2m_mean', [None])[0],
                    'pressure': daily.get('pressure_msl_mean', [None])[0],
                    'wind_speed': daily.get('wind_speed_10m_max', [None])[0],
                    'precipitation': daily.get('precipitation_sum', [None])[0],
                    'description': description,
                    'latitude': lat,
                    'longitude': lon
                }

            return None

        except Exception as e:
            print(f"Error fetching historical weather: {e}")
            return None

    def _get_weather_description(self, code: int) -> str:
        """
        Convert WMO Weather interpretation codes to human-readable descriptions.
        Source: https://open-meteo.com/en/docs

        Args:
            code: WMO weather code

        Returns:
            Human-readable weather description
        """
        weather_codes = {
            0: "Clear sky",
            1: "Mainly clear",
            2: "Partly cloudy",
            3: "Overcast",
            45: "Foggy",
            48: "Depositing rime fog",
            51: "Light drizzle",
            53: "Moderate drizzle",
            55: "Dense drizzle",
            56: "Light freezing drizzle",
            57: "Dense freezing drizzle",
            61: "Slight rain",
            63: "Moderate rain",
            65: "Heavy rain",
            66: "Light freezing rain",
            67: "Heavy freezing rain",
            71: "Slight snow fall",
            73: "Moderate snow fall",
            75: "Heavy snow fall",
            77: "Snow grains",
            80: "Slight rain showers",
            81: "Moderate rain showers",
            82: "Violent rain showers",
            85: "Slight snow showers",
            86: "Heavy snow showers",
            95: "Thunderstorm",
            96: "Thunderstorm with slight hail",
            99: "Thunderstorm with heavy hail"
        }
        return weather_codes.get(code, "Unknown")

    def get_sunrise_sunset(
        self,
        lat: float,
        lon: float,
        date: str
    ) -> Optional[Dict[str, str]]:
        """
        Get sunrise and sunset times for a location and date.
        Uses the Open-Meteo API (free, no API key required).
        Returns times in HH:MM:SS format.

        Args:
            lat: Latitude
            lon: Longitude
            date: Date in 'YYYY-MM-DD' format

        Returns:
            Dictionary with sunrise, sunset, and day_length
        """
        try:
            # For current/future dates, use forecast API
            # For historical dates, use archive API
            from datetime import datetime as dt

            date_obj = dt.strptime(date, '%Y-%m-%d').date()
            today = dt.now().date()

            # Use archive for past dates, forecast for today and future
            if date_obj < today:
                url = self.archive_url
            else:
                url = self.forecast_url

            params = {
                'latitude': lat,
                'longitude': lon,
                'start_date': date,
                'end_date': date,
                'daily': 'sunrise,sunset',
                'timezone': 'auto'
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if 'daily' in data and len(data['daily'].get('time', [])) > 0:
                daily = data['daily']

                sunrise_iso = daily.get('sunrise', [None])[0]
                sunset_iso = daily.get('sunset', [None])[0]

                if sunrise_iso and sunset_iso:
                    # Convert ISO datetime to HH:MM:SS format
                    sunrise_time = dt.fromisoformat(sunrise_iso).strftime('%H:%M:%S')
                    sunset_time = dt.fromisoformat(sunset_iso).strftime('%H:%M:%S')

                    # Calculate day length
                    sunrise_dt = dt.fromisoformat(sunrise_iso)
                    sunset_dt = dt.fromisoformat(sunset_iso)
                    day_length = sunset_dt - sunrise_dt

                    # Format day_length as HH:MM:SS
                    total_seconds = int(day_length.total_seconds())
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    seconds = total_seconds % 60
                    day_length_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

                    return {
                        'sunrise': sunrise_time,
                        'sunset': sunset_time,
                        'day_length': day_length_str,
                        'timezone': data.get('timezone', 'UTC')
                    }

            return None

        except Exception as e:
            print(f"Error fetching sunrise/sunset: {e}")
            return None
