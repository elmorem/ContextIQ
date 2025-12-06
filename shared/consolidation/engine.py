"""
Core consolidation engine for memory deduplication and merging.

Provides functionality for detecting similar memories, merging duplicates,
and resolving conflicts between contradictory memories.
"""

import logging
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from shared.consolidation.config import ConsolidationSettings, get_consolidation_settings

logger = logging.getLogger(__name__)


@dataclass
class Memory:
    """Memory representation for consolidation."""

    id: UUID
    fact: str
    confidence: float
    embedding: list[float]
    source_session_id: UUID | None = None
    metadata: dict[str, Any] | None = None


@dataclass
class MergeCandidate:
    """Candidate memory pair for merging."""

    memory1: Memory
    memory2: Memory
    similarity_score: float
    is_conflict: bool


@dataclass
class MergedMemory:
    """Result of merging memories."""

    fact: str
    confidence: float
    source_memory_ids: list[UUID]
    merge_reason: str


class ConsolidationResult:
    """Result of consolidation operation."""

    def __init__(
        self,
        merged_memories: list[MergedMemory] | None = None,
        conflicts_detected: list[MergeCandidate] | None = None,
        memories_processed: int = 0,
        memories_merged: int = 0,
        success: bool = True,
        error: str | None = None,
    ):
        """
        Initialize consolidation result.

        Args:
            merged_memories: List of merged memory results
            conflicts_detected: List of conflicting memory pairs
            memories_processed: Number of memories processed
            memories_merged: Number of memories that were merged
            success: Whether consolidation succeeded
            error: Error message if failed
        """
        self.merged_memories = merged_memories or []
        self.conflicts_detected = conflicts_detected or []
        self.memories_processed = memories_processed
        self.memories_merged = memories_merged
        self.success = success
        self.error = error

    @property
    def merge_count(self) -> int:
        """Get number of successful merges."""
        return len(self.merged_memories)

    @property
    def conflict_count(self) -> int:
        """Get number of conflicts detected."""
        return len(self.conflicts_detected)


