"""
Tests for financial reporting (modules R1-R5).

Uses real PostgreSQL session (rolled back after each test).
"""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.reporting import ReportingService
from tests.conftest import CPA_OWNER_USER_ID


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_client(db: AsyncSession, name: str = "Test Client") -> uuid.UUID:
    cid = uuid.uuid4()
    await db.execute(
        text(
            "INSERT INTO clients (id, name, entity_type, is_active) "
            "VALUES (:id, :name, 'SOLE_PROP', true)"
        ),
        {"id": str(cid), "name": name},
    )
    await db.flush()
    return cid


async def _create_account(
    db: AsyncSession,
    client_id: uuid.UUID,
    number: str,
    name: str,
    acct_type: str,
    sub_type: str | None = None,
) -> uuid.UUID:
    aid = uuid.uuid4()
    await db.execute(
        text(
            "INSERT INTO chart_of_accounts "
            "(id, client_id, account_number, account_name, account_type, sub_type, is_active) "
            "VALUES (:id, :client_id, :number, :name, :type, :sub_type, true)"
        ),
        {
            "id": str(aid),
            "client_id": str(client_id),
            "number": number,
            "name": name,
            "type": acct_type,
            "sub_type": sub_type,
        },
    )
    await db.flush()
    return aid


async def _create_user(db: AsyncSession) -> uuid.UUID:
    uid = uuid.uuid4()
    await db.execute(
        text(
            "INSERT INTO users (id, email, password_hash, full_name, role, is_active) "
            "VALUES (:id, :email, 'hash', 'Test User', 'CPA_OWNER', true)"
        ),
        {"id": str(uid), "email": f"test-{uid}@example.com"},
    )
    await db.flush()
    return uid


async def _post_journal_entry(
    db: AsyncSession,
    client_id: uuid.UUID,
    user_id: uuid.UUID,
    entry_date: date,
    lines: list[tuple[uuid.UUID, Decimal, Decimal]],
    description: str = "Test entry",
) -> uuid.UUID:
    """Create a POSTED journal entry with the given lines.

    Each line is (account_id, debit, credit).
    Creates as DRAFT first, adds lines, then transitions to POSTED
    (required by DB trigger).
    """
    je_id = uuid.uuid4()
    await db.execute(
        text(
            "INSERT INTO journal_entries "
            "(id, client_id, entry_date, description, status, created_by) "
            "VALUES (:id, :client_id, :entry_date, :desc, 'DRAFT', :user_id)"
        ),
        {
            "id": str(je_id),
            "client_id": str(client_id),
            "entry_date": entry_date,
            "desc": description,
            "user_id": str(user_id),
        },
    )
    await db.flush()

    for account_id, debit, credit in lines:
        line_id = uuid.uuid4()
        await db.execute(
            text(
                "INSERT INTO journal_entry_lines "
                "(id, journal_entry_id, account_id, debit, credit) "
                "VALUES (:id, :je_id, :account_id, :debit, :credit)"
            ),
            {
                "id": str(line_id),
                "je_id": str(je_id),
                "account_id": str(account_id),
                "debit": debit,
                "credit": credit,
            },
        )
    await db.flush()

    # Transition to POSTED
    now = datetime.now(timezone.utc)
    await db.execute(
        text(
            "UPDATE journal_entries SET status = 'POSTED', "
            "approved_by = :user_id, posted_at = :now "
            "WHERE id = :id"
        ),
        {"id": str(je_id), "user_id": str(user_id), "now": now},
    )
    await db.flush()
    return je_id


# ---------------------------------------------------------------------------
# R1 — Profit & Loss Tests
# ---------------------------------------------------------------------------


