from pydantic_settings import BaseSettings
from typing import Optional, List
from functools import lru_cache


class Settings(BaseSettings):
    """
    Application configuration settings.
    All settings can be overridden via environment variables.
    """
    
    # OpenSky Network API Configuration
    # Now uses OAuth2 Client Credentials Flow
    OPENSKY_CLIENT_ID: str = "assounrodrigue5@gmail.com-api-client"
    OPENSKY_CLIENT_SECRET: str = "2vH1YKD4Rzg5uNF879E0Da9jPmfMKHiN"
    OPENSKY_TOKEN_URL: str = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"
    OPENSKY_API_BASE_URL: str = "https://opensky-network.org/api"
    
    # AviationStack API Configuration
    # For real-time, historical (3 months), and future flights (> 7 days)
    AVIATIONSTACK_ACCESS_KEY: str = "6aa0ce63b4dd360da28df1903268126b"
    AVIATIONSTACK_API_BASE_URL: str = "https://api.aviationstack.com/v1"
    
    # Airport Configuration
    AIRPORT_ICAO: str = "DXXX"  # Lomé-Tokoin (ICAO)
    AIRPORT_IATA: str = "LFW"   # Lomé-Tokoin (IATA)
    AIRPORT_NAME: str = "Gnassingbe Eyadema International Airport"
    
    # Synchronization Settings
    SYNC_INTERVAL_MINUTES: int = 5
    SYNC_LOOKBACK_HOURS: int = 2
    
    # AI Models Configuration
    USE_MOCK_AI: bool = True
    
    # ML API (Hugging Face Space: TAGBA/ubuntuairlab)
    ML_API_BASE_URL: str = "https://tagba-ubuntuairlab.hf.space"
    ML_API_TIMEOUT: float = 30.0
    ML_API_MAX_RETRIES: int = 3
    
    # Legacy model endpoints (deprecated, use ML API)
    MODEL_ETA_ENDPOINT: str = "http://localhost:8001/api/v1/model/eta/predict"
    MODEL_OCCUPATION_ENDPOINT: str = "http://localhost:8001/api/v1/model/occupation/predict"
    MODEL_CONFLIT_ENDPOINT: str = "http://localhost:8001/api/v1/model/conflit/predict"
    MODEL_API_KEY: Optional[str] = None
    MODEL_TIMEOUT_SECONDS: int = 30
    MODEL_MAX_RETRIES: int = 3
    
    # Database Configuration
    DATABASE_URL: str = "postgresql+asyncpg://airport_user:airport_pass@localhost:5432/airport_db"
    DATABASE_ECHO: bool = False
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    
    # Redis Cache Configuration
    REDIS_URL: str = "redis://localhost:6379/0"
    ENABLE_PREDICTION_CACHE: bool = True
    CACHE_TTL_SECONDS: int = 300
    
    # JWT Authentication
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 60
    
    # API Configuration
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    
    # Logging Configuration
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    # Monitoring Configuration
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 9090
    
    # Rate Limiting Configuration
    ENABLE_RATE_LIMIT: bool = True
    RATE_LIMIT_PER_MINUTE: int = 100
    
    # Debug
    DEBUG: bool = False
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached application settings.
    This function is cached to avoid reading .env file multiple times.
    """
    return Settings()


# Global settings instance
settings = get_settings()
