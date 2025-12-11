import random
from app.services.ai_models.base import BaseAIModel
from app.schemas.ai_models import OccupationInput, OccupationOutput
from app.services.cache.prediction_cache import PredictionCache
from app.core.config import get_settings

settings = get_settings()


class OccupationModel(BaseAIModel[OccupationInput, OccupationOutput]):
    """
    AI model client for parking occupation duration predictions.
    Predicts how long an aircraft will occupy a parking spot.
    """
    
    def __init__(self, cache: PredictionCache):
        super().__init__(
            model_name="occupation",
            endpoint_url=settings.MODEL_OCCUPATION_ENDPOINT,
            cache=cache
        )
    
    async def _predict_real(self, input_data: OccupationInput) -> OccupationOutput:
        """
        Call real occupation duration prediction endpoint.
        
        Args:
            input_data: Aircraft and operation parameters
        
        Returns:
            Predicted occupation duration with confidence interval
        """
        if not self._http_client:
            raise RuntimeError("HTTP client not initialized")
        
        response = await self._http_client.post(
            self.endpoint_url,
            json=input_data.model_dump(mode='json')
        )
        response.raise_for_status()
        
        data = response.json()
        return OccupationOutput(**data)
    
    def _predict_mock(self, input_data: OccupationInput) -> OccupationOutput:
        """
        Generate mock occupation duration prediction.
        Simulates realistic duration based on operations and aircraft type.
        
        Args:
            input_data: Aircraft and operation parameters
        
        Returns:
            Mock prediction with duration and confidence interval
        """
        # Base duration from historical average
        base_duration = input_data.historique_occupation_type
        
        # Adjust based on operations
        operation_time = 0
        
        if input_data.carburant == 1:
            operation_time += random.randint(10, 20)
        
        if input_data.catering == 1:
            operation_time += random.randint(15, 25)
        
        if input_data.maintenance == 1:
            operation_time += random.randint(20, 40)
        
        # Passenger count factor
        if input_data.passagers > 200:
            operation_time += random.randint(10, 15)
        elif input_data.passagers > 150:
            operation_time += random.randint(5, 10)
        
        # Delay impact
        if input_data.retard > 30:
            operation_time += random.randint(5, 15)
        
        # Weather impact
        if input_data.pluie == 1:
            operation_time += random.randint(5, 10)
        if input_data.temperature_extreme == 1:
            operation_time += random.randint(3, 8)
        
        # Congestion impact
        if input_data.taux_occupation > 80:
            operation_time -= random.randint(5, 10)  # Rush to free spot
        
        # Provenance impact
        if input_data.provenance == "long":
            operation_time += random.randint(10, 20)
        elif input_data.provenance == "medium":
            operation_time += random.randint(5, 10)
        
        # Calculate total duration
        total_duration = int(base_duration + operation_time)
        total_duration = max(20, total_duration)  # Minimum 20 minutes
        
        # Calculate confidence interval (±15%)
        confidence_margin = int(total_duration * 0.15)
        lower_bound = total_duration - confidence_margin
        upper_bound = total_duration + confidence_margin
        
        return OccupationOutput(
            occupation_minutes=total_duration,
            intervalle_confiance=f"{lower_bound} - {upper_bound}"
        )
    
    def _get_output_class(self) -> type[OccupationOutput]:
        """Return output class for deserialization"""
        return OccupationOutput
