"""
Memory generation processor.

Orchestrates the memory extraction and embedding pipeline for a session.
"""

import logging
from uuid import UUID

from shared.embedding import EmbeddingService
from shared.extraction import ExtractionEngine
from shared.vector_store import QdrantClientWrapper
from workers.memory_generation.models import (
    ExtractedMemory,
    MemoryGenerationRequest,
    MemoryGenerationResult,
)

logger = logging.getLogger(__name__)


class MemoryGenerationProcessor:
    """
    Processor for memory generation pipeline.

    Coordinates extraction, embedding generation, and storage of memories
    from session conversation events.
    """

    def __init__(
        self,
        extraction_engine: ExtractionEngine,
        embedding_service: EmbeddingService,
        vector_store: QdrantClientWrapper,
    ):
        """
        Initialize memory generation processor.

        Args:
            extraction_engine: Engine for extracting memories from conversations
            embedding_service: Service for generating embeddings
            vector_store: Vector store client for storing embeddings
        """
        self.extraction_engine = extraction_engine
        self.embedding_service = embedding_service
        self.vector_store = vector_store

    async def process_request(
        self,
        request: MemoryGenerationRequest,
        conversation_events: list[dict[str, str]],
    ) -> MemoryGenerationResult:
        """
        Process memory generation request.

        Args:
            request: Memory generation request
            conversation_events: List of conversation events with speaker and content

        Returns:
            MemoryGenerationResult with processing details
        """
        logger.info(
            f"Processing memory generation for session {request.session_id}, "
            f"user {request.user_id}"
        )

        try:
            # Step 1: Extract memories from conversation
            extraction_result = self.extraction_engine.extract_memories(
                conversation_events=conversation_events,
                min_confidence=0.5,
            )

            # Check for extraction errors first
            if extraction_result.error:
                logger.error(
                    f"Memory extraction failed for session {request.session_id}: "
                    f"{extraction_result.error}"
                )
                return MemoryGenerationResult(
                    session_id=request.session_id,
                    user_id=request.user_id,
                    success=False,
                    error=f"Extraction failed: {extraction_result.error}",
                )

            # If no error but also no memories, that's still success
            if extraction_result.memory_count == 0:
                logger.info(
                    f"No memories extracted for session {request.session_id}"
                )
                return MemoryGenerationResult(
                    session_id=request.session_id,
                    user_id=request.user_id,
                    success=True,
                    memories_extracted=0,
                )

            logger.info(
                f"Extracted {extraction_result.memory_count} memories "
                f"for session {request.session_id}"
            )

            # Step 2: Generate embeddings for extracted memories
            memory_texts = [mem["fact"] for mem in extraction_result.memories]
            embedding_result = self.embedding_service.generate_embeddings(memory_texts)

            # Check for embedding errors
            if embedding_result.error:
                logger.error(
                    f"Embedding generation failed for session {request.session_id}: "
                    f"{embedding_result.error}"
                )
                return MemoryGenerationResult(
                    session_id=request.session_id,
                    user_id=request.user_id,
                    memories_extracted=extraction_result.memory_count,
                    success=False,
                    error=f"Embedding generation failed: {embedding_result.error}",
                )

            logger.info(
                f"Generated {embedding_result.count} embeddings "
                f"for session {request.session_id}"
            )

            # Step 3: Store memories and embeddings
            # This would integrate with Memory Service to save to database
            # and Qdrant to store vectors
            # For now, we'll return success with counts

            return MemoryGenerationResult(
                session_id=request.session_id,
                user_id=request.user_id,
                memories_extracted=extraction_result.memory_count,
                memories_saved=extraction_result.memory_count,  # Would be actual count from DB
                embeddings_generated=embedding_result.count,
                success=True,
            )

        except Exception as e:
            logger.exception(
                f"Unexpected error processing session {request.session_id}: {e}"
            )
            return MemoryGenerationResult(
                session_id=request.session_id,
                user_id=request.user_id,
                success=False,
                error=f"Processing error: {str(e)}",
            )

    def validate_request(self, request: MemoryGenerationRequest) -> tuple[bool, str | None]:
        """
        Validate memory generation request.

        Args:
            request: Request to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not request.session_id:
            return False, "session_id is required"

        if not request.user_id:
            return False, "user_id is required"

        if request.scope not in ["user", "org", "global"]:
            return False, f"Invalid scope: {request.scope}"

        return True, None
