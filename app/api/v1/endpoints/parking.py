"""
Parking endpoints.
Manage parking spots and allocations.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database import get_db
from app.repositories.parking_repository import ParkingSpotRepository, ParkingAllocationRepository
from app.repositories.flight_repository import FlightRepository
from app.services.business.parking_service import ParkingService
from app.schemas.parking import (
    ParkingSpotResponse,
    ParkingAllocationResponse,
    ParkingSpotUpdate,
    ParkingSpotCreate
)
from app.api.v1.endpoints.auth import get_current_active_user
from app.models.user import User
from app.models.parking import SpotType, SpotStatus, AircraftSizeCategory

router = APIRouter()


class AssignParkingRequest(BaseModel):
    icao24: str
    manual_override: bool = False


class MilitaryTransferRequest(BaseModel):
    icao24: str
    reason: str


class CivilRecallRequest(BaseModel):
    icao24: str


@router.get("/spots", response_model=List[ParkingSpotResponse])
async def list_parking_spots(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    spot_type: Optional[str] = Query(None, description="Filter by type (civil/military)"),
    status: Optional[str] = Query(None, description="Filter by status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    List all parking spots with optional filters.
    Requires authentication.
    """
    parking_repo = ParkingSpotRepository(db)
    
    spots, total = await parking_repo.list_spots(
        skip=skip,
        limit=limit,
        spot_type=spot_type,
        status=status
    )
    
    return spots


