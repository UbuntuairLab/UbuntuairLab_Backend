"""
Main FastAPI application entry point.
Initializes the API, database, scheduler, and monitoring.
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.core.metrics import PrometheusMiddleware
from app.database import init_db, close_db
from app.api.v1.router import api_router
from app.services.orchestration.scheduler import FlightSyncScheduler

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)
settings = get_settings()

# Global scheduler instance
scheduler: FlightSyncScheduler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    global scheduler
    
    logger.info("Starting UbuntuAirLab Backend...")
    
    # Create database tables if needed
    logger.info("Initializing database...")
    await init_db()
    
    # Initialize and start scheduler
    logger.info("Starting flight sync scheduler...")
    scheduler = FlightSyncScheduler()
    await scheduler.start()
    
    logger.info("Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    if scheduler:
        await scheduler.stop()
    logger.info("Application shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="UbuntuAirLab Backend API",
    description="API backend pour gestion aeroportuaire avec IA",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus metrics middleware
if settings.ENABLE_METRICS:
    app.add_middleware(PrometheusMiddleware)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)

# Prometheus metrics endpoint
if settings.ENABLE_METRICS:
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "UbuntuAirLab Backend API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "scheduler": hasattr(scheduler, 'scheduler') and scheduler.scheduler.running if scheduler else False,
        "next_sync": scheduler.get_next_run_time() if scheduler else None
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.LOG_LEVEL.lower()
    )
