"""
SQLAlchemy ORM models for bank reconciliation tables (module T3).

Maps to existing PostgreSQL tables created by 001_initial_schema.sql:
- bank_accounts
- bank_transactions
- reconciliations

Compliance (CLAUDE.md rule #4): client_id is non-nullable on bank_accounts.
Compliance (CLAUDE.md rule #2): soft deletes only via deleted_at.
"""

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin


class BankTransactionType(str, enum.Enum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"


class ReconciliationStatus(str, enum.Enum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class BankAccount(Base, TimestampMixin, SoftDeleteMixin):
    """
    Bank account linked to a client and a GL account.

    Each row represents a real-world bank account for a specific client.
    The account_id FK links to the corresponding chart_of_accounts entry
    (e.g., a Cash asset account).
    """

    __tablename__ = "bank_accounts"

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
    account_name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_number_encrypted: Mapped[bytes | None] = mapped_column(nullable=True)
    institution_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chart_of_accounts.id", ondelete="RESTRICT"),
        nullable=True,
    )

    transactions: Mapped[list["BankTransaction"]] = relationship(
        back_populates="bank_account", lazy="selectin",
    )
    reconciliations: Mapped[list["Reconciliation"]] = relationship(
        back_populates="bank_account", lazy="selectin",
    )


class BankTransaction(Base, TimestampMixin, SoftDeleteMixin):
    """
    A single bank statement transaction.

    Imported from bank statements (CSV/OFX). Matched against GL journal
    entries during reconciliation.
    """

    __tablename__ = "bank_transactions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    bank_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bank_accounts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    transaction_type: Mapped[str] = mapped_column(
        Enum(
            "DEBIT", "CREDIT",
            name="bank_transaction_type",
            create_type=False,
        ),
        nullable=False,
    )
    is_reconciled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false"),
    )
    reconciled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    journal_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("journal_entries.id", ondelete="RESTRICT"),
        nullable=True,
    )

    bank_account: Mapped["BankAccount"] = relationship(back_populates="transactions")


class Reconciliation(Base, TimestampMixin, SoftDeleteMixin):
    """
    A reconciliation session for a bank account.

    Tracks the process of matching bank statement entries to GL entries
    for a specific statement period.
    """

    __tablename__ = "reconciliations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    bank_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bank_accounts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    statement_date: Mapped[date] = mapped_column(Date, nullable=False)
    statement_balance: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    reconciled_balance: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True,
    )
    status: Mapped[str] = mapped_column(
        Enum(
            "IN_PROGRESS", "COMPLETED",
            name="reconciliation_status",
            create_type=False,
        ),
        nullable=False,
        server_default=text("'IN_PROGRESS'"),
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    completed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )

    bank_account: Mapped["BankAccount"] = relationship(back_populates="reconciliations")
