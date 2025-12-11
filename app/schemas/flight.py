"""
Flight response schemas.
"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class FlightResponse(BaseModel):
    """Flight response schema"""
    icao24: str
    callsign: Optional[str] = None
    origin_country: Optional[str] = None
    flight_type: str
    status: str
    departure_airport: Optional[str] = None
    arrival_airport: Optional[str] = None
    first_seen: Optional[int] = None
    last_seen: Optional[int] = None
    predicted_eta: Optional[datetime] = None
    predicted_etd: Optional[datetime] = None
    predicted_delay_minutes: Optional[int] = None
    predicted_occupation_minutes: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    est_departure_time: Optional[str] = None  # For future flights
    est_arrival_time: Optional[str] = None    # For future flights
    
    class Config:
        from_attributes = True


class FlightListResponse(BaseModel):
    """Paginated flight list response"""
    total: int
    skip: int
    limit: int
    flights: List[FlightResponse]
    source: Optional[str] = "database"  # "database", "aviationstack_future", "aviationstack_timetable"
