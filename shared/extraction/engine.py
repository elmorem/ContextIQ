"""
Core extraction engine for memory generation.

Orchestrates the extraction process using LLM client and prompts
to generate structured memories from conversation events.
"""

from typing import Any

from anthropic import AnthropicError

from shared.extraction.config import ExtractionSettings, get_extraction_settings
from shared.extraction.llm_client import LLMClient
from shared.extraction.prompts import (
    EXTRACTION_RESPONSE_SCHEMA,
    EXTRACTION_SYSTEM_PROMPT,
    build_extraction_prompt,
)


class ExtractionResult:
    """Result of memory extraction operation."""

    def __init__(
        self,
        memories: list[dict[str, Any]],
        raw_response: str | None = None,
        error: str | None = None,
    ):
        """
        Initialize extraction result.

        Args:
            memories: List of extracted memory dictionaries
            raw_response: Raw LLM response text
            error: Error message if extraction failed
        """
        self.memories = memories
        self.raw_response = raw_response
        self.error = error

    @property
    def success(self) -> bool:
        """Check if extraction was successful."""
        return self.error is None and len(self.memories) > 0

    @property
    def memory_count(self) -> int:
        """Get number of extracted memories."""
        return len(self.memories)


class ExtractionEngine:
    """
    Core engine for extracting memories from conversation events.

    Handles batching, LLM interaction, and result parsing for
    memory generation operations.
    """

    def __init__(
        self,
        settings: ExtractionSettings | None = None,
        llm_client: LLMClient | None = None,
    ):
        """
        Initialize extraction engine.

        Args:
            settings: Extraction settings (uses defaults if not provided)
            llm_client: LLM client instance (creates new if not provided)
        """
        self.settings = settings or get_extraction_settings()
        self.llm_client = llm_client or LLMClient(settings=self.settings)

    def extract_memories(
        self,
        conversation_events: list[dict[str, str]],
        min_confidence: float = 0.5,
    ) -> ExtractionResult:
        """
        Extract memories from conversation events.

        Args:
            conversation_events: List of events with 'speaker' and 'content'
            min_confidence: Minimum confidence threshold for extracted memories

        Returns:
            ExtractionResult with extracted memories and metadata

        Raises:
            ValueError: If conversation_events is empty or invalid
        """
        # Validate input
        if not conversation_events:
            raise ValueError("conversation_events cannot be empty")

        if len(conversation_events) < self.settings.extraction_min_events:
            return ExtractionResult(
                memories=[],
                error=f"Insufficient events: need at least {self.settings.extraction_min_events}",
            )

        try:
            # Build extraction prompt
            prompt = build_extraction_prompt(
                conversation_events=conversation_events,
                include_few_shot=self.settings.use_few_shot,
                max_examples=self.settings.max_few_shot_examples,
            )

            # Call LLM for extraction
            response = self.llm_client.extract_structured(
                system_prompt=EXTRACTION_SYSTEM_PROMPT,
                user_message=prompt,
                response_schema=EXTRACTION_RESPONSE_SCHEMA,
            )

            # Extract and filter memories
            raw_memories = response.get("memories", [])
            filtered_memories = self._filter_by_confidence(
                memories=raw_memories,
                min_confidence=min_confidence,
            )

            # Limit to max facts
            if len(filtered_memories) > self.settings.extraction_max_facts:
                filtered_memories = filtered_memories[: self.settings.extraction_max_facts]

            return ExtractionResult(
                memories=filtered_memories,
                raw_response=str(response),
            )

        except AnthropicError as e:
            return ExtractionResult(
                memories=[],
                error=f"LLM API error: {e}",
            )
        except Exception as e:
            return ExtractionResult(
                memories=[],
                error=f"Extraction failed: {e}",
            )

    def extract_memories_batch(
        self,
        event_batches: list[list[dict[str, str]]],
        min_confidence: float = 0.5,
    ) -> list[ExtractionResult]:
        """
        Extract memories from multiple batches of conversation events.

        Args:
            event_batches: List of event batches to process
            min_confidence: Minimum confidence threshold

        Returns:
            List of ExtractionResult objects, one per batch
        """
        results = []

        for batch in event_batches:
            result = self.extract_memories(
                conversation_events=batch,
                min_confidence=min_confidence,
            )
            results.append(result)

        return results

    def _filter_by_confidence(
        self,
        memories: list[dict[str, Any]],
        min_confidence: float,
    ) -> list[dict[str, Any]]:
        """
        Filter memories by confidence threshold.

        Args:
            memories: List of memory dictionaries
            min_confidence: Minimum confidence threshold

        Returns:
            Filtered list of memories
        """
        return [memory for memory in memories if memory.get("confidence", 0.0) >= min_confidence]

    def validate_memory(self, memory: dict[str, Any]) -> bool:
        """
        Validate a single memory dictionary.

        Args:
            memory: Memory dictionary to validate

        Returns:
            True if memory is valid, False otherwise
        """
        required_fields = ["fact", "category", "confidence"]

        # Check required fields
        if not all(field in memory for field in required_fields):
            return False

        # Validate confidence range
        confidence = memory.get("confidence", 0.0)
        if not isinstance(confidence, int | float) or not (0.0 <= confidence <= 1.0):
            return False

        # Validate category
        valid_categories = {
            "preference",
            "fact",
            "goal",
            "habit",
            "relationship",
            "professional",
            "location",
            "temporal",
        }
        if memory.get("category") not in valid_categories:
            return False

        # Validate fact is non-empty string
        fact = memory.get("fact")
        if not isinstance(fact, str) or not fact.strip():
            return False

        return True

    def close(self) -> None:
        """Close LLM client connection."""
        if self.llm_client:
            self.llm_client.close()

    def __enter__(self) -> "ExtractionEngine":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()
