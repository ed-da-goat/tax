"""
Pydantic schemas for 1099-NEC data generation.
"""

from decimal import Decimal
from uuid import UUID

from app.schemas import BaseSchema


class Form1099NECData(BaseSchema):
    """1099-NEC data for a single vendor for a tax year."""

    vendor_id: UUID
    vendor_name: str
    vendor_address: str | None = None
    vendor_city: str | None = None
    vendor_state: str | None = None
    vendor_zip: str | None = None
    tax_year: int
    # Box 1 — Nonemployee compensation
    box1_nonemployee_compensation: Decimal = Decimal("0.00")


class Form1099NECSummaryResponse(BaseSchema):
    """List of 1099-NEC data for all eligible vendors of a client."""

    client_id: UUID
    tax_year: int
    payer_name: str
    payer_address: str | None = None
    forms: list[Form1099NECData] = []
    total_nonemployee_compensation: Decimal = Decimal("0.00")
