"""
SQLAlchemy ORM model for the tax_filing_submissions table (Phase 8B).

Tracks electronic tax filing submissions to IRS (via TaxBandits)
and Georgia DOR (via FSET/GTC).

Compliance (CLAUDE.md rule #4): client_id is non-nullable for isolation.
Compliance (CLAUDE.md rule #2): soft deletes only via deleted_at.
"""

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin, TimestampMixin


class TaxFilingStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    ERROR = "ERROR"


class TaxFilingProvider(str, enum.Enum):
    TAXBANDITS = "TAXBANDITS"
    GA_FSET = "GA_FSET"
    MANUAL = "MANUAL"


class TaxFilingSubmission(Base, TimestampMixin, SoftDeleteMixin):
    """
    Tracks a tax form filing submission to IRS or Georgia DOR.

    Supported providers:
    - TAXBANDITS: REST API for 1099, W-2, 940, 941, 943, 944, 945
    - GA_FSET: SFTP + XML for Georgia G-7 withholding returns
    - MANUAL: Filed manually through IRS/DOR portals (tracking only)

    Lifecycle: DRAFT -> SUBMITTED -> ACCEPTED/REJECTED/ERROR
    """

    __tablename__ = "tax_filing_submissions"

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
    form_type: Mapped[str] = mapped_column(
        String(20), nullable=False,
    )
    tax_year: Mapped[int] = mapped_column(
        Integer, nullable=False,
    )
    tax_quarter: Mapped[int | None] = mapped_column(
        Integer, nullable=True,
    )
    filing_period_start: Mapped[date | None] = mapped_column(
        Date, nullable=True,
    )
    filing_period_end: Mapped[date | None] = mapped_column(
        Date, nullable=True,
    )
    provider: Mapped[str] = mapped_column(
        Enum(
            "TAXBANDITS", "GA_FSET", "MANUAL",
            name="tax_filing_provider",
            create_type=False,
        ),
        nullable=False,
        server_default=text("'MANUAL'"),
    )
    provider_submission_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True,
    )
    provider_reference: Mapped[str | None] = mapped_column(
        String(255), nullable=True,
    )
    status: Mapped[str] = mapped_column(
        Enum(
            "DRAFT", "SUBMITTED", "ACCEPTED", "REJECTED", "ERROR",
            name="tax_filing_status",
            create_type=False,
        ),
        nullable=False,
        server_default=text("'DRAFT'"),
    )
    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    rejected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    rejection_reason: Mapped[str | None] = mapped_column(
        Text, nullable=True,
    )
    submission_data: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
    )
    response_data: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
    )
    submitted_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
