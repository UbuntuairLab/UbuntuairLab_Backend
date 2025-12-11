from typing import Optional, List
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from app.models.parking import (
    ParkingSpot, ParkingAllocation, 
    SpotType, SpotStatus, AircraftSizeCategory
)


class ParkingSpotRepository:
    """Repository for ParkingSpot model operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(
        self,
        spot_id: str,
        spot_number: int,
        spot_type: SpotType,
        aircraft_size_capacity: AircraftSizeCategory,
        has_jetway: bool = False,
        distance_to_terminal: int = 100
    ) -> ParkingSpot:
        """Create new parking spot"""
        spot = ParkingSpot(
            spot_id=spot_id,
            spot_number=spot_number,
            spot_type=spot_type,
            aircraft_size_capacity=aircraft_size_capacity,
            has_jetway=has_jetway,
            distance_to_terminal=distance_to_terminal
        )
        self.db.add(spot)
        await self.db.commit()
        await self.db.refresh(spot)
        return spot
    
    async def get_by_id(self, spot_id: str) -> Optional[ParkingSpot]:
        """Get parking spot by ID"""
        result = await self.db.execute(
            select(ParkingSpot).where(ParkingSpot.spot_id == spot_id)
        )
        return result.scalar_one_or_none()
    
    async def get_all(self) -> List[ParkingSpot]:
        """Get all parking spots"""
        result = await self.db.execute(select(ParkingSpot))
        return list(result.scalars().all())
    
    async def list_spots(
        self,
        skip: int = 0,
        limit: int = 50,
        spot_type: Optional[str] = None,
        status: Optional[str] = None
    ) -> tuple[List[ParkingSpot], int]:
        """List parking spots with pagination - CIVIL ONLY"""
        from sqlalchemy import func, cast, String
        
        # Base query - CIVIL only, cast to string to avoid enum comparison
        query = select(ParkingSpot).where(cast(ParkingSpot.spot_type, String) == "civil")
        
        # Apply additional filters with cast to string
        if status:
            query = query.where(cast(ParkingSpot.status, String) == status.lower())
        
        # Get total count
        count_query = select(func.count()).select_from(ParkingSpot)
        count_query = count_query.where(cast(ParkingSpot.spot_type, String) == "civil")
        if status:
            count_query = count_query.where(cast(ParkingSpot.status, String) == status.lower())
        
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        
        # Apply pagination
        query = query.offset(skip).limit(limit).order_by(ParkingSpot.spot_number.asc())
        
        result = await self.db.execute(query)
        spots = list(result.scalars().all())
        
        return spots, total
    
    async def get_available_by_type(
        self,
        spot_type: SpotType,
        aircraft_size: AircraftSizeCategory
    ) -> List[ParkingSpot]:
        """
        Get available parking spots by type and compatible with aircraft size.
        Returns spots ordered by: jetway availability DESC, terminal distance ASC
        """
        result = await self.db.execute(
            select(ParkingSpot)
            .where(
                and_(
                    ParkingSpot.spot_type == spot_type,
                    ParkingSpot.status == SpotStatus.AVAILABLE,
                    ParkingSpot.aircraft_size_capacity >= aircraft_size
                )
            )
            .order_by(
                ParkingSpot.has_jetway.desc(),
                ParkingSpot.distance_to_terminal.asc()
            )
        )
        return list(result.scalars().all())
    
    async def update_status(self, spot_id: str, status: SpotStatus) -> Optional[ParkingSpot]:
        """Update parking spot status"""
        spot = await self.get_by_id(spot_id)
        if not spot:
            return None
        
        spot.status = status
        await self.db.commit()
        await self.db.refresh(spot)
        return spot
    
    async def get_by_type(self, spot_type: SpotType) -> List[ParkingSpot]:
        """Get all parking spots of specific type"""
        result = await self.db.execute(
            select(ParkingSpot).where(ParkingSpot.spot_type == spot_type)
        )
        return list(result.scalars().all())
    
    async def count_available(self, spot_type: Optional[SpotType] = None) -> int:
        """Count available parking spots"""
        query = select(ParkingSpot).where(ParkingSpot.status == SpotStatus.AVAILABLE)
        
        if spot_type:
            query = query.where(ParkingSpot.spot_type == spot_type)
        
        result = await self.db.execute(query)
        return len(list(result.scalars().all()))
    
    async def update(
        self,
        spot_id: str,
        status: Optional[SpotStatus] = None,
        has_jetway: Optional[bool] = None,
        distance_to_terminal: Optional[int] = None,
        notes: Optional[str] = None
    ) -> Optional[ParkingSpot]:
        """Update parking spot details"""
        spot = await self.get_by_id(spot_id)
        if not spot:
            return None
        
        if status:
            spot.status = status
        if has_jetway is not None:
            spot.has_jetway = has_jetway
        if distance_to_terminal is not None:
            spot.distance_to_terminal = distance_to_terminal
        if notes is not None:
            spot.notes = notes
        
        await self.db.commit()
        await self.db.refresh(spot)
        return spot
    
    async def delete(self, spot_id: str) -> bool:
        """Delete parking spot"""
        spot = await self.get_by_id(spot_id)
        if not spot:
            return False
        
        await self.db.delete(spot)
        await self.db.commit()
        return True


class ParkingAllocationRepository:
    """Repository for ParkingAllocation model operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(
        self,
        flight_icao24: str,
        spot_id: str,
        predicted_duration_minutes: int,
        predicted_end_time: datetime,
        overflow_to_military: bool = False,
        overflow_reason: Optional[str] = None,
        conflict_detected: bool = False,
        conflict_probability: Optional[float] = None
    ) -> ParkingAllocation:
        """Create new parking allocation"""
        allocation = ParkingAllocation(
            flight_icao24=flight_icao24,
            spot_id=spot_id,
            predicted_duration_minutes=predicted_duration_minutes,
            predicted_end_time=predicted_end_time,
            overflow_to_military=overflow_to_military,
            overflow_reason=overflow_reason,
            conflict_detected=conflict_detected,
            conflict_probability=conflict_probability
        )
        self.db.add(allocation)
        await self.db.commit()
        await self.db.refresh(allocation)
        return allocation
    
    async def get_by_id(self, allocation_id: int) -> Optional[ParkingAllocation]:
        """Get allocation by ID"""
        result = await self.db.execute(
            select(ParkingAllocation).where(ParkingAllocation.allocation_id == allocation_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_flight(self, flight_icao24: str) -> Optional[ParkingAllocation]:
        """Get active allocation for flight"""
        result = await self.db.execute(
            select(ParkingAllocation)
            .where(
                and_(
                    ParkingAllocation.flight_icao24 == flight_icao24,
                    ParkingAllocation.actual_end_time.is_(None)
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def get_by_spot(self, spot_id: str, active_only: bool = True) -> List[ParkingAllocation]:
        """Get allocations for specific spot"""
        query = select(ParkingAllocation).where(ParkingAllocation.spot_id == spot_id)
        
        if active_only:
            query = query.where(ParkingAllocation.actual_end_time.is_(None))
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_active_allocations(self) -> List[ParkingAllocation]:
        """Get all active allocations"""
        result = await self.db.execute(
            select(ParkingAllocation).where(ParkingAllocation.actual_end_time.is_(None))
        )
        return list(result.scalars().all())
    
    async def complete_allocation(
        self,
        allocation_id: int,
        actual_start_time: datetime,
        actual_end_time: datetime,
        actual_duration_minutes: int
    ) -> Optional[ParkingAllocation]:
        """Mark allocation as complete with actual times"""
        allocation = await self.get_by_id(allocation_id)
        if not allocation:
            return None
        
        allocation.actual_start_time = actual_start_time
        allocation.actual_end_time = actual_end_time
        allocation.actual_duration_minutes = actual_duration_minutes
        
        await self.db.commit()
        await self.db.refresh(allocation)
        return allocation
    
    async def get_conflicting_allocations(
        self,
        spot_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[ParkingAllocation]:
        """Find allocations that conflict with time window"""
        result = await self.db.execute(
            select(ParkingAllocation)
            .where(
                and_(
                    ParkingAllocation.spot_id == spot_id,
                    ParkingAllocation.actual_end_time.is_(None),
                    ParkingAllocation.allocated_at < end_time,
                    ParkingAllocation.predicted_end_time > start_time
                )
            )
        )
        return list(result.scalars().all())
    
    async def get_overflow_allocations(self) -> List[ParkingAllocation]:
        """Get all allocations that used military overflow"""
        result = await self.db.execute(
            select(ParkingAllocation).where(ParkingAllocation.overflow_to_military == True)
        )
        return list(result.scalars().all())
    
    async def get_conflict_allocations(self) -> List[ParkingAllocation]:
        """Get all allocations with detected conflicts"""
        result = await self.db.execute(
            select(ParkingAllocation).where(ParkingAllocation.conflict_detected == True)
        )
        return list(result.scalars().all())
