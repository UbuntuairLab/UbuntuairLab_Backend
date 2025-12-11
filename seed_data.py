"""
Seed database with test data
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import get_settings
from app.models.flight import Flight, FlightType, FlightStatus
from app.models.parking import ParkingSpot, SpotType, SpotStatus, AircraftSizeCategory
from app.models.user import User
import bcrypt
from datetime import datetime

settings = get_settings()

async def seed_database():
    """Seed database with test data"""
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        print("🌱 Seeding database...")
        
        # 1. Create parking spots (CIVIL only)
        print("\n📍 Creating parking spots...")
        parking_spots = [
            ParkingSpot(
                spot_id="C01",
                spot_number=1,
                spot_type=SpotType.CIVIL,
                status=SpotStatus.AVAILABLE,
                aircraft_size_capacity=AircraftSizeCategory.LARGE,
                has_jetway=True,
                distance_to_terminal=50,
                notes="Near terminal entrance"
            ),
            ParkingSpot(
                spot_id="C02",
                spot_number=2,
                spot_type=SpotType.CIVIL,
                status=SpotStatus.AVAILABLE,
                aircraft_size_capacity=AircraftSizeCategory.LARGE,
                has_jetway=True,
                distance_to_terminal=60
            ),
            ParkingSpot(
                spot_id="C03",
                spot_number=3,
                spot_type=SpotType.CIVIL,
                status=SpotStatus.OCCUPIED,
                aircraft_size_capacity=AircraftSizeCategory.MEDIUM,
                has_jetway=False,
                distance_to_terminal=100
            ),
            ParkingSpot(
                spot_id="C04",
                spot_number=4,
                spot_type=SpotType.CIVIL,
                status=SpotStatus.AVAILABLE,
                aircraft_size_capacity=AircraftSizeCategory.SMALL,
                has_jetway=False,
                distance_to_terminal=150
            ),
            ParkingSpot(
                spot_id="C05",
                spot_number=5,
                spot_type=SpotType.CIVIL,
                status=SpotStatus.MAINTENANCE,
                aircraft_size_capacity=AircraftSizeCategory.MEDIUM,
                has_jetway=True,
                distance_to_terminal=75,
                notes="Under maintenance until next week"
            ),
        ]
        
        for spot in parking_spots:
            session.add(spot)
        
        # 2. Create test flights
        print("\n✈️  Creating test flights...")
        now_timestamp = int(datetime.now(datetime.UTC if hasattr(datetime, 'UTC') else None).timestamp())
        
        flights = [
            Flight(
                icao24="3c6444",
                callsign="RAM512",
                origin_country="Morocco",
                flight_type=FlightType.ARRIVAL,
                status=FlightStatus.ACTIVE,
                departure_airport="GMMN",
                arrival_airport="DXXX",
                first_seen=now_timestamp - 3600,
                last_seen=now_timestamp
            ),
            Flight(
                icao24="0200af",
                callsign="ETH500",
                origin_country="Ethiopia",
                flight_type=FlightType.ARRIVAL,
                status=FlightStatus.SCHEDULED,
                departure_airport="HAAB",
                arrival_airport="DXXX",
                first_seen=now_timestamp - 1800,
                last_seen=now_timestamp
            ),
            Flight(
                icao24="aabb99",
                callsign="AFR578",
                origin_country="France",
                flight_type=FlightType.DEPARTURE,
                status=FlightStatus.ACTIVE,
                departure_airport="DXXX",
                arrival_airport="LFPG",
                first_seen=now_timestamp - 7200,
                last_seen=now_timestamp - 600
            ),
            Flight(
                icao24="44aa33",
                callsign="UAE421",
                origin_country="United Arab Emirates",
                flight_type=FlightType.DEPARTURE,
                status=FlightStatus.COMPLETED,
                departure_airport="OMDB",
                arrival_airport="DXXX",
                first_seen=now_timestamp - 14400,
                last_seen=now_timestamp - 7200
            ),
        ]
        
        for flight in flights:
            session.add(flight)
        
        await session.commit()
        print("\n✅ Database seeded successfully!")
        print("\n📊 Summary:")
        print(f"   - {len(parking_spots)} parking spots created")
        print(f"   - {len(flights)} flights created")
        print("\n🔑 Test data:")
        print("   Flights ICAO24: 3c6444, 0200af, aabb99, 44aa33")
        print("   Parking spots: C01, C02, C03, C04, C05")

if __name__ == "__main__":
    asyncio.run(seed_database())
