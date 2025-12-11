import redis.asyncio as redis
import hashlib
import json
import logging
from typing import Optional, TypeVar, Type
from pydantic import BaseModel
from app.core.config import get_settings
from app.exceptions import CacheException

logger = logging.getLogger(__name__)
settings = get_settings()

T = TypeVar('T', bound=BaseModel)


class PredictionCache:
    """
    Redis-based cache for AI model predictions.
    Caches predictions with TTL to reduce redundant API calls.
    """
    
    def __init__(self):
        self.redis_url = settings.REDIS_URL
        self.ttl = settings.CACHE_TTL_SECONDS
        self.enabled = settings.ENABLE_PREDICTION_CACHE
        self._client: Optional[redis.Redis] = None
    
    async def connect(self):
        """Initialize Redis connection"""
        if not self.enabled:
            logger.info("Prediction cache disabled via configuration")
            return
        
        try:
            self._client = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            await self._client.ping()
            logger.info("Successfully connected to Redis cache")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            self._client = None
            # Don't raise exception - cache is optional
    
    async def disconnect(self):
        """Close Redis connection"""
        if self._client:
            await self._client.close()
            logger.info("Disconnected from Redis cache")
    
    def _generate_cache_key(self, model_name: str, input_data: BaseModel) -> str:
        """
        Generate unique cache key from model name and input data.
        Uses MD5 hash of sorted JSON to ensure consistent keys.
        
        Args:
            model_name: Name of the AI model (e.g., "eta", "occupation")
            input_data: Pydantic model with input parameters
        
        Returns:
            Cache key string
        """
        # Convert to JSON with sorted keys for consistency
        data_json = input_data.model_dump_json(exclude_none=True)
        data_hash = hashlib.md5(data_json.encode()).hexdigest()
        
        return f"prediction:{model_name}:{data_hash}"
    
    async def get(
        self,
        model_name: str,
        input_data: BaseModel,
        output_class: Type[T]
    ) -> Optional[T]:
        """
        Retrieve cached prediction if available.
        
        Args:
            model_name: Name of the AI model
            input_data: Input parameters used for prediction
            output_class: Pydantic class for deserializing output
        
        Returns:
            Cached prediction or None if not found/cache disabled
        """
        if not self.enabled or not self._client:
            return None
        
        try:
            key = self._generate_cache_key(model_name, input_data)
            cached_value = await self._client.get(key)
            
            if cached_value:
                logger.debug(f"Cache HIT for {model_name}", extra={"key": key})
                return output_class.model_validate_json(cached_value)
            
            logger.debug(f"Cache MISS for {model_name}", extra={"key": key})
            return None
            
        except Exception as e:
            logger.warning(f"Error retrieving from cache: {str(e)}")
            return None  # Fail gracefully
    
    async def set(
        self,
        model_name: str,
        input_data: BaseModel,
        output_data: BaseModel,
        ttl: Optional[int] = None
    ):
        """
        Store prediction in cache with TTL.
        
        Args:
            model_name: Name of the AI model
            input_data: Input parameters used for prediction
            output_data: Prediction result to cache
            ttl: Time-to-live in seconds (default: from settings)
        """
        if not self.enabled or not self._client:
            return
        
        try:
            key = self._generate_cache_key(model_name, input_data)
            value = output_data.model_dump_json()
            ttl = ttl or self.ttl
            
            await self._client.setex(key, ttl, value)
            
            logger.debug(
                f"Cached prediction for {model_name}",
                extra={"key": key, "ttl": ttl}
            )
            
        except Exception as e:
            logger.warning(f"Error storing in cache: {str(e)}")
            # Fail gracefully - cache is optional
    
    async def delete(self, model_name: str, input_data: BaseModel):
        """
        Delete specific cached prediction.
        
        Args:
            model_name: Name of the AI model
            input_data: Input parameters identifying the prediction
        """
        if not self.enabled or not self._client:
            return
        
        try:
            key = self._generate_cache_key(model_name, input_data)
            await self._client.delete(key)
            logger.debug(f"Deleted cache entry for {model_name}")
        except Exception as e:
            logger.warning(f"Error deleting from cache: {str(e)}")
    
    async def clear_model_cache(self, model_name: str):
        """
        Clear all cached predictions for a specific model.
        
        Args:
            model_name: Name of the AI model
        """
        if not self.enabled or not self._client:
            return
        
        try:
            pattern = f"prediction:{model_name}:*"
            cursor = 0
            deleted_count = 0
            
            while True:
                cursor, keys = await self._client.scan(cursor, match=pattern, count=100)
                if keys:
                    await self._client.delete(*keys)
                    deleted_count += len(keys)
                
                if cursor == 0:
                    break
            
            logger.info(
                f"Cleared {deleted_count} cache entries for {model_name}"
            )
            
        except Exception as e:
            logger.error(f"Error clearing model cache: {str(e)}")
            raise CacheException(f"Failed to clear cache for {model_name}: {str(e)}")
    
    async def clear_all(self):
        """Clear all prediction caches"""
        if not self.enabled or not self._client:
            return
        
        try:
            await self.clear_model_cache("eta")
            await self.clear_model_cache("occupation")
            await self.clear_model_cache("conflit")
            logger.info("Cleared all prediction caches")
        except Exception as e:
            logger.error(f"Error clearing all caches: {str(e)}")
            raise CacheException(f"Failed to clear all caches: {str(e)}")
    
    async def health_check(self) -> bool:
        """
        Check if Redis cache is healthy.
        
        Returns:
            True if cache is operational, False otherwise
        """
        if not self.enabled:
            return True  # Cache disabled is not an error
        
        if not self._client:
            return False
        
        try:
            await self._client.ping()
            return True
        except Exception as e:
            logger.error(f"Cache health check failed: {str(e)}")
            return False
