"""
SQLAlchemy ORM model for the direct_deposit_batches table (Phase 8A).

Tracks NACHA file generation and submission status for payroll runs.

Compliance (CLAUDE.md rule #4): client_id is non-nullable for isolation.
Compliance (CLAUDE.md rule #2): soft deletes only via deleted_at.
"""

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin, TimestampMixin


class DDBatchStatus(str, enum.Enum):
    GENERATED = "GENERATED"
    DOWNLOADED = "DOWNLOADED"
    SUBMITTED = "SUBMITTED"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"


class DirectDepositBatch(Base, TimestampMixin, SoftDeleteMixin):
    """
    Tracks a NACHA file generated for a payroll run's direct deposits.

    Lifecycle: GENERATED -> DOWNLOADED -> SUBMITTED -> CONFIRMED
    The CPA generates the NACHA file, downloads it, uploads to the bank portal,
    then marks it confirmed once the bank processes it.
    """

    __tablename__ = "direct_deposit_batches"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    payroll_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("payroll_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    batch_number: Mapped[int] = mapped_column(
        Integer, nullable=False,
    )
    file_id_modifier: Mapped[str] = mapped_column(
        String(1), nullable=False, server_default=text("'A'"),
    )
    entry_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0"),
    )
    total_credit_amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False, server_default=text("0"),
    )
    company_name: Mapped[str] = mapped_column(
        String(16), nullable=False,
    )
    company_id: Mapped[str] = mapped_column(
        String(10), nullable=False,
    )
    status: Mapped[str] = mapped_column(
        Enum(
            "GENERATED", "DOWNLOADED", "SUBMITTED", "CONFIRMED", "FAILED",
            name="dd_batch_status",
            create_type=False,
        ),
        nullable=False,
        server_default=text("'GENERATED'"),
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
    downloaded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    nacha_file_path: Mapped[str | None] = mapped_column(
        String(500), nullable=True,
    )
    generated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
