"""
SQLAlchemy ORM models for payroll_runs and payroll_items tables (modules P2-P6).

Maps to existing PostgreSQL tables created by 001_initial_schema.sql.

Compliance (CLAUDE.md):
- Rule #2: Soft deletes only via deleted_at.
- Rule #4: client_id is non-nullable on payroll_runs.
- Rule #5: Approval workflow via status enum (DRAFT -> PENDING_APPROVAL -> FINALIZED).
- Rule #6: Payroll finalization must verify CPA_OWNER at function level.
"""

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Numeric, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin


class PayrollRunStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    FINALIZED = "FINALIZED"
    VOID = "VOID"


class PayrollRun(Base, TimestampMixin, SoftDeleteMixin):
    """
    A payroll run for a client's employees over a pay period.

    Status workflow: DRAFT -> PENDING_APPROVAL -> FINALIZED -> VOID
    Only CPA_OWNER can transition to FINALIZED or VOID (rule #6).
    """

    __tablename__ = "payroll_runs"

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
    pay_period_start: Mapped[date] = mapped_column(Date, nullable=False)
    pay_period_end: Mapped[date] = mapped_column(Date, nullable=False)
    pay_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(
        Enum(
            "DRAFT", "PENDING_APPROVAL", "FINALIZED", "VOID",
            name="payroll_run_status",
            create_type=False,
        ),
        nullable=False,
        server_default=text("'DRAFT'"),
    )
    finalized_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    finalized_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    # Relationships
    items: Mapped[list["PayrollItem"]] = relationship(
        "PayrollItem",
        back_populates="payroll_run",
        lazy="selectin",
    )


class PayrollItem(Base, TimestampMixin, SoftDeleteMixin):
    """
    Individual payroll calculation for one employee within a payroll run.

    Stores all tax withholdings and employer-side taxes.
    """

    __tablename__ = "payroll_items"

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
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="RESTRICT"),
        nullable=False,
    )
    gross_pay: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False,
    )
    federal_withholding: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False, default=Decimal("0.00"),
        server_default=text("0"),
    )
    state_withholding: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False, default=Decimal("0.00"),
        server_default=text("0"),
    )
    social_security: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False, default=Decimal("0.00"),
        server_default=text("0"),
    )
    medicare: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False, default=Decimal("0.00"),
        server_default=text("0"),
    )
    ga_suta: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False, default=Decimal("0.00"),
        server_default=text("0"),
    )
    futa: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False, default=Decimal("0.00"),
        server_default=text("0"),
    )
    net_pay: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False,
    )

    # Relationships
    payroll_run: Mapped["PayrollRun"] = relationship(
        "PayrollRun", back_populates="items",
    )
