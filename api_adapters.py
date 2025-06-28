# api_adapters.py
# Contains the adapter classes for communicating with external mapping APIs.

import requests
import os
from datetime import datetime
from urllib.parse import quote
from abc import ABC, abstractmethod

# Import our standard data structures
from api_structures import Coordinates, RouteInfo

# --- API Configuration ---
# Keys are read from environment variables for security.
TOMTOM_API_KEY = os.getenv("TOMTOM_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")


# --- Blueprint for all API Adapters ---

class ApiAdapter(ABC):
    """
    Abstract Base Class (blueprint) for all API clients.
    It ensures every adapter we create has the same public methods.
    """
    @abstractmethod
    def get_coordinates(self, address: str) -> Coordinates | None:
        """Converts a string address into our standard Coordinates object."""
        pass

    @abstractmethod
    def get_route(self, start_coords: Coordinates, end_coords: Coordinates, departure_time: datetime) -> RouteInfo | None:
        """Calculates a route and returns our standard RouteInfo object."""
        pass


# --- TomTom Implementation ---

class TomTomAdapter(ApiAdapter):
    """The adapter for the TomTom API."""
    GEOCODE_URL = "https://api.tomtom.com/search/2/geocode/{address}.json"
    ROUTING_URL = "https://api.tomtom.com/routing/1/calculateRoute/{locations}/json"

    def __init__(self):
        if not TOMTOM_API_KEY:
            raise ValueError(
                "FATAL ERROR: The TOMTOM_API_KEY environment variable is not set.")

    def get_coordinates(self, address: str) -> Coordinates | None:
        print(f"   > [TomTom] Geocoding address: '{address}'...")
        encoded_address = quote(address)
        url = self.GEOCODE_URL.format(address=encoded_address)
        params = {'key': TOMTOM_API_KEY}
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            if data and data.get('results'):
                position = data['results'][0]['position']
                # *** NORMALIZATION to our standard Coordinates object ***
                return Coordinates(lat=position['lat'], lon=position['lon'])
            else:
                print(
                    f"   > Error: Could not find coordinates for address: {address}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"   > Error connecting to TomTom Geocoding API: {e}")
            return None
        except (KeyError, IndexError):
            print(
                f"   > Error parsing TomTom Geocoding API response for: {address}")
            return None

    def get_route(self, start_coords: Coordinates, end_coords: Coordinates, departure_time: datetime) -> RouteInfo | None:
        locations = f"{start_coords.lat},{start_coords.lon}:{end_coords.lat},{end_coords.lon}"
        url = self.ROUTING_URL.format(locations=locations)
        params = {
            'key': TOMTOM_API_KEY,
            'departAt': departure_time.isoformat(),
            'traffic': 'true'
        }
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            # *** NORMALIZATION to our standard RouteInfo object ***
            travel_seconds = data['routes'][0]['summary']['travelTimeInSeconds']
            return RouteInfo(travel_time_sec=travel_seconds)
        except requests.exceptions.RequestException as e:
            print(
                f"   > [TomTom] A network error occurred for route calculation: {e}")
            return None
        except (KeyError, IndexError):
            print(
                f"   > [TomTom] Could not find a valid route for the specified time.")
            return None

# --- Google Maps Implementation ---


class GoogleMapsAdapter(ApiAdapter):
    """The adapter for the Google Maps API."""
    GEOCODING_URL = "https://maps.googleapis.com/maps/api/geocode/json"
    DIRECTIONS_URL = "https://maps.googleapis.com/maps/api/directions/json"

    def __init__(self):
        if not GOOGLE_API_KEY:
            raise ValueError(
                "FATAL ERROR: The GOOGLE_API_KEY environment variable is not set.")

    def get_coordinates(self, address: str) -> Coordinates | None:
        print(f"   > [Google] Geocoding address: '{address}'...")
        params = {
            'address': address,
            'key': GOOGLE_API_KEY
        }
        try:
            response = requests.get(self.GEOCODING_URL, params=params)
            response.raise_for_status()
            data = response.json()
            if data.get('status') == 'OK' and data.get('results'):
                location = data['results'][0]['geometry']['location']
                # *** NORMALIZATION to our standard Coordinates object ***
                return Coordinates(lat=location['lat'], lon=location['lng'])
            else:
                print(
                    f"   > Error: Could not find coordinates for address: {address}. Status: {data.get('status')}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"   > Error connecting to Google Geocoding API: {e}")
            return None
        except (KeyError, IndexError):
            print(
                f"   > Error parsing Google Geocoding API response for: {address}")
            return None

    def get_route(self, start_coords: Coordinates, end_coords: Coordinates, departure_time: datetime) -> RouteInfo | None:
        origin = f"{start_coords.lat},{start_coords.lon}"
        destination = f"{end_coords.lat},{end_coords.lon}"

        # Google Directions API requires departure_time as a Unix timestamp.
        departure_timestamp = int(departure_time.timestamp())

        params = {
            'origin': origin,
            'destination': destination,
            'departure_time': departure_timestamp,
            'key': GOOGLE_API_KEY
        }
        try:
            response = requests.get(self.DIRECTIONS_URL, params=params)
            response.raise_for_status()
            data = response.json()
            if data.get('status') == 'OK' and data.get('routes'):
                leg = data['routes'][0]['legs'][0]
                # Use duration_in_traffic if available, otherwise fall back to duration.
                if 'duration_in_traffic' in leg:
                    travel_seconds = leg['duration_in_traffic']['value']
                else:
                    travel_seconds = leg['duration']['value']

                # *** NORMALIZATION to our standard RouteInfo object ***
                return RouteInfo(travel_time_sec=travel_seconds)
            else:
                print(
                    f"   > [Google] Could not find a valid route. Status: {data.get('status')}")
                return None
        except requests.exceptions.RequestException as e:
            print(
                f"   > [Google] A network error occurred for route calculation: {e}")
            return None
        except (KeyError, IndexError):
            print(
                f"   > [Google] Could not find a valid route for the specified time.")
            return None
