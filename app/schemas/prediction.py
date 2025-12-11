"""
Pydantic schemas for ML predictions (Hugging Face API)
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ============================================================================
# REQUEST SCHEMAS
# ============================================================================

class FlightPredictionRequest(BaseModel):
    """
    Request schema for flight prediction (all 3 models)
    Based on Hugging Face API documentation
    """
    # Identification (optional)
    callsign: Optional[str] = Field(None, description="Flight callsign (e.g., 'AF1234')")
    icao24: Optional[str] = Field(None, description="ICAO24 code")
    
    # Flight parameters
    vitesse_actuelle: float = Field(..., description="Current speed in knots", ge=0)
    altitude: float = Field(..., description="Altitude in feet", ge=0)
    distance_piste: float = Field(..., description="Distance to runway in km", ge=0)
    
    # Weather conditions (auto-filled from real data if not provided)
    temperature: Optional[float] = Field(None, description="Temperature in Celsius (auto-filled if None)")
    vent_vitesse: Optional[float] = Field(None, description="Wind speed in knots (auto-filled if None)", ge=0)
    visibilite: Optional[float] = Field(None, description="Visibility in km (auto-filled if None)", ge=0)
    pluie: Optional[float] = Field(None, description="Rain intensity in mm/h (auto-filled if None)", ge=0)
    meteo_score: Optional[float] = Field(None, description="Weather score 0-1 (auto-filled if None)", ge=0, le=1)
    
    # Airline data (auto-filled from DB if not provided)
    compagnie: Optional[str] = Field(None, description="Airline name or code (auto-filled from flight data)")
    retard_historique_compagnie: Optional[float] = Field(None, description="Historical delay avg in minutes (auto-filled)")
    
    # Traffic data (auto-filled from DB in real-time)
    trafic_approche: Optional[int] = Field(None, description="Number of aircraft in approach (auto-filled)", ge=0)
    occupation_tarmac: Optional[float] = Field(None, description="Tarmac occupation rate 0-1 (auto-filled)", ge=0, le=1)
    trafic_entrant: Optional[int] = Field(None, description="Incoming flights count (auto-filled)", ge=0)
    trafic_sortant: Optional[int] = Field(None, description="Outgoing flights count (auto-filled)", ge=0)
    
    # Aircraft data (auto-filled from flight data)
    type_avion: Optional[str] = Field(None, description="Aircraft type e.g. A320 (auto-filled if None)")
    historique_occupation_avion: Optional[float] = Field(None, description="Historical avg duration minutes (auto-filled)")
    type_vol: int = Field(..., description="0=arrival, 1=departure", ge=0, le=1)
    passagers_estimes: Optional[int] = Field(None, description="Estimated passengers (auto-filled)", ge=0)
    
    # Parking/capacity (auto-filled from DB parking_spots)
    disponibilite_emplacements: Optional[int] = Field(None, description="Available parking spots (auto-filled)", ge=0)
    occupation_actuelle: Optional[float] = Field(None, description="Current occupation rate 0-1 (auto-filled)", ge=0, le=1)
    priorite_vol: Optional[int] = Field(None, description="0=normal, 1=priority (auto-filled)", ge=0, le=1)
    emplacements_futurs_libres: Optional[int] = Field(None, description="Future spots to be freed (auto-filled)", ge=0)
    
    # Timestamp (optional)
    timestamp: Optional[str] = Field(None, description="ISO 8601 timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "callsign": "AF1234",
                "icao24": "3944ef",
                "vitesse_actuelle": 250.0,
                "altitude": 3500.0,
                "distance_piste": 15.5,
                "temperature": 22.0,
                "vent_vitesse": 12.0,
                "visibilite": 10.0,
                "pluie": 0.5,
                "compagnie": "Air France",
                "retard_historique_compagnie": 8.5,
                "trafic_approche": 5,
                "occupation_tarmac": 0.65,
                "type_avion": "A320",
                "historique_occupation_avion": 45.0,
                "type_vol": 0,
                "passagers_estimes": 180,
                "disponibilite_emplacements": 12,
                "occupation_actuelle": 0.7,
                "meteo_score": 0.85,
                "trafic_entrant": 8,
                "trafic_sortant": 6,
                "priorite_vol": 0,
                "emplacements_futurs_libres": 3
            }
        }


# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================

class Model1ETAResponse(BaseModel):
    """Model 1: ETA/ETD prediction with delay probabilities"""
    eta_ajuste: float = Field(..., description="Adjusted ETA in minutes")
    proba_delay_15: float = Field(..., description="Probability of delay > 15 min (0-1)")
    proba_delay_30: float = Field(..., description="Probability of delay > 30 min (0-1)")
    estimation_minutes: float = Field(..., description="Same as eta_ajuste")
    confiance_retard_15min: str = Field(..., description="Delay confidence 15min (percentage)")
    confiance_retard_30min: str = Field(..., description="Delay confidence 30min (percentage)")


class Model2OccupationResponse(BaseModel):
    """Model 2: Parking occupation duration prediction"""
    temps_occupation_minutes: float = Field(..., description="Predicted occupation time in minutes")
    temps_min_minutes: float = Field(..., description="Lower bound (95% confidence)")
    temps_max_minutes: float = Field(..., description="Upper bound (95% confidence)")
    intervalle_confiance: str = Field(..., description="Confidence interval (e.g., '95%')")


class Model3ConflictResponse(BaseModel):
    """Model 3: Conflict detection and decision recommendation"""
    risque_conflit: int = Field(..., description="0=no conflict, 1=conflict detected")
    proba_conflit: float = Field(..., description="Conflict probability (0-1)")
    risque_saturation: int = Field(..., description="0=capacity OK, 1=saturation")
    proba_saturation: float = Field(..., description="Saturation probability (0-1)")
    decision_recommandee: int = Field(..., description="Decision code (0-3)")
    decision_label: str = Field(..., description="Decision label in French")
    explication: str = Field(..., description="Detailed explanation")


class PredictionMetadata(BaseModel):
    """Metadata about the prediction"""
    timestamp: str = Field(..., description="Prediction timestamp (ISO 8601)")
    pipeline_version: str = Field(..., description="ML pipeline version")


class FlightPredictionResponse(BaseModel):
    """
    Complete prediction response from all 3 models
    """
    model_1_eta: Model1ETAResponse
    model_2_occupation: Model2OccupationResponse
    model_3_conflict: Model3ConflictResponse
    metadata: PredictionMetadata
    
    class Config:
        json_schema_extra = {
            "example": {
                "model_1_eta": {
                    "eta_ajuste": 36.37,
                    "proba_delay_15": 0.23,
                    "proba_delay_30": 0.08,
                    "estimation_minutes": 36.37,
                    "confiance_retard_15min": "23%",
                    "confiance_retard_30min": "8%"
                },
                "model_2_occupation": {
                    "temps_occupation_minutes": 52.99,
                    "temps_min_minutes": 48.5,
                    "temps_max_minutes": 57.3,
                    "intervalle_confiance": "95%"
                },
                "model_3_conflict": {
                    "risque_conflit": 0,
                    "proba_conflit": 0.0001,
                    "risque_saturation": 1,
                    "proba_saturation": 0.78,
                    "decision_recommandee": 1,
                    "decision_label": "Réaffecter à un autre emplacement",
                    "explication": "Faible risque de conflit (0.01%), saturation élevée (78%)"
                },
                "metadata": {
                    "timestamp": "2025-12-11T13:30:00",
                    "pipeline_version": "1.0.0"
                }
            }
        }


# ============================================================================
# HEALTH CHECK SCHEMAS
# ============================================================================

class MLHealthResponse(BaseModel):
    """Health check response from ML API"""
    status: str = Field(..., description="healthy or models_not_trained")
    timestamp: str = Field(..., description="Health check timestamp")
    models_loaded: bool = Field(..., description="Whether models are loaded")


class MLModelsInfoResponse(BaseModel):
    """Models information response"""
    models_trained: bool
    model_1_eta: dict
    model_2_occupation: dict
    model_3_conflict: dict
