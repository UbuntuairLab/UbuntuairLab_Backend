from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum


class FlightStatus(str, Enum):
    """Flight status from AviationStack"""
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    LANDED = "landed"
    CANCELLED = "cancelled"
    INCIDENT = "incident"
    DIVERTED = "diverted"


class AirlineInfo(BaseModel):
    """Airline information"""
    name: Optional[str] = None
    iata: Optional[str] = Field(None, alias="iataCode")
    icao: Optional[str] = Field(None, alias="icaoCode")
    
    class Config:
        populate_by_name = True


class FlightNumber(BaseModel):
    """Flight number details"""
    number: Optional[str] = None
    iata: Optional[str] = Field(None, alias="iataNumber")
    icao: Optional[str] = Field(None, alias="icaoNumber")
    
    class Config:
        populate_by_name = True


class AircraftInfo(BaseModel):
    """Aircraft information"""
    registration: Optional[str] = None
    iata: Optional[str] = None
    icao: Optional[str] = None
    icao24: Optional[str] = None
    model_code: Optional[str] = Field(None, alias="modelCode")
    model_text: Optional[str] = Field(None, alias="modelText")
    
    class Config:
        populate_by_name = True


class LocationInfo(BaseModel):
    """Airport/location information for departure or arrival"""
    airport: Optional[str] = None
    timezone: Optional[str] = None
    iata: Optional[str] = Field(None, alias="iataCode")
    icao: Optional[str] = Field(None, alias="icaoCode")
    terminal: Optional[str] = None
    gate: Optional[str] = None
    baggage: Optional[str] = None
    delay: Optional[int] = None
    scheduled: Optional[str] = Field(None, alias="scheduledTime")
    estimated: Optional[str] = Field(None, alias="estimatedTime")
    actual: Optional[str] = Field(None, alias="actualTime")
    estimated_runway: Optional[str] = Field(None, alias="estimatedRunway")
    actual_runway: Optional[str] = Field(None, alias="actualRunway")
    
    class Config:
        populate_by_name = True
    
    def get_best_time(self) -> Optional[datetime]:
        """Get the most accurate time available (actual > estimated > scheduled)"""
        for time_str in [self.actual, self.estimated, self.scheduled]:
            if time_str:
                try:
                    return datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                except:
                    pass
        return None


class LiveInfo(BaseModel):
    """Live flight tracking data"""
    updated: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude: Optional[float] = None
    direction: Optional[float] = None
    speed_horizontal: Optional[float] = None
    speed_vertical: Optional[float] = None
    is_ground: Optional[bool] = None
    
    class Config:
        populate_by_name = True


class AviationStackFlight(BaseModel):
    """
    Flight data from AviationStack API.
    Supports both real-time, historical, and future flights.
    """
    flight_date: Optional[str] = None
    flight_status: Optional[FlightStatus] = None
    departure: Optional[LocationInfo] = None
    arrival: Optional[LocationInfo] = None
    airline: Optional[AirlineInfo] = None
    flight: Optional[FlightNumber] = None
    aircraft: Optional[AircraftInfo] = None
    live: Optional[LiveInfo] = None
    weekday: Optional[str] = None  # For future flights
    
    def get_icao24(self) -> Optional[str]:
        """Extract ICAO24 transponder address"""
        if self.aircraft and self.aircraft.icao24:
            return self.aircraft.icao24.lower()
        return None
    
    def get_callsign(self) -> Optional[str]:
        """Get flight callsign (IATA or ICAO number)"""
        if self.flight:
            return self.flight.iata or self.flight.icao
        return None
    
    def is_future_flight(self) -> bool:
        """Check if this is a future scheduled flight"""
        return self.weekday is not None
    
    def get_departure_time(self) -> Optional[datetime]:
        """Get best available departure time"""
        if self.departure:
            return self.departure.get_best_time()
        return None
    
    def get_arrival_time(self) -> Optional[datetime]:
        """Get best available arrival time"""
        if self.arrival:
            return self.arrival.get_best_time()
        return None
    
    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "flight_date": "2025-12-12",
                "flight_status": "scheduled",
                "departure": {
                    "airport": "Addis Ababa Bole International",
                    "iataCode": "ADD",
                    "icaoCode": "HAAB",
                    "scheduledTime": "2025-12-12T08:00:00+00:00"
                },
                "arrival": {
                    "airport": "Gnassingbe Eyadema International",
                    "iataCode": "LFW",
                    "icaoCode": "DXXX",
                    "scheduledTime": "2025-12-12T10:30:00+00:00"
                },
                "airline": {
                    "name": "Ethiopian Airlines",
                    "iataCode": "ET",
                    "icaoCode": "ETH"
                },
                "flight": {
                    "number": "500",
                    "iataNumber": "ET500",
                    "icaoNumber": "ETH500"
                },
                "aircraft": {
                    "icao24": "0200af"
                }
            }
        }


class FutureFlightSchedule(BaseModel):
    """Future flight schedule from AviationStack (flightsFuture endpoint)"""
    weekday: str = Field(..., description="Day of week (1-7)")
    departure: LocationInfo
    arrival: LocationInfo
    aircraft: Optional[AircraftInfo] = None
    airline: AirlineInfo
    flight: FlightNumber
    codeshared: Optional[dict] = None
    
    def to_aviation_stack_flight(self, date: str) -> AviationStackFlight:
        """Convert future schedule to standard flight format"""
        return AviationStackFlight(
            flight_date=date,
            flight_status=FlightStatus.SCHEDULED,
            departure=self.departure,
            arrival=self.arrival,
            airline=self.airline,
            flight=self.flight,
            aircraft=self.aircraft,
            weekday=self.weekday
        )
    
    class Config:
        populate_by_name = True


class AviationStackPagination(BaseModel):
    """Pagination info from AviationStack"""
    limit: Optional[int] = 100
    offset: Optional[int] = 0
    count: Optional[int] = 0
    total: Optional[int] = 0


class AviationStackResponse(BaseModel):
    """Response wrapper for AviationStack API"""
    pagination: AviationStackPagination
    data: List[AviationStackFlight]
    
    class Config:
        populate_by_name = True


class AviationStackFutureResponse(BaseModel):
    """Response wrapper for AviationStack future flights"""
    pagination: AviationStackPagination
    data: List[FutureFlightSchedule]
    
    class Config:
        populate_by_name = True
