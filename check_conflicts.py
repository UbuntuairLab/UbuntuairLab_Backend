import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def check():
    engine = create_async_engine('postgresql+asyncpg://airport_user:airport_pass@localhost:5433/airport_db')
    async with engine.connect() as conn:
        # Check total allocations
        result = await conn.execute(text('SELECT COUNT(*) FROM parking_allocations'))
        total = result.scalar()
        print(f'\n📊 Total allocations: {total}')
        
        # Check allocations with conflicts
        result = await conn.execute(text('SELECT COUNT(*) FROM parking_allocations WHERE conflict_detected = true'))
        conflicts = result.scalar()
        print(f'⚠️  Allocations avec conflict_detected=true: {conflicts}')
        
        # Show recent allocations
        result = await conn.execute(text('''
            SELECT allocation_id, flight_icao24, spot_id, conflict_detected, conflict_probability, overflow_to_military
            FROM parking_allocations 
            ORDER BY allocated_at DESC 
            LIMIT 10
        '''))
        rows = result.fetchall()
        print(f'\n📋 10 dernières allocations:')
        for row in rows:
            print(f'  ID={row[0]}, Flight={row[1]}, Spot={row[2]}, Conflict={row[3]}, Prob={row[4]}, Military={row[5]}')
    
    await engine.dispose()

asyncio.run(check())
