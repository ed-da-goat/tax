"""
SQLAlchemy ORM models for firm-to-client service invoicing (PM2).

Tables: service_invoices, service_invoice_lines, service_invoice_payments
These are invoices FROM the CPA firm TO the client for professional services.
Separate from AR invoices (which are the client's customer invoices).
"""

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean, Date, DateTime, Enum, ForeignKey, Integer, Numeric,
    String, Text, text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin


class ServiceInvoiceStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SENT = "SENT"
    VIEWED = "VIEWED"
    PAID = "PAID"
    PARTIAL = "PARTIAL"
    OVERDUE = "OVERDUE"
    VOID = "VOID"


class PaymentMethod(str, enum.Enum):
    CHECK = "CHECK"
    ACH = "ACH"
    CREDIT_CARD = "CREDIT_CARD"
    CASH = "CASH"
    OTHER = "OTHER"


class ServiceInvoice(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "service_invoices"

    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False
    )
    invoice_number: Mapped[str] = mapped_column(String(50), nullable=False)
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"), nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"), nullable=False)
    amount_paid: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"), nullable=False)
    balance_due: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"), nullable=False)
    status: Mapped[ServiceInvoiceStatus] = mapped_column(
        Enum(ServiceInvoiceStatus, name="service_invoice_status", create_type=False),
        default=ServiceInvoiceStatus.DRAFT, nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    terms: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    recurrence_interval: Mapped[str | None] = mapped_column(String(20), nullable=True)
    next_recurrence_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    engagement_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("engagements.id"), nullable=True
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    viewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    lines: Mapped[list["ServiceInvoiceLine"]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan", lazy="selectin"
    )
    payments: Mapped[list["ServiceInvoicePayment"]] = relationship(
        back_populates="invoice", lazy="selectin"
    )


class ServiceInvoiceLine(Base, TimestampMixin):
    __tablename__ = "service_invoice_lines"

    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("service_invoices.id", ondelete="CASCADE"), nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("1"), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    time_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("time_entries.id"), nullable=True
    )
    service_type: Mapped[str | None] = mapped_column(String(100), nullable=True)

    invoice: Mapped["ServiceInvoice"] = relationship(back_populates="lines")


class ServiceInvoicePayment(Base, TimestampMixin):
    __tablename__ = "service_invoice_payments"

    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("service_invoices.id"), nullable=False
    )
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    payment_method: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod, name="payment_method", create_type=False),
        default=PaymentMethod.CHECK, nullable=False
    )
    reference_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    invoice: Mapped["ServiceInvoice"] = relationship(back_populates="payments")
