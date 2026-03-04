"""
Pydantic schemas for Payroll (modules P2-P6).
"""

import enum
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field

from app.schemas import BaseSchema, RecordSchema


class PayrollRunStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    FINALIZED = "FINALIZED"
    VOID = "VOID"


# ---------------------------------------------------------------------------
# Payroll Item schemas
# ---------------------------------------------------------------------------

class PayrollItemCreate(BaseSchema):
    """Data to add an employee to a payroll run."""

    employee_id: UUID
    hours_worked: Decimal | None = Field(None, ge=0, description="Hours for hourly employees")


class PayrollItemResponse(RecordSchema):
    payroll_run_id: UUID
    employee_id: UUID
    gross_pay: Decimal
    federal_withholding: Decimal
    state_withholding: Decimal
    social_security: Decimal
    medicare: Decimal
    ga_suta: Decimal
    futa: Decimal
    net_pay: Decimal


# ---------------------------------------------------------------------------
# Payroll Run schemas
# ---------------------------------------------------------------------------

class PayrollRunCreate(BaseSchema):
    """Create a new payroll run (DRAFT status)."""

    pay_period_start: date
    pay_period_end: date
    pay_date: date
    employee_items: list[PayrollItemCreate] = Field(
        ..., min_length=1, description="At least one employee must be included",
    )
    pay_periods_per_year: int = Field(
        default=26, ge=1, le=52, description="Pay periods per year (e.g. 26=biweekly)",
    )
    tax_year: int = Field(default=2026, ge=2024, le=2030)
    suta_rate: Decimal | None = Field(
        None, ge=0, le=1,
        description="Custom SUTA rate for this client (None = default 2.7%)",
    )


class PayrollRunResponse(RecordSchema):
    client_id: UUID
    pay_period_start: date
    pay_period_end: date
    pay_date: date
    status: PayrollRunStatus
    finalized_by: UUID | None = None
    finalized_at: datetime | None = None
    items: list[PayrollItemResponse] = []


class PayrollRunList(BaseSchema):
    items: list[PayrollRunResponse]
    total: int


class PayrollRunSummary(BaseSchema):
    """Summary of a payroll run's financials."""

    payroll_run_id: UUID
    total_gross: Decimal
    total_federal_withholding: Decimal
    total_state_withholding: Decimal
    total_social_security: Decimal
    total_medicare: Decimal
    total_ga_suta: Decimal
    total_futa: Decimal
    total_net_pay: Decimal
    employee_count: int
