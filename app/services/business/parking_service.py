import logging
from typing import Optional, List
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.parking_repository import ParkingSpotRepository, ParkingAllocationRepository
from app.repositories.flight_repository import FlightRepository
from app.services.notifications.notification_service import NotificationService
from app.models.parking import SpotType, SpotStatus, AircraftSizeCategory, ParkingSpot, ParkingAllocation
from app.models.flight import Flight

logger = logging.getLogger(__name__)


class ParkingAllocationResult:
    """Result of parking allocation attempt"""
    
    def __init__(
        self,
        success: bool,
        allocation: Optional[ParkingAllocation] = None,
        spot: Optional[ParkingSpot] = None,
        overflow_to_military: bool = False,
        reason: Optional[str] = None
    ):
        self.success = success
        self.allocation = allocation
        self.spot = spot
        self.overflow_to_military = overflow_to_military
        self.reason = reason


class ParkingService:
    """
    Business logic for parking spot allocation and conflict management.
    Implements rules for civil/military overflow and conflict resolution.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.spot_repo = ParkingSpotRepository(db)
        self.allocation_repo = ParkingAllocationRepository(db)
        self.flight_repo = FlightRepository(db)
        self.notification_service = NotificationService(db)
    
    async def allocate_spot(
        self,
        flight: Flight,
        predicted_occupation_minutes: int,
        conflict_data: Optional[dict] = None
    ) -> ParkingAllocationResult:
        """
        Main allocation logic: find optimal spot or overflow to military.
        Implements smart saturation management by transferring late-departure flights.
        
        Args:
            flight: Flight object
            predicted_occupation_minutes: Expected occupation duration
            conflict_data: ML model_3_conflict data
        
        Returns:
            ParkingAllocationResult with allocation decision
        """
        logger.info(
            f"Allocating parking for flight {flight.icao24} ({flight.callsign})",
            extra={
                "duration": predicted_occupation_minutes,
                "flight_type": flight.flight_type.value
            }
        )
        
        # Determine aircraft size
        aircraft_size = self._get_aircraft_size("A320")  # Default, extract from flight if available
        
        # Check conflict probability
        conflict_detected = False
        conflict_probability = 0.0
        if conflict_data:
            conflict_probability = conflict_data.get("risque_conflit", 0.0)
            conflict_detected = conflict_probability > 0.5
            
            # Log conflict detection
            if conflict_detected:
                logger.warning(
                    f"High conflict probability ({conflict_probability:.2%}) detected for flight {flight.icao24}"
                )
        
        # Try civil spots first
        civil_spots = await self.spot_repo.get_available_by_type(
            spot_type=SpotType.CIVIL,
            aircraft_size=aircraft_size
        )
        
        if civil_spots and not conflict_detected:
            # Allocate to civil spot
            best_spot = civil_spots[0]  # Already sorted by priority
            
            predicted_end_time = datetime.utcnow() + timedelta(minutes=predicted_occupation_minutes)
            
            allocation = await self.allocation_repo.create(
                flight_icao24=flight.icao24,
                spot_id=best_spot.spot_id,
                predicted_duration_minutes=predicted_occupation_minutes,
                predicted_end_time=predicted_end_time,
                conflict_detected=conflict_detected,
                conflict_probability=conflict_probability
            )
            
            # Update spot status
            await self.spot_repo.update_status(best_spot.spot_id, SpotStatus.OCCUPIED)
            
            # Update flight parking assignment
            await self.flight_repo.update_parking_assignment(flight.icao24, best_spot.spot_id)
            
            # Create conflict notification if detected
            if conflict_detected:
                await self.notification_service.create_conflict_notification(
                    flight_icao24=flight.icao24,
                    spot_id=best_spot.spot_id,
                    conflict_probability=conflict_probability
                )
            
            logger.info(f"Allocated civil spot {best_spot.spot_id} for flight {flight.icao24}")
            
            return ParkingAllocationResult(
                success=True,
                allocation=allocation,
                spot=best_spot,
                overflow_to_military=False,
                reason="Civil spot allocated"
            )
        
        # Civil saturation detected - try smart transfer to military
        logger.warning(f"Civil saturation for flight {flight.icao24}, attempting smart military transfer")
        
        # Try to free a civil spot by transferring late-departure flight to military
        transferred = await self._transfer_late_departure_to_military(flight, aircraft_size)
        
        if transferred:
            # A civil spot was freed, allocate it to the new flight
            civil_spots = await self.spot_repo.get_available_by_type(
                spot_type=SpotType.CIVIL,
                aircraft_size=aircraft_size
            )
            
            if civil_spots:
                best_spot = civil_spots[0]
                predicted_end_time = datetime.utcnow() + timedelta(minutes=predicted_occupation_minutes)
                
                allocation = await self.allocation_repo.create(
                    flight_icao24=flight.icao24,
                    spot_id=best_spot.spot_id,
                    predicted_duration_minutes=predicted_occupation_minutes,
                    predicted_end_time=predicted_end_time,
                    conflict_detected=conflict_detected,
                    conflict_probability=conflict_probability
                )
                
                await self.spot_repo.update_status(best_spot.spot_id, SpotStatus.OCCUPIED)
                await self.flight_repo.update_parking_assignment(flight.icao24, best_spot.spot_id)
                
                logger.info(f"Allocated civil spot {best_spot.spot_id} after military transfer")
                
                return ParkingAllocationResult(
                    success=True,
                    allocation=allocation,
                    spot=best_spot,
                    overflow_to_military=False,
                    reason="Civil spot allocated after smart transfer"
                )
        
        # No automatic military assignment for new flights - require admin decision
        logger.error(
            f"Complete civil saturation for flight {flight.icao24}. "
            f"No automatic transfer possible. Attempting direct military overflow.\
"
        )
        
        # Get available military spots
        military_spots = await self.spot_repo.get_available_by_type(
            spot_type=SpotType.MILITARY,
            aircraft_size=aircraft_size
        )
        
        if military_spots:
            military_spot = military_spots[0]
            
            # Allocate to military
            allocation = await self.allocation_repo.create(
                flight_icao24=flight.icao24,
                spot_id=military_spot.spot_id,
                predicted_duration_minutes=predicted_occupation_minutes,
                predicted_end_time=predicted_end_time,
                overflow_to_military=True,
                overflow_reason="Civil parking full - automatic military overflow",
                conflict_detected=conflict_detected,
                conflict_probability=conflict_probability
            )
            
            await self.spot_repo.update_status(military_spot.spot_id, SpotStatus.OCCUPIED)
            await self.flight_repo.update_parking_assignment(flight.icao24, military_spot.spot_id)
            
            # Create overflow notification
            await self.notification_service.create_overflow_notification(
                flight_icao24=flight.icao24,
                spot_id=military_spot.spot_id,
                reason="Civil parking saturated - automatic overflow"
            )
            
            logger.info(
                f"Flight {flight.icao24} allocated to military overflow spot {military_spot.spot_id}"
            )
            
            return ParkingAllocationResult(
                success=True,
                spot=military_spot,
                allocation=allocation,
                overflow_to_military=True,
                reason="Allocated to military parking (civil full)"
            )
        
        # Complete saturation - no spots available anywhere
        logger.error(
            f"Complete saturation for flight {flight.icao24}. "
            f"No civil or military spots available."
        )
        
        # Create alert notification for admin
        await self.notification_service.create_saturation_alert(
            occupation_rate=100.0,
            available_spots=0
        )
        
        return ParkingAllocationResult(
            success=False,
            reason="Complete parking saturation - no spots available (civil and military full). Admin intervention required."
        )
    
    
    async def _transfer_late_departure_to_military(
        self,
        incoming_flight: Flight,
        aircraft_size: AircraftSizeCategory
    ) -> bool:
        """
        Transfer the flight with the latest departure to military to free a civil spot.
        Only transfers if military spots are available.
        
        Args:
            incoming_flight: The new flight needing a civil spot
            aircraft_size: Required aircraft size category
        
        Returns:
            True if a flight was successfully transferred
        """
        # Check if military spots are available
        military_spots = await self.spot_repo.get_available_by_type(
            spot_type=SpotType.MILITARY,
            aircraft_size=aircraft_size
        )
        
        if not military_spots:
            logger.info("No military spots available for transfer")
            return False
        
        # Get all active civil allocations
        active_allocations = await self.allocation_repo.get_active_allocations()
        
        # Filter for civil spots only
        civil_allocations = [
            alloc for alloc in active_allocations
            if not alloc.overflow_to_military
        ]
        
        if not civil_allocations:
            logger.info("No civil allocations to transfer")
            return False
        
        # Find flight with latest predicted end time (departs last)
        latest_allocation = max(
            civil_allocations,
            key=lambda x: x.predicted_end_time
        )
        
        # Get the flight details
        late_flight = await self.flight_repo.get_by_icao24(latest_allocation.flight_icao24)
        if not late_flight:
            logger.warning(f"Could not find flight {latest_allocation.flight_icao24}")
            return False
        
        # Get the current civil spot
        current_spot = await self.spot_repo.get_by_id(latest_allocation.spot_id)
        if not current_spot:
            logger.warning(f"Could not find spot {latest_allocation.spot_id}")
            return False
        
        logger.info(
            f"Transferring flight {late_flight.icao24} from civil spot {current_spot.spot_id} "
            f"to military (departs at {latest_allocation.predicted_end_time})"
        )
        
        # Complete current allocation
        now = datetime.utcnow()
        duration = int((now - latest_allocation.allocated_at).total_seconds() / 60)
        await self.allocation_repo.complete_allocation(
            allocation_id=latest_allocation.allocation_id,
            actual_start_time=latest_allocation.allocated_at,
            actual_end_time=now,
            actual_duration_minutes=duration
        )
        
        # Free civil spot
        await self.spot_repo.update_status(current_spot.spot_id, SpotStatus.AVAILABLE)
        
        # Allocate to military spot
        military_spot = military_spots[0]
        remaining_minutes = int((latest_allocation.predicted_end_time - now).total_seconds() / 60)
        
        new_allocation = await self.allocation_repo.create(
            flight_icao24=late_flight.icao24,
            spot_id=military_spot.spot_id,
            predicted_duration_minutes=remaining_minutes,
            predicted_end_time=latest_allocation.predicted_end_time,
            overflow_to_military=True,
            overflow_reason="Transferred to free civil spot for earlier departure"
        )
        
        # Update military spot status
        await self.spot_repo.update_status(military_spot.spot_id, SpotStatus.OCCUPIED)
        
        # Update flight parking assignment
        await self.flight_repo.update_parking_assignment(late_flight.icao24, military_spot.spot_id)
        
        # Create transfer notification
        await self.notification_service.create_overflow_notification(
            flight=late_flight,
            reason=f"Transferred from {current_spot.spot_id} to prioritize earlier departures",
            military_spot=military_spot
        )
        
        logger.info(
            f"Successfully transferred flight {late_flight.icao24} to military spot {military_spot.spot_id}, "
            f"freed civil spot {current_spot.spot_id}"
        )
        
        return True
    
    async def recall_from_military(
        self,
        flight: Flight,
        civil_spot: ParkingSpot
    ) -> bool:
        """
        Recall flight from military to civil parking when spot becomes available.
        
        Args:
            flight: Flight object
            civil_spot: Available civil spot
        
        Returns:
            True if recall successful
        """
        logger.info(f"Recalling flight {flight.icao24} from military to civil spot {civil_spot.spot_id}")
        
        # Get current allocation
        current_allocation = await self.allocation_repo.get_by_flight(flight.icao24)
        if not current_allocation or not current_allocation.overflow_to_military:
            logger.warning(f"Flight {flight.icao24} not in military overflow")
            return False
        
        # Complete old allocation
        now = datetime.now(timezone.utc)
        duration = int((now - current_allocation.allocated_at).total_seconds() / 60)
        await self.allocation_repo.complete_allocation(
            allocation_id=current_allocation.allocation_id,
            actual_start_time=current_allocation.allocated_at,
            actual_end_time=now,
            actual_duration_minutes=duration
        )
        
        # Free military spot
        await self.spot_repo.update_status(current_allocation.spot_id, SpotStatus.AVAILABLE)
        
        # Create new civil allocation
        predicted_end_time = now + timedelta(minutes=current_allocation.predicted_duration_minutes)
        new_allocation = await self.allocation_repo.create(
            flight_icao24=flight.icao24,
            spot_id=civil_spot.spot_id,
            predicted_duration_minutes=current_allocation.predicted_duration_minutes,
            predicted_end_time=predicted_end_time,
            overflow_to_military=False
        )
        
        # Update spot status
        await self.spot_repo.update_status(civil_spot.spot_id, SpotStatus.OCCUPIED)
        
        # Update flight parking assignment
        await self.flight_repo.update_parking_assignment(flight.icao24, civil_spot.spot_id)
        
        # Create recall notification
        await self.notification_service.create_recall_notification(flight, civil_spot)
        
        logger.info(f"Successfully recalled flight {flight.icao24} to civil spot {civil_spot.spot_id}")
        return True
    
    def _get_aircraft_size(self, aircraft_type: str) -> AircraftSizeCategory:
        """
        Determine aircraft size category from type.
        
        Args:
            aircraft_type: Aircraft type code (e.g., A320, B737, B777)
        
        Returns:
            Size category enum
        """
        large_aircraft = ['B747', 'B777', 'B787', 'A330', 'A340', 'A350', 'A380']
        small_aircraft = ['ATR', 'DHC', 'CRJ', 'E190', 'E170']
        
        aircraft_upper = aircraft_type.upper()
        
        if any(large in aircraft_upper for large in large_aircraft):
            return AircraftSizeCategory.LARGE
        elif any(small in aircraft_upper for small in small_aircraft):
            return AircraftSizeCategory.SMALL
        else:
            return AircraftSizeCategory.MEDIUM
    
    async def check_saturation(self) -> dict:
        """Check parking saturation and create alerts if needed"""
        stats = await self.allocation_repo.get_availability_stats()
        
        if stats["occupation_rate"] > 85:
            await self.notification_service.create_saturation_alert(
                occupation_rate=stats["occupation_rate"],
                available_spots=stats["civil_available"]
            )
        
        return stats
