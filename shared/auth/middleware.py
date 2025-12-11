"""
Authentication middleware for FastAPI applications.

Provides automatic authentication enforcement for all routes.
"""

from collections.abc import Callable
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from shared.auth.api_key import APIKeyHandler
from shared.auth.jwt import JWTHandler
from shared.auth.models import UserIdentity


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce authentication on all routes."""

    def __init__(
        self,
        app: Any,
        jwt_handler: JWTHandler | None = None,
        api_key_handler: APIKeyHandler | None = None,
        exempt_paths: list[str] | None = None,
    ):
        """
        Initialize authentication middleware.

        Args:
            app: FastAPI application
            jwt_handler: JWT handler for token validation
            api_key_handler: API key handler for key validation
            exempt_paths: List of paths that don't require authentication
        """
        super().__init__(app)
        self.jwt_handler = jwt_handler
        self.api_key_handler = api_key_handler
        self.exempt_paths = exempt_paths or [
            "/health",
            "/health/live",
            "/health/ready",
            "/health/detailed",
            "/health/services",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/metrics",
        ]

    def _is_exempt(self, path: str) -> bool:
        """
        Check if path is exempt from authentication.

        Args:
            path: Request path

        Returns:
            True if path is exempt
        """
        return any(path.startswith(exempt) for exempt in self.exempt_paths)

    async def _authenticate(self, request: Request) -> UserIdentity | None:
        """
        Authenticate request using JWT or API key.

        Args:
            request: HTTP request

        Returns:
            User identity if authenticated, None otherwise
        """
        # Try JWT authentication
        if self.jwt_handler:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header.replace("Bearer ", "")
                identity = self.jwt_handler.verify_token(token)
                if identity:
                    return identity

        # Try API key authentication
        if self.api_key_handler:
            api_key = request.headers.get("X-API-Key")
            if api_key:
                identity = self.api_key_handler.verify_api_key(api_key)
                if identity:
                    return identity

        return None

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with authentication.

        Args:
            request: HTTP request
            call_next: Next middleware in chain

        Returns:
            HTTP response

        Raises:
            AuthenticationError: If authentication is required but fails
        """
        # Skip authentication for exempt paths
        if self._is_exempt(request.url.path):
            return await call_next(request)

        # Authenticate request
        identity = await self._authenticate(request)

        if identity is None:
            # Return 401 Unauthorized
            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=401,
                content={
                    "detail": "Authentication required",
                    "error": "Missing or invalid authentication credentials",
                },
            )

        # Attach user identity to request state
        request.state.user = identity

        # Continue processing
        return await call_next(request)
