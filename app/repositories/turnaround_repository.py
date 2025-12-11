from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.turnaround import AircraftTurnaroundRule


class TurnaroundRepository:
    """Repository for AircraftTurnaroundRule model operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_aircraft_type(self, aircraft_type: str) -> Optional[AircraftTurnaroundRule]:
        """Get turnaround rule by aircraft type"""
        # Try exact match first
        result = await self.db.execute(
            select(AircraftTurnaroundRule).where(
                AircraftTurnaroundRule.aircraft_type == aircraft_type.upper()
            )
        )
        rule = result.scalar_one_or_none()
        
        # Fall back to DEFAULT if no match
        if not rule:
            result = await self.db.execute(
                select(AircraftTurnaroundRule).where(
                    AircraftTurnaroundRule.aircraft_type == "DEFAULT"
                )
            )
            rule = result.scalar_one_or_none()
        
        return rule
    
    async def get_default(self) -> Optional[AircraftTurnaroundRule]:
        """Get default turnaround rule"""
        result = await self.db.execute(
            select(AircraftTurnaroundRule).where(
                AircraftTurnaroundRule.aircraft_type == "DEFAULT"
            )
        )
        return result.scalar_one_or_none()
