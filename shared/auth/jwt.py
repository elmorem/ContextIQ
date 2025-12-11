"""
JWT token utilities for authentication.

Provides JWT encoding, decoding, and validation.
"""

from datetime import datetime, timedelta

import jwt
from jwt.exceptions import DecodeError, ExpiredSignatureError, InvalidTokenError

from shared.auth.models import AuthProvider, Permission, TokenPayload, UserIdentity


class JWTHandler:
    """Handler for JWT token operations."""

    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 60,
        issuer: str = "contextiq",
    ):
        """
        Initialize JWT handler.

        Args:
            secret_key: Secret key for signing tokens
            algorithm: JWT algorithm (default: HS256)
            access_token_expire_minutes: Token expiration time in minutes
            issuer: Token issuer identifier
        """
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.issuer = issuer

    def create_access_token(
        self,
        user_id: str,
        org_id: str | None = None,
        email: str | None = None,
        name: str | None = None,
        permissions: list[Permission] | None = None,
        expires_delta: timedelta | None = None,
    ) -> str:
        """
        Create a JWT access token.

        Args:
            user_id: User identifier
            org_id: Organization identifier
            email: User email
            name: User name
            permissions: User permissions
            expires_delta: Custom expiration time delta

        Returns:
            Encoded JWT token
        """
        if expires_delta is None:
            expires_delta = timedelta(minutes=self.access_token_expire_minutes)

        now = datetime.utcnow()
        expire = now + expires_delta

        payload = TokenPayload(
            sub=user_id,
            org_id=org_id,
            email=email,
            name=name,
            permissions=[p.value for p in (permissions or [])],
            exp=int(expire.timestamp()),
            iat=int(now.timestamp()),
            iss=self.issuer,
        )

        return jwt.encode(payload.model_dump(), self.secret_key, algorithm=self.algorithm)

    def decode_token(self, token: str) -> TokenPayload:
        """
        Decode and validate a JWT token.

        Args:
            token: JWT token string

        Returns:
            Token payload

        Raises:
            ExpiredSignatureError: If token is expired
            InvalidTokenError: If token is invalid
        """
        try:
            payload = jwt.decode(
                token, self.secret_key, algorithms=[self.algorithm], issuer=self.issuer
            )
            return TokenPayload(**payload)
        except ExpiredSignatureError as e:
            raise ExpiredSignatureError("Token has expired") from e
        except DecodeError as e:
            raise InvalidTokenError("Invalid token format") from e
        except Exception as e:
            raise InvalidTokenError(f"Token validation failed: {str(e)}") from e

    def verify_token(self, token: str) -> UserIdentity | None:
        """
        Verify token and extract user identity.

        Args:
            token: JWT token string

        Returns:
            User identity if valid, None otherwise
        """
        try:
            payload = self.decode_token(token)

            return UserIdentity(
                user_id=payload.sub,
                org_id=payload.org_id,
                email=payload.email,
                name=payload.name,
                permissions=[Permission(p) for p in payload.permissions],
                provider=AuthProvider.JWT,
                metadata={"exp": payload.exp, "iat": payload.iat, "iss": payload.iss},
            )
        except (ExpiredSignatureError, InvalidTokenError):
            return None

    def refresh_token(self, token: str) -> str | None:
        """
        Refresh an existing token.

        Args:
            token: Current JWT token

        Returns:
            New JWT token if current token is valid, None otherwise
        """
        identity = self.verify_token(token)
        if identity is None:
            return None

        return self.create_access_token(
            user_id=identity.user_id,
            org_id=identity.org_id,
            email=identity.email,
            name=identity.name,
            permissions=identity.permissions,
        )
