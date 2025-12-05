"""
Revisions API v1 endpoints.

Provides REST API for memory revision history.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from services.memory.app.api.schemas.responses import RevisionListResponse, RevisionResponse
from services.memory.app.core.dependencies import get_revision_service
from services.memory.app.services.revision_service import RevisionService

router = APIRouter(prefix="/api/v1")


@router.get(
    "/memories/{memory_id}/revisions",
    response_model=RevisionListResponse,
    summary="Get revision history for a memory",
)
async def list_revisions(
    memory_id: UUID,
    service: Annotated[RevisionService, Depends(get_revision_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> RevisionListResponse:
    """
    Retrieve revision history for a memory with pagination.

    Returns revisions ordered by revision number descending (newest first).
    """
    # Get revisions
    revisions = await service.get_memory_history(
        memory_id=memory_id,
        limit=limit,
        offset=offset,
    )

    # Get total count
    total = await service.count_revisions(memory_id)

    return RevisionListResponse(
        revisions=[RevisionResponse.model_validate(r) for r in revisions],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/memories/{memory_id}/revisions/{revision_number}",
    response_model=RevisionResponse,
    summary="Get a specific revision by number",
)
async def get_revision(
    memory_id: UUID,
    revision_number: int,
    service: Annotated[RevisionService, Depends(get_revision_service)],
) -> RevisionResponse:
    """
    Retrieve a specific revision by its revision number.

    Args:
        memory_id: Memory ID
        revision_number: Sequential revision number (1, 2, 3, ...)
    """
    revision = await service.get_revision_by_number(
        memory_id=memory_id,
        revision_number=revision_number,
    )

    if revision is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Revision {revision_number} not found for memory {memory_id}",
        )

    return RevisionResponse.model_validate(revision)
