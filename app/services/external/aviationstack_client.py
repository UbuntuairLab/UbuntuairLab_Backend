import httpx
import logging
from typing import Optional, List
from datetime import datetime, date, timedelta
from app.core.config import get_settings
from app.schemas.aviationstack import (
    AviationStackFlight,
    AviationStackResponse,
    AviationStackFutureResponse,
    FutureFlightSchedule,
    FlightStatus
)
from app.exceptions import OpenSkyAPIException
from app.utils.decorators import retry_with_backoff, singleton

logger = logging.getLogger(__name__)
settings = get_settings()


@singleton
class AviationStackClient:
    """
    Client for AviationStack API.
    Provides:
    - Real-time flight tracking
    - Historical flight data (last 3 months)
    - Future flight schedules (> 7 days ahead)
    - Timetable (current day schedules)
    
    Rate limits:
    - Free plan: 1 request/60s for timetable & future flights
    - Paid plans: 1 request/10s for timetable & future flights
    """
    
    def __init__(self):
        self.access_key = settings.AVIATIONSTACK_ACCESS_KEY
        self.api_base_url = settings.AVIATIONSTACK_API_BASE_URL
        self._http_client: Optional[httpx.AsyncClient] = None
        self._rate_limit_remaining: Optional[int] = None
    
    async def __aenter__(self):
        """Initialize HTTP client on context enter"""
        self._http_client = httpx.AsyncClient(timeout=30.0)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Close HTTP client on context exit"""
        if self._http_client:
            await self._http_client.aclose()
    
    @retry_with_backoff(max_retries=2, initial_delay=1.0)
    async def _make_request(
        self,
        endpoint: str,
        params: Optional[dict] = None
    ) -> dict:
        """
        Make HTTP request to AviationStack API.
        
        Args:
            endpoint: API endpoint path (e.g., "/flights")
            params: Query parameters
        
        Returns:
            JSON response as dictionary
        
        Raises:
            OpenSkyAPIException: If request fails
        """
        url = f"{self.api_base_url}{endpoint}"
        
        # Add access_key to all requests
        request_params = params or {}
        request_params["access_key"] = self.access_key
        
        try:
            logger.debug(f"Making request to {endpoint}", extra={"params": params})
            
            response = await self._http_client.get(url, params=request_params)
            
            # Handle rate limiting
            if response.status_code == 429:
                logger.error("Rate limit exceeded for AviationStack API")
                raise OpenSkyAPIException("Rate limit exceeded. Please wait before retrying.")
            
            # Handle authentication errors
            if response.status_code == 401:
                logger.error("Invalid AviationStack API access key")
                raise OpenSkyAPIException("Authentication failed. Check your access key.")
            
            # Handle function access restricted (upgrade required)
            if response.status_code == 403:
                logger.error(f"Access restricted to {endpoint}. Upgrade plan required.")
                raise OpenSkyAPIException(f"This endpoint requires a paid plan")
            
            response.raise_for_status()
            data = response.json()
            
            # Check for API errors in response
            if "error" in data:
                error_msg = data["error"].get("message", "Unknown error")
                logger.error(f"AviationStack API error: {error_msg}")
                raise OpenSkyAPIException(f"API error: {error_msg}")
            
            return data
            
        except httpx.HTTPStatusError as e:
            logger.error(
                f"HTTP error on {endpoint}: {e.response.status_code}",
                extra={"response": e.response.text}
            )
            raise OpenSkyAPIException(f"API request failed: {e.response.text}")
        except Exception as e:
            logger.error(f"Error making request to {endpoint}: {str(e)}")
            raise OpenSkyAPIException(f"Request error: {str(e)}")
    
    async def get_real_time_flights(
        self,
        airport_iata: Optional[str] = None,
        airport_icao: Optional[str] = None,
        flight_status: Optional[FlightStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> AviationStackResponse:
        """
        Get real-time flight data.
        
        Args:
            airport_iata: Filter by airport IATA code
            airport_icao: Filter by airport ICAO code
            flight_status: Filter by flight status
            limit: Number of results (max 100 for free, 1000 for paid)
            offset: Pagination offset
        
        Returns:
            AviationStackResponse with current flights
        """
        logger.info(f"Fetching real-time flights for {airport_iata or airport_icao}")
        
        params = {
            "limit": limit,
            "offset": offset
        }
        
        if airport_iata:
            # Can filter by arrival or departure
            params["arr_iata"] = airport_iata
        if airport_icao:
            params["arr_icao"] = airport_icao
        if flight_status:
            params["flight_status"] = flight_status.value
        
        data = await self._make_request("/flights", params)
        return AviationStackResponse(**data)
    
    async def get_historical_flights(
        self,
        flight_date: date,
        airport_iata: Optional[str] = None,
        airport_icao: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> AviationStackResponse:
        """
        Get historical flight data (last 3 months only).
        
        Args:
            flight_date: Date to query (YYYY-MM-DD)
            airport_iata: Filter by airport IATA code
            airport_icao: Filter by airport ICAO code
            limit: Number of results
            offset: Pagination offset
        
        Returns:
            AviationStackResponse with historical flights
        """
        logger.info(f"Fetching historical flights for {flight_date}")
        
        # Check if date is within last 3 months
        max_age = date.today() - timedelta(days=90)
        if flight_date < max_age:
            logger.warning(f"Date {flight_date} is older than 3 months, may not have data")
        
        params = {
            "flight_date": flight_date.isoformat(),
            "limit": limit,
            "offset": offset
        }
        
        if airport_iata:
            params["arr_iata"] = airport_iata
        if airport_icao:
            params["arr_icao"] = airport_icao
        
        data = await self._make_request("/flights", params)
        return AviationStackResponse(**data)
    
    async def get_timetable(
        self,
        airport_iata: str,
        timetable_type: str = "arrival",  # "arrival" or "departure"
        status: Optional[str] = None
    ) -> AviationStackResponse:
        """
        Get current day flight schedules (timetable).
        
        Rate limit: 1 req/60s (free) or 1 req/10s (paid)
        
        Args:
            airport_iata: Airport IATA code (e.g., "LFW" for Lomé)
            timetable_type: "arrival" or "departure"
            status: Filter by status (landed, scheduled, cancelled, etc.)
        
        Returns:
            AviationStackResponse with today's flights
        """
        logger.info(f"Fetching timetable for {airport_iata} ({timetable_type})")
        
        params = {
            "iataCode": airport_iata,
            "type": timetable_type
        }
        
        if status:
            params["status"] = status
        
        data = await self._make_request("/timetable", params)
        
        # Convert to standard response format
        if "data" in data:
            # Map timetable format to flight format
            flights = []
            for item in data["data"]:
                flight = AviationStackFlight(**item)
                flights.append(flight)
            
            return AviationStackResponse(
                pagination=data["pagination"],
                data=flights
            )
        
        return AviationStackResponse(**data)
    
    async def get_future_flights(
        self,
        airport_iata: str,
        future_date: date,
        timetable_type: str = "arrival",  # "arrival" or "departure"
        airline_iata: Optional[str] = None,
        flight_number: Optional[str] = None
    ) -> List[AviationStackFlight]:
        """
        Get future flight schedules (> 7 days ahead).
        
        IMPORTANT: Date must be > 7 days from today.
        Rate limit: 1 req/60s (free) or 1 req/10s (paid)
        
        Args:
            airport_iata: Airport IATA code (e.g., "LFW")
            future_date: Date to query (must be > current_date + 7 days)
            timetable_type: "arrival" or "departure"
            airline_iata: Filter by airline IATA code
            flight_number: Filter by flight number
        
        Returns:
            List of future flights for the given date
        """
        # Validate date is > 7 days ahead
        min_date = date.today() + timedelta(days=7)
        if future_date <= min_date:
            raise OpenSkyAPIException(
                f"Future date must be > 7 days ahead. "
                f"Requested: {future_date}, minimum: {min_date.isoformat()}"
            )
        
        logger.info(f"Fetching future flights for {airport_iata} on {future_date} ({timetable_type})")
        
        params = {
            "iataCode": airport_iata,
            "type": timetable_type,
            "date": future_date.isoformat()
        }
        
        if airline_iata:
            params["airline_iata"] = airline_iata
        if flight_number:
            params["flight_number"] = flight_number
        
        data = await self._make_request("/flightsFuture", params)
        
        # Parse future flights
        future_response = AviationStackFutureResponse(**data)
        
        # Convert to standard flight format
        flights = []
        for schedule in future_response.data:
            flight = schedule.to_aviation_stack_flight(future_date.isoformat())
            flights.append(flight)
        
        logger.info(f"Retrieved {len(flights)} future flights")
        return flights
    
    async def get_arrivals_and_departures(
        self,
        airport_iata: str,
        airport_icao: str,
        target_date: Optional[date] = None,
        use_future: bool = False
    ) -> List[AviationStackFlight]:
        """
        Get both arrivals and departures for an airport.
        
        Args:
            airport_iata: Airport IATA code (e.g., "LFW")
            airport_icao: Airport ICAO code (e.g., "DXXX")
            target_date: Date to query (None = today, past = historical, future = scheduled)
            use_future: Force use of future endpoint (requires date > 7 days)
        
        Returns:
            Combined list of arrivals and departures
        """
        all_flights = []
        
        if use_future and target_date:
            # Future flights (> 7 days)
            arrivals = await self.get_future_flights(
                airport_iata=airport_iata,
                future_date=target_date,
                timetable_type="arrival"
            )
            departures = await self.get_future_flights(
                airport_iata=airport_iata,
                future_date=target_date,
                timetable_type="departure"
            )
            all_flights = arrivals + departures
            
        elif target_date and target_date < date.today():
            # Historical flights
            arrivals_response = await self.get_historical_flights(
                flight_date=target_date,
                airport_icao=airport_icao
            )
            # Note: API doesn't separate arr/dep for historical, need to filter manually
            all_flights = arrivals_response.data
            
        else:
            # Current day timetable
            arrivals_response = await self.get_timetable(
                airport_iata=airport_iata,
                timetable_type="arrival"
            )
            departures_response = await self.get_timetable(
                airport_iata=airport_iata,
                timetable_type="departure"
            )
            all_flights = arrivals_response.data + departures_response.data
        
        logger.info(f"Retrieved {len(all_flights)} total flights")
        return all_flights
