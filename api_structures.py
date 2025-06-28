# api_structures.py
# Defines the standardized data structures for our application.

from dataclasses import dataclass


@dataclass
class Coordinates:
    """Our internal, standardized representation of geographic coordinates."""
    lat: float
    lon: float


@dataclass
class RouteInfo:
    """Our internal, standardized representation of a route's travel time."""
    travel_time_sec: int
