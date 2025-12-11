from sqlalchemy import Column, String, Integer, Boolean, Float, Enum as SQLEnum, ForeignKey, DateTime, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base


class SpotType(str, enum.Enum):
    """Parking spot type"""
    CIVIL = "civil"
    MILITARY = "military"


class SpotStatus(str, enum.Enum):
    """Parking spot availability status"""
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    RESERVED = "reserved"
    MAINTENANCE = "maintenance"


class AircraftSizeCategory(str, enum.Enum):
    """Aircraft size category for spot compatibility"""
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class ParkingSpot(Base):
    """
    Parking spot model.
    Represents physical parking locations at the airport.
    """
    __tablename__ = "parking_spots"
    
    # Primary key
    spot_id = Column(String(10), primary_key=True, doc="Unique spot identifier (e.g., C01, M01)")
    
    # Spot characteristics
    spot_number = Column(Integer, nullable=False, doc="Numeric spot number")
    spot_type = Column(SQLEnum(SpotType, values_callable=lambda x: [e.value for e in x]), nullable=False, index=True, doc="Civil or military")
    status = Column(SQLEnum(SpotStatus, values_callable=lambda x: [e.value for e in x]), default=SpotStatus.AVAILABLE, index=True, doc="Current status")
    
    # Capacity and features
    aircraft_size_capacity = Column(SQLEnum(AircraftSizeCategory, values_callable=lambda x: [e.value for e in x]), nullable=False, doc="Maximum aircraft size")
    has_jetway = Column(Boolean, default=False, doc="Jetway/bridge available")
    distance_to_terminal = Column(Integer, nullable=False, doc="Distance to terminal in meters")
    
    # Admin management
    admin_configurable = Column(Boolean, default=True, doc="Can be modified by admin")
    notes = Column(String(500), nullable=True, doc="Admin notes")
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), doc="Record creation timestamp")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), doc="Record update timestamp")
    
    # Relationships
    allocations = relationship("ParkingAllocation", back_populates="spot", lazy="selectin")
    flights = relationship("Flight", back_populates="parking_spot")
    
    # Indexes
    __table_args__ = (
        Index('idx_spot_type_status', 'spot_type', 'status'),
    )
    
    def __repr__(self):
        return f"<ParkingSpot(spot_id={self.spot_id}, type={self.spot_type}, status={self.status})>"
    
    def is_available(self) -> bool:
        """Check if spot is available for allocation"""
        return self.status == SpotStatus.AVAILABLE


class ParkingAllocation(Base):
    """
    Parking allocation model.
    Tracks assignment of flights to parking spots.
    """
    __tablename__ = "parking_allocations"
    
    # Primary key
    allocation_id = Column(Integer, primary_key=True, autoincrement=True, doc="Unique allocation ID")
    
    # Foreign keys
    flight_icao24 = Column(String(6), ForeignKey("flights.icao24"), nullable=False, index=True, doc="Flight ICAO24")
    spot_id = Column(String(10), ForeignKey("parking_spots.spot_id"), nullable=False, index=True, doc="Parking spot ID")
    
    # Allocation timing
    allocated_at = Column(DateTime(timezone=True), server_default=func.now(), doc="Allocation timestamp")
    predicted_duration_minutes = Column(Integer, nullable=False, doc="AI-predicted occupation duration")
    predicted_end_time = Column(DateTime(timezone=True), nullable=False, doc="Predicted liberation time")
    
    # Actual timing (filled when flight departs)
    actual_start_time = Column(DateTime(timezone=True), nullable=True, doc="Actual occupation start")
    actual_end_time = Column(DateTime(timezone=True), nullable=True, doc="Actual liberation time")
    actual_duration_minutes = Column(Integer, nullable=True, doc="Actual occupation duration")
    
    # Overflow management
    overflow_to_military = Column(Boolean, default=False, doc="Whether this is military overflow")
    overflow_reason = Column(String(200), nullable=True, doc="Reason for overflow")
    
    # Conflict tracking
    conflict_detected = Column(Boolean, default=False, doc="AI detected conflict")
    conflict_probability = Column(Float, nullable=True, doc="Conflict probability (0-1)")
    conflict_resolution = Column(String(200), nullable=True, doc="How conflict was resolved")
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), doc="Record creation timestamp")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), doc="Record update timestamp")
    
    # Relationships
    spot = relationship("ParkingSpot", back_populates="allocations")
    
    # Indexes
    __table_args__ = (
        Index('idx_allocation_flight_spot', 'flight_icao24', 'spot_id'),
        Index('idx_allocation_times', 'allocated_at', 'predicted_end_time'),
        Index('idx_allocation_overflow', 'overflow_to_military'),
    )
    
    def __repr__(self):
        return f"<ParkingAllocation(id={self.allocation_id}, flight={self.flight_icao24}, spot={self.spot_id})>"
    
    def is_active(self) -> bool:
        """Check if allocation is currently active"""
        return self.actual_end_time is None
