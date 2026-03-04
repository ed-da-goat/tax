"""
Financial reporting service (modules R1-R5).

Generates Profit & Loss, Balance Sheet, Cash Flow Statement, PDF exports,
and firm-level dashboard reports.

Compliance (CLAUDE.md):
- Rule #1: Reports read from POSTED GL entries only (double-entry guaranteed).
- Rule #4: CLIENT ISOLATION — every query filters by client_id.
- Rule #5: Only POSTED entries contribute to report figures.
"""

import io
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select, text, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bill import Bill
from app.models.chart_of_accounts import ChartOfAccounts
from app.models.client import Client
from app.models.invoice import Invoice
from app.models.journal_entry import JournalEntry, JournalEntryLine, JournalEntryStatus
from app.schemas.reporting import (
    BalanceSheetReport,
    BalanceSheetRow,
    CashFlowReport,
    CashFlowSection,
    ClientMetric,
    FirmDashboard,
    ProfitLossReport,
    ProfitLossRow,
)


# ---------------------------------------------------------------------------
# Cash flow classification by account sub_type
# ---------------------------------------------------------------------------
INVESTING_SUB_TYPES = {
    "Fixed Assets",
    "Property, Plant, Equipment",
    "Other Non-Current Assets",
    "Intangible Assets",
    "Investments",
}
FINANCING_SUB_TYPES = {
    "Long-term Debt",
    "Notes Payable",
    "Equity",
    "Owner's Equity",
    "Retained Earnings",
    "Paid-in Capital",
    "Common Stock",
    "Preferred Stock",
    "Dividends",
}


