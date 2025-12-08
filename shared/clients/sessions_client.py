"""HTTP client for Sessions Service."""

import logging
from uuid import UUID

from shared.clients.base import BaseHTTPClient
from shared.clients.config import http_client_settings

logger = logging.getLogger(__name__)


class SessionsServiceClient(BaseHTTPClient):
    """HTTP client for communicating with the Sessions Service."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout: int | None = None,
        max_retries: int | None = None,
        retry_delay: float | None = None,
    ):
        """
        Initialize Sessions Service client.

        Args:
            base_url: Base URL for Sessions Service (defaults to config)
            timeout: Request timeout in seconds (defaults to config)
            max_retries: Maximum retry attempts (defaults to config)
            retry_delay: Delay between retries (defaults to config)
        """
        super().__init__(
            base_url=base_url or http_client_settings.sessions_service_url,
            timeout=timeout or http_client_settings.sessions_service_timeout,
            max_retries=max_retries or http_client_settings.sessions_service_max_retries,
            retry_delay=retry_delay or http_client_settings.sessions_service_retry_delay,
        )

    async def create_session(
        self,
        scope: dict[str, str],
        title: str | None = None,
        description: str | None = None,
        state: dict | None = None,
        ttl: int | None = None,
    ) -> dict:
        """
        Create a new session.

        Args:
            scope: Scope for session isolation (e.g., {"user_id": "123"})
            title: Optional session title
            description: Optional session description
            state: Optional initial state
            ttl: Optional time-to-live in seconds

        Returns:
            Created session response

        Raises:
            ServiceUnavailableError: If service is unavailable
            httpx.HTTPStatusError: If API returns error status
        """
        request_data = {
            "scope": scope,
            "state": state or {},
        }

        if title is not None:
            request_data["title"] = title
        if description is not None:
            request_data["description"] = description
        if ttl is not None:
            request_data["ttl"] = ttl

        response = await self.post(
            "/api/v1/sessions",
            json=request_data,
        )

        return response.json()

    async def get_session(self, session_id: UUID | str) -> dict:
        """
        Get a session by ID.

        Args:
            session_id: Session UUID

        Returns:
            Session response

        Raises:
            ServiceUnavailableError: If service is unavailable
            httpx.HTTPStatusError: If session not found or other error
        """
        response = await self.get(f"/api/v1/sessions/{session_id}")
        return response.json()

    async def list_sessions(
        self,
        scope_user_id: str | None = None,
        scope_agent_id: str | None = None,
        include_ended: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> dict:
        """
        List sessions filtered by scope parameters.

        Args:
            scope_user_id: Filter by user ID in scope
            scope_agent_id: Filter by agent ID in scope
            include_ended: Include ended sessions
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of sessions

        Raises:
            ServiceUnavailableError: If service is unavailable
        """
        params = {
            "limit": limit,
            "offset": offset,
            "include_ended": include_ended,
        }

        if scope_user_id:
            params["scope_user_id"] = scope_user_id
        if scope_agent_id:
            params["scope_agent_id"] = scope_agent_id

        response = await self.get("/api/v1/sessions", params=params)
        return response.json()

    async def update_session_state(
        self,
        session_id: UUID | str,
        state: dict,
    ) -> dict:
        """
        Update session state.

        Args:
            session_id: Session UUID
            state: New state to merge with existing state

        Returns:
            Updated session response

        Raises:
            ServiceUnavailableError: If service is unavailable
            httpx.HTTPStatusError: If session not found or other error
        """
        request_data = {"state": state}

        response = await self.patch(
            f"/api/v1/sessions/{session_id}/state",
            json=request_data,
        )

        return response.json()

    async def end_session(self, session_id: UUID | str) -> dict:
        """
        End a session.

        Args:
            session_id: Session UUID

        Returns:
            Ended session response

        Raises:
            ServiceUnavailableError: If service is unavailable
            httpx.HTTPStatusError: If session not found or other error
        """
        response = await self.post(f"/api/v1/sessions/{session_id}/end")
        return response.json()

    async def delete_session(self, session_id: UUID | str) -> dict:
        """
        Delete a session.

        Args:
            session_id: Session UUID

        Returns:
            Delete response with success status

        Raises:
            ServiceUnavailableError: If service is unavailable
            httpx.HTTPStatusError: If session not found or other error
        """
        response = await self.delete(f"/api/v1/sessions/{session_id}")
        return response.json()

    # Event methods

    async def create_event(
        self,
        session_id: UUID | str,
        event_type: str,
        data: dict,
        input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> dict:
        """
        Create a new event in a session.

        Args:
            session_id: Session UUID
            event_type: Type of event (e.g., "message", "tool_call")
            data: Event data
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Created event response

        Raises:
            ServiceUnavailableError: If service is unavailable
            httpx.HTTPStatusError: If session not found or other error
        """
        request_data = {
            "event_type": event_type,
            "data": data,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        }

        response = await self.post(
            f"/api/v1/sessions/{session_id}/events",
            json=request_data,
        )

        return response.json()

    async def get_event(self, session_id: UUID | str, event_id: UUID | str) -> dict:
        """
        Get an event by ID.

        Args:
            session_id: Session UUID
            event_id: Event UUID

        Returns:
            Event response

        Raises:
            ServiceUnavailableError: If service is unavailable
            httpx.HTTPStatusError: If event not found or other error
        """
        response = await self.get(f"/api/v1/sessions/{session_id}/events/{event_id}")
        return response.json()

    async def list_events(
        self,
        session_id: UUID | str,
        event_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict:
        """
        List events for a session.

        Args:
            session_id: Session UUID
            event_type: Optional filter by event type
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of events

        Raises:
            ServiceUnavailableError: If service is unavailable
            httpx.HTTPStatusError: If session not found or other error
        """
        params = {
            "limit": limit,
            "offset": offset,
        }

        if event_type:
            params["event_type"] = event_type

        response = await self.get(
            f"/api/v1/sessions/{session_id}/events",
            params=params,
        )

        return response.json()
