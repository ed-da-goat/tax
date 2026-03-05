"""
SQLAlchemy ORM models for bills, bill_lines, and bill_payments tables (module T1 — AP).

Maps to the existing PostgreSQL tables created by 001_initial_schema.sql.
Compliance (CLAUDE.md rule #2): Soft deletes only via deleted_at.
Compliance (CLAUDE.md rule #4): client_id is non-nullable FK on bills.
Compliance (CLAUDE.md rule #5): Approval workflow via status enum —
    bills do not affect GL until APPROVED.
"""

import enum
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, Enum, ForeignKey, Integer, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin


class BillStatus(str, enum.Enum):
    """Status enum matching the PostgreSQL bill_status enum."""

    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    PAID = "PAID"
    VOID = "VOID"


class Bill(Base, TimestampMixin, SoftDeleteMixin):
    """
    Bill (accounts payable) header.

    Each bill belongs to a single client and optionally references a vendor.
    Status workflow: DRAFT -> PENDING_APPROVAL -> APPROVED -> PAID
    Bills only hit the GL when status transitions to APPROVED.
    Only CPA_OWNER can approve or void.
    """

    __tablename__ = "bills"

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
    vendor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vendors.id", ondelete="RESTRICT"),
        nullable=False,
    )
    bill_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    bill_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False, default=Decimal("0.00"),
        server_default=text("0"),
    )
    status: Mapped[BillStatus] = mapped_column(
        Enum(BillStatus, name="bill_status", create_type=False),
        nullable=False,
        default=BillStatus.DRAFT,
        server_default="DRAFT",
    )

    # Relationships
    lines: Mapped[list["BillLine"]] = relationship(
        "BillLine",
        back_populates="bill",
        lazy="selectin",
        order_by="BillLine.created_at",
    )
    payments: Mapped[list["BillPayment"]] = relationship(
        "BillPayment",
        back_populates="bill",
        lazy="selectin",
        order_by="BillPayment.payment_date",
    )


class BillLine(Base, TimestampMixin, SoftDeleteMixin):
    """
    Individual line item on a bill.

    Each line references an expense account from the chart of accounts.
    The sum of all line amounts must equal the bill total_amount.
    """

    __tablename__ = "bill_lines"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    bill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bills.id", ondelete="RESTRICT"),
        nullable=False,
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chart_of_accounts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False, default=Decimal("0.00"),
        server_default=text("0"),
    )

    # Relationships
    bill: Mapped["Bill"] = relationship("Bill", back_populates="lines")


class BillPayment(Base, TimestampMixin, SoftDeleteMixin):
    """
    Payment recorded against a bill.

    Multiple partial payments may be recorded. When total payments
    equal or exceed the bill total, the bill status transitions to PAID.
    """

    __tablename__ = "bill_payments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    bill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bills.id", ondelete="RESTRICT"),
        nullable=False,
    )
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False,
    )
    payment_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reference_number: Mapped[str | None] = mapped_column(String(100), nullable=True)

    check_number: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    bill: Mapped["Bill"] = relationship("Bill", back_populates="payments")
