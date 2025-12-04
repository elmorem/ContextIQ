"""
Configuration Pydantic schemas.
"""

from pydantic import Field

from shared.schemas.base import BaseSchema


class DatabaseConfig(BaseSchema):
    """Database configuration schema."""

    url: str = Field(..., description="Database connection URL")
    pool_size: int = Field(5, ge=1, description="Connection pool size")
    max_overflow: int = Field(10, ge=0, description="Max overflow connections")
    pool_timeout: float = Field(30.0, ge=0, description="Pool timeout in seconds")
    pool_recycle: int = Field(3600, ge=0, description="Pool recycle time in seconds")
    echo: bool = Field(False, description="Echo SQL statements")


class RedisConfig(BaseSchema):
    """Redis configuration schema."""

    url: str = Field(..., description="Redis connection URL")
    max_connections: int = Field(50, ge=1, description="Maximum connections")
    decode_responses: bool = Field(True, description="Decode responses to strings")
    socket_timeout: float = Field(5.0, ge=0, description="Socket timeout in seconds")
    socket_connect_timeout: float = Field(5.0, ge=0, description="Connect timeout in seconds")


class QdrantConfig(BaseSchema):
    """Qdrant configuration schema."""

    url: str = Field(..., description="Qdrant server URL")
    api_key: str | None = Field(None, description="API key for authentication")
    timeout: float = Field(30.0, ge=0, description="Request timeout in seconds")


class RabbitMQConfig(BaseSchema):
    """RabbitMQ configuration schema."""

    url: str = Field(..., description="RabbitMQ connection URL")
    heartbeat: int = Field(60, ge=0, description="Heartbeat interval in seconds")
    connection_attempts: int = Field(3, ge=1, description="Number of connection attempts")
    retry_delay: float = Field(2.0, ge=0, description="Retry delay in seconds")


class LLMConfig(BaseSchema):
    """LLM configuration schema."""

    provider: str = Field("openai", description="LLM provider (openai, anthropic, etc)")
    model: str = Field("gpt-4", description="Model name")
    api_key: str = Field(..., description="API key")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="Temperature")
    max_tokens: int = Field(2000, ge=1, description="Maximum tokens")
    timeout: float = Field(60.0, ge=0, description="Request timeout in seconds")


class ConfigSchema(BaseSchema):
    """Main configuration schema."""

    environment: str = Field(
        "development", description="Environment: development, staging, production"
    )
    debug: bool = Field(False, description="Debug mode")
    log_level: str = Field("INFO", description="Logging level")

    # Service configurations
    database: DatabaseConfig = Field(..., description="Database configuration")
    redis: RedisConfig = Field(..., description="Redis configuration")
    qdrant: QdrantConfig = Field(..., description="Qdrant configuration")
    rabbitmq: RabbitMQConfig = Field(..., description="RabbitMQ configuration")
    llm: LLMConfig = Field(..., description="LLM configuration")
