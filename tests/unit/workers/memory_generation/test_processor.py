"""
Unit tests for memory generation processor.

Tests processor initialization, request processing, and pipeline orchestration.
"""

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from shared.embedding.service import EmbeddingResult
from shared.extraction.engine import ExtractionResult
from workers.memory_generation.models import MemoryGenerationRequest
from workers.memory_generation.processor import MemoryGenerationProcessor


@pytest.fixture
def mock_extraction_engine():
    """Create mock extraction engine."""
    return MagicMock()


@pytest.fixture
def mock_embedding_service():
    """Create mock embedding service."""
    return MagicMock()


@pytest.fixture
def mock_vector_store():
    """Create mock vector store."""
    return MagicMock()


@pytest.fixture
def processor(mock_extraction_engine, mock_embedding_service, mock_vector_store):
    """Create processor with mocked dependencies."""
    return MemoryGenerationProcessor(
        extraction_engine=mock_extraction_engine,
        embedding_service=mock_embedding_service,
        vector_store=mock_vector_store,
    )


@pytest.fixture
def sample_request():
    """Create sample memory generation request."""
    return MemoryGenerationRequest(
        session_id=uuid4(),
        user_id=uuid4(),
        scope="user",
        min_events=3,
    )


@pytest.fixture
def sample_conversation():
    """Create sample conversation events."""
    return [
        {"speaker": "User", "content": "Hi, I'm Mark and I love pizza"},
        {"speaker": "Agent", "content": "Nice to meet you!"},
        {"speaker": "User", "content": "I work at Google as a software engineer"},
    ]


class TestProcessorInitialization:
    """Tests for processor initialization."""

    def test_init_with_services(
        self, mock_extraction_engine, mock_embedding_service, mock_vector_store
    ):
        """Test initialization with services."""
        processor = MemoryGenerationProcessor(
            extraction_engine=mock_extraction_engine,
            embedding_service=mock_embedding_service,
            vector_store=mock_vector_store,
        )

        assert processor.extraction_engine is mock_extraction_engine
        assert processor.embedding_service is mock_embedding_service
        assert processor.vector_store is mock_vector_store


class TestRequestValidation:
    """Tests for request validation."""

    def test_validate_valid_request(self, processor, sample_request):
        """Test validation of valid request."""
        is_valid, error = processor.validate_request(sample_request)

        assert is_valid is True
        assert error is None

    def test_validate_invalid_scope(self, processor):
        """Test validation fails for invalid scope."""
        request = MemoryGenerationRequest(
            session_id=uuid4(),
            user_id=uuid4(),
            scope="invalid_scope",
        )

        is_valid, error = processor.validate_request(request)

        assert is_valid is False
        assert "scope" in error


class TestRequestProcessing:
    """Tests for request processing."""

    @pytest.mark.asyncio
    async def test_process_request_success(
        self,
        processor,
        sample_request,
        sample_conversation,
        mock_extraction_engine,
        mock_embedding_service,
    ):
        """Test successful request processing."""
        # Reset mocks
        mock_extraction_engine.reset_mock()
        mock_embedding_service.reset_mock()

        # Mock extraction result
        mock_extraction_engine.extract_memories.return_value = ExtractionResult(
            memories=[
                {"fact": "User's name is Mark", "category": "fact", "confidence": 1.0},
                {"fact": "User loves pizza", "category": "preference", "confidence": 0.9},
            ],
            raw_response="test",
        )

        # Mock embedding result
        mock_embedding_service.generate_embeddings.return_value = EmbeddingResult(
            embeddings=[[0.1] * 1536, [0.2] * 1536],
            texts=["User's name is Mark", "User loves pizza"],
            model="text-embedding-3-small",
            dimensions=1536,
        )

        result = await processor.process_request(sample_request, sample_conversation)

        assert result.success is True
        assert result.memories_extracted == 2
        assert result.embeddings_generated == 2
        assert result.error is None

    @pytest.mark.asyncio
    async def test_process_request_extraction_failure(
        self,
        processor,
        sample_request,
        sample_conversation,
        mock_extraction_engine,
    ):
        """Test processing handles extraction failure."""
        # Reset mock
        mock_extraction_engine.reset_mock()

        # Mock extraction failure
        mock_extraction_engine.extract_memories.return_value = ExtractionResult(
            memories=[],
            error="LLM API error",
        )

        result = await processor.process_request(sample_request, sample_conversation)

        assert result.success is False
        assert "Extraction failed" in result.error
        assert result.memories_extracted == 0

    @pytest.mark.asyncio
    async def test_process_request_no_memories(
        self,
        processor,
        sample_request,
        sample_conversation,
        mock_extraction_engine,
    ):
        """Test processing when no memories extracted."""
        # Reset mock
        mock_extraction_engine.reset_mock()

        # Mock empty extraction
        mock_extraction_engine.extract_memories.return_value = ExtractionResult(
            memories=[],
            raw_response="test",
        )

        result = await processor.process_request(sample_request, sample_conversation)

        assert result.success is True
        assert result.memories_extracted == 0
        assert result.embeddings_generated == 0

    @pytest.mark.asyncio
    async def test_process_request_embedding_failure(
        self,
        processor,
        sample_request,
        sample_conversation,
        mock_extraction_engine,
        mock_embedding_service,
    ):
        """Test processing handles embedding failure."""
        # Reset mocks
        mock_extraction_engine.reset_mock()
        mock_embedding_service.reset_mock()

        # Mock successful extraction
        mock_extraction_engine.extract_memories.return_value = ExtractionResult(
            memories=[{"fact": "User loves pizza", "category": "preference", "confidence": 0.9}],
            raw_response="test",
        )

        # Mock embedding failure
        mock_embedding_service.generate_embeddings.return_value = EmbeddingResult(
            embeddings=[],
            texts=["User loves pizza"],
            model="text-embedding-3-small",
            dimensions=1536,
            error="OpenAI API error",
        )

        result = await processor.process_request(sample_request, sample_conversation)

        assert result.success is False
        assert "Embedding generation failed" in result.error
        assert result.memories_extracted == 1
        assert result.embeddings_generated == 0

    @pytest.mark.asyncio
    async def test_process_request_exception(
        self,
        processor,
        sample_request,
        sample_conversation,
        mock_extraction_engine,
    ):
        """Test processing handles unexpected exceptions."""
        # Reset mock
        mock_extraction_engine.reset_mock()

        # Mock exception
        mock_extraction_engine.extract_memories.side_effect = Exception("Unexpected error")

        result = await processor.process_request(sample_request, sample_conversation)

        assert result.success is False
        assert "Processing error" in result.error