class ConsolidationEngine:
    """
    Engine for consolidating memories.

    Handles similarity detection, duplicate merging, and conflict resolution
    for memory management.
    """

    def __init__(self, settings: ConsolidationSettings | None = None):
        """
        Initialize consolidation engine.

        Args:
            settings: Consolidation settings (optional)
        """
        self.settings = settings or get_consolidation_settings()
        logger.info(
            f"Consolidation engine initialized with "
            f"similarity_threshold={self.settings.similarity_threshold}, "
            f"merge_strategy={self.settings.merge_strategy}"
        )

    def consolidate_memories(
        self,
        memories: list[Memory],
        detect_conflicts: bool = True,
    ) -> ConsolidationResult:
        """
        Consolidate a list of memories by detecting and merging duplicates.

        Args:
            memories: List of memories to consolidate
            detect_conflicts: Whether to detect conflicts (default: True)

        Returns:
            ConsolidationResult with merged memories and conflicts
        """
        try:
            logger.info(f"Starting consolidation for {len(memories)} memories")

            if len(memories) < 2:
                logger.info("Not enough memories to consolidate")
                return ConsolidationResult(
                    memories_processed=len(memories),
                    success=True,
                )

            # Find merge candidates
            merge_candidates = self._find_merge_candidates(memories)

            if not merge_candidates:
                logger.info("No merge candidates found")
                return ConsolidationResult(
                    memories_processed=len(memories),
                    success=True,
                )

            # Separate conflicts from mergeable pairs
            conflicts = []
            mergeable = []

            for candidate in merge_candidates:
                if detect_conflicts and candidate.is_conflict:
                    conflicts.append(candidate)
                else:
                    mergeable.append(candidate)

            logger.info(f"Found {len(mergeable)} mergeable pairs and {len(conflicts)} conflicts")

            # Merge similar memories
            merged_memories = []
            for candidate in mergeable:
                merged = self._merge_memories(candidate.memory1, candidate.memory2)
                merged_memories.append(merged)

            result = ConsolidationResult(
                merged_memories=merged_memories,
                conflicts_detected=conflicts,
                memories_processed=len(memories),
                memories_merged=len(merged_memories) * 2,  # Count both source memories
                success=True,
            )

            logger.info(
                f"Consolidation complete: {result.merge_count} merges, "
                f"{result.conflict_count} conflicts"
            )

            return result

        except Exception as e:
            logger.exception(f"Error during consolidation: {e}")
            return ConsolidationResult(
                memories_processed=len(memories),
                success=False,
                error=str(e),
            )

    def _find_merge_candidates(
        self,
        memories: list[Memory],
    ) -> list[MergeCandidate]:
        """
        Find pairs of memories that are candidates for merging.

        Args:
            memories: List of memories to analyze

        Returns:
            List of merge candidates
        """
        candidates = []

        # Compare each pair of memories
        for i, memory1 in enumerate(memories):
            for memory2 in memories[i + 1 :]:
                similarity = self._calculate_similarity(memory1, memory2)

                # Check if similar enough to merge
                if similarity >= self.settings.similarity_threshold:
                    is_conflict = self._is_conflicting(memory1, memory2, similarity)

                    candidates.append(
                        MergeCandidate(
                            memory1=memory1,
                            memory2=memory2,
                            similarity_score=similarity,
                            is_conflict=is_conflict,
                        )
                    )

                    # Limit number of candidates per memory
                    if len(candidates) >= self.settings.max_merge_candidates:
                        break

        return candidates

    def _calculate_similarity(self, memory1: Memory, memory2: Memory) -> float:
        """
        Calculate cosine similarity between two memories.

        Args:
            memory1: First memory
            memory2: Second memory

        Returns:
            Similarity score between 0.0 and 1.0
        """
        if not memory1.embedding or not memory2.embedding:
            return 0.0

        # Cosine similarity
        dot_product = sum(a * b for a, b in zip(memory1.embedding, memory2.embedding, strict=False))
        magnitude1 = sum(a * a for a in memory1.embedding) ** 0.5
        magnitude2 = sum(b * b for b in memory2.embedding) ** 0.5

        if magnitude1 == 0.0 or magnitude2 == 0.0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    def _is_conflicting(
        self,
        memory1: Memory,
        memory2: Memory,
        similarity: float,
    ) -> bool:
        """
        Determine if two similar memories are conflicting.

        Memories are considered conflicting if they are semantically similar
        but contain contradictory information.

        Args:
            memory1: First memory
            memory2: Second memory
            similarity: Pre-calculated similarity score

        Returns:
            True if memories conflict, False otherwise
        """
        # Heuristic: if similarity is above conflict threshold but below merge threshold,
        # and facts are different, they might be conflicting
        if self.settings.conflict_threshold <= similarity < self.settings.similarity_threshold:
            # Check if facts are substantively different
            # (simple heuristic - could be enhanced with LLM)
            return memory1.fact.lower() != memory2.fact.lower()

        return False

    def _merge_memories(self, memory1: Memory, memory2: Memory) -> MergedMemory:
        """
        Merge two similar memories into one.

        Args:
            memory1: First memory
            memory2: Second memory

        Returns:
            MergedMemory result
        """
        strategy = self.settings.merge_strategy

        if strategy == "highest_confidence":
            if memory1.confidence >= memory2.confidence:
                selected_fact = memory1.fact
                base_confidence = memory1.confidence
            else:
                selected_fact = memory2.fact
                base_confidence = memory2.confidence

        elif strategy == "most_recent":
            # Assume memory1 is more recent if no timestamp
            selected_fact = memory1.fact
            base_confidence = memory1.confidence

        elif strategy == "longest":
            if len(memory1.fact) >= len(memory2.fact):
                selected_fact = memory1.fact
                base_confidence = memory1.confidence
            else:
                selected_fact = memory2.fact
                base_confidence = memory2.confidence

        else:
            # Default to highest confidence
            selected_fact = (
                memory1.fact if memory1.confidence >= memory2.confidence else memory2.fact
            )
            base_confidence = max(memory1.confidence, memory2.confidence)

        # Apply confidence boost for merged memories
        merged_confidence = min(
            1.0,
            base_confidence + self.settings.merged_confidence_boost,
        )

        return MergedMemory(
            fact=selected_fact,
            confidence=merged_confidence,
            source_memory_ids=[memory1.id, memory2.id],
            merge_reason=f"Merged using {strategy} strategy",
        )

    def close(self) -> None:
        """Clean up resources."""
        logger.info("Consolidation engine closed")

    def __enter__(self) -> "ConsolidationEngine":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()
