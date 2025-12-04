"""
Scope utility functions for memory scoping.
"""

import hashlib
import json

from shared.exceptions import ScopeValidationError

MAX_SCOPE_KEYS = 5
MAX_KEY_LENGTH = 100
MAX_VALUE_LENGTH = 500


def validate_scope(scope: dict[str, str]) -> None:
    """
    Validate scope dictionary.

    Args:
        scope: Scope dictionary to validate

    Raises:
        ScopeValidationError: If scope is invalid
    """
    # Check if scope is a dictionary
    if not isinstance(scope, dict):
        raise ScopeValidationError("Scope must be a dictionary")

    # Check if empty
    if not scope:
        raise ScopeValidationError("Scope cannot be empty")

    # Check number of keys
    if len(scope) > MAX_SCOPE_KEYS:
        raise ScopeValidationError(f"Scope cannot have more than {MAX_SCOPE_KEYS} keys")

    # Validate each key-value pair
    for key, value in scope.items():
        # Check key type
        if not isinstance(key, str):
            raise ScopeValidationError(f"Scope key must be string, got {type(key).__name__}")

        # Check value type
        if not isinstance(value, str):
            raise ScopeValidationError(f"Scope value must be string, got {type(value).__name__}")

        # Check key length
        if len(key) == 0:
            raise ScopeValidationError("Scope key cannot be empty")

        if len(key) > MAX_KEY_LENGTH:
            raise ScopeValidationError(
                f"Scope key '{key}' exceeds maximum length of {MAX_KEY_LENGTH}"
            )

        # Check value length
        if len(value) == 0:
            raise ScopeValidationError(f"Scope value for key '{key}' cannot be empty")

        if len(value) > MAX_VALUE_LENGTH:
            raise ScopeValidationError(
                f"Scope value for key '{key}' exceeds maximum length of {MAX_VALUE_LENGTH}"
            )

        # Check for invalid characters
        if not _is_valid_key(key):
            raise ScopeValidationError(
                f"Scope key '{key}' contains invalid characters. Only alphanumeric, underscore, and hyphen allowed"
            )


def normalize_scope(scope: dict[str, str]) -> dict[str, str]:
    """
    Normalize scope dictionary (sort keys, trim values).

    Args:
        scope: Scope dictionary to normalize

    Returns:
        Normalized scope dictionary

    Raises:
        ScopeValidationError: If scope is invalid
    """
    validate_scope(scope)

    # Sort by keys and trim values
    normalized = {key: value.strip() for key, value in sorted(scope.items())}

    return normalized


def hash_scope(scope: dict[str, str]) -> str:
    """
    Generate consistent hash for scope.

    Args:
        scope: Scope dictionary

    Returns:
        SHA256 hash of normalized scope

    Raises:
        ScopeValidationError: If scope is invalid
    """
    normalized = normalize_scope(scope)

    # Create deterministic JSON representation
    scope_json = json.dumps(normalized, sort_keys=True, separators=(",", ":"))

    # Generate hash
    scope_hash = hashlib.sha256(scope_json.encode()).hexdigest()

    return scope_hash


def _is_valid_key(key: str) -> bool:
    """
    Check if scope key contains only valid characters.

    Args:
        key: Key to validate

    Returns:
        True if valid, False otherwise
    """
    import re

    # Allow alphanumeric, underscore, and hyphen
    pattern = r"^[a-zA-Z0-9_-]+$"
    return bool(re.match(pattern, key))


def scope_matches(scope1: dict[str, str], scope2: dict[str, str]) -> bool:
    """
    Check if two scopes match exactly.

    Args:
        scope1: First scope
        scope2: Second scope

    Returns:
        True if scopes match, False otherwise
    """
    try:
        return hash_scope(scope1) == hash_scope(scope2)
    except ScopeValidationError:
        return False


def scope_contains(parent_scope: dict[str, str], child_scope: dict[str, str]) -> bool:
    """
    Check if parent scope contains all keys from child scope with matching values.

    Args:
        parent_scope: Parent scope (broader)
        child_scope: Child scope (narrower)

    Returns:
        True if parent contains child, False otherwise

    Example:
        parent = {"user_id": "123", "org_id": "456"}
        child = {"user_id": "123"}
        scope_contains(parent, child) -> True
    """
    try:
        parent_normalized = normalize_scope(parent_scope)
        child_normalized = normalize_scope(child_scope)

        # Check if all child keys exist in parent with same values
        for key, value in child_normalized.items():
            if key not in parent_normalized or parent_normalized[key] != value:
                return False

        return True

    except ScopeValidationError:
        return False


def merge_scopes(*scopes: dict[str, str]) -> dict[str, str]:
    """
    Merge multiple scopes (later scopes override earlier ones).

    Args:
        *scopes: Scopes to merge

    Returns:
        Merged scope dictionary

    Raises:
        ScopeValidationError: If any scope is invalid or result exceeds limits
    """
    merged: dict[str, str] = {}

    for scope in scopes:
        validate_scope(scope)
        merged.update(scope)

    # Validate merged result
    validate_scope(merged)

    return normalize_scope(merged)


def filter_scope(scope: dict[str, str], keys: list[str]) -> dict[str, str]:
    """
    Filter scope to only include specified keys.

    Args:
        scope: Scope to filter
        keys: Keys to keep

    Returns:
        Filtered scope

    Raises:
        ScopeValidationError: If filtered scope is invalid
    """
    filtered = {k: v for k, v in scope.items() if k in keys}

    if not filtered:
        raise ScopeValidationError("Filtered scope cannot be empty")

    validate_scope(filtered)
    return normalize_scope(filtered)