class TestProfitLoss:

    @pytest.mark.asyncio
    async def test_empty_pnl(self, db_session: AsyncSession):
        client_id = await _create_client(db_session)
        report = await ReportingService.get_profit_loss(
            db_session, client_id, date(2024, 1, 1), date(2024, 12, 31),
        )
        assert report.client_id == client_id
        assert report.total_revenue == Decimal("0.00")
        assert report.total_expenses == Decimal("0.00")
        assert report.net_income == Decimal("0.00")

    @pytest.mark.asyncio
    async def test_revenue_and_expense(self, db_session: AsyncSession):
        client_id = await _create_client(db_session)
        user_id = await _create_user(db_session)
        cash = await _create_account(db_session, client_id, "1000", "Cash", "ASSET")
        revenue = await _create_account(db_session, client_id, "4000", "Service Revenue", "REVENUE")
        rent = await _create_account(db_session, client_id, "5000", "Rent Expense", "EXPENSE")

        # Revenue: debit cash $1000, credit revenue $1000
        await _post_journal_entry(
            db_session, client_id, user_id, date(2024, 6, 1),
            [(cash, Decimal("1000.00"), Decimal("0.00")),
             (revenue, Decimal("0.00"), Decimal("1000.00"))],
        )
        # Expense: debit rent $400, credit cash $400
        await _post_journal_entry(
            db_session, client_id, user_id, date(2024, 6, 15),
            [(rent, Decimal("400.00"), Decimal("0.00")),
             (cash, Decimal("0.00"), Decimal("400.00"))],
        )

        report = await ReportingService.get_profit_loss(
            db_session, client_id, date(2024, 1, 1), date(2024, 12, 31),
        )
        assert report.total_revenue == Decimal("1000.00")
        assert report.total_expenses == Decimal("400.00")
        assert report.net_income == Decimal("600.00")
        assert len(report.revenue_items) == 1
        assert len(report.expense_items) == 1

    @pytest.mark.asyncio
    async def test_date_range_filter(self, db_session: AsyncSession):
        """Entries outside the date range should not appear."""
        client_id = await _create_client(db_session)
        user_id = await _create_user(db_session)
        cash = await _create_account(db_session, client_id, "1000", "Cash", "ASSET")
        revenue = await _create_account(db_session, client_id, "4000", "Revenue", "REVENUE")

        # Entry in January
        await _post_journal_entry(
            db_session, client_id, user_id, date(2024, 1, 15),
            [(cash, Decimal("500.00"), Decimal("0.00")),
             (revenue, Decimal("0.00"), Decimal("500.00"))],
        )
        # Entry in July
        await _post_journal_entry(
            db_session, client_id, user_id, date(2024, 7, 15),
            [(cash, Decimal("300.00"), Decimal("0.00")),
             (revenue, Decimal("0.00"), Decimal("300.00"))],
        )

        # Q1 only
        report = await ReportingService.get_profit_loss(
            db_session, client_id, date(2024, 1, 1), date(2024, 3, 31),
        )
        assert report.total_revenue == Decimal("500.00")

    @pytest.mark.asyncio
    async def test_only_posted_entries(self, db_session: AsyncSession):
        """Draft entries should not appear in P&L."""
        client_id = await _create_client(db_session)
        user_id = await _create_user(db_session)
        cash = await _create_account(db_session, client_id, "1000", "Cash", "ASSET")
        revenue = await _create_account(db_session, client_id, "4000", "Revenue", "REVENUE")

        # Create a DRAFT entry (not posted)
        je_id = uuid.uuid4()
        await db_session.execute(
            text(
                "INSERT INTO journal_entries "
                "(id, client_id, entry_date, description, status, created_by) "
                "VALUES (:id, :client_id, :entry_date, 'draft', 'DRAFT', :user_id)"
            ),
            {
                "id": str(je_id),
                "client_id": str(client_id),
                "entry_date": date(2024, 6, 1),
                "user_id": str(user_id),
            },
        )
        for acct, d, c in [(cash, Decimal("100"), Decimal("0")),
                           (revenue, Decimal("0"), Decimal("100"))]:
            await db_session.execute(
                text(
                    "INSERT INTO journal_entry_lines "
                    "(id, journal_entry_id, account_id, debit, credit) "
                    "VALUES (:id, :je_id, :acct, :d, :c)"
                ),
                {"id": str(uuid.uuid4()), "je_id": str(je_id), "acct": str(acct), "d": d, "c": c},
            )
        await db_session.flush()

        report = await ReportingService.get_profit_loss(
            db_session, client_id, date(2024, 1, 1), date(2024, 12, 31),
        )
        assert report.total_revenue == Decimal("0.00")

    @pytest.mark.asyncio
    async def test_client_isolation(self, db_session: AsyncSession):
        """Client A's revenue must not appear in Client B's report."""
        client_a = await _create_client(db_session, "Client A")
        client_b = await _create_client(db_session, "Client B")
        user_id = await _create_user(db_session)

        cash_a = await _create_account(db_session, client_a, "1000", "Cash", "ASSET")
        rev_a = await _create_account(db_session, client_a, "4000", "Revenue", "REVENUE")

        cash_b = await _create_account(db_session, client_b, "1000", "Cash", "ASSET")
        rev_b = await _create_account(db_session, client_b, "4000", "Revenue", "REVENUE")

        await _post_journal_entry(
            db_session, client_a, user_id, date(2024, 6, 1),
            [(cash_a, Decimal("1000.00"), Decimal("0.00")),
             (rev_a, Decimal("0.00"), Decimal("1000.00"))],
        )
        await _post_journal_entry(
            db_session, client_b, user_id, date(2024, 6, 1),
            [(cash_b, Decimal("200.00"), Decimal("0.00")),
             (rev_b, Decimal("0.00"), Decimal("200.00"))],
        )

        report_a = await ReportingService.get_profit_loss(
            db_session, client_a, date(2024, 1, 1), date(2024, 12, 31),
        )
        report_b = await ReportingService.get_profit_loss(
            db_session, client_b, date(2024, 1, 1), date(2024, 12, 31),
        )
        assert report_a.total_revenue == Decimal("1000.00")
        assert report_b.total_revenue == Decimal("200.00")


