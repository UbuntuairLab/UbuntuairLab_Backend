from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
import uuid
from app.database import Base


class NotificationType(str, enum.Enum):
    """Notification type categories"""
    CONFLIT = "conflit"
    SATURATION = "saturation"
    RAPPEL = "rappel"
    OVERFLOW = "overflow"
    DELAY = "delay"
    PARKING_FREED = "parking_freed"


class NotificationSeverity(str, enum.Enum):
    """Notification severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class Notification(Base):
    """
    Notification model for system alerts and events.
    Tracks parking conflicts, saturation, overflow, and recalls.
    """
    __tablename__ = "notifications"
    
    # Primary key
    notification_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
        doc="Unique notification ID"
    )
    
    # Foreign key to flight
    flight_icao24 = Column(
        String(6),
        ForeignKey('flights.icao24', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="Associated flight ICAO24"
    )
    
    # Notification details
    notification_type = Column(
        SQLEnum(NotificationType),
        nullable=False,
        index=True,
        doc="Type of notification"
    )
    severity = Column(
        SQLEnum(NotificationSeverity),
        default=NotificationSeverity.INFO,
        nullable=False,
        doc="Severity level"
    )
    message = Column(
        Text,
        nullable=False,
        doc="Notification message content"
    )
    
    # Status
    read_status = Column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        doc="Whether notification has been read"
    )
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
        doc="Notification creation timestamp"
    )
    acknowledged_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="When notification was acknowledged"
    )
    
    # Relationship
    flight = relationship("Flight", backref="notifications")
    
    def __repr__(self):
        return f"<Notification(id={self.notification_id}, type={self.notification_type}, flight={self.flight_icao24})>"
