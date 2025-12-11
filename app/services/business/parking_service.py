import logging
from typing import Optional, List
from enum import Enum

logger = logging.getLogger(__name__)


class SpotType(str, Enum):
    """Parking spot type"""
    CIVIL = "civil"
    MILITARY = "military"


class SpotStatus(str, Enum):
    """Parking spot availability status"""
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    RESERVED = "reserved"
    MAINTENANCE = "maintenance"


class ParkingAllocationResult:
    """Result of parking allocation attempt"""
    
    def __init__(
        self,
        success: bool,
        spot_id: Optional[str] = None,
        spot_type: Optional[SpotType] = None,
        overflow_to_military: bool = False,
        reason: Optional[str] = None
    ):
        self.success = success
        self.spot_id = spot_id
        self.spot_type = spot_type
        self.overflow_to_military = overflow_to_military
        self.reason = reason


class ParkingService:
    """
    Business logic for parking spot allocation and conflict management.
    Implements rules for civil/military overflow and conflict resolution.
    """
    
    def __init__(self):
        # This will be replaced with database queries once DB layer is implemented
        self._mock_civil_spots = []
        self._mock_military_spots = []
    
    def find_available_civil_spots(
        self,
        aircraft_size: str,
        requires_jetway: bool = True
    ) -> List[dict]:
        """
        Find available civil parking spots matching requirements.
        
        Args:
            aircraft_size: Aircraft size category (small/medium/large)
            requires_jetway: Whether aircraft needs jetway access
        
        Returns:
            List of available spot dictionaries
        
        Note:
            This is a placeholder. Will be replaced with database queries.
        """
        # TODO: Implement with database repository
        logger.debug(
            f"Searching civil spots for {aircraft_size} aircraft, jetway={requires_jetway}"
        )
        return []
    
    def find_available_military_spots(
        self,
        aircraft_size: str
    ) -> List[dict]:
        """
        Find available military parking spots for overflow.
        
        Args:
            aircraft_size: Aircraft size category
        
        Returns:
            List of available military spot dictionaries
        
        Note:
            This is a placeholder. Will be replaced with database queries.
        """
        # TODO: Implement with database repository
        logger.debug(f"Searching military spots for {aircraft_size} aircraft")
        return []
    
    def allocate_spot(
        self,
        flight_id: str,
        aircraft_type: str,
        requires_jetway: bool,
        predicted_duration: int,
        conflict_detected: bool
    ) -> ParkingAllocationResult:
        """
        Main allocation logic: find optimal spot or overflow to military.
        
        Args:
            flight_id: Unique flight identifier (ICAO24)
            aircraft_type: Aircraft type (e.g., A320, B737)
            requires_jetway: Whether jetway is needed
            predicted_duration: Expected occupation duration in minutes
            conflict_detected: Whether AI detected a conflict
        
        Returns:
            ParkingAllocationResult with allocation decision
        """
        logger.info(
            f"Allocating parking for flight {flight_id}",
            extra={
                "aircraft_type": aircraft_type,
                "jetway": requires_jetway,
                "duration": predicted_duration,
                "conflict": conflict_detected
            }
        )
        
        # Determine aircraft size category
        aircraft_size = self._get_aircraft_size(aircraft_type)
        
        # Step 1: Try to find civil spot
        civil_spots = self.find_available_civil_spots(
            aircraft_size,
            requires_jetway
        )
        
        if civil_spots and not conflict_detected:
            # Found available civil spot
            best_spot = self._select_optimal_spot(civil_spots, requires_jetway)
            
            logger.info(
                f"Allocated civil spot {best_spot['id']} for flight {flight_id}"
            )
            
            return ParkingAllocationResult(
                success=True,
                spot_id=best_spot['id'],
                spot_type=SpotType.CIVIL,
                overflow_to_military=False,
                reason="Civil spot available"
            )
        
        # Step 2: Check if overflow to military is necessary
        if conflict_detected or not civil_spots:
            logger.warning(
                f"No civil spots available for flight {flight_id}, checking military overflow"
            )
            
            military_spots = self.find_available_military_spots(aircraft_size)
            
            if military_spots:
                best_spot = self._select_optimal_spot(military_spots, False)
                
                logger.info(
                    f"Allocated military spot {best_spot['id']} for flight {flight_id} (overflow)"
                )
                
                return ParkingAllocationResult(
                    success=True,
                    spot_id=best_spot['id'],
                    spot_type=SpotType.MILITARY,
                    overflow_to_military=True,
                    reason="Civil saturation - military overflow"
                )
        
        # Step 3: No spots available
        logger.error(f"No parking available for flight {flight_id}")
        
        return ParkingAllocationResult(
            success=False,
            reason="No parking spots available (civil and military saturated)"
        )
    
    def _get_aircraft_size(self, aircraft_type: str) -> str:
        """
        Determine aircraft size category from type.
        
        Args:
            aircraft_type: Aircraft type code (e.g., A320, B737, B777)
        
        Returns:
            Size category: small, medium, or large
        """
        # Simplified categorization
        large_aircraft = ['B747', 'B777', 'B787', 'A330', 'A340', 'A350', 'A380']
        small_aircraft = ['ATR', 'DHC', 'CRJ', 'E190', 'E170']
        
        aircraft_upper = aircraft_type.upper()
        
        if any(large in aircraft_upper for large in large_aircraft):
            return "large"
        elif any(small in aircraft_upper for small in small_aircraft):
            return "small"
        else:
            return "medium"
    
    def _select_optimal_spot(
        self,
        available_spots: List[dict],
        requires_jetway: bool
    ) -> dict:
        """
        Select the optimal spot from available options.
        
        Args:
            available_spots: List of available spots
            requires_jetway: Whether jetway is required
        
        Returns:
            Best spot dictionary
        """
        if not available_spots:
            return None
        
        # Prioritize spots with jetway if required
        if requires_jetway:
            jetway_spots = [s for s in available_spots if s.get('has_jetway', False)]
            if jetway_spots:
                available_spots = jetway_spots
        
        # Sort by distance to terminal (closest first)
        sorted_spots = sorted(
            available_spots,
            key=lambda s: s.get('distance_to_terminal', 9999)
        )
        
        return sorted_spots[0]
    
    def check_conflicts(
        self,
        spot_id: str,
        incoming_eta: str,
        predicted_duration: int
    ) -> bool:
        """
        Check if incoming flight conflicts with current spot occupation.
        
        Args:
            spot_id: Parking spot identifier
            incoming_eta: ETA of incoming flight (ISO datetime)
            predicted_duration: Duration needed in minutes
        
        Returns:
            True if conflict detected, False otherwise
        
        Note:
            This is a placeholder. Will be replaced with database queries.
        """
        # TODO: Implement with database repository
        # Query current allocation for spot
        # Check if incoming_eta falls within current occupation + buffer
        logger.debug(f"Checking conflicts for spot {spot_id}")
        return False
    
    def handle_overflow(
        self,
        flight_id: str,
        from_spot_type: SpotType,
        to_spot_type: SpotType
    ) -> bool:
        """
        Handle overflow movement between civil and military parking.
        
        Args:
            flight_id: Flight identifier
            from_spot_type: Current spot type
            to_spot_type: Target spot type
        
        Returns:
            True if overflow handled successfully
        
        Note:
            This is a placeholder. Will be replaced with database operations.
        """
        logger.info(
            f"Handling overflow for flight {flight_id}: {from_spot_type} -> {to_spot_type}"
        )
        
        # TODO: Implement with database repository
        # Update allocation record
        # Log overflow event
        # Send notification if configured
        
        return True
