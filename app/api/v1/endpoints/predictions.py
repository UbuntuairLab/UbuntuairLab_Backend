"""
AI Predictions endpoints.
Access historical predictions and request new predictions.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.repositories.prediction_repository import PredictionRepository
from app.services.ai_models.factory import AIModelFactory
from app.schemas.ai_models import ETAETDInput, OccupationInput, ConflitInput
from app.api.v1.endpoints.auth import get_current_active_user

router = APIRouter()


@router.post("/eta")
async def predict_eta(
    input_data: ETAETDInput,
    current_user = Depends(get_current_active_user)
):
    """
    Request ETA/ETD prediction from AI model.
    Requires authentication.
    """
    factory = AIModelFactory()
    await factory.initialize()
    
    try:
        eta_model = factory.get_eta_model()
        
        async with eta_model:
            prediction = await eta_model.predict(input_data, use_cache=True)
        
        return {
            "input": input_data.dict(),
            "prediction": prediction.dict(),
            "model_type": "eta",
            "cached": True
        }
    finally:
        await factory.shutdown()


@router.post("/occupation")
async def predict_occupation(
    input_data: OccupationInput,
    current_user = Depends(get_current_active_user)
):
    """
    Request parking occupation duration prediction.
    Requires authentication.
    """
    factory = AIModelFactory()
    await factory.initialize()
    
    try:
        occupation_model = factory.get_occupation_model()
        
        async with occupation_model:
            prediction = await occupation_model.predict(input_data, use_cache=True)
        
        return {
            "input": input_data.dict(),
            "prediction": prediction.dict(),
            "model_type": "occupation",
            "cached": True
        }
    finally:
        await factory.shutdown()


@router.post("/conflit")
async def predict_conflit(
    input_data: ConflitInput,
    current_user = Depends(get_current_active_user)
):
    """
    Request conflict detection prediction.
    Requires authentication.
    """
    factory = AIModelFactory()
    await factory.initialize()
    
    try:
        conflit_model = factory.get_conflit_model()
        
        async with conflit_model:
            prediction = await conflit_model.predict(input_data, use_cache=True)
        
        return {
            "input": input_data.dict(),
            "prediction": prediction.dict(),
            "model_type": "conflit",
            "cached": True
        }
    finally:
        await factory.shutdown()


@router.get("/history/{flight_icao24}")
async def get_prediction_history(
    flight_icao24: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Get prediction history for a flight.
    Requires authentication.
    """
    prediction_repo = PredictionRepository(db)
    predictions = await prediction_repo.get_by_flight(flight_icao24)
    
    if not predictions:
        raise HTTPException(status_code=404, detail="No predictions found for this flight")
    
    return {
        "flight_icao24": flight_icao24,
        "predictions": predictions
    }


@router.get("/models/health")
async def check_models_health(
    current_user = Depends(get_current_active_user)
):
    """
    Check health status of all AI models.
    Requires authentication.
    """
    factory = AIModelFactory()
    await factory.initialize()
    
    try:
        health = await factory.health_check_all()
        return health
    finally:
        await factory.shutdown()
