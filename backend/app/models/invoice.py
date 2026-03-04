"""
SQLAlchemy ORM models for invoices, invoice_lines, and invoice_payments tables (module T2).

Maps to the existing PostgreSQL tables created by 001_initial_schema.sql.
Compliance (CLAUDE.md rule #4): client_id is non-nullable FK on invoices.
Compliance (CLAUDE.md rule #2): Soft deletes only via deleted_at.
Compliance (CLAUDE.md rule #5): Approval workflow via status enum.
"""

import enum
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import (
    Date,
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


class InvoiceStatus(str, enum.Enum):
    """Status enum matching the PostgreSQL invoice_status enum."""

    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    SENT = "SENT"
    PAID = "PAID"
    VOID = "VOID"
    OVERDUE = "OVERDUE"


class Invoice(Base, TimestampMixin, SoftDeleteMixin):
    """
    Invoice header (Accounts Receivable).

    Each invoice belongs to a single client and contains one or more line items.
    Status workflow: DRAFT -> PENDING_APPROVAL -> SENT -> PAID (or OVERDUE/VOID)
    Only CPA_OWNER can transition to SENT (approve) or VOID.
    Invoices do not affect GL until approved and sent.

    Compliance (CLAUDE.md rule #4): client_id is non-nullable FK.
    Compliance (CLAUDE.md rule #5): Approval workflow via status.
    """

    __tablename__ = "invoices"

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
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    invoice_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False, default=Decimal("0.00"),
        server_default=text("0"),
    )
    status: Mapped[InvoiceStatus] = mapped_column(
        Enum(InvoiceStatus, name="invoice_status", create_type=False),
        nullable=False,
        default=InvoiceStatus.DRAFT,
        server_default="DRAFT",
    )

    # Relationships
    lines: Mapped[list["InvoiceLine"]] = relationship(
        "InvoiceLine",
        back_populates="invoice",
        lazy="selectin",
        order_by="InvoiceLine.created_at",
    )
    payments: Mapped[list["InvoicePayment"]] = relationship(
        "InvoicePayment",
        back_populates="invoice",
        lazy="selectin",
        order_by="InvoicePayment.payment_date",
    )


class InvoiceLine(Base, TimestampMixin, SoftDeleteMixin):
    """
    Individual line item within an invoice.

    Amount is auto-calculated as quantity * unit_price.
    """

    __tablename__ = "invoice_lines"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("invoices.id", ondelete="RESTRICT"),
        nullable=False,
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chart_of_accounts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("1.00"),
        server_default=text("1"),
    )
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False, default=Decimal("0.00"),
        server_default=text("0"),
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False, default=Decimal("0.00"),
        server_default=text("0"),
    )

    # Relationships
    invoice: Mapped["Invoice"] = relationship("Invoice", back_populates="lines")


class InvoicePayment(Base, TimestampMixin, SoftDeleteMixin):
    """
    Payment recorded against an invoice.

    When total payments >= invoice total_amount, status transitions to PAID.
    """

    __tablename__ = "invoice_payments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("invoices.id", ondelete="RESTRICT"),
        nullable=False,
    )
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False,
    )
    payment_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reference_number: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Relationships
    invoice: Mapped["Invoice"] = relationship("Invoice", back_populates="payments")
