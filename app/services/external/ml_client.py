"""
Client for Air Traffic ML API (Hugging Face Space)
Space: TAGBA/ubuntuairlab
URL: https://tagba-ubuntuairlab.hf.space
"""
import httpx
from typing import Dict, Optional, Any
from datetime import datetime
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


class MLAPIClient:
    """
    Client pour l'API de prédiction ML hébergée sur Hugging Face.
    
    Cette API fournit 3 modèles:
    - Modèle 1: Prédiction ETA/ETD avec probabilités de retard (XGBoost)
    - Modèle 2: Durée d'occupation des parkings (LightGBM)
    - Modèle 3: Détection de conflits et recommandations (XGBoost)
    """
    
    def __init__(
        self,
        base_url: str = None,
        timeout: float = 30.0
    ):
        self.base_url = (base_url or settings.ML_API_BASE_URL).rstrip('/')
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        self._client = httpx.AsyncClient(timeout=self.timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self._client:
            await self._client.aclose()
    
    async def _ensure_client(self):
        """Ensure HTTP client is initialized"""
        if not self._client:
            self._client = httpx.AsyncClient(timeout=self.timeout)
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Vérifie l'état de l'API ML.
        
        Returns:
            Dict avec status, timestamp, models_loaded
        """
        await self._ensure_client()
        
        try:
            response = await self._client.get(f"{self.base_url}/health")
            response.raise_for_status()
            result = response.json()
            
            logger.info(f"ML API health check: {result['status']}")
            return result
        
        except httpx.HTTPError as e:
            logger.error(f"ML API health check failed: {str(e)}")
            raise
    
    async def predict(
        self,
        flight_data: Dict[str, Any],
        retry_count: int = 3
    ) -> Dict[str, Any]:
        """
        Effectue une prédiction complète pour un vol.
        
        Args:
            flight_data: Données du vol (26 paramètres requis)
            retry_count: Nombre de tentatives en cas d'échec
        
        Returns:
            Dict contenant:
            - model_1_eta: Prédiction ETA/ETD
            - model_2_occupation: Durée d'occupation
            - model_3_conflict: Détection de conflits
            - metadata: timestamp, version
        """
        await self._ensure_client()
        
        for attempt in range(retry_count):
            try:
                response = await self._client.post(
                    f"{self.base_url}/predict",
                    json=flight_data
                )
                response.raise_for_status()
                result = response.json()
                
                logger.info(
                    f"ML prediction successful for flight {flight_data.get('callsign', 'unknown')} "
                    f"- ETA: {result['model_1_eta']['eta_ajuste']:.1f}min"
                )
                
                return result
            
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 422:
                    logger.error(f"Invalid flight data: {e.response.json()}")
                    raise ValueError(f"Invalid flight data: {e.response.json()}")
                elif e.response.status_code == 503:
                    logger.warning("ML models not loaded")
                    raise RuntimeError("ML models not available")
                else:
                    if attempt == retry_count - 1:
                        logger.error(f"ML prediction failed after {retry_count} attempts: {str(e)}")
                        raise
                    logger.warning(f"ML prediction attempt {attempt + 1} failed, retrying...")
            
            except httpx.RequestError as e:
                if attempt == retry_count - 1:
                    logger.error(f"Network error calling ML API: {str(e)}")
                    raise
                logger.warning(f"Network error, attempt {attempt + 1}, retrying...")
        
        raise RuntimeError("ML prediction failed after all retries")
    
    async def get_models_info(self) -> Dict[str, Any]:
        """
        Récupère les informations sur les modèles ML.
        
        Returns:
            Dict avec détails techniques des 3 modèles
        """
        await self._ensure_client()
        
        try:
            response = await self._client.get(f"{self.base_url}/models/info")
            response.raise_for_status()
            return response.json()
        
        except httpx.HTTPError as e:
            logger.error(f"Failed to get models info: {str(e)}")
            raise
    
    async def close(self):
        """Ferme le client HTTP"""
        if self._client:
            await self._client.aclose()
            self._client = None


def map_flight_to_ml_format(
    flight: Any,
    weather: Optional[Dict] = None,
    traffic_stats: Optional[Dict] = None,
    historical_data: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Convertit les données de vol du backend vers le format attendu par l'API ML.
    
    Args:
        flight: Objet Flight du backend
        weather: Données météo (température, vent, visibilité, pluie)
        traffic_stats: Statistiques de trafic (approche, tarmac, entrant, sortant)
        historical_data: Données historiques (retards compagnie, occupation avion)
    
    Returns:
        Dict au format attendu par l'API ML
    """
    # Données par défaut si non fournies
    weather = weather or {}
    traffic_stats = traffic_stats or {}
    historical_data = historical_data or {}
    
    # Extraction des données de vol réelles
    callsign = getattr(flight, 'callsign', None)
    icao24 = getattr(flight, 'icao24', None)
    velocity = getattr(flight, 'velocity', None)
    baro_altitude = getattr(flight, 'baro_altitude', None)
    origin_country = getattr(flight, 'origin_country', None)
    flight_type = getattr(flight, 'flight_type', None)
    
    # Calcul de distance à la piste basé sur altitude si disponible
    # Approximation: si altitude < 1000m, distance proche de la piste
    if baro_altitude and baro_altitude < 1000:
        distance_piste = max(1.0, baro_altitude / 100)  # 1-10km basé sur altitude
    else:
        distance_piste = 15.0  # Default pour vols éloignés
    
    # Type de vol: 0=arrivée, 1=départ
    type_vol = 1 if flight_type == "departure" else 0
    
    # Mapping vers format ML API avec vraies données
    ml_data = {
        # Identifiants
        "callsign": callsign,
        "icao24": icao24,
        
        # Données de vol réelles de OpenSky
        "vitesse_actuelle": float(velocity) if velocity else 250.0,
        "altitude": float(baro_altitude) if baro_altitude else 3500.0,
        "distance_piste": distance_piste,
        
        # Météo (à intégrer avec API météo réelle)
        "temperature": float(weather.get('temperature', 22.0)),
        "vent_vitesse": float(weather.get('wind_speed', 12.0)),
        "visibilite": float(weather.get('visibility', 10.0)),
        "pluie": float(weather.get('rain', 0.0)),
        
        # Compagnie et historique
        "compagnie": str(origin_country) if origin_country else 'Unknown',
        "retard_historique_compagnie": float(historical_data.get('avg_delay', 5.0)),
        
        # Trafic (à calculer depuis la DB parking_allocations)
        "trafic_approche": int(traffic_stats.get('approaching', 5)),
        "occupation_tarmac": float(traffic_stats.get('tarmac_occupation', 0.65)),
        
        # Type avion (à extraire du callsign ou de la DB aircraft)
        "type_avion": str(historical_data.get('aircraft_type', 'A320')),
        "historique_occupation_avion": float(historical_data.get('avg_occupation_time', 45.0)),
        
        # Type de vol basé sur données réelles
        "type_vol": type_vol,
        
        # Passagers et capacité (à calculer depuis parking_spots)
        "passagers_estimes": int(historical_data.get('passengers', 180)),
        "disponibilite_emplacements": int(traffic_stats.get('available_spots', 12)),
        "occupation_actuelle": float(traffic_stats.get('current_occupation', 0.7)),
        
        # Conditions et priorité
        "meteo_score": float(weather.get('score', 0.85)),
        "trafic_entrant": int(traffic_stats.get('incoming', 8)),
        "trafic_sortant": int(traffic_stats.get('outgoing', 6)),
        "priorite_vol": int(getattr(flight, 'priority', 0) or 0),
        "emplacements_futurs_libres": int(traffic_stats.get('future_free_spots', 3)),
        
        # Timestamp
        "timestamp": datetime.utcnow().isoformat()
    }
    
    return ml_data


async def get_flight_prediction_with_ml(
    flight: Any,
    weather: Optional[Dict] = None,
    traffic_stats: Optional[Dict] = None,
    historical_data: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Fonction utilitaire pour obtenir une prédiction ML complète pour un vol.
    
    Args:
        flight: Objet Flight
        weather: Données météo
        traffic_stats: Statistiques de trafic
        historical_data: Données historiques
    
    Returns:
        Résultat complet de la prédiction ML
    """
    async with MLAPIClient() as client:
        # Vérifier que l'API est disponible
        health = await client.health_check()
        if health['status'] != 'healthy':
            raise RuntimeError(f"ML API not healthy: {health['status']}")
        
        # Préparer les données
        ml_data = map_flight_to_ml_format(
            flight,
            weather=weather,
            traffic_stats=traffic_stats,
            historical_data=historical_data
        )
        
        # Obtenir la prédiction
        prediction = await client.predict(ml_data)
        
        return prediction
