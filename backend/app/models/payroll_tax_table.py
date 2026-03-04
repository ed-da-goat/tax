"""
SQLAlchemy ORM model for the payroll_tax_tables table.

Stores parameterized tax rates (brackets, flat rates) by tax year, tax type,
and filing status. Used by P2 (GA withholding) and P4 (federal withholding).

Compliance (CLAUDE.md rule #3):
    Every rate row must include source_document and review_date.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class PayrollTaxTable(Base, TimestampMixin):
    """Tax rate bracket/flat rate row for a given year and tax type."""

    __tablename__ = "payroll_tax_tables"

    tax_year: Mapped[int] = mapped_column(Integer, nullable=False)
    tax_type: Mapped[str] = mapped_column(String(50), nullable=False)
    filing_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    bracket_min: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    bracket_max: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    rate: Mapped[Decimal] = mapped_column(Numeric(8, 6), nullable=False)
    flat_amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False, default=Decimal("0.00"),
    )
    source_document: Mapped[str] = mapped_column(String(500), nullable=False)
    review_date: Mapped[date] = mapped_column(Date, nullable=False)
