"""
Pydantic schemas for Document Management (module D1).
"""

from datetime import date
from uuid import UUID

from pydantic import Field

from app.schemas import BaseSchema, RecordSchema


class DocumentResponse(RecordSchema):
    client_id: UUID
    file_name: str
    file_type: str | None = None
    file_size_bytes: int | None = None
    description: str | None = None
    tags: list[str] | None = None
    uploaded_by: UUID
    journal_entry_id: UUID | None = None


class DocumentUpdate(BaseSchema):
    description: str | None = None
    tags: list[str] | None = None
    journal_entry_id: UUID | None = None


class DocumentList(BaseSchema):
    items: list[DocumentResponse]
    total: int
