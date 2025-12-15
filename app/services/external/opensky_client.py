import httpx
import logging
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from app.core.config import get_settings
from app.schemas.opensky import FlightData, OpenSkyResponse
from app.exceptions import OpenSkyAPIException
from app.utils.decorators import retry_with_backoff, singleton

logger = logging.getLogger(__name__)
settings = get_settings()


@singleton
class OpenSkyClient:
    """
    Client for OpenSky Network API with OAuth2 Client Credentials authentication.
    Implements rate limiting and retry logic.
    """
    
    def __init__(self):
        self.client_id = settings.OPENSKY_CLIENT_ID
        self.client_secret = settings.OPENSKY_CLIENT_SECRET
        self.token_url = settings.OPENSKY_TOKEN_URL
        self.api_base_url = settings.OPENSKY_API_BASE_URL
        
        self._http_client: Optional[httpx.AsyncClient] = None
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        self._rate_limit_remaining: Optional[int] = None
        self._rate_limit_reset_at: Optional[datetime] = None
    
    async def __aenter__(self):
        """Initialize HTTP client on context enter"""
        self._http_client = httpx.AsyncClient(timeout=30.0)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Close HTTP client on context exit"""
        if self._http_client:
            await self._http_client.aclose()
    
    async def _get_access_token(self) -> str:
        """Get OAuth2 access token using Client Credentials flow"""
        # Return cached token if still valid
        if self._access_token and self._token_expires_at:
            if datetime.utcnow() < self._token_expires_at - timedelta(minutes=5):
                return self._access_token
        
        logger.info("Requesting new OAuth2 access token from OpenSky")
        
        try:
            response = await self._http_client.post(
                self.token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code != 200:
                logger.error(f"OAuth2 token request failed: {response.status_code} - {response.text}")
                raise OpenSkyAPIException(f"Failed to obtain access token: {response.status_code}")
            
            token_data = response.json()
            self._access_token = token_data["access_token"]
            expires_in = token_data.get("expires_in", 3600)
            self._token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            
            logger.info(f"OAuth2 token obtained, expires in {expires_in}s")
            return self._access_token
            
        except Exception as e:
            logger.error(f"Error obtaining OAuth2 token: {e}")
            raise OpenSkyAPIException(f"OAuth2 authentication failed: {e}")
    
    def _get_auth_status(self) -> str:
        """Get authentication status for logging"""
        if self.client_id and self.client_secret:
            return f"authenticated as {self.client_id}"
        return "anonymous (rate limited)"
    
    def _update_rate_limit_info(self, headers: Dict[str, str]):
        """Extract and update rate limit information from response headers"""
        try:
            if "x-rate-limit-remaining" in headers:
                self._rate_limit_remaining = int(headers["x-rate-limit-remaining"])
                
                if self._rate_limit_remaining < 100:
                    logger.warning(
                        f"OpenSky API rate limit low: {self._rate_limit_remaining} credits remaining"
                    )
            
            if "x-rate-limit-retry-after-seconds" in headers:
                retry_after = int(headers["x-rate-limit-retry-after-seconds"])
                self._rate_limit_reset_at = datetime.utcnow() + timedelta(seconds=retry_after)
                
        except (ValueError, KeyError) as e:
            logger.debug(f"Could not parse rate limit headers: {e}")
    
    @retry_with_backoff(max_retries=3, initial_delay=2.0)
    async def _make_authenticated_request(
        self,
        endpoint: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        Make authenticated HTTP request to OpenSky API with OAuth2.
        
        Args:
            endpoint: API endpoint path (e.g., "/flights/arrival")
            params: Query parameters
        
        Returns:
            JSON response as dictionary
        
        Raises:
            OpenSkyAPIException: If request fails
        """
        url = f"{self.api_base_url}{endpoint}"
        
        # Get access token
        access_token = await self._get_access_token()
        
        try:
            logger.debug(f"Making request to {endpoint}", extra={"params": params})
            
            response = await self._http_client.get(
                url,
                params=params or {},
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            # Update rate limit info
            self._update_rate_limit_info(response.headers)
            
            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get("x-rate-limit-retry-after-seconds", 60))
                logger.error(f"Rate limit exceeded. Retry after {retry_after}s")
                raise OpenSkyAPIException(f"Rate limit exceeded. Retry after {retry_after}s")
            
            # Handle authentication errors
            if response.status_code == 401:
                logger.error("Authentication failed. Check your OpenSky username/password")
                raise OpenSkyAPIException("Authentication failed")
            
            response.raise_for_status()
            
            return response.json()
            
        except httpx.HTTPStatusError as e:
            logger.error(
                f"HTTP error on {endpoint}: {e.response.status_code}",
                extra={"response": e.response.text}
            )
            raise OpenSkyAPIException(f"API request failed: {e.response.text}")
        except Exception as e:
            logger.error(f"Error making request to {endpoint}: {str(e)}")
            raise OpenSkyAPIException(f"Request error: {str(e)}")
    
    async def get_arrivals(
        self,
        airport_icao: str,
        begin: int,
        end: int
    ) -> List[FlightData]:
        """
        Get flights arriving at specified airport in time interval.
        
        Args:
            airport_icao: ICAO code of the airport (e.g., "DXXX")
            begin: Start of time interval (Unix timestamp)
            end: End of time interval (Unix timestamp)
        
        Returns:
            List of FlightData objects
        
        Raises:
            OpenSkyAPIException: If API request fails
        """
        logger.info(
            f"Fetching arrivals for {airport_icao}",
            extra={"begin": begin, "end": end}
        )
        
        params = {
            "airport": airport_icao.upper(),
            "begin": begin,
            "end": end
        }
        
        try:
            data = await self._make_authenticated_request("/flights/arrival", params)
            
            if not data:
                logger.info(f"No arrivals found for {airport_icao}")
                return []
            
            flights = [FlightData(**flight) for flight in data]
            logger.info(f"Retrieved {len(flights)} arrivals for {airport_icao}")
            
            return flights
            
        except Exception as e:
            logger.error(f"Failed to fetch arrivals: {str(e)}")
            raise
    
    async def get_departures(
        self,
        airport_icao: str,
        begin: int,
        end: int
    ) -> List[FlightData]:
        """
        Get flights departing from specified airport in time interval.
        
        Args:
            airport_icao: ICAO code of the airport (e.g., "DXXX")
            begin: Start of time interval (Unix timestamp)
            end: End of time interval (Unix timestamp)
        
        Returns:
            List of FlightData objects
        
        Raises:
            OpenSkyAPIException: If API request fails
        """
        logger.info(
            f"Fetching departures for {airport_icao}",
            extra={"begin": begin, "end": end}
        )
        
        params = {
            "airport": airport_icao.upper(),
            "begin": begin,
            "end": end
        }
        
        try:
            data = await self._make_authenticated_request("/flights/departure", params)
            
            if not data:
                logger.info(f"No departures found for {airport_icao}")
                return []
            
            flights = [FlightData(**flight) for flight in data]
            logger.info(f"Retrieved {len(flights)} departures for {airport_icao}")
            
            return flights
            
        except Exception as e:
            logger.error(f"Failed to fetch departures: {str(e)}")
            raise
    
    async def get_states_in_area(
        self,
        lamin: float,
        lamax: float,
        lomin: float,
        lomax: float
    ) -> List[Dict]:
        """
        Get real-time state vectors for aircraft in a bounding box.
        This is the ONLY way to get real-time flight data from OpenSky.
        
        /flights/arrival and /flights/departure only return historical data 
        from previous days (batch processed at night).
        
        Args:
            lamin: Lower bound latitude (decimal degrees)
            lamax: Upper bound latitude (decimal degrees)
            lomin: Lower bound longitude (decimal degrees)
            lomax: Upper bound longitude (decimal degrees)
        
        Returns:
            List of state vectors (aircraft currently in the area)
        """
        logger.info(
            f"Fetching real-time states in area",
            extra={"lamin": lamin, "lamax": lamax, "lomin": lomin, "lomax": lomax}
        )
        
        params = {
            "lamin": lamin,
            "lamax": lamax,
            "lomin": lomin,
            "lomax": lomax,
            "extended": 1  # Get aircraft category
        }
        
        try:
            data = await self._make_authenticated_request("/states/all", params)
            
            if not data or not data.get("states"):
                logger.info("No aircraft found in area")
                return []
            
            states = data["states"]
            logger.info(f"Retrieved {len(states)} aircraft in area")
            
            return states
            
        except Exception as e:
            logger.error(f"Failed to fetch states: {str(e)}")
            raise
    
    def parse_state_vector(self, state: List) -> Optional["StateVectorData"]:
        """
        Parse raw OpenSky state vector into StateVectorData schema.
        
        State vector structure (17+ elements):
        [0]  icao24 (str)
        [1]  callsign (str)
        [2]  origin_country (str)
        [3]  time_position (int, Unix timestamp)
        [4]  last_contact (int, Unix timestamp)
        [5]  longitude (float, degrees)
        [6]  latitude (float, degrees)
        [7]  baro_altitude (float, meters)
        [8]  on_ground (bool)
        [9]  velocity (float, m/s)
        [10] true_track (float, degrees) - heading
        [11] vertical_rate (float, m/s)
        [12] sensors (array)
        [13] geo_altitude (float, meters)
        [14] squawk (str)
        [15] spi (bool)
        [16] position_source (int)
        [17] category (int) - if extended=1
        
        Args:
            state: Raw state vector list from OpenSky API
        
        Returns:
            StateVectorData object or None if parsing fails
        """
        from app.schemas.opensky import StateVectorData
        
        try:
            if not state or len(state) < 12:
                return None
            
            return StateVectorData(
                icao24=state[0],
                callsign=state[1],
                origin_country=state[2],
                time_position=state[3],
                last_contact=state[4],
                longitude=state[5],
                latitude=state[6],
                baro_altitude=state[7],
                on_ground=state[8],
                velocity=state[9],
                heading=state[10],  # true_track
                vertical_rate=state[11],
                geo_altitude=state[13] if len(state) > 13 else None,
                squawk=state[14] if len(state) > 14 else None,
                category=state[17] if len(state) > 17 else None
            )
        except (IndexError, TypeError, ValueError) as e:
            logger.warning(f"Failed to parse state vector: {str(e)}")
            return None
    
    def parse_state_vectors(self, states: List[List]) -> List["StateVectorData"]:
        """
        Parse multiple raw state vectors into StateVectorData objects.
        
        Args:
            states: List of raw state vector arrays from OpenSky API
        
        Returns:
            List of successfully parsed StateVectorData objects
        """
        from app.schemas.opensky import StateVectorData
        
        parsed = []
        for state in states:
            state_data = self.parse_state_vector(state)
            if state_data:
                parsed.append(state_data)
        
        logger.info(f"Parsed {len(parsed)}/{len(states)} state vectors")
        return parsed
    
    async def get_arrivals_and_departures(
        self,
        airport_icao: str,
        begin: int,
        end: int,
        exclude_military: bool = True
    ) -> OpenSkyResponse:
        """
        Get both arrivals and departures for specified airport.
        
        IMPORTANT: /flights/arrival and /flights/departure only return 
        historical data from the previous day or earlier (batch processed).
        For real-time data, use get_states_in_area() instead.
        
        Args:
            airport_icao: ICAO code of the airport
            begin: Start of time interval (Unix timestamp)
            end: End of time interval (Unix timestamp)
            exclude_military: If True, filter out military aircraft
        
        Returns:
            OpenSkyResponse with combined flights
        """
        arrivals = await self.get_arrivals(airport_icao, begin, end)
        departures = await self.get_departures(airport_icao, begin, end)
        
        all_flights = arrivals + departures
        
        # Filter military if requested
        if exclude_military:
            all_flights = [f for f in all_flights if not f.is_military()]
            logger.info(f"Filtered out military aircraft, {len(all_flights)} civilian flights remaining")
        
        return OpenSkyResponse(
            flights=all_flights,
            total_count=len(all_flights)
        )
    
    def get_rate_limit_status(self) -> Dict:
        """Get current rate limit status"""
        return {
            "credits_remaining": self._rate_limit_remaining,
            "reset_at": self._rate_limit_reset_at.isoformat() if self._rate_limit_reset_at else None,
            "token_expires_at": self._token_expires_at.isoformat() if self._token_expires_at else None
        }
