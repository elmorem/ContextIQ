"""
Configuration settings for RabbitMQ messaging.

Defines connection settings and messaging behavior.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class MessagingSettings(BaseSettings):
    """Settings for RabbitMQ messaging."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="RABBITMQ_",
        case_sensitive=False,
    )

    # Connection settings
    rabbitmq_url: str = Field(
        default="amqp://guest:guest@localhost:5672/",
        description="RabbitMQ connection URL",
    )

    rabbitmq_host: str = Field(
        default="localhost",
        description="RabbitMQ host",
    )

    rabbitmq_port: int = Field(
        default=5672,
        ge=1,
        le=65535,
        description="RabbitMQ port",
    )

    rabbitmq_user: str = Field(
        default="guest",
        description="RabbitMQ username",
    )

    rabbitmq_password: str = Field(
        default="guest",
        description="RabbitMQ password",
    )

    rabbitmq_vhost: str = Field(
        default="/",
        description="RabbitMQ virtual host",
    )

    # Connection behavior
    heartbeat: int = Field(
        default=60,
        ge=10,
        le=300,
        description="Heartbeat interval in seconds",
    )

    connection_attempts: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Number of connection attempts",
    )

    retry_delay: float = Field(
        default=2.0,
        ge=0.1,
        le=60.0,
        description="Delay between retry attempts in seconds",
    )

    # Queue settings
    default_prefetch_count: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Default prefetch count for consumers",
    )

    default_message_ttl: int = Field(
        default=86400000,  # 24 hours in milliseconds
        ge=0,
        description="Default message TTL in milliseconds (0 = no expiration)",
    )

    # Exchange settings
    default_exchange_type: str = Field(
        default="topic",
        description="Default exchange type (topic, direct, fanout, headers)",
    )

    # Dead letter configuration
    enable_dead_letter: bool = Field(
        default=True,
        description="Enable dead letter queue for failed messages",
    )

    dead_letter_exchange: str = Field(
        default="contextiq.dlx",
        description="Dead letter exchange name",
    )

    # Feature flags
    enable_publisher_confirms: bool = Field(
        default=True,
        description="Enable publisher confirms for reliability",
    )

    enable_consumer_prefetch: bool = Field(
        default=True,
        description="Enable consumer prefetch for flow control",
    )

    @property
    def connection_url(self) -> str:
        """
        Build RabbitMQ connection URL from components.

        Returns:
            RabbitMQ connection URL
        """
        return f"amqp://{self.rabbitmq_user}:{self.rabbitmq_password}@{self.rabbitmq_host}:{self.rabbitmq_port}{self.rabbitmq_vhost}"

    def get_effective_url(self) -> str:
        """
        Get the effective RabbitMQ URL (prefer rabbitmq_url if set, otherwise build from components).

        Returns:
            RabbitMQ connection URL
        """
        if self.rabbitmq_url and self.rabbitmq_url != "amqp://guest:guest@localhost:5672/":
            return self.rabbitmq_url
        return self.connection_url


@lru_cache
def get_messaging_settings() -> MessagingSettings:
    """
    Get cached messaging settings instance.

    Returns:
        MessagingSettings: Cached settings instance
    """
    return MessagingSettings()
