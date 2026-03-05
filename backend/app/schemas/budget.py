"""Pydantic schemas for budgeting (AN2)."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field

from app.schemas import BaseSchema, RecordSchema


class BudgetLineCreate(BaseSchema):
    account_id: UUID
    month_1: Decimal = Decimal("0")
    month_2: Decimal = Decimal("0")
    month_3: Decimal = Decimal("0")
    month_4: Decimal = Decimal("0")
    month_5: Decimal = Decimal("0")
    month_6: Decimal = Decimal("0")
    month_7: Decimal = Decimal("0")
    month_8: Decimal = Decimal("0")
    month_9: Decimal = Decimal("0")
    month_10: Decimal = Decimal("0")
    month_11: Decimal = Decimal("0")
    month_12: Decimal = Decimal("0")
    notes: str | None = None


class BudgetCreate(BaseSchema):
    name: str = Field(..., min_length=1, max_length=255)
    fiscal_year: int
    description: str | None = None
    lines: list[BudgetLineCreate] = []


class BudgetLineUpdate(BaseSchema):
    id: UUID | None = None
    account_id: UUID
    month_1: Decimal = Decimal("0")
    month_2: Decimal = Decimal("0")
    month_3: Decimal = Decimal("0")
    month_4: Decimal = Decimal("0")
    month_5: Decimal = Decimal("0")
    month_6: Decimal = Decimal("0")
    month_7: Decimal = Decimal("0")
    month_8: Decimal = Decimal("0")
    month_9: Decimal = Decimal("0")
    month_10: Decimal = Decimal("0")
    month_11: Decimal = Decimal("0")
    month_12: Decimal = Decimal("0")
    notes: str | None = None


class BudgetUpdate(BaseSchema):
    name: str | None = None
    description: str | None = None
    lines: list[BudgetLineUpdate] | None = None


class BudgetLineResponse(RecordSchema):
    budget_id: UUID
    account_id: UUID
    month_1: Decimal
    month_2: Decimal
    month_3: Decimal
    month_4: Decimal
    month_5: Decimal
    month_6: Decimal
    month_7: Decimal
    month_8: Decimal
    month_9: Decimal
    month_10: Decimal
    month_11: Decimal
    month_12: Decimal
    annual_total: Decimal
    notes: str | None = None


class BudgetResponse(RecordSchema):
    client_id: UUID
    name: str
    fiscal_year: int
    description: str | None = None
    is_active: bool
    lines: list[BudgetLineResponse] = []
    deleted_at: datetime | None = None


class BudgetList(BaseSchema):
    items: list[BudgetResponse]
    total: int


class BudgetVsActualLine(BaseSchema):
    account_id: UUID
    account_name: str
    account_number: str
    budget_amount: Decimal
    actual_amount: Decimal
    variance: Decimal
    variance_pct: Decimal | None = None


class BudgetVsActualReport(BaseSchema):
    client_id: UUID
    budget_name: str
    fiscal_year: int
    period_start: str
    period_end: str
    lines: list[BudgetVsActualLine]
    total_budget: Decimal
    total_actual: Decimal
    total_variance: Decimal
