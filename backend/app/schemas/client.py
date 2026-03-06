"""
Pydantic schemas for Client CRUD operations.

Validation rules:
- name and entity_type are required on create
- entity_type must be one of: SOLE_PROP, S_CORP, C_CORP, PARTNERSHIP_LLC
- state defaults to GA
- All string fields are stripped of leading/trailing whitespace (via BaseSchema)
"""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import EmailStr, Field

from app.schemas import BaseSchema, RecordSchema


class EntityType(str, Enum):
    """Client entity types supported by the Georgia CPA firm."""

    SOLE_PROP = "SOLE_PROP"
    S_CORP = "S_CORP"
    C_CORP = "C_CORP"
    PARTNERSHIP_LLC = "PARTNERSHIP_LLC"


class ClientCreate(BaseSchema):
    """Schema for creating a new client."""

    name: str = Field(..., min_length=1, max_length=255)
    entity_type: EntityType
    tax_id: str | None = Field(None, max_length=20)
    address: str | None = Field(None, max_length=500)
    city: str | None = Field(None, max_length=100)
    state: str = Field(default="GA", max_length=2)
    zip: str | None = Field(None, max_length=10)
    phone: str | None = Field(None, max_length=20)
    email: EmailStr | None = None


class ClientUpdate(BaseSchema):
    """Schema for updating an existing client. All fields optional."""

    name: str | None = Field(None, min_length=1, max_length=255)
    entity_type: EntityType | None = None
    tax_id: str | None = Field(None, max_length=20)
    address: str | None = Field(None, max_length=500)
    city: str | None = Field(None, max_length=100)
    state: str | None = Field(None, max_length=2)
    zip: str | None = Field(None, max_length=10)
    phone: str | None = Field(None, max_length=20)
    email: EmailStr | None = None


class ClientResponse(RecordSchema):
    """Schema for a single client in API responses."""

    name: str
    entity_type: EntityType
    address: str | None = None
    city: str | None = None
    state: str
    zip: str | None = None
    phone: str | None = None
    email: str | None = None
    is_active: bool
    deleted_at: datetime | None = None


class ClientList(BaseSchema):
    """Paginated list of clients."""

    items: list[ClientResponse]
    total: int
    skip: int
    limit: int
