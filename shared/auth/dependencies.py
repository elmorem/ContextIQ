"""
FastAPI dependencies for authentication and authorization.

Provides dependency injection for user identity and permission checking.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from shared.auth.api_key import APIKeyHandler
from shared.auth.jwt import JWTHandler
from shared.auth.models import Permission, UserIdentity

# Security schemes
bearer_scheme = HTTPBearer(auto_error=False)
api_key_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)


class AuthenticationError(HTTPException):
    """Authentication failed exception."""

    def __init__(self, detail: str = "Authentication required"):
        """Initialize authentication error."""
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


class AuthorizationError(HTTPException):
    """Authorization failed exception."""

    def __init__(self, detail: str = "Insufficient permissions"):
        """Initialize authorization error."""
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def get_jwt_handler() -> JWTHandler:
    """
    Get JWT handler instance.

    This should be overridden in your application to provide
    the actual JWT handler with your secret key.

    Returns:
        JWT handler instance

    Raises:
        NotImplementedError: If not overridden in application
    """
    raise NotImplementedError("JWT handler not configured. Override get_jwt_handler dependency.")


def get_api_key_handler() -> APIKeyHandler:
    """
    Get API key handler instance.

    This should be overridden in your application to provide
    the actual API key handler with your keys.

    Returns:
        API key handler instance

    Raises:
        NotImplementedError: If not overridden in application
    """
    raise NotImplementedError(
        "API key handler not configured. Override get_api_key_handler dependency."
    )


async def get_current_user(
    bearer: Annotated[HTTPAuthorizationCredentials | None, Security(bearer_scheme)] = None,
    api_key: Annotated[str | None, Security(api_key_scheme)] = None,
    jwt_handler: Annotated[JWTHandler | None, Depends(get_jwt_handler)] = None,
    api_key_handler: Annotated[APIKeyHandler | None, Depends(get_api_key_handler)] = None,
) -> UserIdentity:
    """
    Get current authenticated user.

    Supports both JWT bearer tokens and API keys.

    Args:
        bearer: Bearer token from Authorization header
        api_key: API key from X-API-Key header
        jwt_handler: JWT handler instance
        api_key_handler: API key handler instance

    Returns:
        User identity

    Raises:
        AuthenticationError: If authentication fails
    """
    # Try JWT authentication first
    if bearer is not None and jwt_handler is not None:
        identity = jwt_handler.verify_token(bearer.credentials)
        if identity is not None:
            return identity

    # Try API key authentication
    if api_key is not None and api_key_handler is not None:
        identity = api_key_handler.verify_api_key(api_key)
        if identity is not None:
            return identity

    raise AuthenticationError("Invalid or missing authentication credentials")


async def get_current_user_optional(
    bearer: Annotated[HTTPAuthorizationCredentials | None, Security(bearer_scheme)] = None,
    api_key: Annotated[str | None, Security(api_key_scheme)] = None,
    jwt_handler: Annotated[JWTHandler | None, Depends(get_jwt_handler)] = None,
    api_key_handler: Annotated[APIKeyHandler | None, Depends(get_api_key_handler)] = None,
) -> UserIdentity | None:
    """
    Get current authenticated user (optional).

    Returns None if not authenticated instead of raising an error.

    Args:
        bearer: Bearer token from Authorization header
        api_key: API key from X-API-Key header
        jwt_handler: JWT handler instance
        api_key_handler: API key handler instance

    Returns:
        User identity or None
    """
    try:
        return await get_current_user(bearer, api_key, jwt_handler, api_key_handler)
    except AuthenticationError:
        return None


def require_permissions(*permissions: Permission) -> type[UserIdentity]:
    """
    Dependency factory to require specific permissions.

    Args:
        *permissions: Required permissions

    Returns:
        Dependency function that validates permissions
    """

    async def check_permissions(
        current_user: Annotated[UserIdentity, Depends(get_current_user)],
    ) -> UserIdentity:
        """
        Check if user has required permissions.

        Args:
            current_user: Current user identity

        Returns:
            User identity if authorized

        Raises:
            AuthorizationError: If user lacks required permissions
        """
        if not current_user.has_all_permissions(list(permissions)):
            raise AuthorizationError(
                f"Missing required permissions: {[p.value for p in permissions]}"
            )
        return current_user

    return check_permissions  # type: ignore[return-value]


def require_any_permission(*permissions: Permission) -> type[UserIdentity]:
    """
    Dependency factory to require any of the specified permissions.

    Args:
        *permissions: Permissions (user needs at least one)

    Returns:
        Dependency function that validates permissions
    """

    async def check_permissions(
        current_user: Annotated[UserIdentity, Depends(get_current_user)],
    ) -> UserIdentity:
        """
        Check if user has any of the required permissions.

        Args:
            current_user: Current user identity

        Returns:
            User identity if authorized

        Raises:
            AuthorizationError: If user lacks all required permissions
        """
        if not current_user.has_any_permission(list(permissions)):
            raise AuthorizationError(
                f"Missing one of required permissions: {[p.value for p in permissions]}"
            )
        return current_user

    return check_permissions  # type: ignore[return-value]