# ---------------------------------------------------------------------------
# R2 — Balance Sheet Tests
# ---------------------------------------------------------------------------


class TestBalanceSheet:

    @pytest.mark.asyncio
    async def test_empty_balance_sheet(self, db_session: AsyncSession):
        client_id = await _create_client(db_session)
        report = await ReportingService.get_balance_sheet(
            db_session, client_id, date(2024, 12, 31),
        )
        assert report.total_assets == Decimal("0.00")
        assert report.total_liabilities == Decimal("0.00")
        assert report.total_equity == Decimal("0.00")

    @pytest.mark.asyncio
    async def test_assets_and_liabilities(self, db_session: AsyncSession):
        client_id = await _create_client(db_session)
        user_id = await _create_user(db_session)
        cash = await _create_account(db_session, client_id, "1000", "Cash", "ASSET")
        loan = await _create_account(db_session, client_id, "2000", "Loan Payable", "LIABILITY")

        # Borrow $5000: debit cash, credit loan
        await _post_journal_entry(
            db_session, client_id, user_id, date(2024, 3, 1),
            [(cash, Decimal("5000.00"), Decimal("0.00")),
             (loan, Decimal("0.00"), Decimal("5000.00"))],
        )

        report = await ReportingService.get_balance_sheet(
            db_session, client_id, date(2024, 12, 31),
        )
        assert report.total_assets == Decimal("5000.00")
        assert report.total_liabilities == Decimal("5000.00")
        assert len(report.assets) == 1
        assert len(report.liabilities) == 1

    @pytest.mark.asyncio
    async def test_as_of_date_cutoff(self, db_session: AsyncSession):
        """Entries after as_of_date should be excluded."""
        client_id = await _create_client(db_session)
        user_id = await _create_user(db_session)
        cash = await _create_account(db_session, client_id, "1000", "Cash", "ASSET")
        equity = await _create_account(db_session, client_id, "3000", "Owner Equity", "EQUITY")

        # Jan entry
        await _post_journal_entry(
            db_session, client_id, user_id, date(2024, 1, 1),
            [(cash, Decimal("1000.00"), Decimal("0.00")),
             (equity, Decimal("0.00"), Decimal("1000.00"))],
        )
        # July entry
        await _post_journal_entry(
            db_session, client_id, user_id, date(2024, 7, 1),
            [(cash, Decimal("2000.00"), Decimal("0.00")),
             (equity, Decimal("0.00"), Decimal("2000.00"))],
        )

        report = await ReportingService.get_balance_sheet(
            db_session, client_id, date(2024, 3, 31),
        )
        assert report.total_assets == Decimal("1000.00")
        assert report.total_equity == Decimal("1000.00")


