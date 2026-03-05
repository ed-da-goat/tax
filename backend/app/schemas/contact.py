"""Pydantic schemas for contacts / CRM (PM4)."""

from datetime import datetime
from uuid import UUID

from pydantic import EmailStr, Field

from app.schemas import BaseSchema, RecordSchema


class ContactCreate(BaseSchema):
    client_id: UUID
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=20)
    mobile: str | None = Field(None, max_length=20)
    title: str | None = Field(None, max_length=100)
    is_primary: bool = False
    address: str | None = Field(None, max_length=500)
    city: str | None = Field(None, max_length=100)
    state: str | None = Field(None, max_length=2)
    zip: str | None = Field(None, max_length=10)
    notes: str | None = None
    tags: list[str] = []
    custom_fields: dict = {}


class ContactUpdate(BaseSchema):
    first_name: str | None = Field(None, min_length=1, max_length=100)
    last_name: str | None = Field(None, min_length=1, max_length=100)
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=20)
    mobile: str | None = Field(None, max_length=20)
    title: str | None = Field(None, max_length=100)
    is_primary: bool | None = None
    address: str | None = Field(None, max_length=500)
    city: str | None = Field(None, max_length=100)
    state: str | None = Field(None, max_length=2)
    zip: str | None = Field(None, max_length=10)
    notes: str | None = None
    tags: list[str] | None = None
    custom_fields: dict | None = None


class ContactResponse(RecordSchema):
    client_id: UUID
    first_name: str
    last_name: str
    email: str | None = None
    phone: str | None = None
    mobile: str | None = None
    title: str | None = None
    is_primary: bool
    address: str | None = None
    city: str | None = None
    state: str | None = None
    zip: str | None = None
    notes: str | None = None
    tags: list = []
    custom_fields: dict = {}
    deleted_at: datetime | None = None


class ContactList(BaseSchema):
    items: list[ContactResponse]
    total: int
