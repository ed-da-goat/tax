"""
SQLAlchemy ORM model for the employees table (module P1).

Maps to existing PostgreSQL table created by 001_initial_schema.sql.

Compliance (CLAUDE.md rule #4): client_id is non-nullable.
Compliance (CLAUDE.md rule #2): soft deletes only via deleted_at.
"""

import enum
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, Enum, ForeignKey, Integer, Numeric, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin, TimestampMixin


class FilingStatus(str, enum.Enum):
    SINGLE = "SINGLE"
    MARRIED = "MARRIED"
    HEAD_OF_HOUSEHOLD = "HEAD_OF_HOUSEHOLD"


class PayType(str, enum.Enum):
    HOURLY = "HOURLY"
    SALARY = "SALARY"


class Employee(Base, TimestampMixin, SoftDeleteMixin):
    """
    Employee record belonging to a specific client.

    Foundation for the payroll system (Phase 4). Each client maintains
    their own set of employees. SSN is stored encrypted at rest.
    """

    __tablename__ = "employees"

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
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    ssn_encrypted: Mapped[bytes | None] = mapped_column(nullable=True)
    filing_status: Mapped[str] = mapped_column(
        Enum(
            "SINGLE", "MARRIED", "HEAD_OF_HOUSEHOLD",
            name="filing_status",
            create_type=False,
        ),
        nullable=False,
        server_default=text("'SINGLE'"),
    )
    allowances: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0"),
    )
    pay_rate: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False,
    )
    pay_type: Mapped[str] = mapped_column(
        Enum(
            "HOURLY", "SALARY",
            name="pay_type",
            create_type=False,
        ),
        nullable=False,
    )
    hire_date: Mapped[date] = mapped_column(Date, nullable=False)
    termination_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true"),
    )
