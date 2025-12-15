"""
Geographic calculations for flight tracking.
Provides utilities to calculate distances between coordinates.
"""
from math import radians, sin, cos, sqrt, atan2
from typing import Tuple, Optional

# Aéroport International Gnassingbé Eyadéma (DXXX/LFW) - Lomé, Togo
# Coordonnées du seuil de piste (approximation centre aéroport)
AIRPORT_COORDS = (6.165611, 1.254797)  # (latitude, longitude)
AIRPORT_LATITUDE = 6.165611
AIRPORT_LONGITUDE = 1.254797

# Rayon moyen de la Terre en kilomètres
EARTH_RADIUS_KM = 6371.0


def haversine_distance(coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
    """
    Calculate the great circle distance between two points on Earth using the Haversine formula.
    
    Args:
        coord1: Tuple (latitude, longitude) in decimal degrees
        coord2: Tuple (latitude, longitude) in decimal degrees
    
    Returns:
        Distance in kilometers
    
    Examples:
        >>> haversine_distance((6.165611, 1.254797), (6.200000, 1.300000))
        5.234  # Distance approximative en km
    """
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    
    # Convertir en radians
    lat1_rad = radians(lat1)
    lon1_rad = radians(lon1)
    lat2_rad = radians(lat2)
    lon2_rad = radians(lon2)
    
    # Différences
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    # Formule Haversine
    a = sin(dlat / 2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    
    distance = EARTH_RADIUS_KM * c
    
    return distance


def calculate_distance_to_airport(
    latitude: Optional[float],
    longitude: Optional[float],
    airport_coords: Tuple[float, float] = AIRPORT_COORDS
) -> Optional[float]:
    """
    Calculate distance from aircraft position to airport (DXXX/LFW).
    
    Args:
        latitude: Aircraft latitude in decimal degrees
        longitude: Aircraft longitude in decimal degrees
        airport_coords: Airport coordinates (lat, lon), defaults to DXXX Lomé
    
    Returns:
        Distance in kilometers, or None if coordinates are invalid
    
    Examples:
        >>> calculate_distance_to_airport(6.200000, 1.300000)
        5.234  # Distance en km
        >>> calculate_distance_to_airport(None, None)
        None
    """
    if latitude is None or longitude is None:
        return None
    
    try:
        aircraft_coords = (latitude, longitude)
        distance = haversine_distance(aircraft_coords, airport_coords)
        return round(distance, 2)
    except (ValueError, TypeError):
        return None


def calculate_distance_km(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float
) -> float:
    """
    Calculate distance between two geographic coordinates.
    
    Args:
        lat1: First point latitude in decimal degrees
        lon1: First point longitude in decimal degrees
        lat2: Second point latitude in decimal degrees
        lon2: Second point longitude in decimal degrees
    
    Returns:
        Distance in kilometers
    """
    coord1 = (lat1, lon1)
    coord2 = (lat2, lon2)
    return haversine_distance(coord1, coord2)


def is_within_radius(
    latitude: float,
    longitude: float,
    center_coords: Tuple[float, float],
    radius_km: float
) -> bool:
    """
    Check if a coordinate is within a given radius of a center point.
    
    Args:
        latitude: Point latitude in decimal degrees
        longitude: Point longitude in decimal degrees
        center_coords: Center point (lat, lon)
        radius_km: Radius in kilometers
    
    Returns:
        True if point is within radius, False otherwise
    
    Examples:
        >>> is_within_radius(6.200000, 1.300000, AIRPORT_COORDS, 10.0)
        True  # Dans les 10km
        >>> is_within_radius(7.000000, 2.000000, AIRPORT_COORDS, 10.0)
        False  # Hors des 10km
    """
    point_coords = (latitude, longitude)
    distance = haversine_distance(point_coords, center_coords)
    return distance <= radius_km


def get_bounding_box(
    center_lat: float,
    center_lon: float,
    radius_km: float
) -> Tuple[float, float, float, float]:
    """
    Calculate bounding box (lat_min, lat_max, lon_min, lon_max) for a circle.
    
    Approximation simple basée sur 1 degré ≈ 111 km à l'équateur.
    
    Args:
        center_lat: Center latitude in decimal degrees
        center_lon: Center longitude in decimal degrees
        radius_km: Radius in kilometers
    
    Returns:
        Tuple (lat_min, lat_max, lon_min, lon_max)
    
    Examples:
        >>> get_bounding_box(6.165611, 1.254797, 60.0)
        (5.625611, 6.705611, 0.714797, 1.794797)  # Box de ~60km de rayon
    """
    # Approximation: 1 degré latitude ≈ 111 km
    # 1 degré longitude varie selon latitude: ≈ 111 * cos(lat) km
    lat_delta = radius_km / 111.0
    lon_delta = radius_km / (111.0 * cos(radians(center_lat)))
    
    lat_min = center_lat - lat_delta
    lat_max = center_lat + lat_delta
    lon_min = center_lon - lon_delta
    lon_max = center_lon + lon_delta
    
    return (lat_min, lat_max, lon_min, lon_max)


def meters_to_kilometers(meters: Optional[float]) -> Optional[float]:
    """Convert meters to kilometers."""
    if meters is None:
        return None
    return round(meters / 1000.0, 2)


def meters_per_second_to_kmh(mps: Optional[float]) -> Optional[float]:
    """
    Convert velocity from meters/second to kilometers/hour.
    
    Args:
        mps: Velocity in meters per second
    
    Returns:
        Velocity in km/h, or None if input is None
    """
    if mps is None:
        return None
    return round(mps * 3.6, 1)
