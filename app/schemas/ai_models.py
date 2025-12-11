from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ETAETDInput(BaseModel):
    """Input schema for ETA/ETD prediction model"""
    latitude: float = Field(..., description="Current latitude in decimal degrees")
    longitude: float = Field(..., description="Current longitude in decimal degrees")
    altitude: float = Field(..., description="Barometric altitude in meters")
    vitesse: float = Field(..., description="Velocity over ground in m/s")
    heading: float = Field(..., description="True track in decimal degrees")
    vertical_rate: float = Field(..., description="Vertical rate in m/s")
    distance: float = Field(..., description="Distance to destination in km")
    eta_theorique: str = Field(..., description="Theoretical ETA (ISO datetime)")
    atd: str = Field(..., description="Actual time of departure (ISO datetime)")
    type_avion: str = Field(..., description="Aircraft type (e.g., A320, B737)")
    compagnie: str = Field(..., description="Airline company name")
    vent: float = Field(..., description="Wind speed in km/h")
    visibilite: float = Field(..., description="Visibility in km")
    pluie: int = Field(0, description="Rain indicator (0 or 1)")
    orage: int = Field(0, description="Storm indicator (0 or 1)")
    temperature: float = Field(..., description="Temperature in Celsius")
    heure_locale: int = Field(..., description="Local hour (0-23)")
    jour_semaine: int = Field(..., description="Day of week (0-6, Monday=0)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "latitude": 6.18,
                "longitude": 1.25,
                "altitude": 9000,
                "vitesse": 720,
                "heading": 140,
                "vertical_rate": -4,
                "distance": 120,
                "eta_theorique": "2025-01-15T14:05:00",
                "atd": "2025-01-15T12:30:00",
                "type_avion": "A320",
                "compagnie": "Air France",
                "vent": 25,
                "visibilite": 6,
                "pluie": 0,
                "orage": 0,
                "temperature": 31,
                "heure_locale": 14,
                "jour_semaine": 3
            }
        }


class ETAETDOutput(BaseModel):
    """Output schema for ETA/ETD prediction model"""
    eta_adjusted: str = Field(..., description="Adjusted ETA (ISO datetime)")
    retard_minutes: int = Field(..., description="Delay in minutes")
    
    class Config:
        json_schema_extra = {
            "example": {
                "eta_adjusted": "2025-01-15T14:27:00",
                "retard_minutes": 22
            }
        }


class OccupationInput(BaseModel):
    """Input schema for parking occupation duration prediction model"""
    type_avion: str = Field(..., description="Aircraft type (e.g., A320)")
    compagnie: str = Field(..., description="Airline company name")
    eta_adjusted: str = Field(..., description="Adjusted ETA (ISO datetime)")
    retard: int = Field(..., description="Delay in minutes")
    provenance: str = Field(..., description="Origin type: short/medium/long")
    passagers: int = Field(..., description="Number of passengers")
    operation: str = Field(..., description="Operation type: debarquement/embarquement")
    carburant: int = Field(0, description="Refueling needed (0 or 1)")
    catering: int = Field(0, description="Catering needed (0 or 1)")
    maintenance: int = Field(0, description="Maintenance needed (0 or 1)")
    passerelle: int = Field(1, description="Jetway needed (0 or 1)")
    historique_occupation_type: float = Field(..., description="Historical avg occupation for this aircraft type")
    pluie: int = Field(0, description="Rain indicator (0 or 1)")
    vent: float = Field(..., description="Wind speed in km/h")
    visibilite: float = Field(..., description="Visibility in km")
    temperature_extreme: int = Field(0, description="Extreme temperature indicator (0 or 1)")
    arrivees_40min: int = Field(..., description="Number of arrivals in next 40min")
    departs_40min: int = Field(..., description="Number of departures in next 40min")
    taux_occupation: float = Field(..., description="Current parking occupancy rate %")
    pistes_disponibles: int = Field(1, description="Number of available runways")
    
    class Config:
        json_schema_extra = {
            "example": {
                "type_avion": "A320",
                "compagnie": "Air France",
                "eta_adjusted": "2025-01-15T14:27:00",
                "retard": 22,
                "provenance": "medium",
                "passagers": 150,
                "operation": "debarquement",
                "carburant": 1,
                "catering": 0,
                "maintenance": 0,
                "passerelle": 1,
                "historique_occupation_type": 45,
                "pluie": 0,
                "vent": 15,
                "visibilite": 8,
                "temperature_extreme": 0,
                "arrivees_40min": 3,
                "departs_40min": 4,
                "taux_occupation": 62,
                "pistes_disponibles": 1
            }
        }