# ---------------------------------------------------------------------------
# R3 — Cash Flow Tests
# ---------------------------------------------------------------------------


class TestCashFlow:

    @pytest.mark.asyncio
    async def test_empty_cash_flow(self, db_session: AsyncSession):
        client_id = await _create_client(db_session)
        report = await ReportingService.get_cash_flow(
            db_session, client_id, date(2024, 1, 1), date(2024, 12, 31),
        )
        assert report.net_change_in_cash == Decimal("0.00")
        assert report.operating.subtotal == Decimal("0.00")

    @pytest.mark.asyncio
    async def test_operating_activities(self, db_session: AsyncSession):
        client_id = await _create_client(db_session)
        user_id = await _create_user(db_session)
        cash = await _create_account(db_session, client_id, "1000", "Cash", "ASSET", "Cash and Cash Equivalents")
        revenue = await _create_account(db_session, client_id, "4000", "Service Revenue", "REVENUE")

        await _post_journal_entry(
            db_session, client_id, user_id, date(2024, 6, 1),
            [(cash, Decimal("800.00"), Decimal("0.00")),
             (revenue, Decimal("0.00"), Decimal("800.00"))],
        )

        report = await ReportingService.get_cash_flow(
            db_session, client_id, date(2024, 1, 1), date(2024, 12, 31),
        )
        # Both cash and revenue are operating (no investing/financing sub_types)
        assert len(report.operating.items) >= 1
        assert report.net_change_in_cash != Decimal("0.00") or report.operating.subtotal != Decimal("0.00")

    @pytest.mark.asyncio
    async def test_investing_activities(self, db_session: AsyncSession):
        """Fixed asset purchase should appear in investing section."""
        client_id = await _create_client(db_session)
        user_id = await _create_user(db_session)
        cash = await _create_account(db_session, client_id, "1000", "Cash", "ASSET", "Cash and Cash Equivalents")
        equipment = await _create_account(db_session, client_id, "1500", "Equipment", "ASSET", "Fixed Assets")

        # Buy equipment: debit equipment, credit cash
        await _post_journal_entry(
            db_session, client_id, user_id, date(2024, 6, 1),
            [(equipment, Decimal("3000.00"), Decimal("0.00")),
             (cash, Decimal("0.00"), Decimal("3000.00"))],
        )

        report = await ReportingService.get_cash_flow(
            db_session, client_id, date(2024, 1, 1), date(2024, 12, 31),
        )
        # Equipment should be in investing
        investing_accounts = [i.account_name for i in report.investing.items]
        assert "Equipment" in investing_accounts


# ---------------------------------------------------------------------------
# R4 — PDF Export Tests
# ---------------------------------------------------------------------------


class TestHTMLRendering:
    """Test HTML generation (no WeasyPrint dependency)."""

    @pytest.mark.asyncio
    async def test_pnl_html_rendering(self, db_session: AsyncSession):
        client_id = await _create_client(db_session)
        report = await ReportingService.get_profit_loss(
            db_session, client_id, date(2024, 1, 1), date(2024, 12, 31),
        )
        html = ReportingService._render_report_html(report)
        assert "Profit" in html
        assert "<html>" in html

    @pytest.mark.asyncio
    async def test_bs_html_rendering(self, db_session: AsyncSession):
        client_id = await _create_client(db_session)
        report = await ReportingService.get_balance_sheet(
            db_session, client_id, date(2024, 12, 31),
        )
        html = ReportingService._render_report_html(report)
        assert "Balance Sheet" in html

    @pytest.mark.asyncio
    async def test_cf_html_rendering(self, db_session: AsyncSession):
        client_id = await _create_client(db_session)
        report = await ReportingService.get_cash_flow(
            db_session, client_id, date(2024, 1, 1), date(2024, 12, 31),
        )
        html = ReportingService._render_report_html(report)
        assert "Cash Flow" in html


