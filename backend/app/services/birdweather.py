"""
BirdWeather API Service
Handles communication with the BirdWeather API for fetching detection data.

Version: 1.0.0
"""

import requests
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta


class BirdWeatherAPI:
    """Client for interacting with the BirdWeather API."""

    BASE_URL = "https://app.birdweather.com/api/v1"

    def __init__(self, token: str):
        """
        Initialize the BirdWeather API client.

        Args:
            token: BirdWeather API authentication token
        """
        self.token = token.strip()
        self.headers = {
            "X-Auth-Token": self.token
        }

    def get_detections(
        self,
        station_id: int,
        limit: int = 100,
        cursor: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Fetch detections from a BirdWeather station.
        Uses cursor-based pagination as per BirdWeather API documentation.

        Args:
            station_id: The BirdWeather station ID
            limit: Number of records to fetch (max 100)
            cursor: ID of the last detection from previous page (for pagination)

        Returns:
            Dictionary with 'detections' list and pagination info
        """
        url = f"{self.BASE_URL}/stations/{station_id}/detections"
        params = {
            "limit": min(limit, 100)  # API max is 100
        }

        # Add cursor for pagination if provided
        if cursor is not None:
            params["cursor"] = cursor

        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            return {
                'detections': data.get('detections', []),
                'success': data.get('success', True)
            }
        except requests.exceptions.RequestException as e:
            print(f"Error fetching detections from station {station_id}: {e}")
            return {'detections': [], 'success': False, 'error': str(e)}

    def get_all_detections(
        self,
        station_id: int,
        max_pages: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Fetch all detections using cursor-based pagination.

        Args:
            station_id: The BirdWeather station ID
            max_pages: Maximum number of pages to fetch (each page = 100 records)

        Returns:
            List of all detections fetched
        """
        all_detections = []
        limit = 100  # BirdWeather API maximum
        cursor = None

        for page in range(max_pages):
            result = self.get_detections(station_id, limit=limit, cursor=cursor)
            detections = result['detections']

            if not detections:
                # No more records
                break

            all_detections.extend(detections)

            # If we got fewer records than the limit, we've reached the end
            if len(detections) < limit:
                break

            # Set cursor to the ID of the last detection for next page
            # The cursor is the ID of the last detection to begin pagination from
            cursor = detections[-1].get('id')

            if cursor is None:
                # Can't continue without a cursor
                print(f"Warning: Last detection has no 'id' field, stopping pagination")
                break

        return all_detections

    def get_station_stats(self, station_id: int) -> Dict[str, Any]:
        """
        Get statistics for a BirdWeather station.

        Args:
            station_id: The BirdWeather station ID

        Returns:
            Dictionary containing station statistics
        """
        url = f"{self.BASE_URL}/stations/{station_id}/stats"

        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching stats from station {station_id}: {e}")
            return {}

    def get_species(self, station_id: int) -> List[Dict[str, Any]]:
        """
        Get species list for a BirdWeather station.

        Args:
            station_id: The BirdWeather station ID

        Returns:
            List of species detected at the station
        """
        url = f"{self.BASE_URL}/stations/{station_id}/species"

        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data.get('species', [])
        except requests.exceptions.RequestException as e:
            print(f"Error fetching species from station {station_id}: {e}")
            return []

    def get_station_info(self, station_id: int) -> Dict[str, Any]:
        """
        Get information about a BirdWeather station.

        Args:
            station_id: The BirdWeather station ID

        Returns:
            Dictionary containing station information
        """
        url = f"{self.BASE_URL}/stations/{station_id}"

        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data.get('station', {})
        except requests.exceptions.RequestException as e:
            print(f"Error fetching station info for {station_id}: {e}")
            return {}


def fetch_station_data(
    token: str,
    station_id: int,
    max_pages: int = 10,
    cursor: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Convenience function to fetch detections from a BirdWeather station.

    Args:
        token: BirdWeather API token
        station_id: Station ID
        max_pages: Maximum number of pages to fetch (default 10, each page = 100 records)
        cursor: Optional cursor for starting from a specific detection ID

    Returns:
        List of detection records
    """
    api = BirdWeatherAPI(token)
    if max_pages == 1:
        result = api.get_detections(station_id, limit=100, cursor=cursor)
        return result['detections']
    return api.get_all_detections(station_id, max_pages=max_pages)


def fetch_station_info(token: str, station_id: int) -> Dict[str, Any]:
    """
    Convenience function to fetch station information.

    Args:
        token: BirdWeather API token
        station_id: Station ID

    Returns:
        Dictionary containing station information
    """
    api = BirdWeatherAPI(token)
    return api.get_station_info(station_id)
