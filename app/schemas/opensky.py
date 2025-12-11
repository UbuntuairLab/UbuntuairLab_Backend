from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime
from enum import Enum


class FlightType(str, Enum):
    """Type of flight operation"""
    ARRIVAL = "arrival"
    DEPARTURE = "departure"


class FlightData(BaseModel):
    """
    Schema for flight data from OpenSky Network API.
    Represents a single flight with arrival/departure information.
    """
    icao24: str = Field(..., description="Unique ICAO 24-bit address of the transponder")
    callsign: Optional[str] = Field(None, description="Callsign of the aircraft (8 chars)")
    first_seen: int = Field(..., description="Estimated time of departure (Unix timestamp)")
    last_seen: int = Field(..., description="Estimated time of arrival (Unix timestamp)")
    est_departure_airport: Optional[str] = Field(None, description="ICAO code of departure airport")
    est_arrival_airport: Optional[str] = Field(None, description="ICAO code of arrival airport")
    est_departure_airport_horiz_distance: Optional[int] = Field(None, description="Distance to departure airport (meters)")
    est_departure_airport_vert_distance: Optional[int] = Field(None, description="Vertical distance to departure airport (meters)")
    est_arrival_airport_horiz_distance: Optional[int] = Field(None, description="Distance to arrival airport (meters)")
    est_arrival_airport_vert_distance: Optional[int] = Field(None, description="Vertical distance to arrival airport (meters)")
    departure_airport_candidates_count: Optional[int] = Field(None, description="Number of other possible departure airports")
    arrival_airport_candidates_count: Optional[int] = Field(None, description="Number of other possible arrival airports")
    
    @validator('icao24')
    def validate_icao24(cls, v):
        """Ensure ICAO24 is lowercase hex string"""
        if v:
            return v.lower().strip()
        return v
    
    @validator('callsign')
    def validate_callsign(cls, v):
        """Clean up callsign"""
        if v:
            return v.strip()
        return v
    
    def is_military(self) -> bool:
        """
        Check if aircraft is military based on ICAO24 pattern.
        Military aircraft often have specific ICAO24 prefixes.
        """
        if not self.icao24:
            return False
        
        # Common military prefixes (extend as needed)
        military_prefixes = ['ae', 'af', 'am', '43', '44']
        return any(self.icao24.startswith(prefix) for prefix in military_prefixes)
    
    def get_flight_type(self, target_airport_icao: str) -> Optional[FlightType]:
        """
        Determine if this is an arrival or departure for target airport.
        
        Args:
            target_airport_icao: ICAO code of the target airport (e.g., "DXXX")
        
        Returns:
            FlightType enum or None if not relevant to target airport
        """
        if self.est_arrival_airport and self.est_arrival_airport.upper() == target_airport_icao.upper():
            return FlightType.ARRIVAL
        elif self.est_departure_airport and self.est_departure_airport.upper() == target_airport_icao.upper():
            return FlightType.DEPARTURE
        return None
    
    class Config:
        json_schema_extra = {
            "example": {
                "icao24": "3c6444",
                "callsign": "AFR123",
                "first_seen": 1702200000,
                "last_seen": 1702210000,
                "est_departure_airport": "LFPG",
                "est_arrival_airport": "DXXX",
                "est_departure_airport_horiz_distance": 1200,
                "est_departure_airport_vert_distance": 50,
                "est_arrival_airport_horiz_distance": 800,
                "est_arrival_airport_vert_distance": 30,
                "departure_airport_candidates_count": 0,
                "arrival_airport_candidates_count": 0
            }
        }


class OpenSkyResponse(BaseModel):
    """Response wrapper for OpenSky API flight data"""
    flights: list[FlightData]
    total_count: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "flights": [],
                "total_count": 0,
                "timestamp": "2025-12-10T10:30:00Z"
            }
        }
