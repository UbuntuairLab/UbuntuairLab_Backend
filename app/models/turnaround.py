from sqlalchemy import Column, String, Integer, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from app.database import Base


class AircraftTurnaroundRule(Base):
    """
    Aircraft turnaround time rules by aircraft type.
    Defines minimum, average, and maximum turnaround times.
    """
    __tablename__ = "aircraft_turnaround_rules"
    
    # Primary key
    rule_id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        doc="Unique rule ID"
    )
    
    # Aircraft type
    aircraft_type = Column(
        String(10),
        nullable=False,
        unique=True,
        index=True,
        doc="Aircraft type code (e.g., A320, B737)"
    )
    
    # Turnaround times in minutes
    min_turnaround_minutes = Column(
        Integer,
        nullable=False,
        doc="Minimum turnaround time"
    )
    avg_turnaround_minutes = Column(
        Integer,
        nullable=False,
        doc="Average turnaround time"
    )
    max_turnaround_minutes = Column(
        Integer,
        nullable=False,
        doc="Maximum turnaround time"
    )
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Rule creation timestamp"
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        doc="Rule update timestamp"
    )
    
    __table_args__ = (
        UniqueConstraint('aircraft_type', name='uq_aircraft_type'),
    )
    
    def __repr__(self):
        return f"<TurnaroundRule(type={self.aircraft_type}, avg={self.avg_turnaround_minutes}min)>"
