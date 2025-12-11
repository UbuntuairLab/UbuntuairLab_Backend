import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
from app.core.config import get_settings
from app.services.orchestration.flight_orchestrator import FlightOrchestrator

logger = logging.getLogger(__name__)
settings = get_settings()


class FlightSyncScheduler:
    """
    Manages scheduled flight synchronization using APScheduler.
    Runs background job at configurable intervals.
    """
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.orchestrator = FlightOrchestrator()
        self.interval_minutes = settings.SYNC_INTERVAL_MINUTES
        self._job = None
        self._is_running = False
    
    async def start(self):
        """Start the scheduler with configured interval"""
        if self._is_running:
            logger.warning("Scheduler already running")
            return
        
        # Initialize orchestrator
        await self.orchestrator.initialize()
        
        # Add scheduled job
        self._job = self.scheduler.add_job(
            self._sync_job,
            trigger=IntervalTrigger(minutes=self.interval_minutes),
            id="flight_sync_job",
            name="Flight Synchronization",
            replace_existing=True,
            max_instances=1,  # Prevent overlapping executions
            misfire_grace_time=300  # 5 minutes grace period
        )
        
        self.scheduler.start()
        self._is_running = True
        
        logger.info(
            f"Flight sync scheduler started with {self.interval_minutes}min interval"
        )
    
    async def stop(self):
        """Stop the scheduler gracefully"""
        if not self._is_running:
            return
        
        self.scheduler.shutdown(wait=True)
        await self.orchestrator.shutdown()
        self._is_running = False
        
        logger.info("Flight sync scheduler stopped")
    
    async def _sync_job(self):
        """Internal job method called by scheduler"""
        try:
            logger.info("Executing scheduled flight synchronization")
            stats = await self.orchestrator.sync_flights()
            logger.info("Scheduled sync completed", extra=stats)
        except Exception as e:
            logger.error(f"Error in scheduled sync job: {str(e)}")
    
    async def trigger_manual_sync(self) -> dict:
        """
        Manually trigger a sync outside the schedule.
        Useful for API endpoints or admin actions.
        
        Returns:
            Sync statistics dictionary
        """
        logger.info("Manual flight synchronization triggered")
        
        try:
            stats = await self.orchestrator.sync_flights()
            return {
                "status": "success",
                "triggered_at": datetime.utcnow().isoformat(),
                **stats
            }
        except Exception as e:
            logger.error(f"Error in manual sync: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "triggered_at": datetime.utcnow().isoformat()
            }
    
    def get_next_run_time(self) -> str:
        """
        Get the next scheduled run time.
        
        Returns:
            ISO datetime string of next run, or None if not scheduled
        """
        if self._job:
            next_run = self._job.next_run_time
            return next_run.isoformat() if next_run else None
        return None
    
    def update_interval(self, new_interval_minutes: int):
        """
        Update the sync interval dynamically.
        
        Args:
            new_interval_minutes: New interval in minutes
        """
        if not self._is_running:
            self.interval_minutes = new_interval_minutes
            return
        
        # Reschedule job with new interval
        self.scheduler.reschedule_job(
            "flight_sync_job",
            trigger=IntervalTrigger(minutes=new_interval_minutes)
        )
        
        self.interval_minutes = new_interval_minutes
        
        logger.info(f"Sync interval updated to {new_interval_minutes} minutes")
    
    def get_status(self) -> dict:
        """
        Get scheduler status information.
        
        Returns:
            Status dictionary
        """
        return {
            "running": self._is_running,
            "interval_minutes": self.interval_minutes,
            "next_run": self.get_next_run_time(),
            "job_id": self._job.id if self._job else None
        }
