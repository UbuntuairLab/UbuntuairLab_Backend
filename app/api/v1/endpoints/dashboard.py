"""
Dashboard endpoints.
Provide real-time statistics and metrics.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime, timedelta

from app.database import get_db
from app.repositories.parking_repository import ParkingAllocationRepository
from app.repositories.flight_repository import FlightRepository
from app.repositories.notification_repository import NotificationRepository
from app.api.v1.endpoints.auth import get_current_active_user
from app.models.user import User
from app.models.flight import Flight, FlightStatus
from app.models.notification import NotificationSeverity

router = APIRouter()


@router.get("/stats")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get comprehensive dashboard statistics.
    Requires authentication.
    """
    parking_repo = ParkingAllocationRepository(db)
    flight_repo = FlightRepository(db)
    notification_repo = NotificationRepository(db)
    
    # Parking statistics
    parking_stats = await parking_repo.get_availability_stats()
    
    # Flight statistics
    # Flights approaching in next 30 minutes
    now = datetime.utcnow()
    thirty_min_ahead = now + timedelta(minutes=30)
    
    approaching_result = await db.execute(
        select(func.count()).select_from(Flight).where(
            and_(
                Flight.predicted_eta.between(now, thirty_min_ahead),
                Flight.status != "completed"
            )
        )
    )
    approaching_count = approaching_result.scalar() or 0
    
    # Flights departing in next 30 minutes
    departing_result = await db.execute(
        select(func.count()).select_from(Flight).where(
            and_(
                Flight.predicted_etd.between(now, thirty_min_ahead),
                Flight.status != "completed"
            )
        )
    )
    departing_count = departing_result.scalar() or 0
    
    # Total flights today
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_result = await db.execute(
        select(func.count()).select_from(Flight).where(
            Flight.created_at >= today_start
        )
    )
    today_count = today_result.scalar() or 0
    
    # Notification statistics
    unread_notifications = await notification_repo.get_unread_count()
    critical_notifications = len(await notification_repo.get_critical_unread())
    
    # Conflict statistics
    from app.models.parking import ParkingAllocation
    
    active_conflicts_result = await db.execute(
        select(func.count()).select_from(ParkingAllocation).where(
            and_(
                ParkingAllocation.conflict_detected == True,
                ParkingAllocation.actual_end_time.is_(None)
            )
        )
    )
    active_conflicts = active_conflicts_result.scalar() or 0
    
    resolved_conflicts_result = await db.execute(
        select(func.count()).select_from(ParkingAllocation).where(
            and_(
                ParkingAllocation.conflict_detected == True,
                ParkingAllocation.actual_end_time.isnot(None),
                ParkingAllocation.actual_end_time >= today_start
            )
        )
    )
    resolved_today = resolved_conflicts_result.scalar() or 0
    
    return {
        "parking": {
            "civil_occupied": parking_stats["civil_occupied"],
            "civil_total": parking_stats["civil_total"],
            "civil_available": parking_stats["civil_available"],
            "military_occupied": parking_stats["military_occupied"],
            "military_total": parking_stats["military_total"],
            "military_available": parking_stats["military_available"],
            "overflow_count": parking_stats["overflow_count"],
            "occupation_rate": parking_stats["occupation_rate"]
        },
        "flights": {
            "approaching_30min": approaching_count,
            "departing_30min": departing_count,
            "total_today": today_count
        },
        "conflicts": {
            "active_conflicts": active_conflicts,
            "resolved_today": resolved_today
        },
        "notifications": {
            "unread_count": unread_notifications,
            "critical_alerts": critical_notifications
        },
        "timestamp": now
    }
