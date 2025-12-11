"""
Notification endpoints.
Manage system notifications and alerts.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.repositories.notification_repository import NotificationRepository
from app.models.notification import NotificationType, NotificationSeverity
from app.api.v1.endpoints.auth import get_current_active_user
from app.models.user import User

router = APIRouter()


@router.get("/notifications")
async def list_notifications(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    read_status: Optional[bool] = Query(None, description="Filter by read status"),
    notification_type: Optional[str] = Query(None, description="Filter by type"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    List notifications with optional filters.
    Requires authentication.
    """
    notification_repo = NotificationRepository(db)
    
    # Convert string enums
    type_filter = NotificationType(notification_type) if notification_type else None
    severity_filter = NotificationSeverity(severity) if severity else None
    
    notifications, total = await notification_repo.list_notifications(
        skip=skip,
        limit=limit,
        read_status=read_status,
        notification_type=type_filter,
        severity=severity_filter
    )
    
    return {
        "items": [
            {
                "notification_id": str(n.notification_id),
                "flight_icao24": n.flight_icao24,
                "notification_type": n.notification_type.value,
                "severity": n.severity.value,
                "message": n.message,
                "read_status": n.read_status,
                "created_at": n.created_at,
                "acknowledged_at": n.acknowledged_at
            }
            for n in notifications
        ],
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.post("/notifications/{notification_id}/acknowledge")
async def acknowledge_notification(
    notification_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Mark notification as read/acknowledged.
    Requires authentication.
    """
    notification_repo = NotificationRepository(db)
    
    notification = await notification_repo.acknowledge(notification_id)
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    return {
        "success": True,
        "notification_id": str(notification.notification_id),
        "read_status": notification.read_status,
        "acknowledged_at": notification.acknowledged_at
    }


@router.get("/notifications/unread/count")
async def get_unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get count of unread notifications.
    Requires authentication.
    """
    notification_repo = NotificationRepository(db)
    
    count = await notification_repo.get_unread_count()
    
    return {
        "unread_count": count
    }


@router.get("/notifications/critical")
async def get_critical_notifications(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get critical unread notifications.
    Requires authentication.
    """
    notification_repo = NotificationRepository(db)
    
    notifications = await notification_repo.get_critical_unread()
    
    return [
        {
            "notification_id": str(n.notification_id),
            "flight_icao24": n.flight_icao24,
            "notification_type": n.notification_type.value,
            "message": n.message,
            "created_at": n.created_at
        }
        for n in notifications
    ]
