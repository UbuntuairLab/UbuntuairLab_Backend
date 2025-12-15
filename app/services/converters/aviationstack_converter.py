"""
AviationStack to FlightData Converter.
Converts AviationStack API responses to OpenSky FlightData format for database storage.
"""
import logging
from typing import Optional
from datetime import datetime

from app.schemas.aviationstack import AviationStackFlight
from app.schemas.opensky import FlightData, FlightType

logger = logging.getLogger(__name__)


class AviationStackConverter:
    """
    Converter for AviationStack API data to FlightData schema.
    Handles mapping between different API formats.
    """
    
    @staticmethod
    def to_flight_data(
        av_flight: AviationStackFlight,
        flight_type: Optional[str] = None
    ) -> FlightData:
        """
        Convert AviationStackFlight to FlightData (OpenSky format).
        
        Args:
            av_flight: AviationStack flight object
            flight_type: Optional flight type override ("arrival" or "departure")
        
        Returns:
            FlightData object compatible with database
        
        Raises:
            ValueError: If required fields are missing
        """
        # Extract ICAO24 or generate temporary ID
        icao24 = av_flight.get_icao24()
        if not icao24:
            # For flights without ICAO24, generate temporary ID
            callsign = av_flight.get_callsign()
            if callsign:
                icao24 = f"temp_{callsign.lower()}"
                logger.warning(
                    f"Flight {callsign} missing ICAO24, using temporary ID: {icao24}"
                )
            else:
                raise ValueError("Flight missing both ICAO24 and callsign")
        
        # Extract callsign
        callsign = av_flight.get_callsign()
        
        # Get timestamps
        departure_time = av_flight.get_departure_time()
        arrival_time = av_flight.get_arrival_time()
        
        # Convert datetime to Unix timestamps
        first_seen = int(departure_time.timestamp()) if departure_time else int(datetime.now().timestamp())
        last_seen = int(arrival_time.timestamp()) if arrival_time else int(datetime.now().timestamp())
        
        # Extract airport codes
        est_departure_airport = None
        est_arrival_airport = None
        
        if av_flight.departure:
            est_departure_airport = (
                av_flight.departure.icao_code or 
                av_flight.departure.iata_code
            )
        
        if av_flight.arrival:
            est_arrival_airport = (
                av_flight.arrival.icao_code or 
                av_flight.arrival.iata_code
            )
        
        # Auto-detect flight type if not provided
        if not flight_type:
            # If we have both airports, need to determine based on context
            # Default to arrival if not specified
            flight_type = "arrival"
        
        # Build FlightData object
        flight_data = FlightData(
            icao24=icao24,
            callsign=callsign,
            first_seen=first_seen,
            last_seen=last_seen,
            est_departure_airport=est_departure_airport,
            est_arrival_airport=est_arrival_airport,
            # Optional fields - set to None
            est_departure_airport_horiz_distance=None,
            est_departure_airport_vert_distance=None,
            est_arrival_airport_horiz_distance=None,
            est_arrival_airport_vert_distance=None,
            departure_airport_candidates_count=0,
            arrival_airport_candidates_count=0
        )
        
        logger.info(
            f"Converted AviationStack flight {callsign} ({icao24}) to FlightData"
        )
        
        return flight_data
    
    @staticmethod
    def batch_convert(
        av_flights: list[AviationStackFlight],
        flight_type: Optional[str] = None
    ) -> list[FlightData]:
        """
        Convert multiple AviationStack flights to FlightData format.
        
        Args:
            av_flights: List of AviationStack flight objects
            flight_type: Optional flight type for all flights
        
        Returns:
            List of FlightData objects
        """
        converted_flights = []
        
        for av_flight in av_flights:
            try:
                flight_data = AviationStackConverter.to_flight_data(
                    av_flight, flight_type
                )
                converted_flights.append(flight_data)
            except ValueError as e:
                logger.error(f"Failed to convert flight: {e}")
                continue
        
        logger.info(
            f"Batch converted {len(converted_flights)}/{len(av_flights)} flights"
        )
        
        return converted_flights
