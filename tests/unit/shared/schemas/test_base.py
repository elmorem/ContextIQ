"""
Tests for base schemas.
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from shared.schemas.base import (
    BaseSchema,
    ErrorResponse,
    PaginatedResponse,
    PaginationParams,
    SuccessResponse,
    TimestampSchema,
)


class TestBaseSchema:
    """Tests for BaseSchema."""

    def test_from_attributes(self):
        """Test that from_attributes is enabled."""

        class TestModel(BaseSchema):
            name: str
            value: int

        # Create object with attributes
        class DummyObj:
            name = "test"
            value = 123

        model = TestModel.model_validate(DummyObj())
        assert model.name == "test"
        assert model.value == 123

    def test_populate_by_name(self):
        """Test that populate_by_name is enabled."""

        class TestModel(BaseSchema):
            test_field: str

        # Can use field name
        model = TestModel(test_field="value")
        assert model.test_field == "value"


class TestTimestampSchema:
    """Tests for TimestampSchema."""

    def test_has_created_at(self):
        """Test that TimestampSchema has created_at field."""

        class TestModel(TimestampSchema):
            name: str

        now = datetime.utcnow()
        model = TestModel(name="test", created_at=now)
        assert model.created_at == now

    def test_has_updated_at(self):
        """Test that TimestampSchema has updated_at field."""

        class TestModel(TimestampSchema):
            name: str

        now = datetime.utcnow()
        model = TestModel(name="test", created_at=now, updated_at=now)
        assert model.updated_at == now

    def test_created_at_required(self):
        """Test that created_at is required."""

        class TestModel(TimestampSchema):
            name: str

        with pytest.raises(ValidationError):
            TestModel(name="test")


class TestSuccessResponse:
    """Tests for SuccessResponse."""

    def test_success_response_with_data(self):
        """Test creating success response with data."""
        response = SuccessResponse(data={"key": "value"})
        assert response.success is True
        assert response.data == {"key": "value"}
        assert response.message is None

    def test_success_response_with_message(self):
        """Test creating success response with message."""
        response = SuccessResponse(data=None, message="Operation successful")
        assert response.success is True
        assert response.data is None
        assert response.message == "Operation successful"

    def test_success_response_serialization(self):
        """Test serializing success response."""
        response = SuccessResponse(data={"key": "value"}, message="Success")
        data = response.model_dump()
        assert data["success"] is True
        assert data["data"] == {"key": "value"}
        assert data["message"] == "Success"


class TestErrorResponse:
    """Tests for ErrorResponse."""

    def test_error_response_basic(self):
        """Test creating basic error response."""
        response = ErrorResponse(error="Something went wrong")
        assert response.success is False
        assert response.error == "Something went wrong"
        assert response.error_code is None
        assert response.details is None

    def test_error_response_with_code(self):
        """Test creating error response with error code."""
        response = ErrorResponse(error="Not found", error_code="NOT_FOUND")
        assert response.success is False
        assert response.error == "Not found"
        assert response.error_code == "NOT_FOUND"

    def test_error_response_with_details(self):
        """Test creating error response with details."""
        details = {"field": "email", "reason": "invalid format"}
        response = ErrorResponse(error="Validation failed", details=details)
        assert response.success is False
        assert response.details == details

    def test_error_response_serialization(self):
        """Test serializing error response."""
        response = ErrorResponse(error="Error", error_code="ERR", details={"key": "value"})
        data = response.model_dump()
        assert data["success"] is False
        assert data["error"] == "Error"
        assert data["error_code"] == "ERR"
        assert data["details"] == {"key": "value"}


class TestPaginationParams:
    """Tests for PaginationParams."""

    def test_default_values(self):
        """Test default pagination values."""
        params = PaginationParams()
        assert params.page == 1
        assert params.page_size == 20

    def test_custom_values(self):
        """Test custom pagination values."""
        params = PaginationParams(page=2, page_size=50)
        assert params.page == 2
        assert params.page_size == 50

    def test_page_minimum(self):
        """Test page minimum constraint."""
        with pytest.raises(ValidationError):
            PaginationParams(page=0)

    def test_page_size_constraints(self):
        """Test page_size constraints."""
        with pytest.raises(ValidationError):
            PaginationParams(page_size=0)

        with pytest.raises(ValidationError):
            PaginationParams(page_size=101)

    def test_valid_page_size_range(self):
        """Test valid page_size range."""
        params = PaginationParams(page_size=1)
        assert params.page_size == 1

        params = PaginationParams(page_size=100)
        assert params.page_size == 100


class TestPaginatedResponse:
    """Tests for PaginatedResponse."""

    def test_paginated_response_basic(self):
        """Test creating basic paginated response."""
        items = [{"id": 1}, {"id": 2}, {"id": 3}]
        response = PaginatedResponse(items=items, total=10, page=1, page_size=3)
        assert response.items == items
        assert response.total == 10
        assert response.page == 1
        assert response.page_size == 3
        assert response.total_pages == 4

    def test_total_pages_calculation(self):
        """Test total_pages calculation."""
        # Exact division
        response = PaginatedResponse(items=[], total=20, page=1, page_size=10)
        assert response.total_pages == 2

        # With remainder
        response = PaginatedResponse(items=[], total=25, page=1, page_size=10)
        assert response.total_pages == 3

        # Zero total
        response = PaginatedResponse(items=[], total=0, page=1, page_size=10)
        assert response.total_pages == 0

    def test_has_next_page(self):
        """Test has_next calculation."""
        # Has next page
        response = PaginatedResponse(items=[], total=30, page=1, page_size=10)
        assert response.has_next is True

        # No next page
        response = PaginatedResponse(items=[], total=30, page=3, page_size=10)
        assert response.has_next is False

    def test_has_previous_page(self):
        """Test has_previous calculation."""
        # Has previous page
        response = PaginatedResponse(items=[], total=30, page=2, page_size=10)
        assert response.has_previous is True

        # No previous page
        response = PaginatedResponse(items=[], total=30, page=1, page_size=10)
        assert response.has_previous is False

    def test_serialization(self):
        """Test serializing paginated response."""
        items = [{"id": 1}, {"id": 2}]
        response = PaginatedResponse(items=items, total=10, page=2, page_size=2)
        data = response.model_dump()

        assert data["items"] == items
        assert data["total"] == 10
        assert data["page"] == 2
        assert data["page_size"] == 2
        assert data["total_pages"] == 5
        assert data["has_next"] is True
        assert data["has_previous"] is True
