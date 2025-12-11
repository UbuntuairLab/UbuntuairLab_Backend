from app.services.ai_models.eta_model import ETAModel
from app.services.ai_models.occupation_model import OccupationModel
from app.services.ai_models.conflit_model import ConflitModel
from app.services.cache.prediction_cache import PredictionCache
from app.utils.decorators import singleton


@singleton
class AIModelFactory:
    """
    Factory for creating and managing AI model instances.
    Ensures singleton pattern for model clients to reuse HTTP connections.
    """
    
    def __init__(self):
        self._cache = PredictionCache()
        self._eta_model: ETAModel = None
        self._occupation_model: OccupationModel = None
        self._conflit_model: ConflitModel = None
    
    async def initialize(self):
        """Initialize cache connection"""
        await self._cache.connect()
    
    async def shutdown(self):
        """Shutdown cache connection"""
        await self._cache.disconnect()
    
    def get_eta_model(self) -> ETAModel:
        """
        Get ETA/ETD prediction model instance.
        
        Returns:
            ETAModel singleton instance
        """
        if self._eta_model is None:
            self._eta_model = ETAModel(self._cache)
        return self._eta_model
    
    def get_occupation_model(self) -> OccupationModel:
        """
        Get occupation duration prediction model instance.
        
        Returns:
            OccupationModel singleton instance
        """
        if self._occupation_model is None:
            self._occupation_model = OccupationModel(self._cache)
        return self._occupation_model
    
    def get_conflit_model(self) -> ConflitModel:
        """
        Get conflict detection model instance.
        
        Returns:
            ConflitModel singleton instance
        """
        if self._conflit_model is None:
            self._conflit_model = ConflitModel(self._cache)
        return self._conflit_model
    
    async def health_check_all(self) -> dict:
        """
        Check health of all AI models and cache.
        
        Returns:
            Dictionary with health status for each component
        """
        eta_model = self.get_eta_model()
        occupation_model = self.get_occupation_model()
        conflit_model = self.get_conflit_model()
        
        async with eta_model, occupation_model, conflit_model:
            return {
                "cache": await self._cache.health_check(),
                "eta_model": await eta_model.health_check(),
                "occupation_model": await occupation_model.health_check(),
                "conflit_model": await conflit_model.health_check()
            }
