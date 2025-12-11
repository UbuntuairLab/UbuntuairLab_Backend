from datetime import datetime, timedelta
import random
from app.services.ai_models.base import BaseAIModel
from app.schemas.ai_models import ETAETDInput, ETAETDOutput
from app.services.cache.prediction_cache import PredictionCache
from app.core.config import get_settings

settings = get_settings()


class ETAModel(BaseAIModel[ETAETDInput, ETAETDOutput]):
    """
    AI model client for ETA/ETD predictions.
    Predicts adjusted arrival/departure times based on flight data and weather.
    """
    
    def __init__(self, cache: PredictionCache):
        super().__init__(
            model_name="eta",
            endpoint_url=settings.MODEL_ETA_ENDPOINT,
            cache=cache
        )
    
    async def _predict_real(self, input_data: ETAETDInput) -> ETAETDOutput:
        """
        Call real ETA/ETD prediction endpoint.
        
        Args:
            input_data: Flight and weather parameters
        
        Returns:
            Adjusted ETA and delay prediction
        """
        if not self._http_client:
            raise RuntimeError("HTTP client not initialized")
        
        response = await self._http_client.post(
            self.endpoint_url,
            json=input_data.model_dump(mode='json')
        )
        response.raise_for_status()
        
        data = response.json()
        return ETAETDOutput(**data)
    
    def _predict_mock(self, input_data: ETAETDInput) -> ETAETDOutput:
        """
        Generate mock ETA/ETD prediction for testing.
        Simulates realistic delay based on weather and distance.
        
        Args:
            input_data: Flight and weather parameters
        
        Returns:
            Mock prediction with calculated delay
        """
        # Parse theoretical ETA
        eta_theo = datetime.fromisoformat(input_data.eta_theorique)
        
        # Calculate delay based on factors
        base_delay = 0
        
        # Weather factors
        if input_data.pluie == 1:
            base_delay += random.randint(5, 15)
        if input_data.orage == 1:
            base_delay += random.randint(10, 30)
        if input_data.vent > 30:
            base_delay += random.randint(5, 20)
        if input_data.visibilite < 5:
            base_delay += random.randint(10, 25)
        
        # Distance factor (longer flights more uncertainty)
        if input_data.distance > 500:
            base_delay += random.randint(0, 15)
        
        # Time of day factor (peak hours)
        if 7 <= input_data.heure_locale <= 9 or 17 <= input_data.heure_locale <= 19:
            base_delay += random.randint(5, 15)
        
        # Add some randomness
        delay_minutes = base_delay + random.randint(-5, 10)
        delay_minutes = max(0, delay_minutes)  # No negative delays in mock
        
        # Calculate adjusted ETA
        eta_adjusted = eta_theo + timedelta(minutes=delay_minutes)
        
        return ETAETDOutput(
            eta_adjusted=eta_adjusted.isoformat(),
            retard_minutes=delay_minutes
        )
    
    def _get_output_class(self) -> type[ETAETDOutput]:
        """Return output class for deserialization"""
        return ETAETDOutput
