"""
Parking schemas.
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ParkingSpotResponse(BaseModel):
    """Parking spot response schema"""
    spot_id: str
    spot_number: int
    spot_type: str
    status: str
    aircraft_size_capacity: str
    has_jetway: bool
    distance_to_terminal: int
    admin_configurable: bool
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ParkingSpotUpdate(BaseModel):
    """Parking spot update schema"""
    status: Optional[str] = None
    notes: Optional[str] = None


class ParkingSpotCreate(BaseModel):
    """Parking spot creation schema"""
    spot_id: str
    spot_number: int
    spot_type: str  # 'civil' or 'military'
    status: Optional[str] = 'available'
    aircraft_size_capacity: str  # 'small', 'medium', 'large'
    has_jetway: bool = False
    distance_to_terminal: int
    admin_configurable: Optional[bool] = True
    notes: Optional[str] = None


class ParkingAllocationResponse(BaseModel):
    """Parking allocation response schema"""
    allocation_id: int
    flight_icao24: str
    spot_id: str
    allocated_at: datetime
    predicted_duration_minutes: int
    predicted_end_time: datetime
    actual_start_time: Optional[datetime]
    actual_end_time: Optional[datetime]
    actual_duration_minutes: Optional[int]
    overflow_to_military: bool
    overflow_reason: Optional[str]
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True
