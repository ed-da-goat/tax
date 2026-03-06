"""
Pydantic schemas for Vendor CRUD operations (module T1 — Accounts Payable).

Validation rules:
- name is required on create
- All string fields stripped of whitespace (via BaseSchema)
- client_id is NOT in schemas — it comes from the URL path parameter
"""

from datetime import datetime
from uuid import UUID

from pydantic import EmailStr, Field

from app.schemas import BaseSchema, RecordSchema


class VendorCreate(BaseSchema):
    """Schema for creating a new vendor."""

    name: str = Field(..., min_length=1, max_length=255)
    tax_id: str | None = Field(None, max_length=20)
    address: str | None = Field(None, max_length=500)
    city: str | None = Field(None, max_length=100)
    state: str | None = Field(None, max_length=2)
    zip: str | None = Field(None, max_length=10)
    phone: str | None = Field(None, max_length=20)
    email: EmailStr | None = None
    is_1099_eligible: bool = False


class VendorUpdate(BaseSchema):
    """Schema for updating an existing vendor. All fields optional."""

    name: str | None = Field(None, min_length=1, max_length=255)
    tax_id: str | None = Field(None, max_length=20)
    address: str | None = Field(None, max_length=500)
    city: str | None = Field(None, max_length=100)
    state: str | None = Field(None, max_length=2)
    zip: str | None = Field(None, max_length=10)
    phone: str | None = Field(None, max_length=20)
    email: EmailStr | None = None
    is_1099_eligible: bool | None = None


class VendorResponse(RecordSchema):
    """Schema for a single vendor in API responses."""

    client_id: UUID
    name: str
    address: str | None = None
    city: str | None = None
    state: str | None = None
    zip: str | None = None
    phone: str | None = None
    email: str | None = None
    is_1099_eligible: bool = False
    deleted_at: datetime | None = None


class VendorList(BaseSchema):
    """Paginated list of vendors."""

    items: list[VendorResponse]
    total: int
    skip: int
    limit: int
