"""
Application settings using Pydantic Settings.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Environment
    environment: str = Field(
        "development", description="Environment: development, staging, production"
    )
    debug: bool = Field(False, description="Debug mode")
    log_level: str = Field("INFO", description="Logging level")

    # Database
    database_url: str = Field(..., description="PostgreSQL connection URL")
    database_pool_size: int = Field(5, description="Database connection pool size")
    database_max_overflow: int = Field(10, description="Database max overflow connections")
    database_echo: bool = Field(False, description="Echo SQL statements")

    # Redis
    redis_url: str = Field("redis://localhost:6379/0", description="Redis connection URL")
    redis_max_connections: int = Field(50, description="Redis max connections")
    redis_socket_timeout: float = Field(5.0, description="Redis socket timeout")

    # Qdrant
    qdrant_url: str = Field("http://localhost:6333", description="Qdrant server URL")
    qdrant_api_key: str | None = Field(None, description="Qdrant API key")
    qdrant_timeout: float = Field(30.0, description="Qdrant request timeout")

    # RabbitMQ
    rabbitmq_url: str = Field("amqp://guest:guest@localhost:5672/", description="RabbitMQ URL")
    rabbitmq_heartbeat: int = Field(60, description="RabbitMQ heartbeat interval")
    rabbitmq_connection_attempts: int = Field(3, description="RabbitMQ connection attempts")
    rabbitmq_retry_delay: float = Field(2.0, description="RabbitMQ retry delay")

    # LLM
    llm_provider: str = Field("openai", description="LLM provider")
    llm_model: str = Field("gpt-4", description="LLM model")
    llm_api_key: str = Field(..., description="LLM API key")
    llm_temperature: float = Field(0.7, description="LLM temperature")
    llm_max_tokens: int = Field(2000, description="LLM max tokens")
    llm_timeout: float = Field(60.0, description="LLM timeout")

    # Service Configuration
    service_name: str = Field("contextiq", description="Service name")
    service_host: str = Field("0.0.0.0", description="Service host")
    service_port: int = Field(8000, description="Service port")

    # Feature Flags
    enable_memory_extraction: bool = Field(True, description="Enable automatic memory extraction")
    enable_memory_consolidation: bool = Field(True, description="Enable memory consolidation")
    enable_procedural_memory: bool = Field(True, description="Enable procedural memory")


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Returns:
        Settings instance loaded from environment
    """
    return Settings()