class ReportingService:
    """Business logic for financial report generation."""

    @staticmethod
    async def get_profit_loss(
        db: AsyncSession,
        client_id: uuid.UUID,
        period_start: date,
        period_end: date,
    ) -> ProfitLossReport:
        """
        Generate Profit & Loss report for a client and date range.

        Only POSTED journal entries within the date range are included.
        Revenue accounts: credit balance (credits - debits).
        Expense accounts: debit balance (debits - credits).

        Compliance (rule #4): ALWAYS filters by client_id.
        """
        stmt = text(
            "SELECT "
            "    coa.account_number, "
            "    coa.account_name, "
            "    coa.account_type, "
            "    coa.sub_type, "
            "    COALESCE(SUM(jel.debit), 0) AS total_debits, "
            "    COALESCE(SUM(jel.credit), 0) AS total_credits "
            "FROM chart_of_accounts coa "
            "LEFT JOIN ( "
            "    journal_entry_lines jel "
            "    INNER JOIN journal_entries je "
            "        ON je.id = jel.journal_entry_id "
            "        AND je.status = 'POSTED' "
            "        AND je.deleted_at IS NULL "
            "        AND je.entry_date >= :period_start "
            "        AND je.entry_date <= :period_end "
            "        AND je.client_id = :client_id "
            ") ON jel.account_id = coa.id "
            "    AND jel.deleted_at IS NULL "
            "WHERE coa.client_id = :client_id "
            "    AND coa.deleted_at IS NULL "
            "    AND coa.is_active = TRUE "
            "    AND coa.account_type IN ('REVENUE', 'EXPENSE') "
            "GROUP BY coa.account_number, coa.account_name, "
            "         coa.account_type, coa.sub_type "
            "HAVING COALESCE(SUM(jel.debit), 0) != 0 "
            "    OR COALESCE(SUM(jel.credit), 0) != 0 "
            "ORDER BY coa.account_number"
        )
        result = await db.execute(stmt, {
            "client_id": str(client_id),
            "period_start": period_start,
            "period_end": period_end,
        })
        rows = result.all()

        report = ProfitLossReport(
            client_id=client_id,
            period_start=period_start,
            period_end=period_end,
        )

        for row in rows:
            # Revenue: natural credit balance (credits - debits)
            # Expense: natural debit balance (debits - credits)
            if row.account_type == "REVENUE":
                balance = row.total_credits - row.total_debits
            else:
                balance = row.total_debits - row.total_credits

            pl_row = ProfitLossRow(
                account_number=row.account_number,
                account_name=row.account_name,
                account_type=row.account_type,
                sub_type=row.sub_type,
                total_debits=row.total_debits,
                total_credits=row.total_credits,
                balance=balance,
            )

            if row.account_type == "REVENUE":
                report.revenue_items.append(pl_row)
            else:
                report.expense_items.append(pl_row)

        report.total_revenue = sum(r.balance for r in report.revenue_items)
        report.total_expenses = sum(r.balance for r in report.expense_items)
        report.net_income = report.total_revenue - report.total_expenses

        return report

    @staticmethod
    async def get_balance_sheet(
        db: AsyncSession,
        client_id: uuid.UUID,
        as_of_date: date,
    ) -> BalanceSheetReport:
        """
        Generate Balance Sheet as of a specific date.

        Includes all POSTED journal entries on or before as_of_date.
        Asset accounts: debit balance (debits - credits).
        Liability accounts: credit balance (credits - debits).
        Equity accounts: credit balance (credits - debits).

        Compliance (rule #4): ALWAYS filters by client_id.
        """
        stmt = text(
            "SELECT "
            "    coa.account_number, "
            "    coa.account_name, "
            "    coa.account_type, "
            "    coa.sub_type, "
            "    COALESCE(SUM(jel.debit), 0) AS total_debits, "
            "    COALESCE(SUM(jel.credit), 0) AS total_credits "
            "FROM chart_of_accounts coa "
            "LEFT JOIN ( "
            "    journal_entry_lines jel "
            "    INNER JOIN journal_entries je "
            "        ON je.id = jel.journal_entry_id "
            "        AND je.status = 'POSTED' "
            "        AND je.deleted_at IS NULL "
            "        AND je.entry_date <= :as_of_date "
            "        AND je.client_id = :client_id "
            ") ON jel.account_id = coa.id "
            "    AND jel.deleted_at IS NULL "
            "WHERE coa.client_id = :client_id "
            "    AND coa.deleted_at IS NULL "
            "    AND coa.is_active = TRUE "
            "    AND coa.account_type IN ('ASSET', 'LIABILITY', 'EQUITY') "
            "GROUP BY coa.account_number, coa.account_name, "
            "         coa.account_type, coa.sub_type "
            "HAVING COALESCE(SUM(jel.debit), 0) != 0 "
            "    OR COALESCE(SUM(jel.credit), 0) != 0 "
            "ORDER BY coa.account_number"
        )
        result = await db.execute(stmt, {
            "client_id": str(client_id),
            "as_of_date": as_of_date,
        })
        rows = result.all()

        report = BalanceSheetReport(client_id=client_id, as_of_date=as_of_date)

        for row in rows:
            # Asset: natural debit balance
            # Liability & Equity: natural credit balance
            if row.account_type == "ASSET":
                balance = row.total_debits - row.total_credits
            else:
                balance = row.total_credits - row.total_debits

            bs_row = BalanceSheetRow(
                account_number=row.account_number,
                account_name=row.account_name,
                account_type=row.account_type,
                sub_type=row.sub_type,
                total_debits=row.total_debits,
                total_credits=row.total_credits,
                balance=balance,
            )

            if row.account_type == "ASSET":
                report.assets.append(bs_row)
            elif row.account_type == "LIABILITY":
                report.liabilities.append(bs_row)
            else:
                report.equity.append(bs_row)

        report.total_assets = sum(r.balance for r in report.assets)
        report.total_liabilities = sum(r.balance for r in report.liabilities)
        report.total_equity = sum(r.balance for r in report.equity)

        return report

    @staticmethod
    async def get_cash_flow(
        db: AsyncSession,
        client_id: uuid.UUID,
        period_start: date,
        period_end: date,
    ) -> CashFlowReport:
        """
        Generate Cash Flow Statement for a client and date range.

        Uses the direct method: categorizes GL entries by account sub_type
        into operating, investing, and financing activities.

        Operating: all entries not classified as investing or financing.
        Investing: entries in fixed asset / investment accounts.
        Financing: entries in long-term debt / equity accounts.

        Compliance (rule #4): ALWAYS filters by client_id.
        """
        stmt = text(
            "SELECT "
            "    coa.account_number, "
            "    coa.account_name, "
            "    coa.account_type, "
            "    coa.sub_type, "
            "    COALESCE(SUM(jel.debit), 0) AS total_debits, "
            "    COALESCE(SUM(jel.credit), 0) AS total_credits "
            "FROM chart_of_accounts coa "
            "LEFT JOIN ( "
            "    journal_entry_lines jel "
            "    INNER JOIN journal_entries je "
            "        ON je.id = jel.journal_entry_id "
            "        AND je.status = 'POSTED' "
            "        AND je.deleted_at IS NULL "
            "        AND je.entry_date >= :period_start "
            "        AND je.entry_date <= :period_end "
            "        AND je.client_id = :client_id "
            ") ON jel.account_id = coa.id "
            "    AND jel.deleted_at IS NULL "
            "WHERE coa.client_id = :client_id "
            "    AND coa.deleted_at IS NULL "
            "    AND coa.is_active = TRUE "
            "GROUP BY coa.account_number, coa.account_name, "
            "         coa.account_type, coa.sub_type "
            "HAVING COALESCE(SUM(jel.debit), 0) != 0 "
            "    OR COALESCE(SUM(jel.credit), 0) != 0 "
            "ORDER BY coa.account_number"
        )
        result = await db.execute(stmt, {
            "client_id": str(client_id),
            "period_start": period_start,
            "period_end": period_end,
        })
        rows = result.all()

        report = CashFlowReport(
            client_id=client_id,
            period_start=period_start,
            period_end=period_end,
        )

        for row in rows:
            # Net cash effect: credits to cash-increasing accounts, debits to cash-decreasing
            if row.account_type in ("ASSET",):
                net = row.total_debits - row.total_credits
            else:
                net = row.total_credits - row.total_debits

            cf_row = ProfitLossRow(
                account_number=row.account_number,
                account_name=row.account_name,
                account_type=row.account_type,
                sub_type=row.sub_type,
                total_debits=row.total_debits,
                total_credits=row.total_credits,
                balance=net,
            )

            sub = (row.sub_type or "").strip()
            if sub in INVESTING_SUB_TYPES:
                report.investing.items.append(cf_row)
            elif sub in FINANCING_SUB_TYPES:
                report.financing.items.append(cf_row)
            else:
                report.operating.items.append(cf_row)

        report.operating.subtotal = sum(r.balance for r in report.operating.items)
        report.investing.subtotal = sum(r.balance for r in report.investing.items)
        report.financing.subtotal = sum(r.balance for r in report.financing.items)
        report.net_change_in_cash = (
            report.operating.subtotal
            + report.investing.subtotal
            + report.financing.subtotal
        )

        return report

    @staticmethod
    async def generate_report_pdf(
        report_data: ProfitLossReport | BalanceSheetReport | CashFlowReport,
    ) -> bytes:
        """
        Generate a PDF from a report using WeasyPrint.

        CPA_OWNER only (enforced at router level).
        Returns raw PDF bytes.
        """
        from weasyprint import HTML

        html = ReportingService._render_report_html(report_data)
        pdf_bytes = HTML(string=html).write_pdf()
        return pdf_bytes

    @staticmethod
    def _render_report_html(
        report_data: ProfitLossReport | BalanceSheetReport | CashFlowReport,
    ) -> str:
        """Render a report to an HTML string for PDF conversion."""
        styles = (
            "<style>"
            "body { font-family: 'Helvetica Neue', Arial, sans-serif; margin: 40px; font-size: 12px; }"
            "h1 { font-size: 18px; border-bottom: 2px solid #333; padding-bottom: 8px; }"
            "h2 { font-size: 14px; margin-top: 20px; color: #444; }"
            "table { width: 100%; border-collapse: collapse; margin-top: 10px; }"
            "th, td { padding: 6px 10px; text-align: left; border-bottom: 1px solid #ddd; }"
            "th { background-color: #f5f5f5; font-weight: bold; }"
            "td.amount { text-align: right; font-family: monospace; }"
            ".total-row { font-weight: bold; border-top: 2px solid #333; }"
            ".footer { margin-top: 30px; font-size: 10px; color: #888; }"
            "</style>"
        )

        if isinstance(report_data, ProfitLossReport):
            return ReportingService._render_pnl_html(report_data, styles)
        elif isinstance(report_data, BalanceSheetReport):
            return ReportingService._render_bs_html(report_data, styles)
        else:
            return ReportingService._render_cf_html(report_data, styles)

    @staticmethod
    def _render_pnl_html(report: ProfitLossReport, styles: str) -> str:
        rows_html = ""

        if report.revenue_items:
            rows_html += "<h2>Revenue</h2><table><tr><th>Account</th><th>Name</th><th class='amount'>Amount</th></tr>"
            for r in report.revenue_items:
                rows_html += f"<tr><td>{r.account_number}</td><td>{r.account_name}</td><td class='amount'>{r.balance:,.2f}</td></tr>"
            rows_html += f"<tr class='total-row'><td colspan='2'>Total Revenue</td><td class='amount'>{report.total_revenue:,.2f}</td></tr></table>"

        if report.expense_items:
            rows_html += "<h2>Expenses</h2><table><tr><th>Account</th><th>Name</th><th class='amount'>Amount</th></tr>"
            for r in report.expense_items:
                rows_html += f"<tr><td>{r.account_number}</td><td>{r.account_name}</td><td class='amount'>{r.balance:,.2f}</td></tr>"
            rows_html += f"<tr class='total-row'><td colspan='2'>Total Expenses</td><td class='amount'>{report.total_expenses:,.2f}</td></tr></table>"

        return (
            f"<html><head>{styles}</head><body>"
            f"<h1>Profit &amp; Loss Statement</h1>"
            f"<p>Period: {report.period_start} to {report.period_end}</p>"
            f"{rows_html}"
            f"<h2>Net Income: {report.net_income:,.2f}</h2>"
            f"<div class='footer'>Generated by Georgia CPA Accounting System</div>"
            f"</body></html>"
        )

    @staticmethod
    def _render_bs_html(report: BalanceSheetReport, styles: str) -> str:
        sections = ""
        for label, items, total in [
            ("Assets", report.assets, report.total_assets),
            ("Liabilities", report.liabilities, report.total_liabilities),
            ("Equity", report.equity, report.total_equity),
        ]:
            if items:
                sections += f"<h2>{label}</h2><table><tr><th>Account</th><th>Name</th><th class='amount'>Balance</th></tr>"
                for r in items:
                    sections += f"<tr><td>{r.account_number}</td><td>{r.account_name}</td><td class='amount'>{r.balance:,.2f}</td></tr>"
                sections += f"<tr class='total-row'><td colspan='2'>Total {label}</td><td class='amount'>{total:,.2f}</td></tr></table>"

        return (
            f"<html><head>{styles}</head><body>"
            f"<h1>Balance Sheet</h1>"
            f"<p>As of: {report.as_of_date}</p>"
            f"{sections}"
            f"<div class='footer'>Generated by Georgia CPA Accounting System</div>"
            f"</body></html>"
        )

    @staticmethod
    def _render_cf_html(report: CashFlowReport, styles: str) -> str:
        sections = ""
        for section in [report.operating, report.investing, report.financing]:
            if section.items:
                sections += f"<h2>{section.label}</h2><table><tr><th>Account</th><th>Name</th><th class='amount'>Amount</th></tr>"
                for r in section.items:
                    sections += f"<tr><td>{r.account_number}</td><td>{r.account_name}</td><td class='amount'>{r.balance:,.2f}</td></tr>"
                sections += f"<tr class='total-row'><td colspan='2'>Subtotal</td><td class='amount'>{section.subtotal:,.2f}</td></tr></table>"

        return (
            f"<html><head>{styles}</head><body>"
            f"<h1>Cash Flow Statement</h1>"
            f"<p>Period: {report.period_start} to {report.period_end}</p>"
            f"{sections}"
            f"<h2>Net Change in Cash: {report.net_change_in_cash:,.2f}</h2>"
            f"<div class='footer'>Generated by Georgia CPA Accounting System</div>"
            f"</body></html>"
        )

    @staticmethod
    async def get_firm_dashboard(
        db: AsyncSession,
        period_start: date | None = None,
        period_end: date | None = None,
    ) -> FirmDashboard:
        """
        Generate firm-level dashboard with key metrics for all active clients.

        If period_start/period_end not provided, uses all-time data.

        Compliance (rule #4): Each client's data is queried separately.
        """
        # Get all active clients
        client_stmt = (
            select(Client)
            .where(Client.is_active.is_(True), Client.deleted_at.is_(None))
            .order_by(Client.name)
        )
        client_result = await db.execute(client_stmt)
        clients = list(client_result.scalars().all())

        dashboard = FirmDashboard(
            total_clients=len(clients),
            active_clients=len(clients),
        )

        for client in clients:
            # Revenue & Expense totals from GL
            gl_stmt = text(
                "SELECT "
                "    coa.account_type, "
                "    COALESCE(SUM(jel.debit), 0) AS total_debits, "
                "    COALESCE(SUM(jel.credit), 0) AS total_credits "
                "FROM chart_of_accounts coa "
                "LEFT JOIN ( "
                "    journal_entry_lines jel "
                "    INNER JOIN journal_entries je "
                "        ON je.id = jel.journal_entry_id "
                "        AND je.status = 'POSTED' "
                "        AND je.deleted_at IS NULL "
                "        AND je.client_id = :client_id "
                + ("        AND je.entry_date >= :period_start " if period_start else "")
                + ("        AND je.entry_date <= :period_end " if period_end else "")
                + ") ON jel.account_id = coa.id "
                "    AND jel.deleted_at IS NULL "
                "WHERE coa.client_id = :client_id "
                "    AND coa.deleted_at IS NULL "
                "    AND coa.account_type IN ('REVENUE', 'EXPENSE') "
                "GROUP BY coa.account_type"
            )
            params: dict = {"client_id": str(client.id)}
            if period_start:
                params["period_start"] = period_start
            if period_end:
                params["period_end"] = period_end

            gl_result = await db.execute(gl_stmt, params)
            gl_rows = gl_result.all()

            revenue = Decimal("0.00")
            expenses = Decimal("0.00")
            for row in gl_rows:
                if row.account_type == "REVENUE":
                    revenue = row.total_credits - row.total_debits
                elif row.account_type == "EXPENSE":
                    expenses = row.total_debits - row.total_credits

            # Outstanding AR
            ar_stmt = text(
                "SELECT COALESCE(SUM(total_amount), 0) AS total "
                "FROM invoices "
                "WHERE client_id = :client_id "
                "    AND deleted_at IS NULL "
                "    AND status IN ('SENT', 'OVERDUE')"
            )
            ar_result = await db.execute(ar_stmt, {"client_id": str(client.id)})
            ar_total = ar_result.scalar_one()

            # Outstanding AP
            ap_stmt = text(
                "SELECT COALESCE(SUM(total_amount), 0) AS total "
                "FROM bills "
                "WHERE client_id = :client_id "
                "    AND deleted_at IS NULL "
                "    AND status IN ('APPROVED', 'PENDING_APPROVAL')"
            )
            ap_result = await db.execute(ap_stmt, {"client_id": str(client.id)})
            ap_total = ap_result.scalar_one()

            metric = ClientMetric(
                client_id=client.id,
                client_name=client.name,
                entity_type=client.entity_type.value if hasattr(client.entity_type, 'value') else str(client.entity_type),
                total_revenue=revenue,
                total_expenses=expenses,
                net_income=revenue - expenses,
                total_ar_outstanding=ar_total,
                total_ap_outstanding=ap_total,
            )
            dashboard.client_metrics.append(metric)

        dashboard.firm_total_revenue = sum(m.total_revenue for m in dashboard.client_metrics)
        dashboard.firm_total_expenses = sum(m.total_expenses for m in dashboard.client_metrics)
        dashboard.firm_net_income = sum(m.net_income for m in dashboard.client_metrics)
        dashboard.firm_total_ar = sum(m.total_ar_outstanding for m in dashboard.client_metrics)
        dashboard.firm_total_ap = sum(m.total_ap_outstanding for m in dashboard.client_metrics)

        return dashboard
