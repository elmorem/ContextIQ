"""
API key authentication utilities.

Provides API key validation and management.
"""

import hashlib
import secrets
from datetime import datetime

from shared.auth.models import APIKeyInfo, AuthProvider, UserIdentity


class APIKeyHandler:
    """Handler for API key authentication."""

    def __init__(self, api_keys: dict[str, APIKeyInfo] | None = None):
        """
        Initialize API key handler.

        Args:
            api_keys: Dictionary mapping API key hashes to key info
        """
        self.api_keys = api_keys or {}

    def generate_api_key(self) -> str:
        """
        Generate a new API key.

        Returns:
            API key string (format: ck_xxxxx...)
        """
        return f"ck_{secrets.token_urlsafe(32)}"

    def hash_api_key(self, api_key: str) -> str:
        """
        Hash an API key for storage.

        Args:
            api_key: API key string

        Returns:
            SHA-256 hash of the API key
        """
        return hashlib.sha256(api_key.encode()).hexdigest()

    def register_api_key(self, api_key: str, key_info: APIKeyInfo) -> None:
        """
        Register a new API key.

        Args:
            api_key: API key string
            key_info: API key information
        """
        key_hash = self.hash_api_key(api_key)
        self.api_keys[key_hash] = key_info

    def verify_api_key(self, api_key: str) -> UserIdentity | None:
        """
        Verify an API key and extract user identity.

        Args:
            api_key: API key string

        Returns:
            User identity if valid, None otherwise
        """
        key_hash = self.hash_api_key(api_key)
        key_info = self.api_keys.get(key_hash)

        if key_info is None:
            return None

        # Check if key is active
        if not key_info.is_active:
            return None

        # Check if key is expired
        if key_info.expires_at is not None and datetime.utcnow() > key_info.expires_at:
            return None

        return UserIdentity(
            user_id=key_info.user_id,
            org_id=key_info.org_id,
            email=None,
            name=None,
            permissions=key_info.permissions,
            provider=AuthProvider.API_KEY,
            metadata={
                "key_id": key_info.key_id,
                "rate_limit": key_info.rate_limit,
                **key_info.metadata,
            },
        )
