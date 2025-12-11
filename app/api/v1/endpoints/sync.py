"""
Synchronization endpoints.
Manage flight synchronization with OpenSky Network.
"""
from fastapi import APIRouter, Depends, HTTPException
from app.api.v1.endpoints.auth import get_current_active_user
from app.models.user import User

router = APIRouter()


# Global scheduler instance will be injected during startup
_scheduler = None

def set_scheduler(scheduler):
    """Called by main.py during startup to inject scheduler instance"""
    global _scheduler
    _scheduler = scheduler


@router.post("/trigger")
async def trigger_manual_sync(
    current_user: User = Depends(get_current_active_user)
):
    """
    Manually trigger flight synchronization.
    Admin only - requires authentication.
    """
    # Check admin role
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if not _scheduler:
        raise HTTPException(status_code=503, detail="Scheduler not initialized")
    
    result = await _scheduler.trigger_manual_sync()
    
    return result


@router.get("/status")
async def get_sync_status(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get synchronization scheduler status.
    Requires authentication.
    """
    if not _scheduler:
        return {
            "scheduler_running": False,
            "next_run": None
        }
    
    return _scheduler.get_status()


@router.patch("/interval/{minutes}")
async def update_sync_interval(
    minutes: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    Update synchronization interval.
    Admin only - requires authentication.
    """
    # Check admin role
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if minutes < 1 or minutes > 60:
        raise HTTPException(
            status_code=400,
            detail="Interval must be between 1 and 60 minutes"
        )
    
    if not _scheduler:
        raise HTTPException(status_code=503, detail="Scheduler not initialized")
    
    _scheduler.update_interval(minutes)
    
    return {
        "message": "Sync interval updated",
        "new_interval_minutes": minutes,
        "next_run": _scheduler.get_next_run_time()
    }
