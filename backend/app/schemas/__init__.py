"""
Pydantic schemas package.

Contains request/response schemas used across the application.
Base schemas and common error response models are defined here.
Module-specific schemas go in their own files within this package.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """Base schema with shared configuration for all Pydantic models."""

    model_config = ConfigDict(
        from_attributes=True,  # Enable ORM mode for SQLAlchemy models
        str_strip_whitespace=True,
    )


class TimestampSchema(BaseSchema):
    """Schema mixin for models that include audit timestamps."""

    created_at: datetime
    updated_at: datetime


class RecordSchema(TimestampSchema):
    """Standard schema for a persisted record with UUID + timestamps."""

    id: UUID


class ErrorResponse(BaseModel):
    """
    Standard error response body.

    Used for 4xx and 5xx responses across the API.
    """

    error: str
    detail: str | None = None


class PermissionErrorResponse(BaseModel):
    """
    403 Forbidden response per CLAUDE.md role permission schema.

    Format: {"error": "Insufficient permissions", "required_role": "<role>"}
    """

    error: str = "Insufficient permissions"
    required_role: str


class PaginatedResponse(BaseSchema):
    """Generic paginated response wrapper."""

    items: list[Any]
    total: int
    page: int
    page_size: int
    pages: int


class MessageResponse(BaseModel):
    """Simple message response for operations that return a status message."""

    message: str
