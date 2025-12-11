"""
Authentication models and schemas.

Defines user identity, permissions, and authentication tokens.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AuthProvider(str, Enum):
    """Authentication provider types."""

    API_KEY = "api_key"
    JWT = "jwt"
    SERVICE = "service"


class Permission(str, Enum):
    """Permission types for authorization."""

    # Session permissions
    SESSION_CREATE = "session:create"
    SESSION_READ = "session:read"
    SESSION_UPDATE = "session:update"
    SESSION_DELETE = "session:delete"
    SESSION_LIST = "session:list"

    # Memory permissions
    MEMORY_CREATE = "memory:create"
    MEMORY_READ = "memory:read"
    MEMORY_UPDATE = "memory:update"
    MEMORY_DELETE = "memory:delete"
    MEMORY_SEARCH = "memory:search"
    MEMORY_LIST = "memory:list"

    # Admin permissions
    ADMIN_READ = "admin:read"
    ADMIN_WRITE = "admin:write"


class UserIdentity(BaseModel):
    """User identity information from authentication."""

    user_id: str = Field(..., description="Unique user identifier")
    org_id: str | None = Field(None, description="Organization identifier")
    email: str | None = Field(None, description="User email address")
    name: str | None = Field(None, description="User display name")
    permissions: list[Permission] = Field(default_factory=list, description="User permissions")
    provider: AuthProvider = Field(..., description="Authentication provider")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    def has_permission(self, permission: Permission) -> bool:
        """
        Check if user has a specific permission.

        Args:
            permission: Permission to check

        Returns:
            True if user has permission
        """
        return permission in self.permissions

    def has_any_permission(self, permissions: list[Permission]) -> bool:
        """
        Check if user has any of the specified permissions.

        Args:
            permissions: List of permissions to check

        Returns:
            True if user has at least one permission
        """
        return any(p in self.permissions for p in permissions)

    def has_all_permissions(self, permissions: list[Permission]) -> bool:
        """
        Check if user has all of the specified permissions.

        Args:
            permissions: List of permissions to check

        Returns:
            True if user has all permissions
        """
        return all(p in self.permissions for p in permissions)


class TokenPayload(BaseModel):
    """JWT token payload."""

    sub: str = Field(..., description="Subject (user_id)")
    org_id: str | None = Field(None, description="Organization ID")
    email: str | None = Field(None, description="User email")
    name: str | None = Field(None, description="User name")
    permissions: list[str] = Field(default_factory=list, description="Permissions")
    exp: int = Field(..., description="Expiration timestamp")
    iat: int = Field(..., description="Issued at timestamp")
    iss: str = Field(default="contextiq", description="Issuer")


class APIKeyInfo(BaseModel):
    """API key information."""

    key_id: str = Field(..., description="API key identifier")
    user_id: str = Field(..., description="User ID associated with key")
    org_id: str | None = Field(None, description="Organization ID")
    permissions: list[Permission] = Field(..., description="API key permissions")
    expires_at: datetime | None = Field(None, description="Expiration timestamp")
    rate_limit: int = Field(default=1000, description="Requests per hour")
    is_active: bool = Field(default=True, description="Whether key is active")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