class TestPDFExport:

    @pytest.mark.asyncio
    async def test_pnl_pdf_generation(self, db_session: AsyncSession):
        client_id = await _create_client(db_session)
        report = await ReportingService.get_profit_loss(
            db_session, client_id, date(2024, 1, 1), date(2024, 12, 31),
        )
        pdf_bytes = await ReportingService.generate_report_pdf(report)
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
        # PDF magic bytes
        assert pdf_bytes[:5] == b"%PDF-"

    @pytest.mark.asyncio
    async def test_balance_sheet_pdf(self, db_session: AsyncSession):
        client_id = await _create_client(db_session)
        report = await ReportingService.get_balance_sheet(
            db_session, client_id, date(2024, 12, 31),
        )
        pdf_bytes = await ReportingService.generate_report_pdf(report)
        assert pdf_bytes[:5] == b"%PDF-"

    @pytest.mark.asyncio
    async def test_cash_flow_pdf(self, db_session: AsyncSession):
        client_id = await _create_client(db_session)
        report = await ReportingService.get_cash_flow(
            db_session, client_id, date(2024, 1, 1), date(2024, 12, 31),
        )
        pdf_bytes = await ReportingService.generate_report_pdf(report)
        assert pdf_bytes[:5] == b"%PDF-"


# ---------------------------------------------------------------------------
# R5 — Firm Dashboard Tests
# ---------------------------------------------------------------------------


class TestFirmDashboard:

    @pytest.mark.asyncio
    async def test_empty_dashboard(self, db_session: AsyncSession):
        dashboard = await ReportingService.get_firm_dashboard(db_session)
        # May have existing clients from seed data; just verify structure
        assert dashboard.total_clients >= 0
        assert isinstance(dashboard.firm_total_revenue, Decimal)

    @pytest.mark.asyncio
    async def test_dashboard_with_clients(self, db_session: AsyncSession):
        client_id = await _create_client(db_session, "Dashboard Client")
        user_id = await _create_user(db_session)
        cash = await _create_account(db_session, client_id, "1000", "Cash", "ASSET")
        revenue = await _create_account(db_session, client_id, "4000", "Revenue", "REVENUE")

        await _post_journal_entry(
            db_session, client_id, user_id, date(2024, 6, 1),
            [(cash, Decimal("2000.00"), Decimal("0.00")),
             (revenue, Decimal("0.00"), Decimal("2000.00"))],
        )

        dashboard = await ReportingService.get_firm_dashboard(db_session)
        assert dashboard.total_clients >= 1
        # Find our test client
        client_metric = next(
            (m for m in dashboard.client_metrics if m.client_id == client_id), None
        )
        assert client_metric is not None
        assert client_metric.total_revenue == Decimal("2000.00")
        assert client_metric.net_income == Decimal("2000.00")

    @pytest.mark.asyncio
    async def test_dashboard_period_filter(self, db_session: AsyncSession):
        client_id = await _create_client(db_session, "Period Client")
        user_id = await _create_user(db_session)
        cash = await _create_account(db_session, client_id, "1000", "Cash", "ASSET")
        revenue = await _create_account(db_session, client_id, "4000", "Revenue", "REVENUE")

        # Jan entry
        await _post_journal_entry(
            db_session, client_id, user_id, date(2024, 1, 15),
            [(cash, Decimal("500.00"), Decimal("0.00")),
             (revenue, Decimal("0.00"), Decimal("500.00"))],
        )
        # July entry
        await _post_journal_entry(
            db_session, client_id, user_id, date(2024, 7, 15),
            [(cash, Decimal("300.00"), Decimal("0.00")),
             (revenue, Decimal("0.00"), Decimal("300.00"))],
        )

        # Q1 filter
        dashboard = await ReportingService.get_firm_dashboard(
            db_session, period_start=date(2024, 1, 1), period_end=date(2024, 3, 31),
        )
        client_metric = next(
            (m for m in dashboard.client_metrics if m.client_id == client_id), None
        )
        assert client_metric is not None
        assert client_metric.total_revenue == Decimal("500.00")
