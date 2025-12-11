"""
Flight endpoints.
Provides read access to flight data.
"""
from typing import List, Optional
from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.repositories.flight_repository import FlightRepository
from app.schemas.flight import FlightResponse, FlightListResponse
from app.api.v1.endpoints.auth import get_current_active_user
from app.services.external.aviationstack_client import AviationStackClient
from app.core.config import get_settings

router = APIRouter()
settings = get_settings()


@router.get("/", response_model=FlightListResponse)
async def list_flights(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of records to return"),
    flight_type: Optional[str] = Query(None, description="Filter by flight type (arrival/departure)"),
    status: Optional[str] = Query(None, description="Filter by status"),
    future_date: Optional[str] = Query(None, description="Get future flights for date (YYYY-MM-DD, must be > 7 days ahead)"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    List flights with pagination and filters.
    
    - Without future_date: Returns flights from database (synced from OpenSky)
    - With future_date: Returns future scheduled flights from AviationStack (> 7 days ahead)
    
    Requires authentication.
    """
    # If future_date is provided, use AviationStack
    if future_date:
        try:
            target_date = date.fromisoformat(future_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        
        # Validate date is > 7 days ahead
        min_date = date.today() + timedelta(days=7)
        if target_date <= min_date:
            raise HTTPException(
                status_code=400,
                detail=f"Future date must be more than 7 days ahead. Minimum: {min_date.isoformat()}"
            )
        
        # Fetch from AviationStack
        async with AviationStackClient() as client:
            try:
                if flight_type == "arrival":
                    future_flights = await client.get_future_flights(
                        airport_iata=settings.AIRPORT_IATA,
                        future_date=target_date,
                        timetable_type="arrival"
                    )
                elif flight_type == "departure":
                    future_flights = await client.get_future_flights(
                        airport_iata=settings.AIRPORT_IATA,
                        future_date=target_date,
                        timetable_type="departure"
                    )
                else:
                    # Both arrivals and departures
                    arrivals = await client.get_future_flights(
                        airport_iata=settings.AIRPORT_IATA,
                        future_date=target_date,
                        timetable_type="arrival"
                    )
                    departures = await client.get_future_flights(
                        airport_iata=settings.AIRPORT_IATA,
                        future_date=target_date,
                        timetable_type="departure"
                    )
                    future_flights = arrivals + departures
                
                # Convert AviationStack format to our FlightResponse format
                flights = []
                for av_flight in future_flights[skip:skip+limit]:
                    # Map AviationStack fields to our schema
                    flight_dict = {
                        "icao24": av_flight.aircraft.icao24 if av_flight.aircraft and av_flight.aircraft.icao24 else f"future_{av_flight.flight.iata}",
                        "callsign": av_flight.flight.iata or "",
                        "origin_country": "",
                        "first_seen": None,
                        "last_seen": None,
                        "est_departure_time": av_flight.departure.scheduled if av_flight.departure else None,
                        "est_arrival_time": av_flight.arrival.scheduled if av_flight.arrival else None,
                        "departure_airport": av_flight.departure.iata if av_flight.departure else None,
                        "arrival_airport": av_flight.arrival.iata if av_flight.arrival else None,
                        "flight_type": flight_type or "arrival",
                        "status": av_flight.flight_status.value if av_flight.flight_status else "scheduled",
                        "created_at": None,
                        "updated_at": None
                    }
                    flights.append(flight_dict)
                
                return {
                    "total": len(future_flights),
                    "skip": skip,
                    "limit": limit,
                    "flights": flights,
                    "source": "aviationstack_future"
                }
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to fetch future flights: {str(e)}")
    
    # Default: return from database
    flight_repo = FlightRepository(db)
    
    flights, total = await flight_repo.list_flights(
        skip=skip,
        limit=limit,
        flight_type=flight_type,
        status=status
    )
    
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "flights": flights,
        "source": "database"
    }


@router.get("/{icao24}", response_model=FlightResponse)
async def get_flight(
    icao24: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Get flight details by ICAO24.
    Requires authentication.
    """
    flight_repo = FlightRepository(db)
    flight = await flight_repo.get_by_icao24(icao24)
    
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")
    
    return flight


@router.get("/{icao24}/predictions")
async def get_flight_predictions(
    icao24: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Get AI predictions for a specific flight.
    Requires authentication.
    """
    from app.repositories.prediction_repository import PredictionRepository
    
    flight_repo = FlightRepository(db)
    flight = await flight_repo.get_by_icao24(icao24)
    
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")
    
    prediction_repo = PredictionRepository(db)
    predictions = await prediction_repo.get_by_flight(icao24)
    
    return {
        "flight_icao24": icao24,
        "predictions": predictions
    }
