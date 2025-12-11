class AirportBackendException(Exception):
    """Base exception for all airport backend errors"""
    pass


class OpenSkyAPIException(AirportBackendException):
    """Exception raised for OpenSky Network API errors"""
    pass


class AIModelException(AirportBackendException):
    """Exception raised for AI model prediction errors"""
    pass


class ParkingAllocationException(AirportBackendException):
    """Exception raised for parking allocation errors"""
    pass


class AuthenticationException(AirportBackendException):
    """Exception raised for authentication/authorization errors"""
    pass


class CacheException(AirportBackendException):
    """Exception raised for cache operation errors"""
    pass
