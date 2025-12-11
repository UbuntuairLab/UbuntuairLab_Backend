import logging
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.services.external.opensky_client import OpenSkyClient
from app.services.ml.prediction_service import MLPredictionService
from app.services.business.parking_service import ParkingService
from app.repositories.flight_repository import FlightRepository
from app.schemas.opensky import FlightData, FlightType
from app.models.flight import FlightStatus, FlightType as FlightTypeEnum
from app.exceptions import OpenSkyAPIException

logger = logging.getLogger(__name__)
settings = get_settings()


class FlightOrchestrator:
    """
    Main orchestrator for flight processing pipeline.
    Coordinates OpenSky data retrieval, ML predictions via Hugging Face API, and database persistence.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.opensky_client = OpenSkyClient()
        self.ml_service = MLPredictionService(db)
        self.parking_service = ParkingService(db)
        self.flight_repo = FlightRepository(db)
        self.airport_icao = settings.AIRPORT_ICAO
        self.lookback_hours = settings.SYNC_LOOKBACK_HOURS
    
    async def initialize(self):
        """Initialize dependencies"""
        logger.info("FlightOrchestrator initialized with ML Hugging Face API integration")
    
    async def shutdown(self):
        """Cleanup resources"""
        logger.info("FlightOrchestrator shutdown")
    
    def _get_time_window(self) -> tuple[int, int]:
        """
        Calculate Unix timestamp window for flight queries.
        
        Returns:
            Tuple of (begin, end) Unix timestamps
        """
        end_time = datetime.utcnow()
        begin_time = end_time - timedelta(hours=self.lookback_hours)
        
        return int(begin_time.timestamp()), int(end_time.timestamp())
    
    async def sync_flights(self) -> dict:
        """
        Main synchronization method: fetch flights from OpenSky and process them.
        This is called by the scheduler at regular intervals.
        
        Returns:
            Summary dictionary with processing statistics
        """
        logger.info("Starting flight synchronization")
        
        begin, end = self._get_time_window()
        
        try:
            # Fetch arrivals and departures
            async with self.opensky_client:
                response = await self.opensky_client.get_arrivals_and_departures(
                    airport_icao=self.airport_icao,
                    begin=begin,
                    end=end,
                    exclude_military=True  # Filter military aircraft
                )
            
            flights = response.flights
            logger.info(
                f"Retrieved {len(flights)} civilian flights for {self.airport_icao}",
                extra={"begin": begin, "end": end}
            )
            
            # Process flights in batches
            results = await self._process_flights_batch(flights)
            
            # Compile statistics
            stats = {
                "timestamp": datetime.utcnow().isoformat(),
                "total_flights": len(flights),
                "successful": results["successful"],
                "failed": results["failed"],
                "errors": results["errors"]
            }
            
            logger.info("Flight synchronization completed", extra=stats)
            return stats
            
        except OpenSkyAPIException as e:
            logger.error(f"OpenSky API error during sync: {str(e)}")
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
                "total_flights": 0,
                "successful": 0,
                "failed": 0
            }
        except Exception as e:
            logger.error(f"Unexpected error during sync: {str(e)}")
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
                "total_flights": 0,
                "successful": 0,
                "failed": 0
            }
    
    async def _process_flights_batch(
        self,
        flights: List[FlightData],
        batch_size: int = 10
    ) -> dict:
        """
        Process multiple flights in parallel batches.
        
        Args:
            flights: List of flight data to process
            batch_size: Number of flights to process in parallel
        
        Returns:
            Dictionary with success/failure counts and errors
        """
        successful = 0
        failed = 0
        errors = []
        
        for i in range(0, len(flights), batch_size):
            batch = flights[i:i + batch_size]
            
            # Process batch in parallel
            results = await asyncio.gather(
                *[self.process_single_flight(flight) for flight in batch],
                return_exceptions=True
            )
            
            # Count successes and failures
            for result in results:
                if isinstance(result, Exception):
                    failed += 1
                    errors.append(str(result))
                elif result:
                    successful += 1
                else:
                    failed += 1
        
        return {
            "successful": successful,
            "failed": failed,
            "errors": errors[:10]  # Limit error list
        }
    
    async def process_single_flight(self, flight: FlightData) -> bool:
        """
        Process a single flight through complete pipeline.
        
        Pipeline:
        1. Determine flight type (arrival/departure)
        2. Persist/update flight in database (upsert)
        3. Call MLPredictionService for complete ML prediction (Hugging Face API)
        4. Database automatically updated by MLPredictionService
        
        Args:
            flight: Flight data from OpenSky Network
        
        Returns:
            True if processing succeeded, False otherwise
        """
        try:
            logger.debug(f"Processing flight {flight.icao24} ({flight.callsign})")
            
            # Step 1: Determine flight type
            flight_type = flight.get_flight_type(self.airport_icao)
            
            if flight_type is None:
                logger.warning(
                    f"Flight {flight.icao24} not relevant to {self.airport_icao}"
                )
                return False
            
            # Step 2: Upsert flight to database (create or update)
            db_flight = await self.flight_repo.upsert(flight)
            logger.info(
                f"Flight {db_flight.icao24} persisted to DB (type: {flight_type.value})"
            )
            
            # Step 3: Execute ML predictions via Hugging Face API
            # MLPredictionService handles:
            # - Calling ML API (https://tagba-ubuntuairlab.hf.space/predict)
            # - Storing predictions in ai_predictions table
            # - Updating flight record with predicted_eta, predicted_etd, predicted_delay_minutes, etc.
            prediction_result = await self.ml_service.predict_and_update_flight(
                flight=db_flight,
                force_refresh=False
            )
            
            # Step 4: Allocate parking spot
            # Use ML predictions for occupation time and conflict detection
            occupation_minutes = prediction_result.get("model_2_occupation", {}).get("temps_occupation_minutes", 60)
            conflict_data = prediction_result.get("model_3_conflict", {})
            
            parking_result = await self.parking_service.allocate_spot(
                flight=db_flight,
                predicted_occupation_minutes=int(occupation_minutes),
                conflict_data=conflict_data
            )
            
            if parking_result.success:
                logger.info(
                    f"Parking allocated: {parking_result.spot.spot_id} "
                    f"(overflow={parking_result.overflow_to_military})"
                )
            else:
                logger.error(
                    f"Parking allocation failed for {db_flight.icao24}: {parking_result.reason}"
                )
            
            # Step 5: Log success with key metrics
            logger.info(
                f"✅ Flight {db_flight.icao24} processed successfully",
                extra={
                    "callsign": db_flight.callsign,
                    "flight_type": flight_type.value,
                    "eta_minutes": prediction_result.get("model_1_eta", {}).get("eta_ajuste"),
                    "occupation_minutes": prediction_result.get("model_2_occupation", {}).get("temps_occupation_minutes"),
                    "decision": prediction_result.get("model_3_conflict", {}).get("decision_label")
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(
                f"❌ Error processing flight {flight.icao24}: {str(e)}",
                exc_info=True
            )
            return False
