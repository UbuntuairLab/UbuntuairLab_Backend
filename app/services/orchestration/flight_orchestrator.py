import logging
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional
from app.core.config import get_settings
from app.services.external.opensky_client import OpenSkyClient
from app.services.ai_models.factory import AIModelFactory
from app.schemas.opensky import FlightData, FlightType
from app.schemas.ai_models import (
    ETAETDInput, OccupationInput, ConflitInput
)
from app.exceptions import OpenSkyAPIException, AIModelException

logger = logging.getLogger(__name__)
settings = get_settings()


class FlightOrchestrator:
    """
    Main orchestrator for flight processing pipeline.
    Coordinates OpenSky data retrieval, AI predictions, and business logic.
    """
    
    def __init__(self):
        self.opensky_client = OpenSkyClient()
        self.ai_factory = AIModelFactory()
        self.airport_icao = settings.AIRPORT_ICAO
        self.lookback_hours = settings.SYNC_LOOKBACK_HOURS
    
    async def initialize(self):
        """Initialize dependencies"""
        await self.ai_factory.initialize()
        logger.info("FlightOrchestrator initialized")
    
    async def shutdown(self):
        """Cleanup resources"""
        await self.ai_factory.shutdown()
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
        Process a single flight through the complete AI pipeline.
        
        Steps:
        1. Determine flight type (arrival/departure)
        2. Call ETA/ETD prediction model
        3. Call occupation duration model
        4. Call conflict detection model
        5. Apply business logic (parking allocation)
        6. Persist results to database
        
        Args:
            flight: Flight data from OpenSky
        
        Returns:
            True if processing succeeded, False otherwise
        """
        try:
            logger.debug(f"Processing flight {flight.icao24}")
            
            # Determine flight type
            flight_type = flight.get_flight_type(self.airport_icao)
            
            if flight_type is None:
                logger.warning(
                    f"Flight {flight.icao24} not relevant to {self.airport_icao}"
                )
                return False
            
            # Step 1: Predict ETA/ETD
            eta_prediction = await self._predict_eta(flight, flight_type)
            
            # Step 2: Predict occupation duration
            occupation_prediction = await self._predict_occupation(
                flight,
                eta_prediction
            )
            
            # Step 3: Check for conflicts
            conflict_prediction = await self._predict_conflict(
                flight,
                eta_prediction,
                occupation_prediction
            )
            
            # Step 4: Apply business logic (will be implemented with DB layer)
            # TODO: Implement parking allocation logic
            # await self._allocate_parking(flight, predictions)
            
            logger.info(
                f"Successfully processed flight {flight.icao24}",
                extra={
                    "flight_type": flight_type.value,
                    "eta_delay": eta_prediction.retard_minutes,
                    "occupation": occupation_prediction.occupation_minutes,
                    "conflict": conflict_prediction.conflit
                }
            )
            
            return True
            
        except AIModelException as e:
            logger.error(
                f"AI model error processing flight {flight.icao24}: {str(e)}"
            )
            return False
        except Exception as e:
            logger.error(
                f"Error processing flight {flight.icao24}: {str(e)}"
            )
            return False
    
    async def _predict_eta(self, flight: FlightData, flight_type: FlightType):
        """
        Predict adjusted ETA/ETD for flight.
        
        Args:
            flight: Flight data
            flight_type: ARRIVAL or DEPARTURE
        
        Returns:
            ETAETDOutput with adjusted times
        """
        # Prepare input (mock data for now, will use real weather API later)
        eta_input = ETAETDInput(
            latitude=0.0,  # TODO: Get from flight tracking
            longitude=0.0,
            altitude=10000.0,
            vitesse=250.0,
            heading=90.0,
            vertical_rate=0.0,
            distance=100.0,
            eta_theorique=datetime.fromtimestamp(flight.last_seen).isoformat(),
            atd=datetime.fromtimestamp(flight.first_seen).isoformat(),
            type_avion="A320",  # TODO: Get from aircraft database
            compagnie=flight.callsign[:3] if flight.callsign else "UNKNOWN",
            vent=15.0,
            visibilite=10.0,
            pluie=0,
            orage=0,
            temperature=28.0,
            heure_locale=datetime.now().hour,
            jour_semaine=datetime.now().weekday()
        )
        
        eta_model = self.ai_factory.get_eta_model()
        async with eta_model:
            return await eta_model.predict(eta_input)
    
    async def _predict_occupation(self, flight: FlightData, eta_prediction):
        """
        Predict parking occupation duration.
        
        Args:
            flight: Flight data
            eta_prediction: ETA prediction result
        
        Returns:
            OccupationOutput with duration
        """
        occupation_input = OccupationInput(
            type_avion="A320",
            compagnie=flight.callsign[:3] if flight.callsign else "UNKNOWN",
            eta_adjusted=eta_prediction.eta_adjusted,
            retard=eta_prediction.retard_minutes,
            provenance="medium",
            passagers=150,
            operation="debarquement",
            carburant=1,
            catering=0,
            maintenance=0,
            passerelle=1,
            historique_occupation_type=45.0,
            pluie=0,
            vent=15.0,
            visibilite=10.0,
            temperature_extreme=0,
            arrivees_40min=2,
            departs_40min=2,
            taux_occupation=60.0,
            pistes_disponibles=1
        )
        
        occupation_model = self.ai_factory.get_occupation_model()
        async with occupation_model:
            return await occupation_model.predict(occupation_input)
    
    async def _predict_conflict(
        self,
        flight: FlightData,
        eta_prediction,
        occupation_prediction
    ):
        """
        Detect potential parking conflicts.
        
        Args:
            flight: Flight data
            eta_prediction: ETA prediction result
            occupation_prediction: Occupation prediction result
        
        Returns:
            ConflitOutput with conflict detection
        """
        conflit_input = ConflitInput(
            eta_adjusted=eta_prediction.eta_adjusted,
            type_avion_in="A320",
            compagnie_in=flight.callsign[:3] if flight.callsign else "UNKNOWN",
            besoin_passerelle=1,
            sensibilite_meteo=0,
            importance_vol="commercial",
            occupation_predite=occupation_prediction.occupation_minutes,
            temps_restant=30,
            retard_historique=10,
            type_avion_out="B737",
            operations_en_cours="none",
            taille_compatible=1,
            distance_terminal=200,
            reserve=0,
            maintenance=0,
            pluie=0,
            vent_fort=0,
            visibilite=10.0,
            approche_60min=3,
            depart_60min=2,
            saturation_piste=0,
            taux_occupation_global=60.0
        )
        
        conflit_model = self.ai_factory.get_conflit_model()
        async with conflit_model:
            return await conflit_model.predict(conflit_input)