@router.get("/spots/{spot_id}", response_model=ParkingSpotResponse)
async def get_parking_spot(
    spot_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get parking spot details.
    Requires authentication.
    """
    parking_repo = ParkingSpotRepository(db)
    spot = await parking_repo.get_by_id(spot_id)
    
    if not spot:
        raise HTTPException(status_code=404, detail="Parking spot not found")
    
    return spot


@router.patch("/spots/{spot_id}", response_model=ParkingSpotResponse)
async def update_parking_spot(
    spot_id: str,
    update_data: ParkingSpotUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update parking spot configuration.
    Admin only - requires authentication.
    """
    # Check admin role
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    parking_repo = ParkingSpotRepository(db)
    
    # Update status if provided
    if update_data.status:
        spot = await parking_repo.update_status(spot_id, update_data.status)
    else:
        spot = await parking_repo.get_by_id(spot_id)
    
    if not spot:
        raise HTTPException(status_code=404, detail="Parking spot not found")
    
    # Update notes if provided (requires additional update method)
    # For now, just return the spot
    
    return spot


@router.post("/spots", response_model=ParkingSpotResponse, status_code=201)
async def create_parking_spot(
    spot_data: ParkingSpotCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new parking spot.
    Admin only - requires authentication.
    """
    # Check admin role
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    parking_repo = ParkingSpotRepository(db)
    
    # Check if spot_id already exists
    existing = await parking_repo.get_by_id(spot_data.spot_id)
    if existing:
        raise HTTPException(status_code=400, detail=f"Spot {spot_data.spot_id} already exists")
    
    # Create new spot
    from app.models.parking import ParkingSpot
    new_spot = ParkingSpot(
        spot_id=spot_data.spot_id,
        spot_number=spot_data.spot_number,
        spot_type=SpotType(spot_data.spot_type),
        status=SpotStatus(spot_data.status) if spot_data.status else SpotStatus.AVAILABLE,
        aircraft_size_capacity=AircraftSizeCategory(spot_data.aircraft_size_capacity),
        has_jetway=spot_data.has_jetway,
        distance_to_terminal=spot_data.distance_to_terminal,
        admin_configurable=spot_data.admin_configurable if spot_data.admin_configurable is not None else True,
        notes=spot_data.notes
    )
    
    db.add(new_spot)
    await db.commit()
    await db.refresh(new_spot)
    
    return new_spot


@router.delete("/spots/{spot_id}", status_code=204)
async def delete_parking_spot(
    spot_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete a parking spot.
    Admin only - requires authentication.
    Cannot delete if spot has active allocations.
    """
    # Check admin role
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    parking_repo = ParkingSpotRepository(db)
    allocation_repo = ParkingAllocationRepository(db)
    
    # Check if spot exists
    spot = await parking_repo.get_by_id(spot_id)
    if not spot:
        raise HTTPException(status_code=404, detail="Parking spot not found")
    
    # Check for active allocations
    from sqlalchemy import select
    from app.models.parking import ParkingAllocation
    result = await db.execute(
        select(ParkingAllocation).where(
            ParkingAllocation.spot_id == spot_id,
            ParkingAllocation.actual_end_time.is_(None)
        ).limit(1)
    )
    active_allocation = result.scalar_one_or_none()
    
    if active_allocation:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete spot {spot_id} - has active allocation (flight {active_allocation.flight_icao24})"
        )
    
    # Delete spot
    await db.delete(spot)
    await db.commit()
    
    return None


@router.get("/allocations", response_model=List[ParkingAllocationResponse])
async def list_allocations(
    active_only: bool = Query(True, description="Show only active allocations"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    List parking allocations.
    Requires authentication.
    """
    parking_repo = ParkingAllocationRepository(db)
    
    allocations, total = await parking_repo.list_allocations(active_only=active_only)
    
    return allocations


@router.get("/allocations/{allocation_id}", response_model=ParkingAllocationResponse)
async def get_allocation(
    allocation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get allocation details.
    Requires authentication.
    """
    parking_repo = ParkingAllocationRepository(db)
    allocation = await parking_repo.get_allocation(allocation_id)
    
    if not allocation:
        raise HTTPException(status_code=404, detail="Allocation not found")
    
    return allocation


@router.get("/availability")
async def get_parking_availability(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current parking availability statistics.
    Requires authentication.
    """
    parking_repo = ParkingAllocationRepository(db)
    
    stats = await parking_repo.get_availability_stats()
    
    return stats


@router.post("/assign")
async def assign_parking(
    request: AssignParkingRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Manually trigger parking allocation for a flight.
    Requires authentication.
    """
    flight_repo = FlightRepository(db)
    parking_service = ParkingService(db)
    
    # Get flight
    flight = await flight_repo.get_by_icao24(request.icao24)
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")
    
    # Allocate parking
    result = await parking_service.allocate_spot(
        flight=flight,
        predicted_occupation_minutes=flight.predicted_occupation_minutes or 60,
        conflict_data=None
    )
    
    if not result.success:
        raise HTTPException(status_code=400, detail=result.reason)
    
    return {
        "success": True,
        "spot_id": result.spot.spot_id,
        "spot_type": result.spot.spot_type.value,
        "overflow_to_military": result.overflow_to_military,
        "reason": result.reason
    }


@router.post("/military-transfer")
async def military_transfer(
    request: MilitaryTransferRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Manually transfer flight to military parking (ADMIN ONLY).
    This is used when civil saturation occurs and admin decides to override.
    Only transfers flights that are ALREADY allocated to civil spots.
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    flight_repo = FlightRepository(db)
    parking_service = ParkingService(db)
    spot_repo = ParkingSpotRepository(db)
    allocation_repo = ParkingAllocationRepository(db)
    
    # Get flight
    flight = await flight_repo.get_by_icao24(request.icao24)
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")
    
    # Check if flight already has an allocation
    existing_allocation = await allocation_repo.get_by_flight(request.icao24)
    
    if existing_allocation:
        # Flight already allocated - transfer it
        if existing_allocation.overflow_to_military:
            raise HTTPException(status_code=400, detail="Flight already in military parking")
        
        # Get current civil spot
        current_spot = await spot_repo.get_by_id(existing_allocation.spot_id)
        if not current_spot:
            raise HTTPException(status_code=404, detail="Current spot not found")
        
        # Get available military spot
        military_spots = await spot_repo.get_available_by_type(
            spot_type=SpotType.MILITARY,
            aircraft_size=parking_service._get_aircraft_size("A320")
        )
        
        if not military_spots:
            raise HTTPException(status_code=400, detail="No military spots available")
        
        # Complete old allocation
        from datetime import datetime, timedelta, timezone
        now = datetime.now(timezone.utc)
        duration = int((now - existing_allocation.allocated_at).total_seconds() / 60)
        
        await allocation_repo.complete_allocation(
            allocation_id=existing_allocation.allocation_id,
            actual_start_time=existing_allocation.allocated_at,
            actual_end_time=now,
            actual_duration_minutes=duration
        )
        
        # Free civil spot
        await spot_repo.update_status(current_spot.spot_id, SpotStatus.AVAILABLE)
        
        # Create new military allocation
        remaining_minutes = int((existing_allocation.predicted_end_time - now).total_seconds() / 60)
        new_allocation = await allocation_repo.create(
            flight_icao24=flight.icao24,
            spot_id=military_spots[0].spot_id,
            predicted_duration_minutes=max(remaining_minutes, 10),
            predicted_end_time=existing_allocation.predicted_end_time,
            overflow_to_military=True,
            overflow_reason=f"Admin manual transfer: {request.reason}"
        )
        
        # Update military spot status
        await spot_repo.update_status(military_spots[0].spot_id, SpotStatus.OCCUPIED)
        
        # Update flight parking assignment
        await flight_repo.update_parking_assignment(flight.icao24, military_spots[0].spot_id)
        
        return {
            "success": True,
            "allocation_id": new_allocation.allocation_id,
            "spot_id": military_spots[0].spot_id,
            "previous_spot": current_spot.spot_id,
            "reason": request.reason,
            "freed_civil_spot": True
        }
    else:
        # New flight without allocation - create military allocation directly
        military_spots = await spot_repo.get_available_by_type(
            spot_type=SpotType.MILITARY,
            aircraft_size=parking_service._get_aircraft_size("A320")
        )
        
        if not military_spots:
            raise HTTPException(status_code=400, detail="No military spots available")
        
        from datetime import timezone
        predicted_minutes = flight.predicted_occupation_minutes or 60
        
        allocation = await allocation_repo.create(
            flight_icao24=flight.icao24,
            spot_id=military_spots[0].spot_id,
            predicted_duration_minutes=predicted_minutes,
            predicted_end_time=datetime.now(timezone.utc) + timedelta(minutes=predicted_minutes),
            overflow_to_military=True,
            overflow_reason=f"Admin decision: {request.reason}"
        )
        
        await spot_repo.update_status(military_spots[0].spot_id, SpotStatus.OCCUPIED)
        await flight_repo.update_parking_assignment(flight.icao24, military_spots[0].spot_id)
        
        return {
            "success": True,
            "allocation_id": allocation.allocation_id,
            "spot_id": military_spots[0].spot_id,
            "reason": request.reason,
            "freed_civil_spot": False
        }


@router.post("/civil-recall")
async def civil_recall(
    request: CivilRecallRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Recall flight from military to civil parking.
    Requires authentication.
    """
    flight_repo = FlightRepository(db)
    parking_service = ParkingService(db)
    spot_repo = ParkingSpotRepository(db)
    
    # Get flight
    flight = await flight_repo.get_by_icao24(request.icao24)
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")
    
    # Get available civil spot
    civil_spots = await spot_repo.get_available_by_type(
        spot_type=SpotType.CIVIL,
        aircraft_size=parking_service._get_aircraft_size("A320")
    )
    
    if not civil_spots:
        raise HTTPException(status_code=400, detail="No civil spots available for recall")
    
    # Execute recall
    success = await parking_service.recall_from_military(flight, civil_spots[0])
    
    if not success:
        raise HTTPException(status_code=400, detail="Recall failed - flight not in military overflow")
    
    return {
        "success": True,
        "new_spot_id": civil_spots[0].spot_id,
        "message": f"Flight recalled to civil spot {civil_spots[0].spot_id}"
    }


@router.get("/conflicts")
async def list_conflicts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    List all detected parking conflicts.
    Requires authentication.
    """
    from sqlalchemy.orm import joinedload
    from sqlalchemy import select
    from app.models.parking import ParkingAllocation
    
    allocation_repo = ParkingAllocationRepository(db)
    
    # Get allocations with conflicts
    result = await db.execute(
        select(ParkingAllocation)
        .options(
            joinedload(ParkingAllocation.spot)
        )
        .where(ParkingAllocation.conflict_detected == True)
        .order_by(ParkingAllocation.allocated_at.desc())
    )
    allocations = list(result.scalars().all())
    
    return [
        {
            "allocation_id": alloc.allocation_id,
            "flight_icao24": alloc.flight_icao24,
            "callsign": None,  # Flight relationship not available
            "spot_id": alloc.spot_id,
            "conflict_probability": alloc.conflict_probability,
            "allocated_at": alloc.allocated_at,
            "predicted_end_time": alloc.predicted_end_time,
            "overflow_to_military": alloc.overflow_to_military
        }
        for alloc in allocations
    ]

