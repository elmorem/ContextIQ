"""Tests for database configuration."""


import pytest

from shared.database.config import DatabaseSettings, get_database_settings


class TestDatabaseSettings:
    """Test database settings configuration."""

    def test_default_settings(self):
        """Test default configuration values."""
        settings = DatabaseSettings()

        assert settings.database_host == "localhost"
        assert settings.database_port == 5432
        assert settings.database_name == "contextiq"
        assert settings.database_user == "postgres"
        assert settings.database_password == "postgres"
        assert settings.pool_size == 5
        assert settings.max_overflow == 10
        assert settings.pool_timeout == 30.0
        assert settings.pool_recycle == 3600
        assert settings.pool_pre_ping is True
        assert settings.echo is False
        assert settings.echo_pool is False

    def test_custom_settings(self):
        """Test custom configuration values."""
        settings = DatabaseSettings(
            database_host="db.example.com",
            database_port=5433,
            database_name="testdb",
            database_user="testuser",
            database_password="testpass",
            pool_size=10,
            max_overflow=20,
        )

        assert settings.database_host == "db.example.com"
        assert settings.database_port == 5433
        assert settings.database_name == "testdb"
        assert settings.database_user == "testuser"
        assert settings.database_password == "testpass"
        assert settings.pool_size == 10
        assert settings.max_overflow == 20

    def test_connection_url_property(self):
        """Test connection URL building from components."""
        settings = DatabaseSettings(
            database_host="db.example.com",
            database_port=5433,
            database_name="testdb",
            database_user="testuser",
            database_password="testpass",
        )

        url = settings.connection_url
        assert url == "postgresql+asyncpg://testuser:testpass@db.example.com:5433/testdb"

    def test_get_effective_url_with_explicit_url(self):
        """Test effective URL when explicit database_url is set."""
        custom_url = "postgresql+asyncpg://custom:pass@custom.host:5432/customdb"
        settings = DatabaseSettings(database_url=custom_url)

        assert settings.get_effective_url() == custom_url

    def test_get_effective_url_with_components(self):
        """Test effective URL built from components."""
        settings = DatabaseSettings(
            database_host="db.example.com",
            database_port=5433,
            database_name="testdb",
            database_user="testuser",
            database_password="testpass",
        )

        url = settings.get_effective_url()
        assert url == "postgresql+asyncpg://testuser:testpass@db.example.com:5433/testdb"

    def test_get_effective_url_default(self):
        """Test effective URL with default database_url."""
        settings = DatabaseSettings()

        # Should build from components since database_url is default
        url = settings.get_effective_url()
        assert url == settings.connection_url

    def test_get_connection_kwargs(self):
        """Test connection kwargs generation."""
        settings = DatabaseSettings(
            connect_timeout=15,
            command_timeout=90,
        )

        kwargs = settings.get_connection_kwargs()
        assert kwargs["timeout"] == 15
        assert kwargs["command_timeout"] == 90

    def test_get_connection_kwargs_with_ssl(self):
        """Test connection kwargs with SSL configuration."""
        settings = DatabaseSettings(
            ssl_mode="require",
            ssl_cert="/path/to/cert",
            ssl_key="/path/to/key",
            ssl_root_cert="/path/to/root",
        )

        kwargs = settings.get_connection_kwargs()
        assert kwargs["ssl_cert"] == "/path/to/cert"
        assert kwargs["ssl_key"] == "/path/to/key"
        assert kwargs["ssl_root_cert"] == "/path/to/root"

    def test_get_connection_kwargs_no_ssl(self):
        """Test connection kwargs without SSL."""
        settings = DatabaseSettings(ssl_mode="disable")

        kwargs = settings.get_connection_kwargs()
        assert "ssl_cert" not in kwargs
        assert "ssl_key" not in kwargs
        assert "ssl_root_cert" not in kwargs

    def test_ssl_mode_validation_valid(self):
        """Test valid SSL mode values."""
        valid_modes = ["disable", "allow", "prefer", "require", "verify-ca", "verify-full"]

        for mode in valid_modes:
            settings = DatabaseSettings(ssl_mode=mode)
            assert settings.ssl_mode == mode

    def test_ssl_mode_validation_invalid(self):
        """Test invalid SSL mode raises error."""
        with pytest.raises(ValueError, match="Invalid ssl_mode"):
            DatabaseSettings(ssl_mode="invalid")

    def test_pool_size_constraints(self):
        """Test pool size validation."""
        # Valid pool size
        settings = DatabaseSettings(pool_size=10)
        assert settings.pool_size == 10

        # Invalid pool size (too small)
        with pytest.raises(ValueError):
            DatabaseSettings(pool_size=0)

        # Invalid pool size (too large)
        with pytest.raises(ValueError):
            DatabaseSettings(pool_size=100)

    def test_max_overflow_constraints(self):
        """Test max overflow validation."""
        # Valid max overflow
        settings = DatabaseSettings(max_overflow=20)
        assert settings.max_overflow == 20

        # Invalid max overflow (negative)
        with pytest.raises(ValueError):
            DatabaseSettings(max_overflow=-1)

        # Invalid max overflow (too large)
        with pytest.raises(ValueError):
            DatabaseSettings(max_overflow=100)

    def test_pool_timeout_constraints(self):
        """Test pool timeout validation."""
        # Valid timeout
        settings = DatabaseSettings(pool_timeout=60.0)
        assert settings.pool_timeout == 60.0

        # Invalid timeout (too small)
        with pytest.raises(ValueError):
            DatabaseSettings(pool_timeout=0.5)

        # Invalid timeout (too large)
        with pytest.raises(ValueError):
            DatabaseSettings(pool_timeout=400.0)

    def test_pool_recycle_constraints(self):
        """Test pool recycle validation."""
        # Valid recycle time
        settings = DatabaseSettings(pool_recycle=7200)
        assert settings.pool_recycle == 7200

        # Invalid recycle time (too small)
        with pytest.raises(ValueError):
            DatabaseSettings(pool_recycle=30)

        # Invalid recycle time (too large)
        with pytest.raises(ValueError):
            DatabaseSettings(pool_recycle=100000)

    def test_explicit_settings_override_defaults(self):
        """Test that explicit settings override environment."""
        # Test that explicitly passed settings take precedence
        settings = DatabaseSettings(
            database_host="explicit.host.com",
            database_port=9999,
            database_name="explicitdb",
            database_user="explicit_user",
            database_password="explicit_pass",
            pool_size=25,
        )

        assert settings.database_host == "explicit.host.com"
        assert settings.database_port == 9999
        assert settings.database_name == "explicitdb"
        assert settings.database_user == "explicit_user"
        assert settings.database_password == "explicit_pass"
        assert settings.pool_size == 25


class TestGetDatabaseSettings:
    """Test get_database_settings function."""

    def test_get_database_settings_returns_instance(self):
        """Test that get_database_settings returns DatabaseSettings instance."""
        settings = get_database_settings()
        assert isinstance(settings, DatabaseSettings)

    def test_get_database_settings_is_cached(self):
        """Test that get_database_settings returns cached instance."""
        settings1 = get_database_settings()
        settings2 = get_database_settings()
        assert settings1 is settings2
