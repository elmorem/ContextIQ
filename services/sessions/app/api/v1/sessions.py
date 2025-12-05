"""
Sessions API v1 endpoints.

Provides REST API for session and event management.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from services.sessions.app.api.schemas.requests import (
    CreateEventRequest,
    CreateSessionRequest,
    UpdateSessionStateRequest,
)
from services.sessions.app.api.schemas.responses import (
    DeleteResponse,
    EventListResponse,
    EventResponse,
    SessionListResponse,
    SessionResponse,
)
from services.sessions.app.core.dependencies import (
    get_event_repository,
    get_session_repository,
    get_session_service,
)
from services.sessions.app.db.repositories.event_repository import EventRepository
from services.sessions.app.db.repositories.session_repository import SessionRepository
from services.sessions.app.services.session_service import (
    InvalidTTLError,
    SessionExpiredError,
    SessionNotFoundError,
    SessionService,
)

router = APIRouter(prefix="/api/v1")


@router.post(
    "/sessions",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new session",
)
async def create_session(
    request: CreateSessionRequest,
    service: Annotated[SessionService, Depends(get_session_service)],
) -> SessionResponse:
    """Create a new session with the provided scope and optional metadata."""
    try:
        session = await service.create_session(
            scope=request.scope,
            title=request.title,
            description=request.description,
            state=request.state,
            ttl=request.ttl,
        )
        return SessionResponse.model_validate(session)
    except InvalidTTLError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid TTL: {e.ttl} exceeds maximum {e.max_ttl}",
        ) from e


@router.get(
    "/sessions/{session_id}",
    response_model=SessionResponse,
    summary="Get a session by ID",
)
async def get_session(
    session_id: UUID,
    service: Annotated[SessionService, Depends(get_session_service)],
) -> SessionResponse:
    """Retrieve a session by its ID."""
    try:
        session = await service.get_session(session_id)
        return SessionResponse.model_validate(session)
    except SessionNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {e.session_id}",
        ) from e
    except SessionExpiredError as e:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail=f"Session expired: {e.session_id}",
        ) from e


@router.get(
    "/sessions",
    response_model=SessionListResponse,
    summary="List sessions by scope",
)
async def list_sessions(
    session_repo: Annotated[SessionRepository, Depends(get_session_repository)],
    scope_user_id: Annotated[str | None, Query()] = None,
    active_only: Annotated[bool, Query()] = True,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> SessionListResponse:
    """List sessions filtered by scope criteria."""
    scope_filter = None
    if scope_user_id:
        scope_filter = {"user_id": scope_user_id}

    sessions = await session_repo.list_sessions(
        scope=scope_filter,
        active_only=active_only,
        limit=limit,
        offset=offset,
    )

    total = await session_repo.count_sessions(
        scope=scope_filter,
        active_only=active_only,
    )

    return SessionListResponse(
        sessions=[SessionResponse.model_validate(s) for s in sessions],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.put(
    "/sessions/{session_id}/state",
    response_model=SessionResponse,
    summary="Update session state",
)
async def update_session_state(
    session_id: UUID,
    request: UpdateSessionStateRequest,
    service: Annotated[SessionService, Depends(get_session_service)],
) -> SessionResponse:
    """Update the state of a session, either merging or replacing it."""
    try:
        session = await service.update_session_state(
            session_id=session_id,
            state=request.state,
            merge=request.merge,
        )
        return SessionResponse.model_validate(session)
    except SessionNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {e.session_id}",
        ) from e
    except SessionExpiredError as e:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail=f"Session expired: {e.session_id}",
        ) from e


@router.post(
    "/sessions/{session_id}/events",
    response_model=EventResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add an event to a session",
)
async def create_event(
    session_id: UUID,
    request: CreateEventRequest,
    service: Annotated[SessionService, Depends(get_session_service)],
) -> EventResponse:
    """Add a new event to a session and update token counts."""
    try:
        event = await service.add_event(
            session_id=session_id,
            event_type=request.event_type,
            data=request.data,
            input_tokens=request.input_tokens,
            output_tokens=request.output_tokens,
        )
        return EventResponse.model_validate(event)
    except SessionNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {e.session_id}",
        ) from e
    except SessionExpiredError as e:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail=f"Session expired: {e.session_id}",
        ) from e


@router.get(
    "/sessions/{session_id}/events",
    response_model=EventListResponse,
    summary="List events for a session",
)
async def list_events(
    session_id: UUID,
    event_repo: Annotated[EventRepository, Depends(get_event_repository)],
    event_type: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> EventListResponse:
    """List events for a specific session."""
    events = await event_repo.list_events(
        session_id=session_id,
        event_type=event_type,
        limit=limit,
        offset=offset,
    )

    total = await event_repo.count_events(
        session_id=session_id,
        event_type=event_type,
    )

    return EventListResponse(
        events=[EventResponse.model_validate(e) for e in events],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.delete(
    "/sessions/{session_id}",
    response_model=DeleteResponse,
    summary="Delete a session",
)
async def delete_session(
    session_id: UUID,
    service: Annotated[SessionService, Depends(get_session_service)],
) -> DeleteResponse:
    """Delete a session and all its associated events."""
    try:
        await service.delete_session(session_id)
        return DeleteResponse(
            success=True,
            message=f"Session {session_id} deleted successfully",
        )
    except SessionNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {e.session_id}",
        ) from e
