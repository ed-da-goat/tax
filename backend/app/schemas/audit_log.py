"""
Pydantic schemas for the Audit Trail Viewer (Module O1).

All schemas are READ-ONLY — there are no create/update schemas
because the audit_log table is append-only and written by DB triggers.
"""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import Field

from app.schemas import BaseSchema


class AuditAction(str, Enum):
    """Auditable database actions."""

    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


class AuditLogEntry(BaseSchema):
    """Schema for a single audit log entry in API responses."""

    id: UUID
    table_name: str
    record_id: UUID
    action: AuditAction
    old_values: dict | None = None
    new_values: dict | None = None
    user_id: UUID | None = None
    ip_address: str | None = None
    created_at: datetime


class AuditLogList(BaseSchema):
    """Paginated list of audit log entries."""

    items: list[AuditLogEntry]
    total: int
    skip: int
    limit: int


class AuditLogFilters(BaseSchema):
    """Query filters for listing audit log entries. All fields optional."""

    table_name: str | None = None
    record_id: UUID | None = None
    user_id: UUID | None = None
    action: AuditAction | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
