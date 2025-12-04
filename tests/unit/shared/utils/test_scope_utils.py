"""
Tests for scope utilities.
"""

import pytest

from shared.exceptions import ScopeValidationError
from shared.utils.scope_utils import (
    filter_scope,
    hash_scope,
    merge_scopes,
    normalize_scope,
    scope_contains,
    scope_matches,
    validate_scope,
)


class TestValidateScope:
    """Tests for validate_scope."""

    def test_valid_scope(self):
        """Test valid scope passes validation."""
        scope = {"user_id": "123", "org_id": "456"}
        validate_scope(scope)  # Should not raise

    def test_empty_scope_raises_error(self):
        """Test that empty scope raises error."""
        with pytest.raises(ScopeValidationError, match="cannot be empty"):
            validate_scope({})

    def test_non_dict_raises_error(self):
        """Test that non-dict raises error."""
        with pytest.raises(ScopeValidationError, match="must be a dictionary"):
            validate_scope("not-a-dict")

    def test_too_many_keys_raises_error(self):
        """Test that too many keys raises error."""
        scope = {f"key{i}": f"value{i}" for i in range(10)}
        with pytest.raises(ScopeValidationError, match="cannot have more than"):
            validate_scope(scope)

    def test_non_string_key_raises_error(self):
        """Test that non-string key raises error."""
        scope = {123: "value"}
        with pytest.raises(ScopeValidationError, match="key must be string"):
            validate_scope(scope)

    def test_non_string_value_raises_error(self):
        """Test that non-string value raises error."""
        scope = {"key": 123}
        with pytest.raises(ScopeValidationError, match="value must be string"):
            validate_scope(scope)

    def test_empty_key_raises_error(self):
        """Test that empty key raises error."""
        scope = {"": "value"}
        with pytest.raises(ScopeValidationError, match="key cannot be empty"):
            validate_scope(scope)

    def test_empty_value_raises_error(self):
        """Test that empty value raises error."""
        scope = {"key": ""}
        with pytest.raises(ScopeValidationError, match="value .* cannot be empty"):
            validate_scope(scope)

    def test_key_too_long_raises_error(self):
        """Test that key too long raises error."""
        scope = {"a" * 200: "value"}
        with pytest.raises(ScopeValidationError, match="exceeds maximum length"):
            validate_scope(scope)

    def test_value_too_long_raises_error(self):
        """Test that value too long raises error."""
        scope = {"key": "a" * 1000}
        with pytest.raises(ScopeValidationError, match="exceeds maximum length"):
            validate_scope(scope)

    def test_invalid_key_characters_raises_error(self):
        """Test that invalid characters in key raises error."""
        scope = {"key!@#": "value"}
        with pytest.raises(ScopeValidationError, match="invalid characters"):
            validate_scope(scope)

    def test_valid_key_characters(self):
        """Test valid key characters."""
        scope = {"valid_key-123": "value"}
        validate_scope(scope)  # Should not raise


class TestNormalizeScope:
    """Tests for normalize_scope."""

    def test_sorts_keys(self):
        """Test that normalize sorts keys."""
        scope = {"z": "value", "a": "value", "m": "value"}
        result = normalize_scope(scope)
        assert list(result.keys()) == ["a", "m", "z"]

    def test_trims_values(self):
        """Test that normalize trims values."""
        scope = {"key": "  value  "}
        result = normalize_scope(scope)
        assert result["key"] == "value"

    def test_validates_scope(self):
        """Test that normalize validates scope."""
        with pytest.raises(ScopeValidationError):
            normalize_scope({})


class TestHashScope:
    """Tests for hash_scope."""

    def test_consistent_hash(self):
        """Test that same scope produces same hash."""
        scope1 = {"user_id": "123", "org_id": "456"}
        scope2 = {"user_id": "123", "org_id": "456"}
        assert hash_scope(scope1) == hash_scope(scope2)

    def test_different_values_different_hash(self):
        """Test that different values produce different hash."""
        scope1 = {"user_id": "123"}
        scope2 = {"user_id": "456"}
        assert hash_scope(scope1) != hash_scope(scope2)

    def test_key_order_irrelevant(self):
        """Test that key order doesn't affect hash."""
        scope1 = {"user_id": "123", "org_id": "456"}
        scope2 = {"org_id": "456", "user_id": "123"}
        assert hash_scope(scope1) == hash_scope(scope2)

    def test_whitespace_normalized(self):
        """Test that whitespace is normalized."""
        scope1 = {"key": "value"}
        scope2 = {"key": "  value  "}
        assert hash_scope(scope1) == hash_scope(scope2)

    def test_returns_hex_string(self):
        """Test that hash is hex string."""
        scope = {"user_id": "123"}
        result = hash_scope(scope)
        assert isinstance(result, str)
        assert len(result) == 64  # SHA256 hex length
        assert all(c in "0123456789abcdef" for c in result)


