# Defines the standardized, internal data structures for the application.

from dataclasses import dataclass


@dataclass
class Coordinates:
    """A standardized representation of geographic coordinates."""
    lat: float
    lon: float


@dataclass
class RouteInfo:
    """A standardized representation of a route's travel time."""
    travel_time_sec: int
    traffic_data_included: bool
