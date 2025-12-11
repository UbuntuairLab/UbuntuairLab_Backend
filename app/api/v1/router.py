"""
API v1 main router.
Aggregates all API endpoint routers.
"""
from fastapi import APIRouter
from app.api.v1.endpoints import flights, parking, predictions, sync, auth, notifications, dashboard

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(flights.router, prefix="/flights", tags=["Flights"])
api_router.include_router(parking.router, prefix="/parking", tags=["Parking"])
api_router.include_router(predictions.router, prefix="/predictions", tags=["AI Predictions"])
api_router.include_router(sync.router, prefix="/sync", tags=["Synchronization"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
