"""
Custom exceptions for ContextIQ.
"""

from typing import Any


class ContextIQError(Exception):
    """Base exception for all ContextIQ errors."""

    def __init__(self, message: str, error_code: str | None = None, details: dict | None = None):
        """
        Initialize exception.

        Args:
            message: Error message
            error_code: Optional error code
            details: Optional error details
        """
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(message)


# Database Errors


class DatabaseError(ContextIQError):
    """Database-related errors."""

    pass


class RecordNotFoundError(DatabaseError):
    """Record not found in database."""

    def __init__(self, entity: str, identifier: str | dict):
        """
        Initialize exception.

        Args:
            entity: Entity type (e.g., "Session", "Memory")
            identifier: Entity identifier
        """
        message = f"{entity} not found: {identifier}"
        super().__init__(
            message,
            error_code="RECORD_NOT_FOUND",
            details={"entity": entity, "identifier": str(identifier)},
        )


class DuplicateRecordError(DatabaseError):
    """Duplicate record in database."""

    def __init__(self, entity: str, field: str, value: str):
        """
        Initialize exception.

        Args:
            entity: Entity type
            field: Field name
            value: Field value
        """
        message = f"{entity} with {field}={value} already exists"
        super().__init__(
            message,
            error_code="DUPLICATE_RECORD",
            details={"entity": entity, "field": field, "value": value},
        )


# Validation Errors


class ValidationError(ContextIQError):
    """Validation errors."""

    def __init__(self, message: str, field: str | None = None, value: Any = None):
        """
        Initialize exception.

        Args:
            message: Error message
            field: Field name
            value: Field value
        """
        details = {}
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = str(value)
        super().__init__(message, error_code="VALIDATION_ERROR", details=details)


class ScopeValidationError(ValidationError):
    """Scope validation errors."""

    def __init__(self, message: str, scope: dict | None = None):
        """
        Initialize exception.

        Args:
            message: Error message
            scope: Invalid scope
        """
        super().__init__(message, field="scope", value=scope)


# Cache Errors


class CacheError(ContextIQError):
    """Cache-related errors."""

    pass


class CacheConnectionError(CacheError):
    """Cache connection errors."""

    def __init__(self, message: str = "Failed to connect to cache"):
        """Initialize exception."""
        super().__init__(message, error_code="CACHE_CONNECTION_ERROR")


# Messaging Errors


class MessagingError(ContextIQError):
    """Messaging-related errors."""

    pass


class MessagePublishError(MessagingError):
    """Message publishing errors."""

    def __init__(self, queue: str, message: str = "Failed to publish message"):
        """
        Initialize exception.

        Args:
            queue: Queue name
            message: Error message
        """
        super().__init__(message, error_code="MESSAGE_PUBLISH_ERROR", details={"queue": queue})


class MessageConsumeError(MessagingError):
    """Message consumption errors."""

    def __init__(self, queue: str, message: str = "Failed to consume message"):
        """
        Initialize exception.

        Args:
            queue: Queue name
            message: Error message
        """
        super().__init__(message, error_code="MESSAGE_CONSUME_ERROR", details={"queue": queue})


# Vector Store Errors


class VectorStoreError(ContextIQError):
    """Vector store errors."""

    pass


class VectorStoreConnectionError(VectorStoreError):
    """Vector store connection errors."""

    def __init__(self, message: str = "Failed to connect to vector store"):
        """Initialize exception."""
        super().__init__(message, error_code="VECTOR_STORE_CONNECTION_ERROR")


class CollectionNotFoundError(VectorStoreError):
    """Collection not found in vector store."""

    def __init__(self, collection: str):
        """
        Initialize exception.

        Args:
            collection: Collection name
        """
        message = f"Collection '{collection}' not found"
        super().__init__(
            message, error_code="COLLECTION_NOT_FOUND", details={"collection": collection}
        )


# LLM Errors


class LLMError(ContextIQError):
    """LLM-related errors."""

    pass


class LLMRateLimitError(LLMError):
    """LLM rate limit errors."""

    def __init__(self, message: str = "LLM rate limit exceeded"):
        """Initialize exception."""
        super().__init__(message, error_code="LLM_RATE_LIMIT")


class LLMTimeoutError(LLMError):
    """LLM timeout errors."""

    def __init__(self, message: str = "LLM request timed out"):
        """Initialize exception."""
        super().__init__(message, error_code="LLM_TIMEOUT")


# Configuration Errors


class ConfigurationError(ContextIQError):
    """Configuration errors."""

    def __init__(self, message: str, key: str | None = None):
        """
        Initialize exception.

        Args:
            message: Error message
            key: Configuration key
        """
        details = {"key": key} if key else {}
        super().__init__(message, error_code="CONFIGURATION_ERROR", details=details)
