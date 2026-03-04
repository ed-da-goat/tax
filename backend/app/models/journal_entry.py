"""
SQLAlchemy ORM models for journal_entries and journal_entry_lines tables (module F3).

Maps to the existing PostgreSQL tables created by 001_initial_schema.sql.
Compliance (CLAUDE.md rule #1): Double-entry enforced at DB trigger level.
Compliance (CLAUDE.md rule #2): Soft deletes only via deleted_at.
Compliance (CLAUDE.md rule #4): client_id is non-nullable FK on journal_entries.
Compliance (CLAUDE.md rule #5): Approval workflow via status enum.
"""

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin


class JournalEntryStatus(str, enum.Enum):
    """Status enum matching the PostgreSQL journal_entry_status enum."""

    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    POSTED = "POSTED"
    VOID = "VOID"


class JournalEntry(Base, TimestampMixin, SoftDeleteMixin):
    """
    Journal entry header.

    Each entry belongs to a single client and contains one or more lines.
    Status workflow: DRAFT -> PENDING_APPROVAL -> POSTED -> VOID
    Only CPA_OWNER can transition to POSTED or VOID.
    """

    __tablename__ = "journal_entries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    reference_number: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    status: Mapped[JournalEntryStatus] = mapped_column(
        Enum(JournalEntryStatus, name="journal_entry_status", create_type=False),
        nullable=False,
        default=JournalEntryStatus.DRAFT,
        server_default="DRAFT",
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    posted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    lines: Mapped[list["JournalEntryLine"]] = relationship(
        "JournalEntryLine",
        back_populates="journal_entry",
        lazy="selectin",
        order_by="JournalEntryLine.created_at",
    )


class JournalEntryLine(Base, TimestampMixin, SoftDeleteMixin):
    """
    Individual debit or credit line within a journal entry.

    DB constraint chk_debit_xor_credit ensures each line has
    EITHER debit > 0 OR credit > 0, never both, never neither.
    """

    __tablename__ = "journal_entry_lines"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    journal_entry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("journal_entries.id", ondelete="RESTRICT"),
        nullable=False,
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chart_of_accounts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    debit: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False, default=Decimal("0.00"),
        server_default=text("0"),
    )
    credit: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False, default=Decimal("0.00"),
        server_default=text("0"),
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    journal_entry: Mapped["JournalEntry"] = relationship(
        "JournalEntry", back_populates="lines"
    )
