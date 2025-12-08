"""
Memory generation processor.

Orchestrates the memory extraction and embedding pipeline for a session.
"""

import logging

from shared.clients import MemoryServiceClient, SessionsServiceClient
from shared.embedding import EmbeddingService
from shared.extraction import ExtractionEngine
from shared.vector_store import QdrantClientWrapper
from workers.memory_generation.models import (
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
        sessions_client: SessionsServiceClient,
        memory_client: MemoryServiceClient,
    ):
        """
        Initialize memory generation processor.

        Args:
            extraction_engine: Engine for extracting memories from conversations
            embedding_service: Service for generating embeddings
            vector_store: Vector store client for storing embeddings
            sessions_client: HTTP client for Sessions Service
            memory_client: HTTP client for Memory Service
        """
        self.extraction_engine = extraction_engine
        self.embedding_service = embedding_service
        self.vector_store = vector_store
        self.sessions_client = sessions_client
        self.memory_client = memory_client

    async def process_request(
        self,
        request: MemoryGenerationRequest,
    ) -> MemoryGenerationResult:
        """
        Process memory generation request.

        Args:
            request: Memory generation request

        Returns:
            MemoryGenerationResult with processing details
        """
        logger.info(
            f"Processing memory generation for session {request.session_id}, "
            f"user {request.user_id}"
        )

        try:
            # Step 1: Fetch conversation events from Sessions Service
            logger.info(f"Fetching events for session {request.session_id}")

            try:
                events_response = await self.sessions_client.list_events(
                    session_id=request.session_id, limit=1000  # Get all events for the session
                )

                # Transform events into format expected by extraction engine
                conversation_events = [
                    {
                        "speaker": event.get("event_type", "user"),
                        "content": event.get("data", {}).get("content", ""),
                    }
                    for event in events_response.get("events", [])
                    if event.get("data", {}).get("content")
                ]

                logger.info(
                    f"Retrieved {len(conversation_events)} events from session {request.session_id}"
                )

            except Exception as e:
                logger.error(f"Failed to fetch events from Sessions Service: {e}")
                return MemoryGenerationResult(
                    session_id=request.session_id,
                    user_id=request.user_id,
                    success=False,
                    error=f"Failed to fetch session events: {str(e)}",
                )

            # Step 2: Extract memories from conversation
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
                logger.info(f"No memories extracted for session {request.session_id}")
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

            # Step 3: Store memories to Memory Service
            logger.info(f"Saving {extraction_result.memory_count} memories to Memory Service")

            saved_count = 0
            failed_saves = []

            # Build scope based on request scope type
            # For user scope, include user_id
            # For org or global scope, we'd need additional fields in the request
            # For now, we only support user scope properly
            scope = {}
            if request.scope == "user":
                scope["user_id"] = str(request.user_id)

            # Save each memory with its embedding
            for idx, memory_data in enumerate(extraction_result.memories):
                try:
                    # Get corresponding embedding
                    embedding = (
                        embedding_result.embeddings[idx]
                        if idx < len(embedding_result.embeddings)
                        else None
                    )

                    # Create memory via Memory Service
                    await self.memory_client.create_memory(
                        scope=scope,
                        fact=memory_data["fact"],
                        source_type="extracted",
                        source_id=str(request.session_id),
                        topic=memory_data.get("topic"),
                        embedding=embedding,
                        confidence=memory_data.get("confidence", 1.0),
                        importance=memory_data.get("importance", 0.5),
                    )
                    saved_count += 1

                except Exception as e:
                    logger.error(
                        f"Failed to save memory {idx + 1}/{extraction_result.memory_count}: {e}"
                    )
                    failed_saves.append(idx)

            logger.info(
                f"Successfully saved {saved_count}/{extraction_result.memory_count} memories "
                f"for session {request.session_id}"
            )

            # Return result with actual counts
            return MemoryGenerationResult(
                session_id=request.session_id,
                user_id=request.user_id,
                memories_extracted=extraction_result.memory_count,
                memories_saved=saved_count,
                embeddings_generated=embedding_result.count,
                success=True,
                error=f"Failed to save {len(failed_saves)} memories" if failed_saves else None,
            )

        except Exception as e:
            logger.exception(f"Unexpected error processing session {request.session_id}: {e}")
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
