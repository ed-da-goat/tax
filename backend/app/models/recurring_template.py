"""
SQLAlchemy ORM models for recurring transaction templates (C3).

Supports recurring journal entries and bills. Templates store the line items
and scheduling info; the service generates actual transactions when due.
"""

import enum
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, Enum, ForeignKey, Integer, Numeric, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin


class RecurringFrequency(str, enum.Enum):
    WEEKLY = "WEEKLY"
    BIWEEKLY = "BIWEEKLY"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    ANNUALLY = "ANNUALLY"


class RecurringSourceType(str, enum.Enum):
    JOURNAL_ENTRY = "JOURNAL_ENTRY"
    BILL = "BILL"


class RecurringTemplateStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    EXPIRED = "EXPIRED"


class RecurringTemplate(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "recurring_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    source_type: Mapped[RecurringSourceType] = mapped_column(
        Enum(RecurringSourceType, name="recurring_source_type", create_type=False),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    frequency: Mapped[RecurringFrequency] = mapped_column(
        Enum(RecurringFrequency, name="recurring_frequency", create_type=False),
        nullable=False,
    )
    next_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False, default=Decimal("0.00"),
        server_default=text("0"),
    )
    status: Mapped[RecurringTemplateStatus] = mapped_column(
        Enum(RecurringTemplateStatus, name="recurring_template_status", create_type=False),
        nullable=False, default=RecurringTemplateStatus.ACTIVE,
        server_default="ACTIVE",
    )
    vendor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vendors.id", ondelete="RESTRICT"),
        nullable=True,
    )
    occurrences_generated: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0"),
    )
    max_occurrences: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_generated_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    lines: Mapped[list["RecurringTemplateLine"]] = relationship(
        "RecurringTemplateLine", back_populates="template",
        lazy="selectin", order_by="RecurringTemplateLine.created_at",
    )


class RecurringTemplateLine(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "recurring_template_lines"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recurring_templates.id", ondelete="CASCADE"),
        nullable=False,
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chart_of_accounts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    debit: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False, default=Decimal("0.00"),
        server_default=text("0"),
    )
    credit: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False, default=Decimal("0.00"),
        server_default=text("0"),
    )

    template: Mapped["RecurringTemplate"] = relationship(
        "RecurringTemplate", back_populates="lines",
    )
