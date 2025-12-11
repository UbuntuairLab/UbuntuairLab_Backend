from typing import Optional, List
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from app.models.prediction import AIPrediction, ModelType


class PredictionRepository:
    """Repository for AIPrediction model operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(
        self,
        flight_icao24: str,
        model_type: ModelType,
        input_data: dict,
        output_data: dict,
        model_version: str = "1.0.0",
        execution_time_ms: Optional[int] = None,
        cached: bool = False
    ) -> AIPrediction:
        """Create new AI prediction record"""
        prediction = AIPrediction(
            flight_icao24=flight_icao24,
            model_type=model_type,
            model_version=model_version,
            input_data=input_data,
            output_data=output_data,
            execution_time_ms=execution_time_ms,
            cached=cached
        )
        self.db.add(prediction)
        await self.db.commit()
        await self.db.refresh(prediction)
        return prediction
    
    async def get_by_id(self, prediction_id: int) -> Optional[AIPrediction]:
        """Get prediction by ID"""
        result = await self.db.execute(
            select(AIPrediction).where(AIPrediction.prediction_id == prediction_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_flight(
        self,
        flight_icao24: str,
        model_type: Optional[ModelType] = None
    ) -> List[AIPrediction]:
        """Get all predictions for a flight"""
        query = select(AIPrediction).where(AIPrediction.flight_icao24 == flight_icao24)
        
        if model_type:
            query = query.where(AIPrediction.model_type == model_type)
        
        query = query.order_by(AIPrediction.created_at.desc())
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_latest_by_flight_and_model(
        self,
        flight_icao24: str,
        model_type: ModelType
    ) -> Optional[AIPrediction]:
        """Get most recent prediction for flight and model type"""
        result = await self.db.execute(
            select(AIPrediction)
            .where(
                and_(
                    AIPrediction.flight_icao24 == flight_icao24,
                    AIPrediction.model_type == model_type.value  # Use .value for enum comparison
                )
            )
            .order_by(AIPrediction.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
    
    async def get_by_model_type(
        self,
        model_type: ModelType,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[AIPrediction]:
        """Get predictions by model type in time range"""
        query = select(AIPrediction).where(AIPrediction.model_type == model_type)
        
        if start_time:
            query = query.where(AIPrediction.created_at >= start_time)
        if end_time:
            query = query.where(AIPrediction.created_at <= end_time)
        
        query = query.order_by(AIPrediction.created_at.desc())
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_cache_statistics(
        self,
        model_type: Optional[ModelType] = None,
        start_time: Optional[datetime] = None
    ) -> dict:
        """Get cache hit/miss statistics"""
        query = select(AIPrediction)
        
        if model_type:
            query = query.where(AIPrediction.model_type == model_type)
        if start_time:
            query = query.where(AIPrediction.created_at >= start_time)
        
        result = await self.db.execute(query)
        predictions = list(result.scalars().all())
        
        total = len(predictions)
        cached = sum(1 for p in predictions if p.from_cache == 1)
        
        return {
            "total_predictions": total,
            "cache_hits": cached,
            "cache_misses": total - cached,
            "cache_hit_rate": (cached / total * 100) if total > 0 else 0
        }
    
    async def get_performance_metrics(
        self,
        model_type: ModelType,
        start_time: Optional[datetime] = None
    ) -> dict:
        """Get performance metrics for model"""
        query = select(AIPrediction).where(AIPrediction.model_type == model_type)
        
        if start_time:
            query = query.where(AIPrediction.created_at >= start_time)
        
        result = await self.db.execute(query)
        predictions = list(result.scalars().all())
        
        if not predictions:
            return {
                "model_type": model_type.value,
                "total_predictions": 0,
                "avg_latency_ms": 0,
                "avg_confidence": 0
            }
        
        latencies = [p.prediction_time_ms for p in predictions if p.prediction_time_ms]
        confidences = [p.confidence_score for p in predictions if p.confidence_score]
        
        return {
            "model_type": model_type.value,
            "total_predictions": len(predictions),
            "avg_latency_ms": sum(latencies) / len(latencies) if latencies else 0,
            "avg_confidence": sum(confidences) / len(confidences) if confidences else 0
        }
    
    async def delete_old_predictions(self, cutoff_date: datetime) -> int:
        """Delete predictions older than cutoff date"""
        result = await self.db.execute(
            select(AIPrediction).where(AIPrediction.created_at < cutoff_date)
        )
        predictions = result.scalars().all()
        
        for prediction in predictions:
            await self.db.delete(prediction)
        
        await self.db.commit()
        return len(predictions)
