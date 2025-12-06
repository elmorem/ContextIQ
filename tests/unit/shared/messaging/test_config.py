"""
Unit tests for messaging configuration.
"""

from shared.messaging.config import MessagingSettings, get_messaging_settings


class TestMessagingSettings:
    """Tests for messaging settings."""

    def test_default_settings(self):
        """Test default configuration values."""
        settings = MessagingSettings()

        assert settings.rabbitmq_host == "localhost"
        assert settings.rabbitmq_port == 5672
        assert settings.rabbitmq_user == "guest"
        assert settings.rabbitmq_password == "guest"
        assert settings.rabbitmq_vhost == "/"
        assert settings.heartbeat == 60
        assert settings.connection_attempts == 3
        assert settings.retry_delay == 2.0

    def test_connection_url_building(self):
        """Test building connection URL from components."""
        settings = MessagingSettings(
            rabbitmq_user="admin",
            rabbitmq_password="secret",
            rabbitmq_host="rabbitmq.example.com",
            rabbitmq_port=5673,
            rabbitmq_vhost="/production",
        )

        url = settings.connection_url
        assert url == "amqp://admin:secret@rabbitmq.example.com:5673/production"

    def test_effective_url_uses_explicit_url(self):
        """Test that explicit URL takes precedence."""
        settings = MessagingSettings(
            rabbitmq_url="amqp://custom:pass@custom.host:5672/",
            rabbitmq_host="should_be_ignored",
        )

        assert settings.get_effective_url() == "amqp://custom:pass@custom.host:5672/"

    def test_effective_url_builds_from_components(self):
        """Test that URL is built from components when not explicitly set."""
        settings = MessagingSettings(
            rabbitmq_user="testuser",
            rabbitmq_password="testpass",
            rabbitmq_host="testhost",
            rabbitmq_port=5672,
            rabbitmq_vhost="/test",
        )

        assert settings.get_effective_url() == "amqp://testuser:testpass@testhost:5672/test"

    def test_prefetch_count_validation(self):
        """Test prefetch count is within valid range."""
        settings = MessagingSettings(default_prefetch_count=50)
        assert settings.default_prefetch_count == 50

    def test_exchange_settings(self):
        """Test exchange configuration."""
        settings = MessagingSettings()
        assert settings.default_exchange_type == "topic"
        assert settings.enable_dead_letter is True
        assert settings.dead_letter_exchange == "contextiq.dlx"

    def test_feature_flags(self):
        """Test feature flag defaults."""
        settings = MessagingSettings()
        assert settings.enable_publisher_confirms is True
        assert settings.enable_consumer_prefetch is True

    def test_cached_settings(self):
        """Test that get_messaging_settings returns cached instance."""
        settings1 = get_messaging_settings()
        settings2 = get_messaging_settings()
        assert settings1 is settings2
