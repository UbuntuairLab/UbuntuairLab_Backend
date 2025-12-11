import random
from app.services.ai_models.base import BaseAIModel
from app.schemas.ai_models import ConflitInput, ConflitOutput
from app.services.cache.prediction_cache import PredictionCache
from app.core.config import get_settings

settings = get_settings()


class ConflitModel(BaseAIModel[ConflitInput, ConflitOutput]):
    """
    AI model client for parking conflict detection.
    Predicts conflicts between incoming and current aircraft on parking spots.
    """
    
    def __init__(self, cache: PredictionCache):
        super().__init__(
            model_name="conflit",
            endpoint_url=settings.MODEL_CONFLIT_ENDPOINT,
            cache=cache
        )
    
    async def _predict_real(self, input_data: ConflitInput) -> ConflitOutput:
        """
        Call real conflict detection endpoint.
        
        Args:
            input_data: Incoming and current aircraft parameters
        
        Returns:
            Conflict prediction with recommendation
        """
        if not self._http_client:
            raise RuntimeError("HTTP client not initialized")
        
        response = await self._http_client.post(
            self.endpoint_url,
            json=input_data.model_dump(mode='json')
        )
        response.raise_for_status()
        
        data = response.json()
        return ConflitOutput(**data)
    
    def _predict_mock(self, input_data: ConflitInput) -> ConflitOutput:
        """
        Generate mock conflict detection prediction.
        Simulates realistic conflict analysis based on timing and operations.
        
        Args:
            input_data: Incoming and current aircraft parameters
        
        Returns:
            Mock prediction with conflict flag, probability, and recommendation
        """
        # Calculate conflict probability
        conflict_score = 0.0
        
        # Time factor (most important)
        if input_data.temps_restant < input_data.occupation_predite:
            conflict_score += 0.4  # High chance of overlap
        elif input_data.temps_restant < input_data.occupation_predite + 15:
            conflict_score += 0.2  # Tight timing
        
        # Ongoing operations delay risk
        if input_data.operations_en_cours in ["maintenance", "refuel"]:
            conflict_score += 0.15
        elif input_data.operations_en_cours == "catering":
            conflict_score += 0.1
        
        # Size compatibility
        if input_data.taille_compatible == 0:
            conflict_score += 0.2
        
        # Maintenance or reserved status
        if input_data.maintenance == 1:
            conflict_score += 0.3
        if input_data.reserve == 1:
            conflict_score += 0.25
        
        # Weather delays
        if input_data.pluie == 1:
            conflict_score += 0.05
        if input_data.vent_fort == 1:
            conflict_score += 0.05
        if input_data.visibilite < 5:
            conflict_score += 0.05
        
        # Overall congestion
        if input_data.taux_occupation_global > 85:
            conflict_score += 0.15
        elif input_data.taux_occupation_global > 70:
            conflict_score += 0.1
        
        # Runway saturation
        if input_data.saturation_piste == 1:
            conflict_score += 0.1
        
        # Approaching/departing flights pressure
        total_movements = input_data.approche_60min + input_data.depart_60min
        if total_movements > 10:
            conflict_score += 0.1
        elif total_movements > 15:
            conflict_score += 0.15
        
        # Historical delay
        if input_data.retard_historique > 20:
            conflict_score += 0.05
        
        # Add some randomness
        conflict_score += random.uniform(-0.05, 0.05)
        
        # Clamp to [0, 1]
        conflict_probability = max(0.0, min(1.0, conflict_score))
        
        # Determine if conflict exists (threshold: 0.5)
        has_conflict = conflict_probability >= 0.5
        
        # Generate recommendation
        if has_conflict:
            if input_data.taux_occupation_global > 90:
                recommendation = "Deplacer vers parking militaire M2"
            elif input_data.besoin_passerelle == 0:
                recommendation = "Allouer parking distant sans passerelle"
            elif input_data.importance_vol == "private":
                recommendation = "Retarder allocation jusqu'a liberation spot prioritaire"
            else:
                recommendation = "Deplacer vers parking M2 (militaire)"
        else:
            if conflict_probability > 0.3:
                recommendation = "Surveillance renforcee - risque modere de conflit"
            elif input_data.distance_terminal > 500:
                recommendation = "Spot optimal disponible - allocation recommandee"
            else:
                recommendation = "Pas de conflit detecte - allocation normale"
        
        return ConflitOutput(
            conflit=has_conflict,
            probabilite=round(conflict_probability, 2),
            recommendation=recommendation
        )
    
    def _get_output_class(self) -> type[ConflitOutput]:
        """Return output class for deserialization"""
        return ConflitOutput
