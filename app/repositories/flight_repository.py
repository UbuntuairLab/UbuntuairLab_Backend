from typing import Optional, List
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from app.models.flight import Flight, FlightStatus, FlightType
from app.schemas.opensky import FlightData


class FlightRepository:
    """Repository for Flight model operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, flight_data: FlightData) -> Flight:
        """Create new flight record"""
        flight = Flight(
            icao24=flight_data.icao24,
            callsign=flight_data.callsign,
            origin_country=flight_data.estDepartureAirport or flight_data.estArrivalAirport,
            flight_type=FlightType.ARRIVAL if flight_data.estArrivalAirport else FlightType.DEPARTURE,
            departure_airport=flight_data.estDepartureAirport,
            arrival_airport=flight_data.estArrivalAirport,
            first_seen=flight_data.firstSeen,
            last_seen=flight_data.lastSeen,
            status=FlightStatus.SCHEDULED
        )
        self.db.add(flight)
        await self.db.commit()
        await self.db.refresh(flight)
        return flight
    
    async def get_by_icao24(self, icao24: str) -> Optional[Flight]:
        """Get flight by ICAO24 address"""
        result = await self.db.execute(
            select(Flight).where(Flight.icao24 == icao24)
        )
        return result.scalar_one_or_none()
    
    async def get_active_flights(self, flight_type: Optional[FlightType] = None) -> List[Flight]:
        """Get all active (non-completed) flights"""
        query = select(Flight).where(Flight.status.in_(["scheduled", "active"]))
        
        if flight_type:
            query = query.where(Flight.flight_type == flight_type)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def list_flights(
        self,
        skip: int = 0,
        limit: int = 50,
        flight_type: Optional[str] = None,
        status: Optional[str] = None
    ) -> tuple[List[Flight], int]:
        """List flights with pagination and filters"""
        from sqlalchemy import func, cast, String
        
        query = select(Flight)
        
        # Apply filters - cast to string to avoid enum comparison
        if flight_type:
            query = query.where(cast(Flight.flight_type, String) == flight_type.lower())
        if status:
            query = query.where(cast(Flight.status, String) == status.lower())
        
        # Get total count
        count_query = select(func.count()).select_from(Flight)
        if flight_type:
            count_query = count_query.where(cast(Flight.flight_type, String) == flight_type.lower())
        if status:
            count_query = count_query.where(cast(Flight.status, String) == status.lower())
        
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        
        # Apply pagination
        query = query.offset(skip).limit(limit).order_by(Flight.first_seen.desc())
        
        result = await self.db.execute(query)
        flights = list(result.scalars().all())
        
        return flights, total
    
    async def update_predictions(
        self,
        icao24: str,
        predicted_eta: Optional[datetime] = None,
        predicted_etd: Optional[datetime] = None,
        predicted_delay_minutes: Optional[int] = None,
        predicted_occupation_minutes: Optional[int] = None
    ) -> Optional[Flight]:
        """Update flight with AI predictions"""
        flight = await self.get_by_icao24(icao24)
        if not flight:
            return None
        
        if predicted_eta:
            flight.predicted_eta = predicted_eta
        if predicted_etd:
            flight.predicted_etd = predicted_etd
        if predicted_delay_minutes is not None:
            flight.predicted_delay_minutes = predicted_delay_minutes
        if predicted_occupation_minutes is not None:
            flight.predicted_occupation_minutes = predicted_occupation_minutes
        
        flight.status = FlightStatus.ACTIVE
        await self.db.commit()
        await self.db.refresh(flight)
        return flight
    
    async def update_status(self, icao24: str, status: FlightStatus) -> Optional[Flight]:
        """Update flight status"""
        flight = await self.get_by_icao24(icao24)
        if not flight:
            return None
        
        flight.status = status
        await self.db.commit()
        await self.db.refresh(flight)
        return flight
    
    async def update_parking_assignment(
        self,
        icao24: str,
        parking_spot_id: Optional[str]
    ) -> Optional[Flight]:
        """Update flight parking spot assignment"""
        flight = await self.get_by_icao24(icao24)
        if not flight:
            return None
        
        flight.parking_spot_id = parking_spot_id
        await self.db.commit()
        await self.db.refresh(flight)
        return flight
    
    async def get_flights_by_airport(
        self,
        airport_icao: str,
        flight_type: FlightType,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None
    ) -> List[Flight]:
        """Get flights for specific airport in time range"""
        if flight_type == FlightType.ARRIVAL:
            query = select(Flight).where(Flight.arrival_airport == airport_icao)
        else:
            query = select(Flight).where(Flight.departure_airport == airport_icao)
        
        if start_time:
            query = query.where(Flight.first_seen >= start_time)
        if end_time:
            query = query.where(Flight.last_seen <= end_time)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def delete_old_flights(self, cutoff_timestamp: int) -> int:
        """Delete completed flights older than cutoff timestamp"""
        result = await self.db.execute(
            select(Flight).where(
                and_(
                    Flight.status == "completed",
                    Flight.last_seen < cutoff_timestamp
                )
            )
        )
        flights = result.scalars().all()
        
        for flight in flights:
            await self.db.delete(flight)
        
        await self.db.commit()
        return len(flights)
    
    async def get_by_callsign(self, callsign: str) -> List[Flight]:
        """Get flights by callsign"""
        result = await self.db.execute(
            select(Flight).where(Flight.callsign == callsign)
        )
        return list(result.scalars().all())
    
    async def upsert(self, flight_data: FlightData) -> Flight:
        """Create or update flight"""
        existing = await self.get_by_icao24(flight_data.icao24)
        
        if existing:
            # Update existing flight
            existing.callsign = flight_data.callsign
            existing.last_seen = flight_data.lastSeen
            await self.db.commit()
            await self.db.refresh(existing)
            return existing
        else:
            # Create new flight
            return await self.create(flight_data)
    
    async def update_realtime_position(
        self,
        icao24: str,
        state_vector: "StateVectorData"
    ) -> Optional[Flight]:
        """
        Update flight with real-time position data from OpenSky state vector.
        
        Args:
            icao24: Aircraft ICAO24 address
            state_vector: StateVectorData from OpenSky
        
        Returns:
            Updated Flight object or None if not found
        """
        flight = await self.get_by_icao24(icao24)
        
        if not flight:
            return None
        
        # Update real-time tracking fields
        flight.longitude = state_vector.longitude
        flight.latitude = state_vector.latitude
        flight.baro_altitude = state_vector.baro_altitude
        flight.geo_altitude = state_vector.geo_altitude
        flight.velocity = state_vector.velocity
        flight.heading = state_vector.heading
        flight.vertical_rate = state_vector.vertical_rate
        flight.on_ground = 1 if state_vector.on_ground else 0
        flight.last_position_update = datetime.fromtimestamp(state_vector.last_contact) if state_vector.last_contact else None
        
        await self.db.commit()
        await self.db.refresh(flight)
        
        return flight
    
    async def get_flights_needing_position_update(
        self,
        max_age_seconds: int = 300
    ) -> List[Flight]:
        """
        Get active flights that need position update (>5min since last update).
        
        Args:
            max_age_seconds: Maximum age of last position update (default 5min)
        
        Returns:
            List of flights needing update
        """
        from datetime import datetime, timedelta
        
        cutoff_time = datetime.utcnow() - timedelta(seconds=max_age_seconds)
        
        query = select(Flight).where(
            and_(
                Flight.status.in_(["scheduled", "active"]),
                or_(
                    Flight.last_position_update == None,
                    Flight.last_position_update < cutoff_time
                )
            )
        )
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
