"""
Service pour calculer les statistiques de trafic en temps réel.
Utilisé pour enrichir les prédictions ML avec des données réelles.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Dict
from app.models.parking import ParkingAllocation, ParkingSpot, SpotStatus
from app.models.flight import Flight, FlightStatus, FlightType
import logging

logger = logging.getLogger(__name__)


async def get_traffic_statistics(db: AsyncSession) -> Dict:
    """
    Calcule les statistiques de trafic en temps réel depuis la DB.
    
    Returns:
        Dict contenant:
        - approaching: Nombre de vols actifs en approche
        - tarmac_occupation: Taux d'occupation du tarmac (0.0-1.0)
        - available_spots: Nombre de spots disponibles
        - current_occupation: Taux d'occupation actuel (0.0-1.0)
        - incoming: Vols entrants actifs
        - outgoing: Vols sortants actifs
        - future_free_spots: Estimation de spots libres dans 1h
    """
    # Valeurs par défaut au cas où les requêtes échouent
    default_stats = {
        "approaching": 0,
        "tarmac_occupation": 0.0,
        "available_spots": 16,  # Based on seeded civil spots
        "current_occupation": 0.0,
        "incoming": 0,
        "outgoing": 0,
        "future_free_spots": 16
    }
    
    try:
        # Compter les vols actifs en approche (ARRIVAL + ACTIVE)
        result = await db.execute(
            select(func.count(Flight.icao24))
            .where(
                Flight.status == "active",
                Flight.flight_type == "arrival"
            )
        )
        approaching = result.scalar() or 0
        
        # Compter les spots disponibles
        result = await db.execute(
            select(func.count(ParkingSpot.spot_id))
            .where(ParkingSpot.status == SpotStatus.AVAILABLE)
        )
        available_spots = result.scalar() or 0
        
        # Compter le total de spots (civil uniquement pour occupation normale)
        result = await db.execute(
            select(func.count(ParkingSpot.spot_id))
            .where(ParkingSpot.spot_type == "civil")
        )
        total_civil_spots = result.scalar() or 1  # Éviter division par zéro
        
        # Compter les spots occupés
        result = await db.execute(
            select(func.count(ParkingSpot.spot_id))
            .where(ParkingSpot.status == SpotStatus.OCCUPIED)
        )
        occupied_spots = result.scalar() or 0
        
        # Calculer le taux d'occupation
        current_occupation = occupied_spots / total_civil_spots if total_civil_spots > 0 else 0.0
        tarmac_occupation = current_occupation  # Même métrique pour le tarmac
        
        # Compter vols entrants (ACTIVE + ARRIVAL)
        result = await db.execute(
            select(func.count(Flight.icao24))
            .where(
                Flight.status == "active",
                Flight.flight_type == "arrival"
            )
        )
        incoming = result.scalar() or 0
        
        # Compter vols sortants (ACTIVE + DEPARTURE)
        result = await db.execute(
            select(func.count(Flight.icao24))
            .where(
                Flight.status == "active",
                Flight.flight_type == "departure"
            )
        )
        outgoing = result.scalar() or 0
        
        # Estimation des spots futurs libres
        # Basé sur les allocations qui se terminent bientôt (prochaine heure)
        from datetime import datetime, timedelta, timezone
        one_hour_later = datetime.now(timezone.utc) + timedelta(hours=1)
        
        result = await db.execute(
            select(func.count(ParkingAllocation.allocation_id))
            .where(
                ParkingAllocation.actual_end_time.is_(None),  # Active allocations
                ParkingAllocation.predicted_end_time <= one_hour_later
            )
        )
        future_free_spots = result.scalar() or 0
        
        stats = {
            "approaching": approaching,
            "tarmac_occupation": round(tarmac_occupation, 2),
            "available_spots": available_spots,
            "current_occupation": round(current_occupation, 2),
            "incoming": incoming,
            "outgoing": outgoing,
            "future_free_spots": future_free_spots + available_spots  # Spots actuels + futurs
        }
        
        logger.info(f"Traffic stats calculated: {stats}")
        return stats
        
    except Exception as e:
        logger.error(f"Error calculating traffic stats: {str(e)}", exc_info=True)
        # Retourner les valeurs par défaut en cas d'erreur
        return default_stats


async def get_weather_data() -> Dict:
    """
    Récupère les données météo actuelles.
    
    TODO: Intégrer avec une vraie API météo (OpenWeatherMap, Météo France, etc.)
    
    Returns:
        Dict avec température, vent (vitesse et direction), visibilité, pluie, score
    """
    # TODO: Appeler une API météo réelle
    # Pour l'instant, retourner des données simulées réalistes
    return {
        "temperature": 22.0,     # °C
        "wind_speed": 12.0,      # km/h
        "wind_direction": 180.0,  # degrés (0-360, 180 = vent du sud)
        "visibility": 10.0,       # km
        "rain": 0.0,             # mm
        "score": 0.85            # 0.0-1.0 (conditions favorables)
    }


async def get_historical_data(db: AsyncSession, flight: Flight) -> Dict:
    """
    Récupère les données historiques pour un vol depuis la DB.
    
    Args:
        db: Session de base de données
        flight: Objet Flight
    
    Returns:
        Dict avec retard moyen, temps d'occupation, passagers, type d'avion, airline
    """
    try:
        # Extraire la compagnie depuis le callsign ou origin_country
        airline = "Unknown"
        if flight.callsign and len(flight.callsign) >= 3:
            # Les 3 premiers caractères sont souvent le code ICAO de la compagnie
            airline_code = flight.callsign[:3].upper()
            # Mapping basique des codes ICAO vers noms de compagnies
            airline_mapping = {
                "AFR": "Air France",
                "KLM": "KLM",
                "BAW": "British Airways",
                "DLH": "Lufthansa",
                "UAE": "Emirates",
                "QFA": "Qantas",
                "AAL": "American Airlines",
                "DAL": "Delta",
                "UAL": "United",
                "RYR": "Ryanair",
                "EZY": "EasyJet",
                "IBE": "Iberia",
                "TAP": "TAP Portugal",
            }
            airline = airline_mapping.get(airline_code, flight.origin_country or "Unknown")
        elif flight.origin_country:
            airline = flight.origin_country
        
        # Calculer le retard moyen de cette compagnie depuis l'historique des vols complétés
        avg_delay = 5.0  # Default
        try:
            from app.models.flight import FlightStatus
            result = await db.execute(
                select(func.avg(Flight.predicted_delay_minutes))
                .where(
                    Flight.origin_country == flight.origin_country,
                    Flight.status == "completed",
                    Flight.predicted_delay_minutes.isnot(None)
                )
            )
            historical_avg_delay = result.scalar()
            if historical_avg_delay is not None:
                avg_delay = float(historical_avg_delay)
                logger.info(f"Historical avg delay for {airline}: {avg_delay:.1f}min")
        except Exception as e:
            logger.warning(f"Could not calculate historical delay: {str(e)}")
        
        # Extraire le type d'avion du callsign ou de prédictions précédentes
        aircraft_type = "A320"  # Default
        # TODO: Ajouter une table aircraft_registry pour mapper icao24 -> aircraft_type
        
        # Calculer le temps d'occupation moyen pour ce type d'avion depuis les allocations
        avg_occupation_time = 45.0  # Default
        try:
            result = await db.execute(
                select(func.avg(ParkingAllocation.actual_duration_minutes))
                .where(
                    ParkingAllocation.actual_end_time.isnot(None),  # Completed allocations
                    ParkingAllocation.actual_duration_minutes.isnot(None)
                )
            )
            historical_occupation = result.scalar()
            if historical_occupation is not None:
                avg_occupation_time = float(historical_occupation)
                logger.info(f"Historical avg occupation: {avg_occupation_time:.1f}min")
        except Exception as e:
            logger.warning(f"Could not calculate historical occupation: {str(e)}")
        
        # Estimer les passagers selon le type d'avion
        passengers_by_type = {
            "A320": 180,
            "A321": 220,
            "B737": 189,
            "A319": 156,
            "B777": 396,
            "A380": 525,
        }
        passengers = passengers_by_type.get(aircraft_type, 180)
        
        return {
            "avg_delay": avg_delay,
            "aircraft_type": aircraft_type,
            "passengers": passengers,
            "avg_occupation_time": avg_occupation_time,
            "airline": airline
        }
        
    except Exception as e:
        logger.error(f"Error getting historical data: {str(e)}")
        return {
            "avg_delay": 5.0,
            "aircraft_type": "A320",
            "passengers": 180,
            "avg_occupation_time": 45.0,
            "airline": "Unknown"
        }
