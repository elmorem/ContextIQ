"""
Authentication configuration.

Provides settings for JWT and API key authentication.
"""

from pydantic import Field
from pydantic_settings import BaseSettings


class AuthSettings(BaseSettings):
    """Authentication settings."""

    # JWT Settings
    jwt_secret_key: str = Field(
        ...,
        description="Secret key for JWT signing (use strong random value in production)",
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_access_token_expire_minutes: int = Field(
        default=60, description="JWT access token expiration in minutes"
    )
    jwt_issuer: str = Field(default="contextiq", description="JWT issuer")

    # API Key Settings
    api_key_enabled: bool = Field(default=True, description="Enable API key authentication")

    # Authentication Requirements
    require_auth: bool = Field(default=True, description="Require authentication for all endpoints")
    require_auth_exceptions: list[str] = Field(
        default_factory=lambda: [
            "/health",
            "/health/live",
            "/health/ready",
            "/docs",
            "/redoc",
            "/openapi.json",
        ],
        description="Endpoints that don't require authentication",
    )

    model_config = {
        "env_prefix": "AUTH_",
        "env_file": ".env",
        "extra": "ignore",
    }
