import logging
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.services.external.opensky_client import OpenSkyClient
from app.services.external.aviationstack_client import AviationStackClient
from app.services.ml.prediction_service import MLPredictionService
from app.services.business.parking_service import ParkingService
from app.services.converters.aviationstack_converter import AviationStackConverter
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
        self.aviationstack_client = AviationStackClient()
        self.ml_service = MLPredictionService(db)
        self.parking_service = ParkingService(db)
        self.flight_repo = FlightRepository(db)
        self.airport_icao = settings.AIRPORT_ICAO
        self.lookback_hours = settings.SYNC_LOOKBACK_HOURS
        
        # Track last AviationStack usage (rate limit: 1 req/60s, but use 12h cooldown to be conservative)
        self._last_aviationstack_call: Optional[datetime] = None
        self._aviationstack_cooldown_seconds = 43200  # 12 hours = 43200 seconds
    
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
        Falls back to AviationStack if OpenSky is rate-limited.
        This is called by the scheduler at regular intervals.
        
        Returns:
            Summary dictionary with processing statistics
        """
        logger.info("Starting flight synchronization")
        
        begin, end = self._get_time_window()
        flights = []
        source = "OpenSky"
        
        try:
            # Try OpenSky first
            async with self.opensky_client:
                response = await self.opensky_client.get_arrivals_and_departures(
                    airport_icao=self.airport_icao,
                    begin=begin,
                    end=end,
                    exclude_military=True  # Filter military aircraft
                )
            
            flights = response.flights
            logger.info(
                f"Retrieved {len(flights)} civilian flights from OpenSky for {self.airport_icao}",
                extra={"begin": begin, "end": end}
            )
            
        except OpenSkyAPIException as e:
            # OpenSky failed - try AviationStack fallback
            logger.warning(f"OpenSky API error: {str(e)} - Attempting AviationStack fallback")
            
            if self._can_use_aviationstack():
                try:
                    flights = await self._fetch_from_aviationstack()
                    source = "AviationStack"
                    logger.info(
                        f"Retrieved {len(flights)} flights from AviationStack fallback"
                    )
                except Exception as av_error:
                    logger.error(f"AviationStack fallback also failed: {str(av_error)}")
                    return {
                        "timestamp": datetime.utcnow().isoformat(),
                        "error": f"OpenSky: {str(e)}, AviationStack: {str(av_error)}",
                        "total_flights": 0,
                        "successful": 0,
                        "failed": 0,
                        "source": "none"
                    }
            else:
                logger.error("Cannot use AviationStack fallback - rate limit cooldown active")
                return {
                    "timestamp": datetime.utcnow().isoformat(),
                    "error": str(e),
                    "total_flights": 0,
                    "successful": 0,
                    "failed": 0,
                    "source": "OpenSky (failed)"
                }
        
        # Process flights if we got any
        if flights:
            results = await self._process_flights_batch(flights)
            
            # Compile statistics
            stats = {
                "timestamp": datetime.utcnow().isoformat(),
                "source": source,
                "total_flights": len(flights),
                "successful": results["successful"],
                "failed": results["failed"],
                "errors": results["errors"]
            }
            
            logger.info(f"Flight synchronization completed from {source}", extra=stats)
            return stats
        else:
            logger.warning("No flights retrieved from any source")
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "source": source,
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
    
    def _can_use_aviationstack(self) -> bool:
        """
        Check if AviationStack API can be used (respects rate limit).
        
        Returns:
            True if enough time has passed since last call (12h cooldown)
        """
        if self._last_aviationstack_call is None:
            return True
        
        elapsed = (datetime.utcnow() - self._last_aviationstack_call).total_seconds()
        can_use = elapsed >= self._aviationstack_cooldown_seconds
        
        if not can_use:
            remaining_hours = (self._aviationstack_cooldown_seconds - elapsed) / 3600
            logger.warning(
                f"AviationStack rate limit cooldown: {remaining_hours:.1f}h remaining (12h policy)"
            )
        
        return can_use
    
    async def _fetch_from_aviationstack(self) -> List[FlightData]:
        """
        Fetch today's flights from AviationStack API and convert to FlightData format.
        Uses timetable endpoint for current day arrivals and departures.
        
        Returns:
            List of FlightData objects converted from AviationStack
        
        Raises:
            Exception: If AviationStack API call fails
        """
        logger.info("Fetching flights from AviationStack (fallback mode)")
        
        # Mark usage time BEFORE call to prevent concurrent calls
        self._last_aviationstack_call = datetime.utcnow()
        
        try:
            async with self.aviationstack_client:
                # Fetch arrivals for today
                arrivals = await self.aviationstack_client.get_timetable(
                    airport_iata=settings.AIRPORT_IATA,  # LFW
                    timetable_type="arrival"
                )
                
                # Convert to FlightData format
                flight_data_list = AviationStackConverter.batch_convert(
                    av_flights=arrivals.data if hasattr(arrivals, 'data') else [],
                    flight_type="arrival"
                )
                
                logger.info(
                    f"AviationStack: Retrieved {len(flight_data_list)} arrivals"
                )
                
                return flight_data_list
                
        except Exception as e:
            logger.error(f"AviationStack fetch failed: {str(e)}")
            # Reset timer on failure to allow retry sooner
            self._last_aviationstack_call = None
            raise
    
    async def sync_realtime_positions(self) -> dict:
        """
        Fetch real-time state vectors from OpenSky for aircraft near DXXX (Lomé).
        Updates position, velocity, altitude, and heading for active flights.
        
        Uses bounding box of ~60km radius around airport to capture:
        - Approaching aircraft (within 60km final approach)
        - Departing aircraft (within 60km after takeoff)
        - Aircraft in holding patterns
        
        Returns:
            dict: Summary of sync operation (updated_count, total_states, errors)
        """
        from app.utils.geo_calculator import get_bounding_box, AIRPORT_COORDS
        
        logger.info("🛰️ Starting real-time position sync from OpenSky state vectors")
        
        try:
            # Get bounding box for 60km radius around DXXX (Lomé)
            # AIRPORT_COORDS = (6.165611, 1.254797)
            lat_min, lat_max, lon_min, lon_max = get_bounding_box(
                center_lat=AIRPORT_COORDS[0],
                center_lon=AIRPORT_COORDS[1],
                radius_km=60.0
            )
            
            logger.info(
                f"Fetching state vectors in area: "
                f"lat({lat_min:.4f} to {lat_max:.4f}), "
                f"lon({lon_min:.4f} to {lon_max:.4f})"
            )
            
            # Fetch raw state vectors from OpenSky
            raw_states = await self.opensky_client.get_states_in_area(
                lamin=lat_min,
                lamax=lat_max,
                lomin=lon_min,
                lomax=lon_max
            )
            
            if not raw_states:
                logger.info("No aircraft detected in area")
                return {
                    "success": True,
                    "updated_count": 0,
                    "total_states": 0,
                    "errors": 0
                }
            
            # Parse raw state vectors into structured data
            state_vectors = self.opensky_client.parse_state_vectors(raw_states)
            
            logger.info(f"Parsed {len(state_vectors)} state vectors")
            
            # Update positions for known flights only (filter by active status)
            updated_count = 0
            error_count = 0
            
            for state_vector in state_vectors:
                try:
                    # Only update if flight exists in our DB (active tracking)
                    flight = await self.flight_repo.update_realtime_position(
                        icao24=state_vector.icao24,
                        state_vector=state_vector
                    )
                    
                    if flight:
                        updated_count += 1
                        logger.debug(
                            f"✅ Updated position for {state_vector.icao24} "
                            f"({state_vector.callsign}) - "
                            f"Pos: ({state_vector.latitude:.4f}, {state_vector.longitude:.4f}), "
                            f"Alt: {state_vector.baro_altitude}m, "
                            f"Speed: {state_vector.velocity}m/s"
                        )
                    
                except Exception as e:
                    error_count += 1
                    logger.warning(
                        f"Failed to update position for {state_vector.icao24}: {str(e)}"
                    )
            
            # Summary
            logger.info(
                f"✅ Real-time position sync completed: "
                f"{updated_count} flights updated, "
                f"{len(state_vectors)} total states, "
                f"{error_count} errors"
            )
            
            return {
                "success": True,
                "updated_count": updated_count,
                "total_states": len(state_vectors),
                "errors": error_count,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Real-time position sync failed: {str(e)}", exc_info=True)
            return {
                "success": False,
                "updated_count": 0,
                "total_states": 0,
                "errors": 1,
                "error_message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
