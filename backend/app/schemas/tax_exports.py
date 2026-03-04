"""
Pydantic schemas for tax form data exports (modules X1-X9).

Georgia state forms: G-7, 500, 600, ST-3.
Federal forms: Schedule C, 1120-S, 1120, 1065.
Tax document checklist.

All exports produce data-only output (not official IRS/DOR forms).
CPA_OWNER reviews before filing.
"""

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import Field

from app.schemas import BaseSchema


# ---------------------------------------------------------------------------
# X1 — Georgia Form G-7 (Quarterly Payroll Withholding)
# ---------------------------------------------------------------------------


class G7LineItem(BaseSchema):
    """Per-month withholding detail for Form G-7."""

    month: int
    month_name: str
    georgia_withholding: Decimal = Decimal("0.00")
    employee_count: int = 0


class FormG7Data(BaseSchema):
    """Data for Georgia Form G-7 — Quarterly Return of Withholding Tax."""

    client_id: UUID
    client_name: str
    tax_year: int
    quarter: int  # 1-4
    quarter_start: date
    quarter_end: date
    due_date: date
    monthly_details: list[G7LineItem] = []
    total_withholding: Decimal = Decimal("0.00")
    total_employees: int = 0


# ---------------------------------------------------------------------------
# X2 — Georgia Form 500 (Individual Income — Schedule C)
# ---------------------------------------------------------------------------


class Form500Data(BaseSchema):
    """Data for Georgia Form 500 — Individual Income Tax Return (Schedule C portion)."""

    client_id: UUID
    client_name: str
    entity_type: str
    tax_year: int
    gross_revenue: Decimal = Decimal("0.00")
    total_expenses: Decimal = Decimal("0.00")
    net_income: Decimal = Decimal("0.00")
    expense_breakdown: dict[str, Decimal] = {}


# ---------------------------------------------------------------------------
# X3 — Georgia Form 600 (Corporate Income)
# ---------------------------------------------------------------------------


class Form600Data(BaseSchema):
    """Data for Georgia Form 600 — Corporation Tax Return."""

    client_id: UUID
    client_name: str
    entity_type: str
    tax_year: int
    gross_revenue: Decimal = Decimal("0.00")
    total_expenses: Decimal = Decimal("0.00")
    taxable_income: Decimal = Decimal("0.00")
    total_assets: Decimal = Decimal("0.00")
    total_liabilities: Decimal = Decimal("0.00")
    total_equity: Decimal = Decimal("0.00")


# ---------------------------------------------------------------------------
# X4 — Georgia Form ST-3 (Sales Tax)
# ---------------------------------------------------------------------------


class ST3LineItem(BaseSchema):
    """Per-jurisdiction sales tax detail."""

    jurisdiction: str
    gross_sales: Decimal = Decimal("0.00")
    exempt_sales: Decimal = Decimal("0.00")
    taxable_sales: Decimal = Decimal("0.00")
    tax_collected: Decimal = Decimal("0.00")


class FormST3Data(BaseSchema):
    """Data for Georgia Form ST-3 — Sales and Use Tax Return."""

    client_id: UUID
    client_name: str
    tax_year: int
    period_start: date
    period_end: date
    total_gross_sales: Decimal = Decimal("0.00")
    total_exempt_sales: Decimal = Decimal("0.00")
    total_taxable_sales: Decimal = Decimal("0.00")
    total_tax_collected: Decimal = Decimal("0.00")
    line_items: list[ST3LineItem] = []


# ---------------------------------------------------------------------------
# X5 — Federal Schedule C (Sole Proprietors)
# ---------------------------------------------------------------------------


class ScheduleCData(BaseSchema):
    """Data for Federal Schedule C — Profit or Loss from Business."""

    client_id: UUID
    client_name: str
    entity_type: str
    tax_year: int
    gross_receipts: Decimal = Decimal("0.00")
    cost_of_goods_sold: Decimal = Decimal("0.00")
    gross_profit: Decimal = Decimal("0.00")
    total_expenses: Decimal = Decimal("0.00")
    net_profit: Decimal = Decimal("0.00")
    expense_categories: dict[str, Decimal] = {}


# ---------------------------------------------------------------------------
# X6 — Federal Form 1120-S (S-Corps)
# ---------------------------------------------------------------------------


class Form1120SData(BaseSchema):
    """Data for Federal Form 1120-S — U.S. Income Tax Return for an S Corporation."""

    client_id: UUID
    client_name: str
    entity_type: str
    tax_year: int
    gross_receipts: Decimal = Decimal("0.00")
    cost_of_goods_sold: Decimal = Decimal("0.00")
    gross_profit: Decimal = Decimal("0.00")
    total_deductions: Decimal = Decimal("0.00")
    ordinary_business_income: Decimal = Decimal("0.00")
    total_assets: Decimal = Decimal("0.00")
    total_liabilities: Decimal = Decimal("0.00")
    shareholders_equity: Decimal = Decimal("0.00")
    expense_categories: dict[str, Decimal] = {}


# ---------------------------------------------------------------------------
# X7 — Federal Form 1120 (C-Corps)
# ---------------------------------------------------------------------------


class Form1120Data(BaseSchema):
    """Data for Federal Form 1120 — U.S. Corporation Income Tax Return."""

    client_id: UUID
    client_name: str
    entity_type: str
    tax_year: int
    gross_receipts: Decimal = Decimal("0.00")
    cost_of_goods_sold: Decimal = Decimal("0.00")
    gross_profit: Decimal = Decimal("0.00")
    total_deductions: Decimal = Decimal("0.00")
    taxable_income: Decimal = Decimal("0.00")
    total_assets: Decimal = Decimal("0.00")
    total_liabilities: Decimal = Decimal("0.00")
    retained_earnings: Decimal = Decimal("0.00")
    expense_categories: dict[str, Decimal] = {}


# ---------------------------------------------------------------------------
# X8 — Federal Form 1065 (Partnerships/LLCs)
# ---------------------------------------------------------------------------


class Form1065Data(BaseSchema):
    """Data for Federal Form 1065 — U.S. Return of Partnership Income."""

    client_id: UUID
    client_name: str
    entity_type: str
    tax_year: int
    gross_receipts: Decimal = Decimal("0.00")
    cost_of_goods_sold: Decimal = Decimal("0.00")
    gross_profit: Decimal = Decimal("0.00")
    total_deductions: Decimal = Decimal("0.00")
    ordinary_business_income: Decimal = Decimal("0.00")
    total_assets: Decimal = Decimal("0.00")
    total_liabilities: Decimal = Decimal("0.00")
    partners_equity: Decimal = Decimal("0.00")
    expense_categories: dict[str, Decimal] = {}


# ---------------------------------------------------------------------------
# X9 — Tax Document Checklist
# ---------------------------------------------------------------------------


class ChecklistItem(BaseSchema):
    """A single item on the tax document checklist."""

    document: str
    required: bool = True
    status: str = "NEEDED"  # NEEDED, RECEIVED, NOT_APPLICABLE
    notes: str | None = None


class TaxDocumentChecklist(BaseSchema):
    """Per-client tax document checklist based on entity type."""

    client_id: UUID
    client_name: str
    entity_type: str
    tax_year: int
    items: list[ChecklistItem] = []
    total_required: int = 0
    total_received: int = 0
