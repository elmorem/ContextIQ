"""
Memories API v1 endpoints.

Provides REST API for memory management with CRUD operations.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from services.memory.app.api.schemas.requests import (
    CreateMemoryRequest,
    UpdateMemoryRequest,
)
from services.memory.app.api.schemas.responses import (
    DeleteResponse,
    MemoryListResponse,
    MemoryResponse,
)
from services.memory.app.core.dependencies import get_memory_service
from services.memory.app.services.memory_service import MemoryService

router = APIRouter(prefix="/api/v1")


@router.post(
    "/memories",
    response_model=MemoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new memory",
)
async def create_memory(
    request: CreateMemoryRequest,
    service: Annotated[MemoryService, Depends(get_memory_service)],
) -> MemoryResponse:
    """Create a new memory with the provided scope and fact."""
    memory = await service.create_memory(
        scope=request.scope,
        fact=request.fact,
        source_type=request.source_type,
        topic=request.topic,
        embedding=request.embedding,
        confidence=request.confidence,
        importance=request.importance,
        source_id=UUID(request.source_id) if request.source_id else None,
        ttl_days=request.ttl_days,
    )
    await service.db.commit()
    return MemoryResponse.model_validate(memory)


@router.get(
    "/memories/{memory_id}",
    response_model=MemoryResponse,
    summary="Get a memory by ID",
)
async def get_memory(
    memory_id: UUID,
    service: Annotated[MemoryService, Depends(get_memory_service)],
) -> MemoryResponse:
    """Retrieve a memory by its ID and update access tracking."""
    memory = await service.get_memory(memory_id)
    if memory is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Memory not found: {memory_id}",
        )
    await service.db.commit()
    return MemoryResponse.model_validate(memory)


@router.get(
    "/memories",
    response_model=MemoryListResponse,
    summary="List memories by scope",
)
async def list_memories(
    service: Annotated[MemoryService, Depends(get_memory_service)],
    scope_user_id: Annotated[str | None, Query()] = None,
    scope_org_id: Annotated[str | None, Query()] = None,
    topic: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
    include_deleted: Annotated[bool, Query()] = False,
) -> MemoryListResponse:
    """List memories filtered by scope with pagination."""
    # Build scope filter
    scope = {}
    if scope_user_id:
        scope["user_id"] = scope_user_id
    if scope_org_id:
        scope["org_id"] = scope_org_id

    if not scope:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one scope parameter (scope_user_id or scope_org_id) is required",
        )

    # Get memories
    memories = await service.get_memories_by_scope(
        scope=scope,
        topic=topic,
        limit=limit,
        offset=offset,
        include_deleted=include_deleted,
    )

    # Get total count
    total = await service.count_memories(
        scope=scope,
        topic=topic,
        include_deleted=include_deleted,
    )

    return MemoryListResponse(
        memories=[MemoryResponse.model_validate(m) for m in memories],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.patch(
    "/memories/{memory_id}",
    response_model=MemoryResponse,
    summary="Update a memory",
)
async def update_memory(
    memory_id: UUID,
    request: UpdateMemoryRequest,
    service: Annotated[MemoryService, Depends(get_memory_service)],
) -> MemoryResponse:
    """Update a memory with optional revision tracking."""
    memory = await service.update_memory(
        memory_id=memory_id,
        fact=request.fact,
        topic=request.topic,
        embedding=request.embedding,
        confidence=request.confidence,
        importance=request.importance,
        change_reason=request.change_reason,
    )

    if memory is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Memory not found: {memory_id}",
        )

    await service.db.commit()
    return MemoryResponse.model_validate(memory)


@router.delete(
    "/memories/{memory_id}",
    response_model=DeleteResponse,
    summary="Delete a memory",
)
async def delete_memory(
    memory_id: UUID,
    service: Annotated[MemoryService, Depends(get_memory_service)],
) -> DeleteResponse:
    """Soft delete a memory."""
    success = await service.delete_memory(memory_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Memory not found: {memory_id}",
        )

    await service.db.commit()
    return DeleteResponse(
        success=True,
        message="Memory deleted successfully",
    )
