"""
Parking endpoints.
Manage parking spots and allocations.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.repositories.parking_repository import ParkingSpotRepository, ParkingAllocationRepository
from app.schemas.parking import (
    ParkingSpotResponse,
    ParkingAllocationResponse,
    ParkingSpotUpdate
)
from app.api.v1.endpoints.auth import get_current_active_user
from app.models.user import User

router = APIRouter()


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
    
    allocations = await parking_repo.list_allocations(active_only=active_only)
    
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
    parking_repo = ParkingSpotRepository(db)
    
    stats = await parking_repo.get_availability_stats()
    
    return stats
