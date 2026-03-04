"""
SQLAlchemy model for the audit_log table (Module O1).

Compliance (CLAUDE.md rule #2 — AUDIT TRAIL):
    The audit_log table is APPEND-ONLY. Records are NEVER modified or deleted.
    This model is READ-ONLY at the application level — all writes happen via
    database triggers on the 24 data tables.

Note: audit_log does NOT have updated_at or deleted_at columns.
It only has created_at (the timestamp of the audited action).
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, text
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AuditAction(str, enum.Enum):
    """Enumeration of auditable database actions."""

    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


class AuditLog(Base):
    """
    Read-only model for the audit_log table.

    This table is populated exclusively by PostgreSQL triggers.
    Application code must NEVER insert, update, or delete rows.
    """

    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    table_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    action: Mapped[AuditAction] = mapped_column(
        Enum(AuditAction, name="audit_action", create_type=False),
        nullable=False,
    )
    old_values: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    new_values: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    ip_address: Mapped[str | None] = mapped_column(
        INET,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
