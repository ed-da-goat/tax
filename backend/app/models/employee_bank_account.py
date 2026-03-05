"""
SQLAlchemy ORM model for the employee_bank_accounts table (Phase 8A).

Stores encrypted bank account information for employee direct deposit.

Compliance (CLAUDE.md rule #4): client_id is non-nullable for isolation.
Compliance (CLAUDE.md rule #2): soft deletes only via deleted_at.
NACHA compliance: account_number_encrypted stored as BYTEA (encrypted at rest).
"""

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin, TimestampMixin


class AccountType(str, enum.Enum):
    CHECKING = "CHECKING"
    SAVINGS = "SAVINGS"


class PrenoteStatus(str, enum.Enum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"


class EmployeeBankAccount(Base, TimestampMixin, SoftDeleteMixin):
    """
    Bank account linked to an employee for direct deposit.

    NACHA compliance requires:
    - Written authorization on file before initiating deposits
    - Prenote ($0.00 test transaction) recommended before first live deposit
    - Account numbers encrypted at rest
    - Retain authorization 2 years after termination/revocation
    """

    __tablename__ = "employee_bank_accounts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    account_holder_name: Mapped[str] = mapped_column(
        String(255), nullable=False,
    )
    account_number_encrypted: Mapped[bytes] = mapped_column(
        nullable=False,
    )
    routing_number: Mapped[str] = mapped_column(
        String(9), nullable=False,
    )
    account_type: Mapped[str] = mapped_column(
        Enum(
            "CHECKING", "SAVINGS",
            name="account_type",
            create_type=False,
        ),
        nullable=False,
        server_default=text("'CHECKING'"),
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true"),
    )
    enrollment_date: Mapped[date | None] = mapped_column(
        Date, nullable=True,
    )
    authorization_on_file: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false"),
    )
    prenote_status: Mapped[str] = mapped_column(
        Enum(
            "PENDING", "VERIFIED", "FAILED",
            name="prenote_status",
            create_type=False,
        ),
        nullable=False,
        server_default=text("'PENDING'"),
    )
    prenote_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    prenote_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
