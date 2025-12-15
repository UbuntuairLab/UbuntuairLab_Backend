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
        
        # Add departure monitoring job (every 3 minutes)
        self._departure_job = self.scheduler.add_job(
            self._departure_monitoring_job,
            trigger=IntervalTrigger(minutes=3),
            id="departure_monitoring_job",
            name="Departure Monitoring",
            replace_existing=True,
            max_instances=1,
            misfire_grace_time=180
        )
        
        self.scheduler.start()
        self._is_running = True
        
        logger.info(
            f"Flight sync scheduler started with {self.interval_minutes}min interval"
        )
        logger.info("Civil recall scheduler started with 2min interval")
        logger.info("Departure monitoring scheduler started with 3min interval")
    
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
                        select(Flight).where(Flight.icao24 == allocation.flight_icao24)
                    )
                    flight = flight_result.scalar_one_or_none()
                    
                    if not flight:
                        continue
                    
                    # Check for available civil spot matching aircraft size
                    aircraft_size = parking_service._get_aircraft_size(
                        flight.aircraft_type or "A320"
                    )
                    
                    from app.models.parking import SpotType
                    available_civil = await spot_repo.get_available_by_type(
                        spot_type=SpotType.CIVIL,
                        aircraft_size=aircraft_size
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
    
    async def _departure_monitoring_job(self):
        """
        Monitor for completed/departed flights and release their parking spots.
        Runs every 3 minutes.
        """
        async with AsyncSessionLocal() as db:
            try:
                logger.info("Executing departure monitoring check")
                
                from app.models.flight import Flight, FlightStatus
                from app.models.parking import ParkingAllocation, ParkingSpot, SpotStatus
                from app.repositories.parking_repository import ParkingAllocationRepository, ParkingSpotRepository
                from app.repositories.flight_repository import FlightRepository
                from app.services.notifications.notification_service import NotificationService
                from sqlalchemy import select, and_
                from datetime import datetime, timezone
                
                allocation_repo = ParkingAllocationRepository(db)
                spot_repo = ParkingSpotRepository(db)
                flight_repo = FlightRepository(db)
                notification_service = NotificationService(db)
                
                # Find active allocations with completed/departed flights
                result = await db.execute(
                    select(ParkingAllocation, Flight)
                    .join(Flight, Flight.icao24 == ParkingAllocation.flight_icao24)
                    .where(
                        and_(
                            ParkingAllocation.actual_end_time.is_(None),  # Still active
                            Flight.status == FlightStatus.COMPLETED  # Flight completed/departed
                        )
                    )
                )
                completed_allocations = result.all()
                
                released_count = 0
                for allocation, flight in completed_allocations:
                    try:
                        # Calculate actual duration
                        actual_start = allocation.allocated_at
                        actual_end = datetime.now(timezone.utc)
                        actual_duration = int((actual_end - actual_start).total_seconds() / 60)
                        
                        # Complete the allocation
                        await allocation_repo.complete_allocation(
                            allocation_id=allocation.allocation_id,
                            actual_start_time=actual_start,
                            actual_end_time=actual_end,
                            actual_duration_minutes=actual_duration
                        )
                        
                        # Release the parking spot
                        await spot_repo.update_status(allocation.spot_id, SpotStatus.AVAILABLE)
                        
                        # Clear flight parking assignment
                        await flight_repo.update_parking_assignment(flight.icao24, None)
                        
                        # Create notification
                        await notification_service.create_parking_freed(
                            flight_icao24=flight.icao24,
                            spot_id=allocation.spot_id
                        )
                        
                        logger.info(
                            f"Released parking spot {allocation.spot_id} for departed flight {flight.callsign} "
                            f"(duration: {actual_duration}min)"
                        )
                        released_count += 1
                        
                    except Exception as e:
                        logger.error(
                            f"Failed to release spot for flight {flight.icao24}: {str(e)}"
                        )
                
                if released_count > 0:
                    logger.info(f"Departure monitoring completed: {released_count} spots released")
                else:
                    logger.debug("Departure monitoring check: No spots to release")
                    
            except Exception as e:
                logger.error(f"Error in departure monitoring job: {str(e)}", exc_info=True)
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
