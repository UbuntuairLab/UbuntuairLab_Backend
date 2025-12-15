"""
ML Prediction Service.
Orchestrates ML predictions and database updates for flights.
"""
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.external.ml_client import MLAPIClient
from app.repositories.flight_repository import FlightRepository
from app.repositories.prediction_repository import PredictionRepository
from app.repositories.turnaround_repository import TurnaroundRepository
from app.models.prediction import ModelType
from app.models.flight import Flight
from app.services.business.traffic_stats_service import get_traffic_statistics, get_weather_data, get_historical_data

logger = logging.getLogger(__name__)


class MLPredictionService:
    """
    Service for ML predictions integration.
    Calls Hugging Face ML API and updates database.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.flight_repo = FlightRepository(db)
        self.prediction_repo = PredictionRepository(db)
        self.turnaround_repo = TurnaroundRepository(db)
    
    async def predict_and_update_flight(
        self,
        flight: Flight,
        force_refresh: bool = False
    ) -> Dict:
        """
        Execute ML prediction for a flight and update database.
        
        Args:
            flight: Flight object to predict
            force_refresh: Force new prediction (bypass cache)
        
        Returns:
            Complete prediction result with all 3 models
        """
        logger.info(f"Starting ML prediction for flight {flight.icao24}")
        
        # Build input data for ML API
        flight_data = await self._build_ml_input(flight)
        
        # Call ML API
        async with MLAPIClient() as ml_client:
            start_time = datetime.now()
            prediction_result = await ml_client.predict(flight_data)
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        # Store predictions in database
        await self._store_predictions(
            flight.icao24,
            flight_data,
            prediction_result,
            execution_time
        )
        
        # Update flight record with predictions
        await self._update_flight_predictions(flight, prediction_result)
        
        logger.info(f"ML prediction completed for flight {flight.icao24}")
        
        return prediction_result
    
    async def _build_ml_input(self, flight: Flight) -> Dict:
        """
        Build ML API input from flight data.
        Uses REAL data from weather, traffic stats, historical, and real-time tracking.
        """
        from app.utils.geo_calculator import (
            calculate_distance_to_airport,
            meters_per_second_to_kmh
        )
        
        # Get REAL weather data
        weather = await get_weather_data()
        
        # Get REAL traffic statistics
        traffic = await get_traffic_statistics(self.db)
        
        # Get REAL historical data for this flight
        historical = await get_historical_data(self.db, flight)
        
        # Extract airline from callsign
        airline = historical.get("airline", "UNKNOWN")
        
        # REAL-TIME TRACKING DATA (from OpenSky state vectors)
        # Convert velocity from m/s to km/h for ML API
        velocity_kmh = meters_per_second_to_kmh(flight.velocity) if flight.velocity else 250.0
        
        # Use barometric altitude or default
        altitude_m = flight.baro_altitude if flight.baro_altitude else 3500.0
        
        # Calculate distance to runway if position available
        distance_km = calculate_distance_to_airport(flight.latitude, flight.longitude)
        if distance_km is None:
            distance_km = 20.0  # Fallback default
        
        # Build input with REAL DATA
        return {
            "callsign": flight.callsign or "",
            "icao24": flight.icao24,
            "vitesse_actuelle": velocity_kmh,  # Real-time velocity (km/h)
            "altitude": altitude_m,  # Real-time altitude (meters)
            "distance_piste": distance_km,  # Calculated distance (km)
            
            # REAL WEATHER DATA
            "temperature": weather.get("temperature", 20.0),
            "vent_vitesse": weather.get("wind_speed", 10.0),
            "vent_direction": weather.get("wind_direction", 180.0),
            "visibilite": weather.get("visibility", 10.0),
            "pluie": weather.get("rain", 0.0),
            "meteo_score": weather.get("score", 0.8),
            
            # REAL AIRLINE/HISTORICAL DATA
            "compagnie": airline,
            "retard_historique_compagnie": historical.get("avg_delay", 5.0),
            "type_avion": historical.get("aircraft_type", "A320"),
            "historique_occupation_avion": historical.get("avg_occupation_time", 45.0),
            "passagers_estimes": historical.get("passengers", 150),
            
            # REAL TRAFFIC DATA
            "trafic_approche": traffic.get("approaching", 0),
            "occupation_tarmac": traffic.get("tarmac_occupation", 0.0),
            "disponibilite_emplacements": traffic.get("available_spots", 17),
            "occupation_actuelle": traffic.get("current_occupation", 0.0),
            "trafic_entrant": traffic.get("incoming", 0),
            "trafic_sortant": traffic.get("outgoing", 0),
            "emplacements_futurs_libres": traffic.get("future_free_spots", 17),
            
            # Flight metadata
            "type_vol": 0 if flight.flight_type.value == "arrival" else 1,
            "priorite_vol": 0,  # Default priority (could be enhanced with business rules)
            "heure_jour": datetime.now().hour,
            "jour_semaine": datetime.now().weekday(),
            "periode_annee": datetime.now().month
        }
    
    def _extract_airline(self, callsign: str) -> str:
        """Extract airline code from callsign"""
        if not callsign:
            return "UNKNOWN"
        # First 2-3 letters are usually airline code
        return callsign[:3].upper() if len(callsign) >= 3 else callsign.upper()
    
    async def _store_predictions(
        self,
        icao24: str,
        input_data: Dict,
        prediction_result: Dict,
        execution_time_ms: int
    ):
        """Store all 3 model predictions in database"""
        
        # Model 1: ETA
        if "model_1_eta" in prediction_result:
            await self.prediction_repo.create(
                flight_icao24=icao24,
                model_type=ModelType.ETA,
                input_data=input_data,
                output_data=prediction_result["model_1_eta"],
                execution_time_ms=execution_time_ms,
                cached=False
            )
        
        # Model 2: Occupation
        if "model_2_occupation" in prediction_result:
            await self.prediction_repo.create(
                flight_icao24=icao24,
                model_type=ModelType.OCCUPATION,
                input_data=input_data,
                output_data=prediction_result["model_2_occupation"],
                execution_time_ms=execution_time_ms,
                cached=False
            )
        
        # Model 3: Conflict
        if "model_3_conflict" in prediction_result:
            await self.prediction_repo.create(
                flight_icao24=icao24,
                model_type=ModelType.CONFLIT,
                input_data=input_data,
                output_data=prediction_result["model_3_conflict"],
                execution_time_ms=execution_time_ms,
                cached=False
            )
    
    async def _update_flight_predictions(
        self,
        flight: Flight,
        prediction_result: Dict
    ):
        """Update flight record with ML predictions"""
        
        # Extract ETA prediction
        eta_data = prediction_result.get("model_1_eta", {})
        eta_minutes = eta_data.get("eta_ajuste", 0)
        delay_prob_15 = eta_data.get("proba_delay_15", 0)
        
        # Extract occupation prediction
        occupation_data = prediction_result.get("model_2_occupation", {})
        occupation_minutes = occupation_data.get("temps_occupation_minutes", None)
        
        # Calculate predicted times
        predicted_eta = None
        predicted_etd = None
        
        if eta_minutes > 0:
            predicted_eta = datetime.fromtimestamp(flight.last_seen) + timedelta(minutes=eta_minutes)
            
            # Calculate ETD based on flight type
            if flight.flight_type.value == "arrival":
                # For arrivals: ETD = ETA + occupation + turnaround
                aircraft_type = "A320"  # Default
                turnaround_rule = await self.turnaround_repo.get_by_aircraft_type(aircraft_type)
                turnaround_minutes = turnaround_rule.avg_turnaround_minutes if turnaround_rule else 60
                
                occupation = int(occupation_minutes) if occupation_minutes else 50
                predicted_etd = predicted_eta + timedelta(minutes=occupation + turnaround_minutes)
            else:
                # For departures: ETD = current time + delay
                delay_minutes = int(eta_minutes * 0.2) if delay_prob_15 > 0.5 else 0
                predicted_etd = datetime.fromtimestamp(flight.last_seen) + timedelta(minutes=delay_minutes)
        
        # Determine delay based on probability
        predicted_delay = None
        if delay_prob_15 > 0.5:
            predicted_delay = int(eta_minutes * 0.2)  # Estimate delay
        
        # Update flight
        await self.flight_repo.update_predictions(
            icao24=flight.icao24,
            predicted_eta=predicted_eta,
            predicted_etd=predicted_etd,
            predicted_delay_minutes=predicted_delay,
            predicted_occupation_minutes=int(occupation_minutes) if occupation_minutes else None
        )
    
    async def get_flight_predictions_summary(self, icao24: str) -> Dict:
        """Get summary of all predictions for a flight"""
        
        # Get latest prediction for each model
        eta_pred = await self.prediction_repo.get_latest_by_flight_and_model(
            icao24, ModelType.ETA
        )
        occupation_pred = await self.prediction_repo.get_latest_by_flight_and_model(
            icao24, ModelType.OCCUPATION
        )
        conflict_pred = await self.prediction_repo.get_latest_by_flight_and_model(
            icao24, ModelType.CONFLIT
        )
        
        return {
            "flight_icao24": icao24,
            "has_predictions": any([eta_pred, occupation_pred, conflict_pred]),
            "model_1_eta": eta_pred.output_data if eta_pred else None,
            "model_2_occupation": occupation_pred.output_data if occupation_pred else None,
            "model_3_conflict": conflict_pred.output_data if conflict_pred else None,
            "last_prediction_time": eta_pred.created_at if eta_pred else None
        }
