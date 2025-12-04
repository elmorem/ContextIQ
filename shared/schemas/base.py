"""
Base Pydantic schemas.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class BaseSchema(BaseModel):
    """Base Pydantic schema with common configuration."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        use_enum_values=True,
        json_schema_extra={"additionalProperties": False},
    )


class TimestampSchema(BaseSchema):
    """Schema with timestamp fields."""

    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class SuccessResponse(BaseSchema):
    """Standard success response."""

    success: bool = Field(True, description="Operation success status")
    message: str | None = Field(None, description="Success message")
    data: Any | None = Field(None, description="Response data")


class ErrorResponse(BaseSchema):
    """Standard error response."""

    success: bool = Field(False, description="Operation success status")
    error: str = Field(..., description="Error message")
    error_code: str | None = Field(None, description="Error code")
    details: dict[str, Any] | None = Field(None, description="Error details")


class PaginationParams(BaseSchema):
    """Pagination parameters."""

    page: int = Field(1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")


class PaginatedResponse(BaseSchema):
    """Paginated response wrapper."""

    items: list[Any] = Field(..., description="List of items")
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")
    pages: int = Field(..., description="Total number of pages")
