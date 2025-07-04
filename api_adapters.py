# Contains the adapter classes for communicating with external mapping APIs.

import requests
import os
import time
from datetime import datetime
from urllib.parse import quote
from abc import ABC, abstractmethod
from dotenv import load_dotenv

from api_structures import Coordinates, RouteInfo

# --- API Configuration ---
# Keys are read from environment variables for security.
load_dotenv()
TOMTOM_API_KEY = os.getenv("TOMTOM_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GEOCODECO_API_KEY = os.getenv("GEOCODECO_API_KEY")


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


class GeocodeCoAdapter(ApiAdapter):
    """The adapter for the geocode.maps.co API (geocoding only)."""
    GEOCODE_URL = "https://geocode.maps.co/search"

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        if not GEOCODECO_API_KEY:
            raise ValueError(
                "FATAL ERROR: The GEOCODECO_API_KEY environment variable is not set.")

    def get_coordinates(self, address: str) -> Coordinates | None:
        print(f"   > [Geocode.co] Geocoding address: '{address}'...")
        params = {'q': address, 'api_key': GEOCODECO_API_KEY}

        if self.verbose:
            full_url = f"{self.GEOCODE_URL}?{requests.compat.urlencode(params)}"
            print(f"   > [API-TRACE] Request URL: {full_url}")

        try:
            response = requests.get(self.GEOCODE_URL, params=params)
            # This free API has a rate limit of 1 request/second.
            time.sleep(1.1)  # Pause to respect rate limit

            if response.status_code == 429:
                print("   > Error: Exceeded API rate limit for geocode.maps.co.")
                return None

            response.raise_for_status()
            data = response.json()

            if data:
                # *** NORMALIZATION to our standard Coordinates object ***
                location = data[0]
                return Coordinates(lat=float(location['lat']), lon=float(location['lon']))
            else:
                print(
                    f"   > Error: Could not find coordinates for address: {address}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"   > Error connecting to Geocode.co API: {e}")
            return None
        except (KeyError, IndexError):
            print(f"   > Error parsing Geocode.co API response for: {address}")
            return None

    def get_route(self, start_coords: Coordinates, end_coords: Coordinates, departure_time: datetime) -> RouteInfo | None:
        """This service does not provide routing information."""
        raise NotImplementedError(
            "Geocode.co is a geocoding-only service and cannot calculate routes.")


class FallbackGeocoderAdapter(ApiAdapter):
    """
    A composite adapter that uses a primary geocoder and falls back
    to another adapter for routing and failed geocoding lookups.
    """

    def __init__(self, primary_geocoder: ApiAdapter, fallback_adapter: ApiAdapter, verbose: bool = False):
        self.primary_geocoder = primary_geocoder
        self.fallback_adapter = fallback_adapter
        self.verbose = verbose

    def get_coordinates(self, address: str) -> Coordinates | None:
        if self.verbose:
            print(
                f"\nAttempting geocoding with primary: {type(self.primary_geocoder).__name__}")

        coords = self.primary_geocoder.get_coordinates(address)
        if coords:
            return coords

        print(
            f"\n   ! Primary geocoder failed. Falling back to {type(self.fallback_adapter).__name__}.")
        return self.fallback_adapter.get_coordinates(address)

    def get_route(self, start_coords: Coordinates, end_coords: Coordinates, departure_time: datetime) -> RouteInfo | None:
        # Routing is always delegated to the fallback adapter.
        if self.verbose:
            print(
                f"\nRouting calculation handled by: {type(self.fallback_adapter).__name__}")
        return self.fallback_adapter.get_route(start_coords, end_coords, departure_time)


class TomTomAdapter(ApiAdapter):
    """The adapter for the TomTom API."""
    GEOCODE_URL = "https://api.tomtom.com/search/2/geocode/{address}.json"
    ROUTING_URL = "https://api.tomtom.com/routing/1/calculateRoute/{locations}/json"

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        if not TOMTOM_API_KEY:
            raise ValueError(
                "FATAL ERROR: The TOMTOM_API_KEY environment variable is not set.")

    def get_coordinates(self, address: str) -> Coordinates | None:
        print(f"   > [TomTom] Geocoding address: '{address}'...")
        encoded_address = quote(address)
        url = self.GEOCODE_URL.format(address=encoded_address)
        params = {'key': TOMTOM_API_KEY}

        if self.verbose:
            full_url = f"{url}?{requests.compat.urlencode(params)}"
            print(f"   > [API-TRACE] Request URL: {full_url}")

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

        if self.verbose:
            full_url = f"{url}?{requests.compat.urlencode(params)}"
            print(f"   > [API-TRACE] Request URL: {full_url}")

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            # *** NORMALIZATION to our standard RouteInfo object ***
            travel_seconds = data['routes'][0]['summary']['travelTimeInSeconds']
            # When 'traffic' is set to 'true', TomTom's travelTimeInSeconds includes traffic delay.
            return RouteInfo(travel_time_sec=travel_seconds, traffic_data_included=True)
        except requests.exceptions.RequestException as e:
            departure_str = departure_time.strftime('%I:%M %p')
            print(
                f"   > [TomTom] A network error occurred for route calculation at {departure_str}: {e}")
            return None
        except (KeyError, IndexError):
            departure_str = departure_time.strftime('%I:%M %p')
            print(
                f"   > [TomTom] Could not find a valid route for the departure time: {departure_str}.")
            return None


class GoogleMapsAdapter(ApiAdapter):
    """The adapter for the Google Maps API."""
    GEOCODING_URL = "https://maps.googleapis.com/maps/api/geocode/json"
    DIRECTIONS_URL = "https://maps.googleapis.com/maps/api/directions/json"

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        if not GOOGLE_API_KEY:
            raise ValueError(
                "FATAL ERROR: The GOOGLE_API_KEY environment variable is not set.")

    def get_coordinates(self, address: str) -> Coordinates | None:
        print(f"   > [Google] Geocoding address: '{address}'...")
        params = {
            'address': address,
            'key': GOOGLE_API_KEY
        }

        if self.verbose:
            full_url = f"{self.GEOCODING_URL}?{requests.compat.urlencode(params)}"
            print(f"   > [API-TRACE] Request URL: {full_url}")

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

        # Google's Directions API requires departure_time as a Unix timestamp.
        departure_timestamp = int(departure_time.timestamp())

        params = {
            'origin': origin,
            'destination': destination,
            'departure_time': departure_timestamp,
            'key': GOOGLE_API_KEY
        }

        if self.verbose:
            full_url = f"{self.DIRECTIONS_URL}?{requests.compat.urlencode(params)}"
            print(f"   > [API-TRACE] Request URL: {full_url}")

        try:
            response = requests.get(self.DIRECTIONS_URL, params=params)
            response.raise_for_status()
            data = response.json()
            if data.get('status') == 'OK' and data.get('routes'):
                leg = data['routes'][0]['legs'][0]
                traffic_used = False
                # Use duration_in_traffic if available, otherwise fall back to duration.
                if 'duration_in_traffic' in leg:
                    travel_seconds = leg['duration_in_traffic']['value']
                    traffic_used = True
                else:
                    travel_seconds = leg['duration']['value']

                # *** NORMALIZATION to our standard RouteInfo object ***
                return RouteInfo(travel_time_sec=travel_seconds, traffic_data_included=traffic_used)
            else:
                departure_str = departure_time.strftime('%I:%M %p')
                print(
                    f"   > [Google] Could not find a valid route for {departure_str}. Status: {data.get('status')}")
                return None
        except requests.exceptions.RequestException as e:
            departure_str = departure_time.strftime('%I:%M %p')
            print(
                f"   > [Google] A network error occurred for route calculation at {departure_str}: {e}")
            return None
        except (KeyError, IndexError):
            departure_str = departure_time.strftime('%I:%M %p')
            print(
                f"   > [Google] Could not find a valid route for the departure time: {departure_str}.")
            return None