class TestScopeMatches:
    """Tests for scope_matches."""

    def test_identical_scopes_match(self):
        """Test that identical scopes match."""
        scope1 = {"user_id": "123", "org_id": "456"}
        scope2 = {"user_id": "123", "org_id": "456"}
        assert scope_matches(scope1, scope2) is True

    def test_different_scopes_dont_match(self):
        """Test that different scopes don't match."""
        scope1 = {"user_id": "123"}
        scope2 = {"user_id": "456"}
        assert scope_matches(scope1, scope2) is False

    def test_different_keys_dont_match(self):
        """Test that different keys don't match."""
        scope1 = {"user_id": "123"}
        scope2 = {"org_id": "123"}
        assert scope_matches(scope1, scope2) is False

    def test_invalid_scopes_dont_match(self):
        """Test that invalid scopes don't match."""
        assert scope_matches({}, {"user_id": "123"}) is False


class TestScopeContains:
    """Tests for scope_contains."""

    def test_parent_contains_child(self):
        """Test that parent contains child."""
        parent = {"user_id": "123", "org_id": "456"}
        child = {"user_id": "123"}
        assert scope_contains(parent, child) is True

    def test_parent_does_not_contain_child_different_value(self):
        """Test that parent doesn't contain child with different value."""
        parent = {"user_id": "123", "org_id": "456"}
        child = {"user_id": "789"}
        assert scope_contains(parent, child) is False

    def test_parent_does_not_contain_child_missing_key(self):
        """Test that parent doesn't contain child with missing key."""
        parent = {"user_id": "123"}
        child = {"org_id": "456"}
        assert scope_contains(parent, child) is False

    def test_identical_scopes_contain_each_other(self):
        """Test that identical scopes contain each other."""
        scope = {"user_id": "123", "org_id": "456"}
        assert scope_contains(scope, scope) is True

    def test_child_larger_than_parent(self):
        """Test child with more keys than parent."""
        parent = {"user_id": "123"}
        child = {"user_id": "123", "org_id": "456"}
        assert scope_contains(parent, child) is False


class TestMergeScopes:
    """Tests for merge_scopes."""

    def test_merge_two_scopes(self):
        """Test merging two scopes."""
        scope1 = {"user_id": "123"}
        scope2 = {"org_id": "456"}
        result = merge_scopes(scope1, scope2)
        assert result == {"org_id": "456", "user_id": "123"}

    def test_later_overrides_earlier(self):
        """Test that later scopes override earlier."""
        scope1 = {"user_id": "123"}
        scope2 = {"user_id": "456"}
        result = merge_scopes(scope1, scope2)
        assert result["user_id"] == "456"

    def test_merge_multiple_scopes(self):
        """Test merging multiple scopes."""
        scope1 = {"a": "1"}
        scope2 = {"b": "2"}
        scope3 = {"c": "3"}
        result = merge_scopes(scope1, scope2, scope3)
        assert result == {"a": "1", "b": "2", "c": "3"}

    def test_merge_exceeding_limit_raises_error(self):
        """Test that merging exceeding limit raises error."""
        scope1 = {"a": "1", "b": "2", "c": "3"}
        scope2 = {"d": "4", "e": "5", "f": "6"}
        with pytest.raises(ScopeValidationError, match="cannot have more than"):
            merge_scopes(scope1, scope2)

    def test_merge_with_invalid_scope_raises_error(self):
        """Test that merging invalid scope raises error."""
        scope1 = {"user_id": "123"}
        scope2 = {}
        with pytest.raises(ScopeValidationError):
            merge_scopes(scope1, scope2)


class TestFilterScope:
    """Tests for filter_scope."""

    def test_filter_to_subset(self):
        """Test filtering to subset of keys."""
        scope = {"user_id": "123", "org_id": "456", "team_id": "789"}
        result = filter_scope(scope, ["user_id", "org_id"])
        assert result == {"org_id": "456", "user_id": "123"}

    def test_filter_to_single_key(self):
        """Test filtering to single key."""
        scope = {"user_id": "123", "org_id": "456"}
        result = filter_scope(scope, ["user_id"])
        assert result == {"user_id": "123"}

    def test_filter_non_existent_keys(self):
        """Test filtering to non-existent keys."""
        scope = {"user_id": "123"}
        with pytest.raises(ScopeValidationError, match="cannot be empty"):
            filter_scope(scope, ["org_id"])

    def test_filter_empty_result_raises_error(self):
        """Test that empty filter result raises error."""
        scope = {"user_id": "123"}
        with pytest.raises(ScopeValidationError, match="cannot be empty"):
            filter_scope(scope, [])
