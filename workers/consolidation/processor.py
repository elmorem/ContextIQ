"""
Consolidation worker processor.

Orchestrates the memory consolidation pipeline: fetch memories,
run consolidation engine, update database with merged results.
"""

import logging
from typing import Any
from uuid import UUID

from shared.clients import MemoryServiceClient
from shared.consolidation import ConsolidationEngine
from shared.embedding import EmbeddingService
from workers.consolidation.models import ConsolidationRequest, ConsolidationResult

logger = logging.getLogger(__name__)


class ConsolidationProcessor:
    """
    Processor for consolidation pipeline.

    Coordinates fetching memories, running consolidation, and persisting results.
    """

    def __init__(
        self,
        consolidation_engine: ConsolidationEngine,
        embedding_service: EmbeddingService,
        memory_client: MemoryServiceClient,
    ):
        """
        Initialize consolidation processor.

        Args:
            consolidation_engine: Engine for consolidating memories
            embedding_service: Service for embedding operations
            memory_client: HTTP client for Memory Service
        """
        self.consolidation_engine = consolidation_engine
        self.embedding_service = embedding_service
        self.memory_client = memory_client

    async def process_request(
        self,
        request: ConsolidationRequest,
    ) -> ConsolidationResult:
        """
        Process consolidation request.

        Args:
            request: Consolidation request with scope and options

        Returns:
            ConsolidationResult with processing details
        """
        logger.info(f"Processing consolidation for scope {request.scope}")

        try:
            # Step 1: Fetch memories for the scope from Memory Service
            logger.info(f"Fetching memories for scope {request.scope}")

            try:
                # Build query parameters based on scope
                scope_type = request.scope.get("type")
                query_params: dict[str, Any] = {"limit": request.max_memories}

                if scope_type == "user" and request.user_id:
                    query_params["scope_user_id"] = str(request.user_id)
                elif scope_type == "org" and request.scope.get("org_id"):
                    query_params["scope_org_id"] = request.scope["org_id"]
                # For global scope, no additional filters needed

                # Fetch memories from Memory Service
                memories_response = await self.memory_client.list_memories(**query_params)
                memories = memories_response.get("memories", [])

                logger.info(f"Retrieved {len(memories)} memories from Memory Service")

            except Exception as e:
                logger.error(f"Failed to fetch memories from Memory Service: {e}")
                return ConsolidationResult(
                    scope=request.scope,
                    memories_processed=0,
                    success=False,
                    error=f"Failed to fetch memories: {str(e)}",
                )

            if not memories:
                logger.info(f"No memories found for scope {request.scope}")
                return ConsolidationResult(
                    scope=request.scope,
                    memories_processed=0,
                    success=True,
                )

            logger.info(f"Fetched {len(memories)} memories for consolidation")

            # Step 2: Run consolidation engine
            from shared.consolidation.engine import Memory

            # Convert to consolidation Memory format
            consolidation_memories = [
                Memory(
                    id=UUID(mem.get("id")),
                    fact=mem.get("fact", ""),
                    confidence=mem.get("confidence", 0.0),
                    embedding=mem.get("embedding", []),
                    source_session_id=(
                        UUID(mem["source_session_id"]) if mem.get("source_session_id") else None
                    ),
                    metadata=mem.get("metadata"),
                )
                for mem in memories
            ]

            consolidation_result = self.consolidation_engine.consolidate_memories(
                memories=consolidation_memories,
                detect_conflicts=request.detect_conflicts,
            )

            if not consolidation_result.success:
                logger.error(
                    f"Consolidation failed for scope {request.scope}: "
                    f"{consolidation_result.error}"
                )
                return ConsolidationResult(
                    scope=request.scope,
                    memories_processed=len(memories),
                    success=False,
                    error=f"Consolidation failed: {consolidation_result.error}",
                )

            logger.info(
                f"Consolidation complete: {consolidation_result.merge_count} merges, "
                f"{consolidation_result.conflict_count} conflicts"
            )

            # Step 3: Generate embeddings for merged memories
            merged_embeddings: list[list[float]] = []
            if consolidation_result.merged_memories:
                merged_facts = [m.fact for m in consolidation_result.merged_memories]
                embedding_result = self.embedding_service.generate_embeddings(merged_facts)

                if embedding_result.error:
                    logger.warning(
                        f"Embedding generation failed for merged memories: "
                        f"{embedding_result.error}"
                    )
                else:
                    logger.info(
                        f"Generated {embedding_result.count} embeddings for merged memories"
                    )
                    merged_embeddings = embedding_result.embeddings

            # Step 4: Save consolidated memories to Memory Service
            logger.info(f"Saving {len(consolidation_result.merged_memories)} consolidated memories")

            memories_updated = 0
            failed_updates = []

            # Build scope dict for Memory Service
            scope_dict: dict[str, str] = {}
            scope_type = request.scope.get("type")
            if scope_type == "user" and request.user_id:
                scope_dict["user_id"] = str(request.user_id)
            elif scope_type == "org" and request.scope.get("org_id"):
                scope_dict["org_id"] = request.scope["org_id"]

            # Save each merged memory
            for idx, merged_memory in enumerate(consolidation_result.merged_memories):
                try:
                    # Get embedding for this merged memory
                    embedding = merged_embeddings[idx] if idx < len(merged_embeddings) else None

                    # Create consolidated memory via Memory Service
                    await self.memory_client.create_memory(
                        scope=scope_dict,
                        fact=merged_memory.fact,
                        source_type="consolidated",
                        embedding=embedding,
                        confidence=merged_memory.confidence,
                        importance=0.7,  # Consolidated memories are typically important
                    )
                    memories_updated += 1

                    # TODO: Mark superseded memories as soft-deleted
                    # This would require additional Memory Service API to update memory status

                except Exception as e:
                    logger.error(f"Failed to save consolidated memory {idx + 1}: {e}")
                    failed_updates.append(idx)

            logger.info(
                f"Successfully saved {memories_updated}/{len(consolidation_result.merged_memories)} "
                f"consolidated memories"
            )

            return ConsolidationResult(
                scope=request.scope,
                memories_processed=consolidation_result.memories_processed,
                memories_merged=consolidation_result.memories_merged,
                conflicts_detected=consolidation_result.conflict_count,
                memories_updated=memories_updated,
                success=True,
            )

        except Exception as e:
            logger.exception(f"Unexpected error processing consolidation: {e}")
            return ConsolidationResult(
                scope=request.scope,
                success=False,
                error=f"Processing error: {str(e)}",
            )

    def validate_request(
        self,
        request: ConsolidationRequest,
    ) -> tuple[bool, str | None]:
        """
        Validate consolidation request.

        Args:
            request: Request to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Validate scope format (even if empty dict)
        if "type" not in request.scope:
            return False, "scope must contain 'type' field"

        scope_type = request.scope.get("type")
        if scope_type not in ["user", "org", "global"]:
            return False, f"Invalid scope type: {scope_type}"

        # For user scope, user_id is required
        if scope_type == "user" and not request.user_id:
            return False, "user_id is required for user scope"

        # Note: max_memories validation is handled by Pydantic (ge=10)
        # No need to validate here as invalid values will fail at model construction

        return True, None
