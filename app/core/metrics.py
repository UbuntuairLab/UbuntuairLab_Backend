"""
Prometheus metrics instrumentation.
Adds custom metrics for monitoring API and business logic.
"""
from prometheus_client import Counter, Histogram, Gauge, Info
import time
from functools import wraps
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

# API Metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint']
)

http_requests_in_progress = Gauge(
    'http_requests_in_progress',
    'HTTP requests currently in progress',
    ['method', 'endpoint']
)

# OpenSky API Metrics
opensky_requests_total = Counter(
    'opensky_requests_total',
    'Total requests to OpenSky API',
    ['endpoint', 'status']
)

opensky_rate_limit_remaining = Gauge(
    'opensky_rate_limit_remaining',
    'OpenSky API rate limit remaining credits'
)

# AI Model Metrics
ai_predictions_total = Counter(
    'ai_predictions_total',
    'Total AI model predictions',
    ['model_type', 'cached']
)

ai_prediction_duration_seconds = Histogram(
    'ai_prediction_duration_seconds',
    'AI prediction latency',
    ['model_type']
)

ai_model_errors_total = Counter(
    'ai_model_errors_total',
    'Total AI model errors',
    ['model_type', 'error_type']
)

# Flight Sync Metrics
flight_sync_total = Counter(
    'flight_sync_total',
    'Total flight synchronizations',
    ['status']
)

flight_sync_duration_seconds = Histogram(
    'flight_sync_duration_seconds',
    'Flight sync duration'
)

flights_processed_total = Counter(
    'flights_processed_total',
    'Total flights processed',
    ['flight_type', 'status']
)

# Parking Metrics
parking_spots_total = Gauge(
    'parking_spots_total',
    'Total parking spots',
    ['spot_type']
)

parking_spots_available = Gauge(
    'parking_spots_available',
    'Available parking spots',
    ['spot_type']
)

parking_allocations_total = Counter(
    'parking_allocations_total',
    'Total parking allocations',
    ['spot_type', 'overflow']
)

# Application Info
app_info = Info('ubuntuairlab_backend', 'Application information')
app_info.info({
    'version': '1.0.0',
    'name': 'UbuntuAirLab Backend'
})


class PrometheusMiddleware(BaseHTTPMiddleware):
    """
    Middleware to collect HTTP metrics.
    """
    
    async def dispatch(self, request: Request, call_next):
        method = request.method
        endpoint = request.url.path
        
        # Track in-progress requests
        http_requests_in_progress.labels(method=method, endpoint=endpoint).inc()
        
        # Time request
        start_time = time.time()
        
        try:
            response = await call_next(request)
            status = response.status_code
            
            # Record metrics
            http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status=status
            ).inc()
            
            duration = time.time() - start_time
            http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)
            
            return response
            
        finally:
            http_requests_in_progress.labels(method=method, endpoint=endpoint).dec()


def track_ai_prediction(model_type: str):
    """
    Decorator to track AI prediction metrics.
    
    Usage:
        @track_ai_prediction("eta")
        async def predict_eta(...):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            cached = kwargs.get('use_cache', False)
            
            try:
                result = await func(*args, **kwargs)
                
                # Record success
                ai_predictions_total.labels(
                    model_type=model_type,
                    cached=str(cached)
                ).inc()
                
                duration = time.time() - start_time
                ai_prediction_duration_seconds.labels(
                    model_type=model_type
                ).observe(duration)
                
                return result
                
            except Exception as e:
                # Record error
                ai_model_errors_total.labels(
                    model_type=model_type,
                    error_type=type(e).__name__
                ).inc()
                raise
                
        return wrapper
    return decorator


def track_flight_sync():
    """
    Decorator to track flight sync metrics.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                
                # Record success
                flight_sync_total.labels(status="success").inc()
                
                duration = time.time() - start_time
                flight_sync_duration_seconds.observe(duration)
                
                # Track processed flights
                if isinstance(result, dict):
                    successful = result.get('successful', 0)
                    failed = result.get('failed', 0)
                    
                    if successful > 0:
                        flights_processed_total.labels(
                            flight_type="all",
                            status="success"
                        ).inc(successful)
                    
                    if failed > 0:
                        flights_processed_total.labels(
                            flight_type="all",
                            status="failed"
                        ).inc(failed)
                
                return result
                
            except Exception as e:
                flight_sync_total.labels(status="error").inc()
                raise
                
        return wrapper
    return decorator
