"""Custom exceptions for Simple Order Management Platform."""


class SimpleOrderManagementPlatformError(Exception):
    """Base exception for all platform-related errors."""
    pass


# Alias for backward compatibility
MarketDataPlatformError = SimpleOrderManagementPlatformError


class ConnectionError(SimpleOrderManagementPlatformError):
    """Raised when there are connection issues with external services."""
    pass


class ConfigurationError(SimpleOrderManagementPlatformError):
    """Raised when there are configuration issues."""
    pass


class DataValidationError(SimpleOrderManagementPlatformError):
    """Raised when data validation fails."""
    pass
