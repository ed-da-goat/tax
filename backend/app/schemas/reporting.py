"""
Pydantic schemas for financial reports (modules R1-R5).

Request/response models for Profit & Loss, Balance Sheet, Cash Flow,
and firm-level dashboard reports.

Compliance (CLAUDE.md rule #4): All reports are scoped to client_id.
"""

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import Field

from app.schemas import BaseSchema


# ---------------------------------------------------------------------------
# R1 — Profit & Loss
# ---------------------------------------------------------------------------


class ProfitLossRow(BaseSchema):
    """A single account row in the P&L report."""

    account_number: str
    account_name: str
    account_type: str  # REVENUE or EXPENSE
    sub_type: str | None = None
    total_debits: Decimal
    total_credits: Decimal
    balance: Decimal


class ProfitLossReport(BaseSchema):
    """Complete Profit & Loss report for a client and period."""

    client_id: UUID
    period_start: date
    period_end: date
    revenue_items: list[ProfitLossRow] = []
    expense_items: list[ProfitLossRow] = []
    total_revenue: Decimal = Decimal("0.00")
    total_expenses: Decimal = Decimal("0.00")
    net_income: Decimal = Decimal("0.00")


# ---------------------------------------------------------------------------
# R2 — Balance Sheet
# ---------------------------------------------------------------------------


class BalanceSheetRow(BaseSchema):
    """A single account row in the Balance Sheet."""

    account_number: str
    account_name: str
    account_type: str
    sub_type: str | None = None
    total_debits: Decimal
    total_credits: Decimal
    balance: Decimal


class BalanceSheetReport(BaseSchema):
    """Complete Balance Sheet report for a client as of a date."""

    client_id: UUID
    as_of_date: date
    assets: list[BalanceSheetRow] = []
    liabilities: list[BalanceSheetRow] = []
    equity: list[BalanceSheetRow] = []
    total_assets: Decimal = Decimal("0.00")
    total_liabilities: Decimal = Decimal("0.00")
    total_equity: Decimal = Decimal("0.00")


# ---------------------------------------------------------------------------
# R3 — Cash Flow Statement
# ---------------------------------------------------------------------------


class CashFlowSection(BaseSchema):
    """A section of the cash flow statement (operating/investing/financing)."""

    label: str
    items: list[ProfitLossRow] = []
    subtotal: Decimal = Decimal("0.00")


class CashFlowReport(BaseSchema):
    """Complete Cash Flow Statement for a client and period."""

    client_id: UUID
    period_start: date
    period_end: date
    operating: CashFlowSection = Field(
        default_factory=lambda: CashFlowSection(label="Operating Activities")
    )
    investing: CashFlowSection = Field(
        default_factory=lambda: CashFlowSection(label="Investing Activities")
    )
    financing: CashFlowSection = Field(
        default_factory=lambda: CashFlowSection(label="Financing Activities")
    )
    net_change_in_cash: Decimal = Decimal("0.00")


# ---------------------------------------------------------------------------
# R5 — Firm Dashboard
# ---------------------------------------------------------------------------


class ClientMetric(BaseSchema):
    """Key financial metrics for a single client."""

    client_id: UUID
    client_name: str
    entity_type: str
    total_revenue: Decimal = Decimal("0.00")
    total_expenses: Decimal = Decimal("0.00")
    net_income: Decimal = Decimal("0.00")
    total_ar_outstanding: Decimal = Decimal("0.00")
    total_ap_outstanding: Decimal = Decimal("0.00")


class FirmDashboard(BaseSchema):
    """Firm-level dashboard with aggregated metrics across all clients."""

    total_clients: int = 0
    active_clients: int = 0
    firm_total_revenue: Decimal = Decimal("0.00")
    firm_total_expenses: Decimal = Decimal("0.00")
    firm_net_income: Decimal = Decimal("0.00")
    firm_total_ar: Decimal = Decimal("0.00")
    firm_total_ap: Decimal = Decimal("0.00")
    client_metrics: list[ClientMetric] = []
