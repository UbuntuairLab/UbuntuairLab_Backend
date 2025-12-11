import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.services.orchestration.flight_orchestrator import FlightOrchestrator
from app.services.business.parking_service import ParkingService
from app.repositories.parking_repository import ParkingAllocationRepository
from app.repositories.parking_repository import ParkingSpotRepository
from app.database import AsyncSessionLocal

logger = logging.getLogger(__name__)
settings = get_settings()


class FlightSyncScheduler:
    """
    Manages scheduled flight synchronization using APScheduler.
    Runs background job at configurable intervals.
    Creates DB session for each orchestrator call.
    """
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.orchestrator = None  # Created dynamically with DB session
        self.interval_minutes = settings.SYNC_INTERVAL_MINUTES
        self._job = None
        self._recall_job = None
        self._is_running = False
    
    async def start(self):
        """Start the scheduler with configured interval"""
        if self._is_running:
            logger.warning("Scheduler already running")
            return
        
        # Add scheduled job (orchestrator created dynamically with DB session)
        self._job = self.scheduler.add_job(
            self._sync_job,
            trigger=IntervalTrigger(minutes=self.interval_minutes),
            id="flight_sync_job",
            name="Flight Synchronization",
            replace_existing=True,
            max_instances=1,  # Prevent overlapping executions
            misfire_grace_time=300  # 5 minutes grace period
        )
        
        # Add recall job (every 2 minutes)
        self._recall_job = self.scheduler.add_job(
            self._civil_recall_job,
            trigger=IntervalTrigger(minutes=2),
            id="civil_recall_job",
            name="Civil Parking Recall",
            replace_existing=True,
            max_instances=1,
            misfire_grace_time=120
        )
        
        self.scheduler.start()
        self._is_running = True
        
        logger.info(
            f"Flight sync scheduler started with {self.interval_minutes}min interval"
        )
        logger.info("Civil recall scheduler started with 2min interval")
    
    async def stop(self):
        """Stop the scheduler"""
        if not self._is_running:
            logger.warning("Scheduler not running")
            return
        
        self.scheduler.shutdown(wait=True)
        self._is_running = False
        logger.info("Flight sync scheduler stopped")
    
    async def _sync_job(self):
        """Internal job method called by scheduler - creates DB session per execution"""
        async with AsyncSessionLocal() as db:
            try:
                logger.info("Executing scheduled flight synchronization")
                orchestrator = FlightOrchestrator(db)
                await orchestrator.initialize()
                stats = await orchestrator.sync_flights()
                logger.info("Scheduled sync completed", extra=stats)
            except Exception as e:
                logger.error(f"Error in scheduled sync job: {str(e)}", exc_info=True)
            finally:
                await db.close()
    
    async def _civil_recall_job(self):
        """
        Internal job method called by scheduler every 2 minutes.
        Automatically recalls flights from military parking to civil when space available.
        """
        async with AsyncSessionLocal() as db:
            try:
                logger.info("Executing civil recall check")
                
                parking_service = ParkingService(db)
                allocation_repo = ParkingAllocationRepository(db)
                spot_repo = ParkingSpotRepository(db)
                
                # Get active military overflows
                from app.models.parking import ParkingAllocation, SpotType
                from sqlalchemy import and_, select
                
                result = await db.execute(
                    select(ParkingAllocation).where(
                        and_(
                            ParkingAllocation.overflow_to_military == True,
                            ParkingAllocation.actual_end_time.is_(None)
                        )
                    )
                )
                overflow_allocations = result.scalars().all()
                
                recalled_count = 0
                for allocation in overflow_allocations:
                    # Get flight
                    from app.models.flight import Flight
                    flight_result = await db.execute(
                        select(Flight).where(Flight.icao24 == allocation.icao24)
                    )
                    flight = flight_result.scalar_one_or_none()
                    
                    if not flight:
                        continue
                    
                    # Check for available civil spot matching aircraft size
                    aircraft_size = parking_service._get_aircraft_size(
                        flight.aircraft_type or "A320"
                    )
                    
                    available_civil = await spot_repo.find_available_civil_spots(
                        aircraft_size=aircraft_size,
                        limit=1
                    )
                    
                    if available_civil:
                        civil_spot = available_civil[0]
                        logger.info(
                            f"Recalling flight {flight.callsign} from military to civil spot {civil_spot.spot_id}"
                        )
                        
                        try:
                            await parking_service.recall_from_military(flight, civil_spot)
                            recalled_count += 1
                        except Exception as e:
                            logger.error(
                                f"Failed to recall flight {flight.callsign}: {str(e)}"
                            )
                
                if recalled_count > 0:
                    logger.info(f"Civil recall completed: {recalled_count} flights recalled")
                else:
                    logger.debug("Civil recall check: No recalls performed")
                    
            except Exception as e:
                logger.error(f"Error in civil recall job: {str(e)}", exc_info=True)
            finally:
                await db.close()
    
    async def trigger_manual_sync(self) -> dict:
        """
        Manually trigger a sync outside the schedule - creates DB session.
        Useful for API endpoints or admin actions.
        
        Returns:
            Sync statistics dictionary
        """
        logger.info("Manual flight synchronization triggered")
        
        async with AsyncSessionLocal() as db:
            try:
                orchestrator = FlightOrchestrator(db)
                await orchestrator.initialize()
                stats = await orchestrator.sync_flights()
                return {
                    "status": "success",
                    "triggered_at": datetime.utcnow().isoformat(),
                    **stats
                }
            except Exception as e:
                logger.error(f"Error in manual sync: {str(e)}", exc_info=True)
                return {
                    "status": "error",
                    "error": str(e),
                    "triggered_at": datetime.utcnow().isoformat()
                }
            finally:
                await db.close()
    
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
