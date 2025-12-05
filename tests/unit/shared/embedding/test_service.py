"""
Unit tests for embedding service.

Tests service initialization, embedding generation, and batch processing with mocked OpenAI.
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from shared.embedding.config import EmbeddingSettings
from shared.embedding.service import EmbeddingResult, EmbeddingService


@pytest.fixture
def mock_settings():
    """Create mock embedding settings."""
    return EmbeddingSettings(
        openai_api_key="test-key",
        openai_embedding_model="text-embedding-3-small",
        openai_embedding_dimensions=1536,
        openai_timeout=60,
        openai_max_retries=3,
        embedding_batch_size=100,
        embedding_max_input_length=8191,
    )


@pytest.fixture
def mock_openai_client():
    """Create a mock OpenAI client."""
    return MagicMock()


@pytest.fixture
def embedding_service(mock_settings, mock_openai_client):
    """Create embedding service with mocked OpenAI client."""
    service = EmbeddingService(settings=mock_settings)
    service._client = mock_openai_client
    return service


class TestEmbeddingResult:
    """Tests for EmbeddingResult class."""

    def test_success_with_embeddings(self):
        """Test result is successful when embeddings are generated."""
        result = EmbeddingResult(
            embeddings=[[0.1, 0.2, 0.3]],
            texts=["test text"],
            model="text-embedding-3-small",
            dimensions=1536,
        )

        assert result.success is True
        assert result.count == 1
        assert result.error is None

    def test_failure_with_error(self):
        """Test result is unsuccessful when error occurs."""
        result = EmbeddingResult(
            embeddings=[],
            texts=["test text"],
            model="text-embedding-3-small",
            dimensions=1536,
            error="API error",
        )

        assert result.success is False
        assert result.count == 0
        assert result.error == "API error"


class TestServiceInitialization:
    """Tests for service initialization."""

    def test_init_with_settings(self, mock_settings):
        """Test initialization with custom settings."""
        service = EmbeddingService(settings=mock_settings)

        assert service.settings == mock_settings
        assert service._client is None

    def test_init_without_settings(self):
        """Test initialization with default settings."""
        with patch("shared.embedding.service.get_embedding_settings") as mock_get:
            mock_get.return_value = EmbeddingSettings(openai_api_key="test-key")
            service = EmbeddingService()

            assert service.settings is not None
            mock_get.assert_called_once()

    def test_client_property_creates_client(self, mock_settings):
        """Test that accessing client property creates the client."""
        with patch("shared.embedding.service.OpenAI") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            service = EmbeddingService(settings=mock_settings)
            client = service.client

            assert client == mock_client
            mock_client_class.assert_called_once()

    def test_client_property_reuses_client(self, embedding_service):
        """Test that client property reuses existing client."""
        client1 = embedding_service.client
        client2 = embedding_service.client
        assert client1 is client2

    def test_client_property_raises_without_api_key(self):
        """Test that client property raises error without API key."""
        settings = EmbeddingSettings(
            openai_api_key="",  # Empty API key
            openai_embedding_model="text-embedding-3-small",
            openai_embedding_dimensions=1536,
        )
        service = EmbeddingService(settings=settings)

        with pytest.raises(ValueError, match="OpenAI API key not configured"):
            _ = service.client


class TestEmbeddingGeneration:
    """Tests for embedding generation."""

    def test_generate_single_embedding(self, embedding_service, mock_openai_client):
        """Test generating embedding for a single text."""
        # Reset mock
        mock_openai_client.reset_mock()

        # Mock OpenAI response
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1, 0.2, 0.3])]
        mock_response.model = "text-embedding-3-small"
        mock_openai_client.embeddings.create.return_value = mock_response

        result = embedding_service.generate_embedding("test text")

        assert result.success is True
        assert result.count == 1
        assert len(result.embeddings[0]) == 3
        mock_openai_client.embeddings.create.assert_called_once()

    def test_generate_multiple_embeddings(self, embedding_service, mock_openai_client):
        """Test generating embeddings for multiple texts."""
        # Reset mock
        mock_openai_client.reset_mock()

        # Mock OpenAI response
        mock_response = Mock()
        mock_response.data = [
            Mock(embedding=[0.1, 0.2, 0.3]),
            Mock(embedding=[0.4, 0.5, 0.6]),
            Mock(embedding=[0.7, 0.8, 0.9]),
        ]
        mock_response.model = "text-embedding-3-small"
        mock_openai_client.embeddings.create.return_value = mock_response

        texts = ["text 1", "text 2", "text 3"]
        result = embedding_service.generate_embeddings(texts)

        assert result.success is True
        assert result.count == 3
        assert len(result.embeddings) == 3

    def test_generate_embeddings_empty_raises(self, embedding_service):
        """Test generating embeddings with empty list raises ValueError."""
        with pytest.raises(ValueError, match="texts cannot be empty"):
            embedding_service.generate_embeddings([])

    def test_generate_embeddings_handles_openai_error(self, embedding_service, mock_openai_client):
        """Test embedding generation handles OpenAI errors gracefully."""
        # Reset mock
        mock_openai_client.reset_mock()

        from openai import OpenAIError

        mock_openai_client.embeddings.create.side_effect = OpenAIError("API error")

        result = embedding_service.generate_embeddings(["test"])

        assert result.success is False
        assert "OpenAI API error" in result.error

    def test_generate_embeddings_handles_general_error(self, embedding_service, mock_openai_client):
        """Test embedding generation handles general errors."""
        # Reset mock
        mock_openai_client.reset_mock()

        mock_openai_client.embeddings.create.side_effect = Exception("Unknown error")

        result = embedding_service.generate_embeddings(["test"])

        assert result.success is False
        assert "Embedding generation failed" in result.error


class TestBatchProcessing:
    """Tests for batch embedding generation."""

    def test_batch_processing_single_batch(self, embedding_service, mock_openai_client):
        """Test batch processing with texts fitting in one batch."""
        # Reset mock
        mock_openai_client.reset_mock()

        # Mock OpenAI response
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1, 0.2, 0.3]) for _ in range(50)]
        mock_response.model = "text-embedding-3-small"
        mock_openai_client.embeddings.create.return_value = mock_response

        texts = [f"text {i}" for i in range(50)]
        results = embedding_service.generate_embeddings_batch(texts)

        assert len(results) == 1
        assert results[0].success is True
        assert results[0].count == 50

    def test_batch_processing_multiple_batches(self, embedding_service, mock_openai_client):
        """Test batch processing with texts spanning multiple batches."""
        # Reset mock
        mock_openai_client.reset_mock()

        # Mock OpenAI responses with different sizes for each batch
        def create_mock_response(count):
            mock_response = Mock()
            mock_response.data = [Mock(embedding=[0.1, 0.2, 0.3]) for _ in range(count)]
            mock_response.model = "text-embedding-3-small"
            return mock_response

        mock_openai_client.embeddings.create.side_effect = [
            create_mock_response(100),  # First batch
            create_mock_response(100),  # Second batch
            create_mock_response(50),  # Third batch
        ]

        texts = [f"text {i}" for i in range(250)]
        results = embedding_service.generate_embeddings_batch(texts, batch_size=100)

        assert len(results) == 3
        assert results[0].count == 100
        assert results[1].count == 100
        assert results[2].count == 50

    def test_batch_processing_custom_batch_size(self, embedding_service, mock_openai_client):
        """Test batch processing with custom batch size."""
        # Reset mock
        mock_openai_client.reset_mock()

        # Mock OpenAI response
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1, 0.2, 0.3]) for _ in range(10)]
        mock_response.model = "text-embedding-3-small"
        mock_openai_client.embeddings.create.return_value = mock_response

        texts = [f"text {i}" for i in range(50)]
        results = embedding_service.generate_embeddings_batch(texts, batch_size=10)

        assert len(results) == 5
        assert all(r.count == 10 for r in results)


class TestTextTruncation:
    """Tests for text truncation."""

    def test_truncate_long_text(self, embedding_service):
        """Test that long texts are truncated."""
        # Create a very long text
        long_text = "a" * 50000
        truncated = embedding_service._truncate_texts([long_text])

        assert len(truncated[0]) < len(long_text)
        assert len(truncated[0]) <= 8191 * 4  # max_chars

    def test_no_truncation_for_short_text(self, embedding_service):
        """Test that short texts are not truncated."""
        short_text = "This is a short text"
        truncated = embedding_service._truncate_texts([short_text])

        assert truncated[0] == short_text


class TestContextManager:
    """Tests for context manager functionality."""

    def test_context_manager(self, mock_settings):
        """Test using service as context manager."""
        mock_client = MagicMock()

        with patch("shared.embedding.service.OpenAI", return_value=mock_client):
            with EmbeddingService(settings=mock_settings) as service:
                assert service is not None
                # Access client property to trigger initialization
                _ = service.client

            mock_client.close.assert_called_once()
