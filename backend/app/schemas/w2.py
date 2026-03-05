"""
Pydantic schemas for W-2 data generation.
"""

from decimal import Decimal
from uuid import UUID

from pydantic import Field

from app.schemas import BaseSchema


class W2Data(BaseSchema):
    """W-2 data for a single employee for a tax year."""

    employee_id: UUID
    employee_first_name: str
    employee_last_name: str
    employee_address: str | None = None
    employee_city: str | None = None
    employee_state: str | None = None
    employee_zip: str | None = None
    tax_year: int
    # Box 1 — Wages, tips, other compensation
    box1_wages: Decimal = Decimal("0.00")
    # Box 2 — Federal income tax withheld
    box2_federal_withheld: Decimal = Decimal("0.00")
    # Box 3 — Social security wages
    box3_ss_wages: Decimal = Decimal("0.00")
    # Box 4 — Social security tax withheld
    box4_ss_tax: Decimal = Decimal("0.00")
    # Box 5 — Medicare wages and tips
    box5_medicare_wages: Decimal = Decimal("0.00")
    # Box 6 — Medicare tax withheld
    box6_medicare_tax: Decimal = Decimal("0.00")
    # Box 16 — State wages, tips, etc.
    box16_state_wages: Decimal = Decimal("0.00")
    # Box 17 — State income tax
    box17_state_tax: Decimal = Decimal("0.00")


class W2SummaryResponse(BaseSchema):
    """List of W-2 data for all employees of a client in a tax year."""

    client_id: UUID
    tax_year: int
    employer_name: str
    employer_address: str | None = None
    w2s: list[W2Data] = []
    total_wages: Decimal = Decimal("0.00")
    total_federal_withheld: Decimal = Decimal("0.00")
