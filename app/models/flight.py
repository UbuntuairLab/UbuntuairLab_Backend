from sqlalchemy import Column, String, Integer, Float, DateTime, Enum as SQLEnum, Index
from sqlalchemy.sql import func
from datetime import datetime
import enum
from app.database import Base


class FlightStatus(str, enum.Enum):
    """Flight processing status"""
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class FlightType(str, enum.Enum):
    """Flight operation type"""
    ARRIVAL = "arrival"
    DEPARTURE = "departure"


class Flight(Base):
    """
    Flight tracking model.
    Stores flight information from OpenSky Network.
    """
    __tablename__ = "flights"
    
    # Primary key
    icao24 = Column(String(6), primary_key=True, index=True, doc="ICAO 24-bit address")
    
    # Flight identification
    callsign = Column(String(8), nullable=True, index=True, doc="Aircraft callsign")
    origin_country = Column(String(100), nullable=True, doc="Country inferred from ICAO24")
    
    # Flight details
    flight_type = Column(SQLEnum(FlightType), nullable=False, index=True, doc="Arrival or departure")
    status = Column(SQLEnum(FlightStatus), default=FlightStatus.SCHEDULED, index=True, doc="Processing status")
    
    # Airports
    departure_airport = Column(String(4), nullable=True, index=True, doc="ICAO code of departure airport")
    arrival_airport = Column(String(4), nullable=True, index=True, doc="ICAO code of arrival airport")
    
    # Timestamps
    first_seen = Column(Integer, nullable=False, doc="Unix timestamp of first detection")
    last_seen = Column(Integer, nullable=False, doc="Unix timestamp of last detection")
    
    # AI predictions
    predicted_eta = Column(DateTime(timezone=True), nullable=True, doc="AI-predicted ETA")
    predicted_etd = Column(DateTime(timezone=True), nullable=True, doc="AI-predicted ETD")
    predicted_delay_minutes = Column(Integer, nullable=True, doc="Predicted delay in minutes")
    predicted_occupation_minutes = Column(Integer, nullable=True, doc="Predicted parking duration")
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), doc="Record creation timestamp")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), doc="Record update timestamp")
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_flight_status_type', 'status', 'flight_type'),
        Index('idx_flight_airports', 'departure_airport', 'arrival_airport'),
        Index('idx_flight_timestamps', 'first_seen', 'last_seen'),
    )
    
    def __repr__(self):
        return f"<Flight(icao24={self.icao24}, callsign={self.callsign}, status={self.status})>"
    
    def is_military(self) -> bool:
        """Check if aircraft is military based on ICAO24 pattern"""
        if not self.icao24:
            return False
        military_prefixes = ['ae', 'af', 'am', '43', '44']
        return any(self.icao24.lower().startswith(prefix) for prefix in military_prefixes)
