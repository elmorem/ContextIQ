"""
Configuration settings for database connections.

Defines PostgreSQL connection settings and pool behavior.
"""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Settings for PostgreSQL database connections."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="DATABASE_",
        case_sensitive=False,
    )

    # Connection settings
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/contextiq",
        description="Database connection URL (asyncpg driver for async support)",
    )

    database_host: str = Field(
        default="localhost",
        description="Database host",
    )

    database_port: int = Field(
        default=5432,
        ge=1,
        le=65535,
        description="Database port",
    )

    database_name: str = Field(
        default="contextiq",
        description="Database name",
    )

    database_user: str = Field(
        default="postgres",
        description="Database username",
    )

    database_password: str = Field(
        default="postgres",
        description="Database password",
    )

    # Connection pool settings
    pool_size: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Number of connections to maintain in pool",
    )

    max_overflow: int = Field(
        default=10,
        ge=0,
        le=50,
        description="Maximum overflow connections beyond pool_size",
    )

    pool_timeout: float = Field(
        default=30.0,
        ge=1.0,
        le=300.0,
        description="Timeout for getting connection from pool (seconds)",
    )

    pool_recycle: int = Field(
        default=3600,
        ge=60,
        le=86400,
        description="Recycle connections after this many seconds",
    )

    # Connection behavior
    pool_pre_ping: bool = Field(
        default=True,
        description="Verify connections before using them",
    )

    echo: bool = Field(
        default=False,
        description="Echo SQL statements for debugging",
    )

    echo_pool: bool = Field(
        default=False,
        description="Echo connection pool logging",
    )

    # Connection retry settings
    connect_timeout: int = Field(
        default=10,
        ge=1,
        le=60,
        description="Timeout for initial connection attempt (seconds)",
    )

    command_timeout: int = Field(
        default=60,
        ge=1,
        le=300,
        description="Timeout for SQL command execution (seconds)",
    )

    # SSL/TLS settings
    ssl_mode: str = Field(
        default="prefer",
        description="SSL mode (disable, allow, prefer, require, verify-ca, verify-full)",
    )

    ssl_cert: str | None = Field(
        default=None,
        description="Path to SSL client certificate",
    )

    ssl_key: str | None = Field(
        default=None,
        description="Path to SSL client key",
    )

    ssl_root_cert: str | None = Field(
        default=None,
        description="Path to SSL root certificate",
    )

    @field_validator("ssl_mode")
    @classmethod
    def validate_ssl_mode(cls, v: str) -> str:
        """Validate SSL mode value."""
        valid_modes = {"disable", "allow", "prefer", "require", "verify-ca", "verify-full"}
        if v not in valid_modes:
            raise ValueError(f"Invalid ssl_mode '{v}'. Must be one of: {', '.join(valid_modes)}")
        return v

    @property
    def connection_url(self) -> str:
        """
        Build database connection URL from components.

        Returns:
            PostgreSQL connection URL with asyncpg driver
        """
        return f"postgresql+asyncpg://{self.database_user}:{self.database_password}@{self.database_host}:{self.database_port}/{self.database_name}"

    def get_effective_url(self) -> str:
        """
        Get the effective database URL.

        Prefers explicit database_url if set to non-default value,
        otherwise builds from components.

        Returns:
            Database connection URL
        """
        default_url = "postgresql+asyncpg://postgres:postgres@localhost:5432/contextiq"
        if self.database_url and self.database_url != default_url:
            return self.database_url
        return self.connection_url

    def get_connection_kwargs(self) -> dict[str, int | str]:
        """
        Get connection keyword arguments for asyncpg.

        Returns:
            Dictionary of connection parameters
        """
        kwargs: dict[str, int | str] = {
            "timeout": self.connect_timeout,
            "command_timeout": self.command_timeout,
        }

        # Add SSL configuration if specified
        if self.ssl_mode != "disable":
            if self.ssl_cert:
                kwargs["ssl_cert"] = self.ssl_cert
            if self.ssl_key:
                kwargs["ssl_key"] = self.ssl_key
            if self.ssl_root_cert:
                kwargs["ssl_root_cert"] = self.ssl_root_cert

        return kwargs


@lru_cache
def get_database_settings() -> DatabaseSettings:
    """
    Get cached database settings instance.

    Returns:
        DatabaseSettings: Cached settings instance
    """
    return DatabaseSettings()
