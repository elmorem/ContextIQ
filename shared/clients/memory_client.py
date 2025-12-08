"""HTTP client for Memory Service."""

import logging
from uuid import UUID

from shared.clients.base import BaseHTTPClient
from shared.clients.config import http_client_settings

logger = logging.getLogger(__name__)


class MemoryServiceClient(BaseHTTPClient):
    """HTTP client for communicating with the Memory Service."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout: int | None = None,
        max_retries: int | None = None,
        retry_delay: float | None = None,
    ):
        """
        Initialize Memory Service client.

        Args:
            base_url: Base URL for Memory Service (defaults to config)
            timeout: Request timeout in seconds (defaults to config)
            max_retries: Maximum retry attempts (defaults to config)
            retry_delay: Delay between retries (defaults to config)
        """
        super().__init__(
            base_url=base_url or http_client_settings.memory_service_url,
            timeout=timeout or http_client_settings.memory_service_timeout,
            max_retries=max_retries or http_client_settings.memory_service_max_retries,
            retry_delay=retry_delay or http_client_settings.memory_service_retry_delay,
        )

    async def create_memory(
        self,
        scope: dict[str, str],
        fact: str,
        source_type: str,
        topic: str | None = None,
        embedding: list[float] | None = None,
        confidence: float = 1.0,
        importance: float = 0.5,
        source_id: str | None = None,
        ttl_days: int | None = None,
    ) -> dict:
        """
        Create a new memory.

        Args:
            scope: Scope for memory isolation (e.g., {"user_id": "123"})
            fact: The memory content/fact
            source_type: Source type ("extracted", "consolidated", "direct")
            topic: Optional topic/category
            embedding: Optional vector embedding (1536 dimensions for OpenAI)
            confidence: Confidence score (0.0-1.0)
            importance: Importance score (0.0-1.0)
            source_id: Optional source ID (session or job ID)
            ttl_days: Optional time-to-live in days

        Returns:
            Created memory response as dict

        Raises:
            ServiceUnavailableError: If service is unavailable
            httpx.HTTPStatusError: If API returns error status
        """
        request_data = {
            "scope": scope,
            "fact": fact,
            "source_type": source_type,
        }

        if topic is not None:
            request_data["topic"] = topic
        if embedding is not None:
            request_data["embedding"] = embedding
        if confidence is not None:
            request_data["confidence"] = confidence
        if importance is not None:
            request_data["importance"] = importance
        if source_id is not None:
            request_data["source_id"] = source_id
        if ttl_days is not None:
            request_data["ttl_days"] = ttl_days

        response = await self.post(
            "/api/v1/memories",
            json=request_data,
        )

        return response.json()

    async def get_memory(self, memory_id: UUID | str) -> dict:
        """
        Get a memory by ID.

        Args:
            memory_id: Memory UUID

        Returns:
            Memory response

        Raises:
            ServiceUnavailableError: If service is unavailable
            httpx.HTTPStatusError: If memory not found or other error
        """
        response = await self.get(f"/api/v1/memories/{memory_id}")
        return response.json()

    async def list_memories(
        self,
        scope_user_id: str | None = None,
        scope_org_id: str | None = None,
        topic: str | None = None,
        limit: int = 100,
        offset: int = 0,
        include_deleted: bool = False,
    ) -> dict:
        """
        List memories filtered by scope parameters.

        Args:
            scope_user_id: Filter by user ID in scope
            scope_org_id: Filter by organization ID in scope
            topic: Optional topic filter
            limit: Maximum number of results
            offset: Offset for pagination
            include_deleted: Include soft-deleted memories

        Returns:
            List of memories with pagination info

        Raises:
            ServiceUnavailableError: If service is unavailable
            httpx.HTTPStatusError: If required scope parameter missing
        """
        params = {
            "limit": limit,
            "offset": offset,
            "include_deleted": include_deleted,
        }

        if scope_user_id:
            params["scope_user_id"] = scope_user_id
        if scope_org_id:
            params["scope_org_id"] = scope_org_id
        if topic:
            params["topic"] = topic

        response = await self.get("/api/v1/memories", params=params)
        return response.json()

    async def update_memory(
        self,
        memory_id: UUID | str,
        fact: str | None = None,
        topic: str | None = None,
        embedding: list[float] | None = None,
        confidence: float | None = None,
        importance: float | None = None,
        change_reason: str | None = None,
    ) -> dict:
        """
        Update a memory.

        Args:
            memory_id: Memory UUID
            fact: Optional new fact content
            topic: Optional new topic
            embedding: Optional new embedding
            confidence: Optional new confidence score
            importance: Optional new importance score
            change_reason: Optional reason for the change (for revision tracking)

        Returns:
            Updated memory response

        Raises:
            ServiceUnavailableError: If service is unavailable
            httpx.HTTPStatusError: If memory not found or other error
        """
        request_data = {}
        if fact is not None:
            request_data["fact"] = fact
        if topic is not None:
            request_data["topic"] = topic
        if embedding is not None:
            request_data["embedding"] = embedding
        if confidence is not None:
            request_data["confidence"] = confidence
        if importance is not None:
            request_data["importance"] = importance
        if change_reason is not None:
            request_data["change_reason"] = change_reason

        response = await self.patch(
            f"/api/v1/memories/{memory_id}",
            json=request_data,
        )

        return response.json()

    async def delete_memory(self, memory_id: UUID | str, hard_delete: bool = False) -> dict:
        """
        Delete a memory (soft delete by default).

        Args:
            memory_id: Memory UUID
            hard_delete: If True, permanently delete; if False, soft delete

        Returns:
            Delete response with success status

        Raises:
            ServiceUnavailableError: If service is unavailable
            httpx.HTTPStatusError: If memory not found or other error
        """
        params = {"hard_delete": hard_delete}
        response = await self.delete(f"/api/v1/memories/{memory_id}", params=params)
        return response.json()

    async def search_memories(
        self,
        scope: dict[str, str],
        query_embedding: list[float],
        limit: int = 10,
        similarity_threshold: float = 0.7,
        topic: str | None = None,
    ) -> dict:
        """
        Search memories by vector similarity.

        Args:
            scope: Scope for memory isolation
            query_embedding: Query vector (1536 dimensions for OpenAI)
            limit: Maximum number of results
            similarity_threshold: Minimum similarity score (0.0-1.0)
            topic: Optional topic filter

        Returns:
            List of similar memories

        Raises:
            ServiceUnavailableError: If service is unavailable
        """
        request_data = {
            "scope": scope,
            "query_embedding": query_embedding,
            "limit": limit,
            "similarity_threshold": similarity_threshold,
        }

        if topic:
            request_data["topic"] = topic

        response = await self.post(
            "/api/v1/memories/search",
            json=request_data,
        )

        return response.json()
