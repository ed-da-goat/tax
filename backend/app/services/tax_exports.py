"""
Tax form data export service (modules X1-X9).

Generates data for Georgia state and federal tax forms by querying the GL,
payroll, and client data. Output is structured data for CPA review —
not official IRS/DOR form PDFs.

Compliance (CLAUDE.md):
- Rule #4: CLIENT ISOLATION — every query filters by client_id.
- Rule #5: Only POSTED GL entries and FINALIZED payroll contribute.
- Tax form exports: CPA_OWNER only (per CLAUDE.md role permissions).
"""

import calendar
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.client import Client
from app.schemas.tax_exports import (
    ChecklistItem,
    Form1065Data,
    Form1120Data,
    Form1120SData,
    Form500Data,
    Form600Data,
    FormG7Data,
    FormST3Data,
    G7LineItem,
    ScheduleCData,
    TaxDocumentChecklist,
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


async def _get_client(db: AsyncSession, client_id: uuid.UUID) -> Client:
    """Fetch client or raise."""
    from sqlalchemy import select
    from fastapi import HTTPException, status as http_status

    stmt = select(Client).where(
        Client.id == client_id,
        Client.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    client = result.scalar_one_or_none()
    if client is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )
    return client


async def _get_income_statement_data(
    db: AsyncSession,
    client_id: uuid.UUID,
    period_start: date,
    period_end: date,
) -> tuple[Decimal, Decimal, dict[str, Decimal]]:
    """
    Get revenue, expenses, and expense breakdown for a period.

    Returns (total_revenue, total_expenses, expense_categories).
    Only POSTED entries in the date range.
    """
    stmt = text(
        "SELECT "
        "    coa.account_type, "
        "    coa.account_name, "
        "    COALESCE(SUM(jel.debit), 0) AS total_debits, "
        "    COALESCE(SUM(jel.credit), 0) AS total_credits "
        "FROM chart_of_accounts coa "
        "INNER JOIN journal_entry_lines jel ON jel.account_id = coa.id "
        "    AND jel.deleted_at IS NULL "
        "INNER JOIN journal_entries je ON je.id = jel.journal_entry_id "
        "    AND je.status = 'POSTED' "
        "    AND je.deleted_at IS NULL "
        "    AND je.client_id = :client_id "
        "    AND je.entry_date >= :period_start "
        "    AND je.entry_date <= :period_end "
        "WHERE coa.client_id = :client_id "
        "    AND coa.deleted_at IS NULL "
        "    AND coa.account_type IN ('REVENUE', 'EXPENSE') "
        "GROUP BY coa.account_type, coa.account_name "
        "ORDER BY coa.account_type, coa.account_name"
    )
    result = await db.execute(stmt, {
        "client_id": str(client_id),
        "period_start": period_start,
        "period_end": period_end,
    })

    total_revenue = Decimal("0.00")
    total_expenses = Decimal("0.00")
    expense_cats: dict[str, Decimal] = {}

    for row in result.all():
        if row.account_type == "REVENUE":
            total_revenue += row.total_credits - row.total_debits
        elif row.account_type == "EXPENSE":
            amount = row.total_debits - row.total_credits
            total_expenses += amount
            expense_cats[row.account_name] = amount

    return total_revenue, total_expenses, expense_cats


async def _get_balance_sheet_totals(
    db: AsyncSession,
    client_id: uuid.UUID,
    as_of_date: date,
) -> tuple[Decimal, Decimal, Decimal]:
    """
    Get total assets, liabilities, equity as of a date.

    Returns (total_assets, total_liabilities, total_equity).
    """
    stmt = text(
        "SELECT "
        "    coa.account_type, "
        "    COALESCE(SUM(jel.debit), 0) AS total_debits, "
        "    COALESCE(SUM(jel.credit), 0) AS total_credits "
        "FROM chart_of_accounts coa "
        "INNER JOIN journal_entry_lines jel ON jel.account_id = coa.id "
        "    AND jel.deleted_at IS NULL "
        "INNER JOIN journal_entries je ON je.id = jel.journal_entry_id "
        "    AND je.status = 'POSTED' "
        "    AND je.deleted_at IS NULL "
        "    AND je.client_id = :client_id "
        "    AND je.entry_date <= :as_of_date "
        "WHERE coa.client_id = :client_id "
        "    AND coa.deleted_at IS NULL "
        "    AND coa.account_type IN ('ASSET', 'LIABILITY', 'EQUITY') "
        "GROUP BY coa.account_type"
    )
    result = await db.execute(stmt, {
        "client_id": str(client_id),
        "as_of_date": as_of_date,
    })

    assets = Decimal("0.00")
    liabilities = Decimal("0.00")
    equity = Decimal("0.00")

    for row in result.all():
        if row.account_type == "ASSET":
            assets += row.total_debits - row.total_credits
        elif row.account_type == "LIABILITY":
            liabilities += row.total_credits - row.total_debits
        elif row.account_type == "EQUITY":
            equity += row.total_credits - row.total_debits

    return assets, liabilities, equity


def _quarter_dates(tax_year: int, quarter: int) -> tuple[date, date, date]:
    """Return (quarter_start, quarter_end, due_date) for a quarter."""
    starts = {1: 1, 2: 4, 3: 7, 4: 10}
    start_month = starts[quarter]
    end_month = start_month + 2
    last_day = calendar.monthrange(tax_year, end_month)[1]

    quarter_start = date(tax_year, start_month, 1)
    quarter_end = date(tax_year, end_month, last_day)

    # Due: last day of month after quarter end
    due_month = end_month + 1
    due_year = tax_year
    if due_month > 12:
        due_month = 1
        due_year += 1
    due_day = calendar.monthrange(due_year, due_month)[1]
    due_date = date(due_year, due_month, due_day)

    return quarter_start, quarter_end, due_date


# ---------------------------------------------------------------------------
# X1 — Georgia Form G-7 (Quarterly Payroll Withholding)
# ---------------------------------------------------------------------------


class FormG7Service:
    """Generate data for Georgia Form G-7."""

    @staticmethod
    async def generate(
        db: AsyncSession,
        client_id: uuid.UUID,
        tax_year: int,
        quarter: int,
    ) -> FormG7Data:
        """
        Generate G-7 quarterly withholding data from FINALIZED payroll runs.

        Due: last day of month after quarter end.
        """
        client = await _get_client(db, client_id)
        quarter_start, quarter_end, due_date = _quarter_dates(tax_year, quarter)

        # Query payroll withholdings by month
        stmt = text(
            "SELECT "
            "    EXTRACT(MONTH FROM pr.pay_date)::int AS pay_month, "
            "    COALESCE(SUM(pi.state_withholding), 0) AS ga_withholding, "
            "    COUNT(DISTINCT pi.employee_id) AS emp_count "
            "FROM payroll_runs pr "
            "INNER JOIN payroll_items pi ON pi.payroll_run_id = pr.id "
            "    AND pi.deleted_at IS NULL "
            "WHERE pr.client_id = :client_id "
            "    AND pr.status = 'FINALIZED' "
            "    AND pr.deleted_at IS NULL "
            "    AND pr.pay_date >= :start "
            "    AND pr.pay_date <= :end "
            "GROUP BY EXTRACT(MONTH FROM pr.pay_date) "
            "ORDER BY pay_month"
        )
        result = await db.execute(stmt, {
            "client_id": str(client_id),
            "start": quarter_start,
            "end": quarter_end,
        })

        month_data = {row.pay_month: row for row in result.all()}
        monthly_details = []
        total_wh = Decimal("0.00")
        total_emps = 0

        for i in range(3):
            m = quarter_start.month + i
            row = month_data.get(m)
            wh = Decimal(str(row.ga_withholding)) if row else Decimal("0.00")
            ec = int(row.emp_count) if row else 0
            monthly_details.append(G7LineItem(
                month=m,
                month_name=calendar.month_name[m],
                georgia_withholding=wh,
                employee_count=ec,
            ))
            total_wh += wh
            total_emps = max(total_emps, ec)

        return FormG7Data(
            client_id=client_id,
            client_name=client.name,
            tax_year=tax_year,
            quarter=quarter,
            quarter_start=quarter_start,
            quarter_end=quarter_end,
            due_date=due_date,
            monthly_details=monthly_details,
            total_withholding=total_wh,
            total_employees=total_emps,
        )


# ---------------------------------------------------------------------------
# X2 — Georgia Form 500 (Individual Income — Schedule C)
# ---------------------------------------------------------------------------


class Form500Service:
    """Generate data for Georgia Form 500 (sole proprietor / Schedule C)."""

    @staticmethod
    async def generate(
        db: AsyncSession,
        client_id: uuid.UUID,
        tax_year: int,
    ) -> Form500Data:
        client = await _get_client(db, client_id)
        period_start = date(tax_year, 1, 1)
        period_end = date(tax_year, 12, 31)

        revenue, expenses, expense_cats = await _get_income_statement_data(
            db, client_id, period_start, period_end,
        )

        return Form500Data(
            client_id=client_id,
            client_name=client.name,
            entity_type=client.entity_type.value if hasattr(client.entity_type, 'value') else str(client.entity_type),
            tax_year=tax_year,
            gross_revenue=revenue,
            total_expenses=expenses,
            net_income=revenue - expenses,
            expense_breakdown=expense_cats,
        )


# ---------------------------------------------------------------------------
# X3 — Georgia Form 600 (Corporate Income)
# ---------------------------------------------------------------------------


class Form600Service:
    """Generate data for Georgia Form 600 (C-Corp)."""

    @staticmethod
    async def generate(
        db: AsyncSession,
        client_id: uuid.UUID,
        tax_year: int,
    ) -> Form600Data:
        client = await _get_client(db, client_id)
        period_start = date(tax_year, 1, 1)
        period_end = date(tax_year, 12, 31)

        revenue, expenses, _ = await _get_income_statement_data(
            db, client_id, period_start, period_end,
        )
        assets, liabilities, equity = await _get_balance_sheet_totals(
            db, client_id, period_end,
        )

        return Form600Data(
            client_id=client_id,
            client_name=client.name,
            entity_type=client.entity_type.value if hasattr(client.entity_type, 'value') else str(client.entity_type),
            tax_year=tax_year,
            gross_revenue=revenue,
            total_expenses=expenses,
            taxable_income=revenue - expenses,
            total_assets=assets,
            total_liabilities=liabilities,
            total_equity=equity,
        )


# ---------------------------------------------------------------------------
# X4 — Georgia Form ST-3 (Sales Tax)
# ---------------------------------------------------------------------------


class FormST3Service:
    """Generate data for Georgia Form ST-3 (Sales Tax)."""

    @staticmethod
    async def generate(
        db: AsyncSession,
        client_id: uuid.UUID,
        tax_year: int,
        period_start: date,
        period_end: date,
    ) -> FormST3Data:
        """
        Generate sales tax data.

        Uses REVENUE accounts as proxy for gross sales.
        # COMPLIANCE REVIEW NEEDED: Sales tax exemptions and jurisdiction
        # breakdown require additional data beyond the current GL structure.
        # This produces a gross sales summary from REVENUE GL accounts.
        """
        client = await _get_client(db, client_id)

        # Get total revenue as proxy for gross sales
        stmt = text(
            "SELECT "
            "    COALESCE(SUM(jel.credit) - SUM(jel.debit), 0) AS gross_sales "
            "FROM chart_of_accounts coa "
            "INNER JOIN journal_entry_lines jel ON jel.account_id = coa.id "
            "    AND jel.deleted_at IS NULL "
            "INNER JOIN journal_entries je ON je.id = jel.journal_entry_id "
            "    AND je.status = 'POSTED' "
            "    AND je.deleted_at IS NULL "
            "    AND je.client_id = :client_id "
            "    AND je.entry_date >= :period_start "
            "    AND je.entry_date <= :period_end "
            "WHERE coa.client_id = :client_id "
            "    AND coa.deleted_at IS NULL "
            "    AND coa.account_type = 'REVENUE'"
        )
        result = await db.execute(stmt, {
            "client_id": str(client_id),
            "period_start": period_start,
            "period_end": period_end,
        })
        gross_sales = result.scalar_one() or Decimal("0.00")

        return FormST3Data(
            client_id=client_id,
            client_name=client.name,
            tax_year=tax_year,
            period_start=period_start,
            period_end=period_end,
            total_gross_sales=gross_sales,
            total_exempt_sales=Decimal("0.00"),
            total_taxable_sales=gross_sales,
            total_tax_collected=Decimal("0.00"),
        )


# ---------------------------------------------------------------------------
# X5 — Federal Schedule C (Sole Proprietors)
# ---------------------------------------------------------------------------


class ScheduleCService:
    """Generate data for Federal Schedule C."""

    @staticmethod
    async def generate(
        db: AsyncSession,
        client_id: uuid.UUID,
        tax_year: int,
    ) -> ScheduleCData:
        client = await _get_client(db, client_id)
        period_start = date(tax_year, 1, 1)
        period_end = date(tax_year, 12, 31)

        revenue, expenses, expense_cats = await _get_income_statement_data(
            db, client_id, period_start, period_end,
        )

        # COGS would normally be a separate category; for now gross profit = revenue
        return ScheduleCData(
            client_id=client_id,
            client_name=client.name,
            entity_type=client.entity_type.value if hasattr(client.entity_type, 'value') else str(client.entity_type),
            tax_year=tax_year,
            gross_receipts=revenue,
            cost_of_goods_sold=Decimal("0.00"),
            gross_profit=revenue,
            total_expenses=expenses,
            net_profit=revenue - expenses,
            expense_categories=expense_cats,
        )


# ---------------------------------------------------------------------------
# X6 — Federal Form 1120-S (S-Corps)
# ---------------------------------------------------------------------------


class Form1120SService:
    """Generate data for Federal Form 1120-S."""

    @staticmethod
    async def generate(
        db: AsyncSession,
        client_id: uuid.UUID,
        tax_year: int,
    ) -> Form1120SData:
        client = await _get_client(db, client_id)
        period_start = date(tax_year, 1, 1)
        period_end = date(tax_year, 12, 31)

        revenue, expenses, expense_cats = await _get_income_statement_data(
            db, client_id, period_start, period_end,
        )
        assets, liabilities, equity = await _get_balance_sheet_totals(
            db, client_id, period_end,
        )

        return Form1120SData(
            client_id=client_id,
            client_name=client.name,
            entity_type=client.entity_type.value if hasattr(client.entity_type, 'value') else str(client.entity_type),
            tax_year=tax_year,
            gross_receipts=revenue,
            cost_of_goods_sold=Decimal("0.00"),
            gross_profit=revenue,
            total_deductions=expenses,
            ordinary_business_income=revenue - expenses,
            total_assets=assets,
            total_liabilities=liabilities,
            shareholders_equity=equity,
            expense_categories=expense_cats,
        )


# ---------------------------------------------------------------------------
# X7 — Federal Form 1120 (C-Corps)
# ---------------------------------------------------------------------------


class Form1120Service:
    """Generate data for Federal Form 1120."""

    @staticmethod
    async def generate(
        db: AsyncSession,
        client_id: uuid.UUID,
        tax_year: int,
    ) -> Form1120Data:
        client = await _get_client(db, client_id)
        period_start = date(tax_year, 1, 1)
        period_end = date(tax_year, 12, 31)

        revenue, expenses, expense_cats = await _get_income_statement_data(
            db, client_id, period_start, period_end,
        )
        assets, liabilities, equity = await _get_balance_sheet_totals(
            db, client_id, period_end,
        )

        return Form1120Data(
            client_id=client_id,
            client_name=client.name,
            entity_type=client.entity_type.value if hasattr(client.entity_type, 'value') else str(client.entity_type),
            tax_year=tax_year,
            gross_receipts=revenue,
            cost_of_goods_sold=Decimal("0.00"),
            gross_profit=revenue,
            total_deductions=expenses,
            taxable_income=revenue - expenses,
            total_assets=assets,
            total_liabilities=liabilities,
            retained_earnings=equity,
            expense_categories=expense_cats,
        )


# ---------------------------------------------------------------------------
# X8 — Federal Form 1065 (Partnerships/LLCs)
# ---------------------------------------------------------------------------


class Form1065Service:
    """Generate data for Federal Form 1065."""

    @staticmethod
    async def generate(
        db: AsyncSession,
        client_id: uuid.UUID,
        tax_year: int,
    ) -> Form1065Data:
        client = await _get_client(db, client_id)
        period_start = date(tax_year, 1, 1)
        period_end = date(tax_year, 12, 31)

        revenue, expenses, expense_cats = await _get_income_statement_data(
            db, client_id, period_start, period_end,
        )
        assets, liabilities, equity = await _get_balance_sheet_totals(
            db, client_id, period_end,
        )

        return Form1065Data(
            client_id=client_id,
            client_name=client.name,
            entity_type=client.entity_type.value if hasattr(client.entity_type, 'value') else str(client.entity_type),
            tax_year=tax_year,
            gross_receipts=revenue,
            cost_of_goods_sold=Decimal("0.00"),
            gross_profit=revenue,
            total_deductions=expenses,
            ordinary_business_income=revenue - expenses,
            total_assets=assets,
            total_liabilities=liabilities,
            partners_equity=equity,
            expense_categories=expense_cats,
        )


# ---------------------------------------------------------------------------
# X9 — Tax Document Checklist Generator
# ---------------------------------------------------------------------------


# Checklists by entity type
_SOLE_PROP_CHECKLIST = [
    ChecklistItem(document="Prior year tax return (Federal Form 1040 + Schedule C)"),
    ChecklistItem(document="QuickBooks/Accounting records export"),
    ChecklistItem(document="Bank statements (all business accounts)"),
    ChecklistItem(document="1099-NEC forms received (independent contractors paid)"),
    ChecklistItem(document="1099-MISC forms received"),
    ChecklistItem(document="1099-K forms received (payment processors)"),
    ChecklistItem(document="W-2 forms (if also employed elsewhere)"),
    ChecklistItem(document="Business vehicle mileage log"),
    ChecklistItem(document="Home office measurements (if applicable)"),
    ChecklistItem(document="Health insurance premium statements"),
    ChecklistItem(document="Estimated tax payment records (Federal + Georgia)"),
    ChecklistItem(document="Georgia Form 500 prior year (if applicable)"),
    ChecklistItem(document="Business licenses and permits"),
    ChecklistItem(document="Depreciation schedules for business assets"),
]

_S_CORP_CHECKLIST = [
    ChecklistItem(document="Prior year tax return (Federal Form 1120-S + K-1s)"),
    ChecklistItem(document="QuickBooks/Accounting records export"),
    ChecklistItem(document="Bank statements (all business accounts)"),
    ChecklistItem(document="Payroll reports (all quarters)"),
    ChecklistItem(document="W-2 forms issued to shareholders/employees"),
    ChecklistItem(document="1099-NEC forms issued"),
    ChecklistItem(document="1099-NEC forms received"),
    ChecklistItem(document="1099-K forms received"),
    ChecklistItem(document="Georgia Form G-7 quarterly returns"),
    ChecklistItem(document="Shareholder basis calculations"),
    ChecklistItem(document="Minutes of shareholder meetings"),
    ChecklistItem(document="Loan agreements (shareholder loans, business loans)"),
    ChecklistItem(document="Depreciation schedules"),
    ChecklistItem(document="Health insurance premium statements"),
    ChecklistItem(document="Estimated tax payment records"),
]

_C_CORP_CHECKLIST = [
    ChecklistItem(document="Prior year tax return (Federal Form 1120)"),
    ChecklistItem(document="QuickBooks/Accounting records export"),
    ChecklistItem(document="Bank statements (all business accounts)"),
    ChecklistItem(document="Payroll reports (all quarters)"),
    ChecklistItem(document="W-2 forms issued to all employees"),
    ChecklistItem(document="1099-NEC forms issued"),
    ChecklistItem(document="1099-NEC forms received"),
    ChecklistItem(document="1099-K forms received"),
    ChecklistItem(document="Georgia Form 600 prior year"),
    ChecklistItem(document="Georgia Form G-7 quarterly returns"),
    ChecklistItem(document="Board of directors meeting minutes"),
    ChecklistItem(document="Dividend distribution records"),
    ChecklistItem(document="Loan agreements"),
    ChecklistItem(document="Depreciation schedules"),
    ChecklistItem(document="Estimated tax payment records (Federal + Georgia)"),
]

_PARTNERSHIP_CHECKLIST = [
    ChecklistItem(document="Prior year tax return (Federal Form 1065 + K-1s)"),
    ChecklistItem(document="Partnership agreement (current version)"),
    ChecklistItem(document="QuickBooks/Accounting records export"),
    ChecklistItem(document="Bank statements (all business accounts)"),
    ChecklistItem(document="Payroll reports (if employees, all quarters)"),
    ChecklistItem(document="W-2 forms issued (if employees)"),
    ChecklistItem(document="1099-NEC forms issued"),
    ChecklistItem(document="1099-NEC forms received"),
    ChecklistItem(document="1099-K forms received"),
    ChecklistItem(document="Partner capital account statements"),
    ChecklistItem(document="Partner distribution records"),
    ChecklistItem(document="Georgia Form G-7 quarterly returns (if employees)"),
    ChecklistItem(document="Loan agreements (partner loans, business loans)"),
    ChecklistItem(document="Depreciation schedules"),
    ChecklistItem(document="Estimated tax payment records"),
]


class TaxChecklistService:
    """Generate tax document checklists by entity type."""

    @staticmethod
    async def generate(
        db: AsyncSession,
        client_id: uuid.UUID,
        tax_year: int,
    ) -> TaxDocumentChecklist:
        client = await _get_client(db, client_id)
        entity = client.entity_type.value if hasattr(client.entity_type, 'value') else str(client.entity_type)

        if entity == "SOLE_PROP":
            items = [ChecklistItem(**i.model_dump()) for i in _SOLE_PROP_CHECKLIST]
        elif entity == "S_CORP":
            items = [ChecklistItem(**i.model_dump()) for i in _S_CORP_CHECKLIST]
        elif entity == "C_CORP":
            items = [ChecklistItem(**i.model_dump()) for i in _C_CORP_CHECKLIST]
        elif entity == "PARTNERSHIP_LLC":
            items = [ChecklistItem(**i.model_dump()) for i in _PARTNERSHIP_CHECKLIST]
        else:
            items = []

        return TaxDocumentChecklist(
            client_id=client_id,
            client_name=client.name,
            entity_type=entity,
            tax_year=tax_year,
            items=items,
            total_required=sum(1 for i in items if i.required),
            total_received=sum(1 for i in items if i.status == "RECEIVED"),
        )
