import httpx
import logging
from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Optional
from pydantic import BaseModel
from app.core.config import get_settings
from app.services.cache.prediction_cache import PredictionCache
from app.exceptions import AIModelException
from app.utils.decorators import retry_with_backoff

logger = logging.getLogger(__name__)
settings = get_settings()

InputT = TypeVar('InputT', bound=BaseModel)
OutputT = TypeVar('OutputT', bound=BaseModel)


class BaseAIModel(ABC, Generic[InputT, OutputT]):
    """
    Abstract base class for all AI model clients.
    Implements common functionality: HTTP calls, caching, mock/production switching.
    
    Subclasses must implement:
    - _predict_real(): Call actual AI model endpoint
    - _predict_mock(): Return mock prediction for testing
    """
    
    def __init__(
        self,
        model_name: str,
        endpoint_url: str,
        cache: PredictionCache
    ):
        self.model_name = model_name
        self.endpoint_url = endpoint_url
        self.cache = cache
        self.use_mock = settings.USE_MOCK_AI
        self.timeout = settings.MODEL_TIMEOUT_SECONDS
        self.api_key = settings.MODEL_API_KEY
        
        self._http_client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        """Initialize HTTP client on context enter"""
        self._http_client = httpx.AsyncClient(
            timeout=self.timeout,
            headers=self._get_headers()
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Close HTTP client on context exit"""
        if self._http_client:
            await self._http_client.aclose()
    
    def _get_headers(self) -> dict:
        """Build HTTP headers for API requests"""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
    
    @abstractmethod
    async def _predict_real(self, input_data: InputT) -> OutputT:
        """
        Call real AI model endpoint for prediction.
        Must be implemented by subclasses.
        
        Args:
            input_data: Input parameters for prediction
        
        Returns:
            Prediction output
        
        Raises:
            AIModelException: If prediction fails
        """
        pass
    
    @abstractmethod
    def _predict_mock(self, input_data: InputT) -> OutputT:
        """
        Generate mock prediction for testing/development.
        Must be implemented by subclasses.
        
        Args:
            input_data: Input parameters for prediction
        
        Returns:
            Mock prediction output
        """
        pass
    
    @retry_with_backoff(max_retries=3, initial_delay=1.0)
    async def _call_endpoint(self, input_data: InputT) -> OutputT:
        """
        Make HTTP POST request to AI model endpoint.
        Includes retry logic via decorator.
        
        Args:
            input_data: Input parameters
        
        Returns:
            Prediction output
        
        Raises:
            AIModelException: If request fails
        """
        if not self._http_client:
            raise AIModelException("HTTP client not initialized. Use async context manager.")
        
        try:
            logger.debug(
                f"Calling {self.model_name} model endpoint",
                extra={"url": self.endpoint_url}
            )
            
            response = await self._http_client.post(
                self.endpoint_url,
                json=input_data.model_dump(mode='json')
            )
            
            response.raise_for_status()
            
            return await self._predict_real(input_data)
            
        except httpx.HTTPStatusError as e:
            logger.error(
                f"{self.model_name} model HTTP error: {e.response.status_code}",
                extra={"response": e.response.text}
            )
            raise AIModelException(
                f"{self.model_name} prediction failed: {e.response.text}"
            )
        except httpx.TimeoutException:
            logger.error(f"{self.model_name} model timeout after {self.timeout}s")
            raise AIModelException(
                f"{self.model_name} prediction timeout"
            )
        except Exception as e:
            logger.error(f"{self.model_name} model error: {str(e)}")
            raise AIModelException(
                f"{self.model_name} prediction error: {str(e)}"
            )
    
    async def predict(
        self,
        input_data: InputT,
        use_cache: bool = True
    ) -> OutputT:
        """
        Main prediction method with caching support.
        Automatically switches between mock and real endpoints based on configuration.
        
        Args:
            input_data: Input parameters for prediction
            use_cache: Whether to check cache first (default: True)
        
        Returns:
            Prediction output
        
        Raises:
            AIModelException: If prediction fails
        """
        # Check cache first if enabled
        if use_cache:
            cached_result = await self.cache.get(
                self.model_name,
                input_data,
                self._get_output_class()
            )
            if cached_result:
                logger.info(f"Using cached prediction for {self.model_name}")
                return cached_result
        
        # Get prediction (mock or real)
        try:
            if self.use_mock:
                logger.info(f"Using MOCK prediction for {self.model_name}")
                result = self._predict_mock(input_data)
            else:
                logger.info(f"Using REAL prediction for {self.model_name}")
                result = await self._predict_real(input_data)
            
            # Cache the result
            if use_cache:
                await self.cache.set(self.model_name, input_data, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Prediction failed for {self.model_name}: {str(e)}")
            
            # If real endpoint fails, fallback to mock if configured
            if not self.use_mock and settings.USE_MOCK_AI:
                logger.warning(
                    f"Real endpoint failed, falling back to mock for {self.model_name}"
                )
                return self._predict_mock(input_data)
            
            raise
    
    @abstractmethod
    def _get_output_class(self) -> type[OutputT]:
        """
        Return the output class type for deserialization.
        Must be implemented by subclasses.
        """
        pass
    
    async def health_check(self) -> bool:
        """
        Check if AI model endpoint is healthy.
        
        Returns:
            True if endpoint is reachable, False otherwise
        """
        if self.use_mock:
            return True  # Mock is always healthy
        
        try:
            if not self._http_client:
                async with self:
                    return await self._health_check_request()
            else:
                return await self._health_check_request()
        except Exception as e:
            logger.error(f"Health check failed for {self.model_name}: {str(e)}")
            return False
    
    async def _health_check_request(self) -> bool:
        """Internal health check HTTP request"""
        try:
            # Try to reach endpoint with HEAD or GET
            response = await self._http_client.get(
                self.endpoint_url.replace("/predict", "/health"),
                timeout=5.0
            )
            return response.status_code < 500
        except:
            return False