class OccupationOutput(BaseModel):
    """Output schema for parking occupation duration prediction model"""
    occupation_minutes: int = Field(..., description="Predicted occupation duration in minutes")
    intervalle_confiance: str = Field(..., description="Confidence interval (e.g., '46 - 58')")
    
    class Config:
        json_schema_extra = {
            "example": {
                "occupation_minutes": 52,
                "intervalle_confiance": "46 - 58"
            }
        }


class ConflitInput(BaseModel):
    """Input schema for parking conflict detection model"""
    eta_adjusted: str = Field(..., description="Adjusted ETA for incoming flight")
    type_avion_in: str = Field(..., description="Incoming aircraft type")
    compagnie_in: str = Field(..., description="Incoming airline")
    besoin_passerelle: int = Field(1, description="Jetway requirement (0 or 1)")
    sensibilite_meteo: int = Field(1, description="Weather sensitivity (0 or 1)")
    importance_vol: str = Field(..., description="Flight importance: commercial/charter/private")
    occupation_predite: int = Field(..., description="Predicted occupation duration in minutes")
    temps_restant: int = Field(..., description="Time remaining for current aircraft in minutes")
    retard_historique: int = Field(..., description="Historical delay for this airline in minutes")
    type_avion_out: str = Field(..., description="Current aircraft type on spot")
    operations_en_cours: str = Field(..., description="Ongoing operations: catering/refuel/maintenance")
    taille_compatible: int = Field(1, description="Size compatibility (0 or 1)")
    distance_terminal: int = Field(..., description="Distance to terminal in meters")
    reserve: int = Field(0, description="Reserved spot indicator (0 or 1)")
    maintenance: int = Field(0, description="Under maintenance (0 or 1)")
    pluie: int = Field(0, description="Rain indicator (0 or 1)")
    vent_fort: int = Field(0, description="Strong wind indicator (0 or 1)")
    visibilite: float = Field(..., description="Visibility in km")
    approche_60min: int = Field(..., description="Flights approaching in next 60min")
    depart_60min: int = Field(..., description="Flights departing in next 60min")
    saturation_piste: int = Field(0, description="Runway saturation indicator (0 or 1)")
    taux_occupation_global: float = Field(..., description="Global parking occupancy rate %")
    
    class Config:
        json_schema_extra = {
            "example": {
                "eta_adjusted": "2025-01-15T14:27:00",
                "type_avion_in": "A320",
                "compagnie_in": "Air France",
                "besoin_passerelle": 1,
                "sensibilite_meteo": 1,
                "importance_vol": "commercial",
                "occupation_predite": 52,
                "temps_restant": 15,
                "retard_historique": 12,
                "type_avion_out": "B737",
                "operations_en_cours": "catering",
                "taille_compatible": 1,
                "distance_terminal": 200,
                "reserve": 0,
                "maintenance": 0,
                "pluie": 0,
                "vent_fort": 0,
                "visibilite": 8,
                "approche_60min": 4,
                "depart_60min": 3,
                "saturation_piste": 0,
                "taux_occupation_global": 68
            }
        }


class ConflitOutput(BaseModel):
    """Output schema for parking conflict detection model"""
    conflit: bool = Field(..., description="Conflict detected (true/false)")
    probabilite: float = Field(..., description="Conflict probability (0-1)")
    recommendation: str = Field(..., description="Recommended action")
    
    class Config:
        json_schema_extra = {
            "example": {
                "conflit": True,
                "probabilite": 0.87,
                "recommendation": "Deplacer vers parking M2 (militaire)"
            }
        }
