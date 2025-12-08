"""Configuration for HTTP service clients."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class HTTPClientSettings(BaseSettings):
    """HTTP client configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Sessions Service
    sessions_service_url: str = "http://localhost:8001"
    sessions_service_timeout: int = 30
    sessions_service_max_retries: int = 3
    sessions_service_retry_delay: float = 1.0

    # Memory Service
    memory_service_url: str = "http://localhost:8002"
    memory_service_timeout: int = 30
    memory_service_max_retries: int = 3
    memory_service_retry_delay: float = 1.0

    # Circuit breaker settings
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_timeout: int = 60
    circuit_breaker_expected_exception: type = Exception


# Global settings instance
http_client_settings = HTTPClientSettings()
