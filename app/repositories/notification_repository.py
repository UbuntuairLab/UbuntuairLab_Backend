from typing import Optional, List
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from app.models.notification import Notification, NotificationType, NotificationSeverity


class NotificationRepository:
    """Repository for Notification model operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(
        self,
        flight_icao24: str,
        notification_type: NotificationType,
        message: str,
        severity: NotificationSeverity = NotificationSeverity.INFO
    ) -> Notification:
        """Create new notification"""
        notification = Notification(
            flight_icao24=flight_icao24,
            notification_type=notification_type,
            message=message,
            severity=severity
        )
        self.db.add(notification)
        await self.db.commit()
        await self.db.refresh(notification)
        return notification
    
    async def get_by_id(self, notification_id: str) -> Optional[Notification]:
        """Get notification by ID"""
        result = await self.db.execute(
            select(Notification).where(Notification.notification_id == notification_id)
        )
        return result.scalar_one_or_none()
    
    async def list_notifications(
        self,
        skip: int = 0,
        limit: int = 50,
        read_status: Optional[bool] = None,
        notification_type: Optional[NotificationType] = None,
        severity: Optional[NotificationSeverity] = None
    ) -> tuple[List[Notification], int]:
        """List notifications with filters and pagination"""
        query = select(Notification)
        count_query = select(func.count()).select_from(Notification)
        
        # Apply filters
        filters = []
        if read_status is not None:
            filters.append(Notification.read_status == read_status)
        if notification_type:
            filters.append(Notification.notification_type == notification_type)
        if severity:
            filters.append(Notification.severity == severity)
        
        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))
        
        # Get total count
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        
        # Apply pagination and ordering
        query = query.order_by(Notification.created_at.desc()).offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        notifications = list(result.scalars().all())
        
        return notifications, total
    
    async def get_unread_count(self) -> int:
        """Get count of unread notifications"""
        result = await self.db.execute(
            select(func.count()).select_from(Notification).where(Notification.read_status == False)
        )
        return result.scalar() or 0
    
    async def acknowledge(self, notification_id: str) -> Optional[Notification]:
        """Mark notification as read"""
        notification = await self.get_by_id(notification_id)
        if not notification:
            return None
        
        notification.read_status = True
        notification.acknowledged_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(notification)
        return notification
    
    async def get_by_flight(self, flight_icao24: str) -> List[Notification]:
        """Get all notifications for a flight"""
        result = await self.db.execute(
            select(Notification)
            .where(Notification.flight_icao24 == flight_icao24)
            .order_by(Notification.created_at.desc())
        )
        return list(result.scalars().all())
    
    async def get_critical_unread(self) -> List[Notification]:
        """Get critical unread notifications"""
        result = await self.db.execute(
            select(Notification)
            .where(
                and_(
                    Notification.read_status == False,
                    Notification.severity == NotificationSeverity.CRITICAL
                )
            )
            .order_by(Notification.created_at.desc())
        )
        return list(result.scalars().all())
