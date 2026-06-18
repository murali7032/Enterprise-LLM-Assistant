class AppException(Exception):
    """Base application exception."""

    def __init__(self, message: str, status_code: int = 500) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class LLMProviderException(AppException):
    """Raised when an LLM provider fails."""

    def __init__(self, message: str = "LLM Provider Unavailable") -> None:
        super().__init__(message=message, status_code=503)


class RetrievalException(AppException):
    """Raised when retrieval fails."""

    def __init__(self, message: str = "Retrieval failed") -> None:
        super().__init__(message=message, status_code=500)


class AuthenticationException(AppException):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed") -> None:
        super().__init__(message=message, status_code=401)


class AuthorizationException(AppException):
    """Raised when authorization fails."""

    def __init__(self, message: str = "Insufficient permissions") -> None:
        super().__init__(message=message, status_code=403)


class GuardrailException(AppException):
    """Raised when input violates guardrails."""

    def __init__(self, message: str = "Request blocked by guardrails") -> None:
        super().__init__(message=message, status_code=400)


class CacheException(AppException):
    """Raised when cache operations fail."""

    def __init__(self, message: str = "Cache operation failed") -> None:
        super().__init__(message=message, status_code=500)


class CircuitBreakerOpenException(AppException):
    """Raised when circuit breaker is open."""

    def __init__(self, message: str = "Circuit breaker is open") -> None:
        super().__init__(message=message, status_code=503)


class ToolExecutionException(AppException):
    """Raised when a tool fails."""

    def __init__(self, message: str = "Tool execution failed") -> None:
        super().__init__(message=message, status_code=500)
