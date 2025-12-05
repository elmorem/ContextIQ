"""
Unit tests for extraction engine.

Tests engine initialization, memory extraction logic, and result handling with mocked LLM.
"""

from unittest.mock import MagicMock, patch

import pytest

from shared.extraction.config import ExtractionSettings
from shared.extraction.engine import ExtractionEngine, ExtractionResult
from shared.extraction.llm_client import LLMClient


@pytest.fixture
def mock_settings():
    """Create mock extraction settings."""
    return ExtractionSettings(
        anthropic_api_key="test-key",
        anthropic_model="claude-3-5-sonnet-20241022",
        anthropic_max_tokens=4096,
        anthropic_temperature=0.0,
        anthropic_timeout=60,
        anthropic_max_retries=3,
        extraction_batch_size=10,
        extraction_min_events=3,
        extraction_max_facts=20,
        use_few_shot=True,
        max_few_shot_examples=3,
    )


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client."""
    return MagicMock(spec=LLMClient)


@pytest.fixture
def extraction_engine(mock_settings, mock_llm_client):
    """Create extraction engine with mocked LLM client."""
    engine = ExtractionEngine(settings=mock_settings, llm_client=mock_llm_client)
    return engine


@pytest.fixture
def sample_conversation():
    """Create sample conversation events."""
    return [
        {"speaker": "User", "content": "Hi, I'm Mark and I love pizza."},
        {"speaker": "Agent", "content": "Nice to meet you, Mark!"},
        {"speaker": "User", "content": "I work as a software engineer at Google."},
    ]


class TestExtractionResult:
    """Tests for ExtractionResult class."""

    def test_success_with_memories(self):
        """Test result is successful when memories are extracted."""
        result = ExtractionResult(
            memories=[{"fact": "User loves pizza", "category": "preference", "confidence": 0.9}],
            raw_response='{"memories": [...]}',
        )

        assert result.success is True
        assert result.memory_count == 1
        assert result.error is None

    def test_failure_with_error(self):
        """Test result is unsuccessful when error occurs."""
        result = ExtractionResult(
            memories=[],
            error="API error",
        )

        assert result.success is False
        assert result.memory_count == 0
        assert result.error == "API error"

    def test_empty_memories(self):
        """Test result with no extracted memories."""
        result = ExtractionResult(
            memories=[],
            raw_response='{"memories": []}',
        )

        assert result.success is False
        assert result.memory_count == 0


class TestEngineInitialization:
    """Tests for engine initialization."""

    def test_init_with_settings(self, mock_settings):
        """Test initialization with custom settings."""
        engine = ExtractionEngine(settings=mock_settings)

        assert engine.settings == mock_settings
        assert engine.llm_client is not None

    def test_init_without_settings(self):
        """Test initialization with default settings."""
        with patch("shared.extraction.engine.get_extraction_settings") as mock_get:
            mock_get.return_value = ExtractionSettings(anthropic_api_key="test-key")
            engine = ExtractionEngine()

            assert engine.settings is not None
            mock_get.assert_called_once()

    def test_init_with_custom_llm_client(self, mock_settings, mock_llm_client):
        """Test initialization with custom LLM client."""
        engine = ExtractionEngine(settings=mock_settings, llm_client=mock_llm_client)

        assert engine.llm_client is mock_llm_client


class TestMemoryExtraction:
    """Tests for memory extraction operations."""

    def test_extract_memories_success(
        self, extraction_engine, mock_llm_client, sample_conversation
    ):
        """Test successful memory extraction."""
        # Reset mock
        mock_llm_client.reset_mock()

        # Mock LLM response
        mock_llm_client.extract_structured.return_value = {
            "memories": [
                {
                    "fact": "User's name is Mark",
                    "category": "fact",
                    "confidence": 1.0,
                    "source_context": "User introduced himself",
                },
                {
                    "fact": "User loves pizza",
                    "category": "preference",
                    "confidence": 0.9,
                    "source_context": "User stated preference",
                },
            ]
        }

        result = extraction_engine.extract_memories(sample_conversation)

        assert result.success is True
        assert result.memory_count == 2
        assert result.memories[0]["fact"] == "User's name is Mark"
        assert result.memories[1]["fact"] == "User loves pizza"
        mock_llm_client.extract_structured.assert_called_once()

    def test_extract_with_confidence_filter(
        self, extraction_engine, mock_llm_client, sample_conversation
    ):
        """Test extraction with confidence filtering."""
        # Reset mock
        mock_llm_client.reset_mock()

        # Mock LLM response with varying confidence
        mock_llm_client.extract_structured.return_value = {
            "memories": [
                {"fact": "High confidence fact", "category": "fact", "confidence": 0.9},
                {"fact": "Medium confidence fact", "category": "fact", "confidence": 0.6},
                {"fact": "Low confidence fact", "category": "fact", "confidence": 0.3},
            ]
        }

        result = extraction_engine.extract_memories(sample_conversation, min_confidence=0.5)

        assert result.success is True
        assert result.memory_count == 2
        # Low confidence memory should be filtered out
        assert all(m["confidence"] >= 0.5 for m in result.memories)

    def test_extract_empty_events_raises(self, extraction_engine):
        """Test extraction with empty events raises ValueError."""
        with pytest.raises(ValueError, match="conversation_events cannot be empty"):
            extraction_engine.extract_memories([])

    def test_extract_insufficient_events(self, extraction_engine):
        """Test extraction with insufficient events returns error result."""
        events = [{"speaker": "User", "content": "Hello"}]

        result = extraction_engine.extract_memories(events)

        assert result.success is False
        assert "Insufficient events" in result.error

    def test_extract_with_max_facts_limit(
        self, extraction_engine, mock_llm_client, sample_conversation
    ):
        """Test extraction respects max facts limit."""
        # Reset mock
        mock_llm_client.reset_mock()

        # Mock LLM response with many facts
        many_memories = [
            {"fact": f"Fact {i}", "category": "fact", "confidence": 0.9} for i in range(30)
        ]
        mock_llm_client.extract_structured.return_value = {"memories": many_memories}

        result = extraction_engine.extract_memories(sample_conversation)

        assert result.success is True
        # Should be limited to extraction_max_facts (20)
        assert result.memory_count <= 20

    def test_extract_handles_llm_error(
        self, extraction_engine, mock_llm_client, sample_conversation
    ):
        """Test extraction handles LLM API errors gracefully."""
        # Reset mock
        mock_llm_client.reset_mock()

        from anthropic import AnthropicError

        mock_llm_client.extract_structured.side_effect = AnthropicError("API error")

        result = extraction_engine.extract_memories(sample_conversation)

        assert result.success is False
        assert "LLM API error" in result.error


class TestBatchExtraction:
    """Tests for batch extraction operations."""

    def test_extract_batch_success(self, extraction_engine, mock_llm_client):
        """Test batch extraction processes multiple batches."""
        # Reset mock
        mock_llm_client.reset_mock()

        batches = [
            [{"speaker": "User", "content": "I love pizza"}] * 3,
            [{"speaker": "User", "content": "I work at Google"}] * 3,
        ]

        # Mock different responses for each batch
        mock_llm_client.extract_structured.side_effect = [
            {
                "memories": [
                    {"fact": "User loves pizza", "category": "preference", "confidence": 0.9}
                ]
            },
            {
                "memories": [
                    {"fact": "User works at Google", "category": "professional", "confidence": 1.0}
                ]
            },
        ]

        results = extraction_engine.extract_memories_batch(batches)

        assert len(results) == 2
        assert results[0].success is True
        assert results[1].success is True

    def test_extract_batch_with_failures(self, extraction_engine, mock_llm_client):
        """Test batch extraction handles partial failures."""
        # Reset mock
        mock_llm_client.reset_mock()

        from anthropic import AnthropicError

        batches = [
            [{"speaker": "User", "content": "I love pizza"}] * 3,
            [{"speaker": "User", "content": "I work at Google"}] * 3,
        ]

        # First succeeds, second fails
        mock_llm_client.extract_structured.side_effect = [
            {
                "memories": [
                    {"fact": "User loves pizza", "category": "preference", "confidence": 0.9}
                ]
            },
            AnthropicError("API error"),
        ]

        results = extraction_engine.extract_memories_batch(batches)

        assert len(results) == 2
        assert results[0].success is True
        assert results[1].success is False


class TestMemoryValidation:
    """Tests for memory validation."""

    def test_validate_valid_memory(self, extraction_engine):
        """Test validation of valid memory."""
        memory = {
            "fact": "User loves pizza",
            "category": "preference",
            "confidence": 0.9,
            "source_context": "User stated preference",
        }

        assert extraction_engine.validate_memory(memory) is True

    def test_validate_missing_required_field(self, extraction_engine):
        """Test validation fails for missing required fields."""
        memory = {
            "fact": "User loves pizza",
            "confidence": 0.9,
            # Missing 'category'
        }

        assert extraction_engine.validate_memory(memory) is False

    def test_validate_invalid_confidence(self, extraction_engine):
        """Test validation fails for invalid confidence."""
        memory = {
            "fact": "User loves pizza",
            "category": "preference",
            "confidence": 1.5,  # Invalid: > 1.0
        }

        assert extraction_engine.validate_memory(memory) is False

    def test_validate_invalid_category(self, extraction_engine):
        """Test validation fails for invalid category."""
        memory = {
            "fact": "User loves pizza",
            "category": "invalid_category",
            "confidence": 0.9,
        }

        assert extraction_engine.validate_memory(memory) is False

    def test_validate_empty_fact(self, extraction_engine):
        """Test validation fails for empty fact."""
        memory = {
            "fact": "",
            "category": "preference",
            "confidence": 0.9,
        }

        assert extraction_engine.validate_memory(memory) is False


class TestContextManager:
    """Tests for context manager functionality."""

    def test_context_manager(self, mock_settings):
        """Test using engine as context manager."""
        mock_llm = MagicMock(spec=LLMClient)

        with ExtractionEngine(settings=mock_settings, llm_client=mock_llm) as engine:
            assert engine is not None

        mock_llm.close.assert_called_once()
