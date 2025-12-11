"""
Notification Service.
Handles creation and management of system notifications.
"""
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.notification_repository import NotificationRepository
from app.models.notification import NotificationType, NotificationSeverity
from app.models.flight import Flight
from app.models.parking import ParkingAllocation, ParkingSpot

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Service for creating and managing notifications.
    Handles conflicts, saturation alerts, overflow, and recalls.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.notification_repo = NotificationRepository(db)
    
    async def create_conflict_notification(
        self,
        flight: Flight,
        allocation: ParkingAllocation,
        conflict_probability: float
    ) -> None:
        """Create notification for detected parking conflict"""
        message = (
            f"Conflit détecté pour le vol {flight.callsign or flight.icao24} "
            f"(spot {allocation.spot_id}). Probabilité: {conflict_probability*100:.1f}%"
        )
        
        severity = NotificationSeverity.WARNING if conflict_probability < 0.5 else NotificationSeverity.CRITICAL
        
        await self.notification_repo.create(
            flight_icao24=flight.icao24,
            notification_type=NotificationType.CONFLIT,
            message=message,
            severity=severity
        )
        
        logger.info(f"Created conflict notification for flight {flight.icao24}")
    
    async def create_saturation_alert(
        self,
        occupation_rate: float,
        available_spots: int
    ) -> None:
        """Create notification for parking saturation"""
        # Note: This needs a flight context, but can be system-wide
        # For now, skip or attach to most recent flight
        from app.repositories.flight_repository import FlightRepository
        flight_repo = FlightRepository(self.db)
        
        # Get a recent flight for context
        flights = await flight_repo.list(skip=0, limit=1)
        if not flights[0]:
            return
        
        recent_flight = flights[0][0]
        
        message = (
            f"Alerte saturation parking: {occupation_rate:.1f}% occupé. "
            f"Seulement {available_spots} places disponibles."
        )
        
        severity = NotificationSeverity.CRITICAL if occupation_rate > 90 else NotificationSeverity.WARNING
        
        await self.notification_repo.create(
            flight_icao24=recent_flight.icao24,
            notification_type=NotificationType.SATURATION,
            message=message,
            severity=severity
        )
        
        logger.warning(f"Created saturation alert: {occupation_rate:.1f}%")
    
    async def create_overflow_notification(
        self,
        flight: Flight,
        reason: str,
        military_spot: ParkingSpot
    ) -> None:
        """Create notification for overflow to military parking"""
        message = (
            f"Vol {flight.callsign or flight.icao24} transféré au parking militaire "
            f"(spot {military_spot.spot_id}). Raison: {reason}"
        )
        
        await self.notification_repo.create(
            flight_icao24=flight.icao24,
            notification_type=NotificationType.OVERFLOW,
            message=message,
            severity=NotificationSeverity.WARNING
        )
        
        logger.info(f"Created overflow notification for flight {flight.icao24}")
    
    async def create_recall_notification(
        self,
        flight: Flight,
        civil_spot: ParkingSpot
    ) -> None:
        """Create notification for recall from military to civil parking"""
        message = (
            f"Vol {flight.callsign or flight.icao24} rappelé vers parking civil "
            f"(spot {civil_spot.spot_id})"
        )
        
        await self.notification_repo.create(
            flight_icao24=flight.icao24,
            notification_type=NotificationType.RAPPEL,
            message=message,
            severity=NotificationSeverity.INFO
        )
        
        logger.info(f"Created recall notification for flight {flight.icao24}")
    
    async def create_parking_freed_notification(
        self,
        flight: Flight,
        freed_spot: ParkingSpot
    ) -> None:
        """Create notification when parking spot is freed"""
        message = (
            f"Place parking {freed_spot.spot_id} libérée par vol "
            f"{flight.callsign or flight.icao24}"
        )
        
        await self.notification_repo.create(
            flight_icao24=flight.icao24,
            notification_type=NotificationType.PARKING_FREED,
            message=message,
            severity=NotificationSeverity.INFO
        )
        
        logger.info(f"Created parking freed notification for spot {freed_spot.spot_id}")
    
    async def create_delay_notification(
        self,
        flight: Flight,
        delay_minutes: int
    ) -> None:
        """Create notification for significant flight delay"""
        message = (
            f"Retard important pour vol {flight.callsign or flight.icao24}: "
            f"{delay_minutes} minutes"
        )
        
        severity = NotificationSeverity.WARNING if delay_minutes < 30 else NotificationSeverity.CRITICAL
        
        await self.notification_repo.create(
            flight_icao24=flight.icao24,
            notification_type=NotificationType.DELAY,
            message=message,
            severity=severity
        )
        
        logger.info(f"Created delay notification for flight {flight.icao24}")
