"""
Tests for tax form data exports (modules X1-X9).

Uses real PostgreSQL session (rolled back after each test).
"""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.tax_exports import (
    Form1065Service,
    Form1120SService,
    Form1120Service,
    Form500Service,
    Form600Service,
    FormG7Service,
    FormST3Service,
    ScheduleCService,
    TaxChecklistService,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_client(
    db: AsyncSession,
    name: str = "Test Client",
    entity_type: str = "SOLE_PROP",
) -> uuid.UUID:
    cid = uuid.uuid4()
    await db.execute(
        text(
            "INSERT INTO clients (id, name, entity_type, is_active) "
            "VALUES (:id, :name, :entity_type, true)"
        ),
        {"id": str(cid), "name": name, "entity_type": entity_type},
    )
    await db.flush()
    return cid


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


async def _create_account(
    db: AsyncSession,
    client_id: uuid.UUID,
    number: str,
    name: str,
    acct_type: str,
) -> uuid.UUID:
    aid = uuid.uuid4()
    await db.execute(
        text(
            "INSERT INTO chart_of_accounts "
            "(id, client_id, account_number, account_name, account_type, is_active) "
            "VALUES (:id, :client_id, :number, :name, :type, true)"
        ),
        {
            "id": str(aid),
            "client_id": str(client_id),
            "number": number,
            "name": name,
            "type": acct_type,
        },
    )
    await db.flush()
    return aid


async def _post_journal_entry(
    db: AsyncSession,
    client_id: uuid.UUID,
    user_id: uuid.UUID,
    entry_date: date,
    lines: list[tuple[uuid.UUID, Decimal, Decimal]],
) -> uuid.UUID:
    je_id = uuid.uuid4()
    await db.execute(
        text(
            "INSERT INTO journal_entries "
            "(id, client_id, entry_date, description, status, created_by) "
            "VALUES (:id, :client_id, :entry_date, 'test', 'DRAFT', :user_id)"
        ),
        {
            "id": str(je_id),
            "client_id": str(client_id),
            "entry_date": entry_date,
            "user_id": str(user_id),
        },
    )
    await db.flush()

    for account_id, debit, credit in lines:
        await db.execute(
            text(
                "INSERT INTO journal_entry_lines "
                "(id, journal_entry_id, account_id, debit, credit) "
                "VALUES (:id, :je_id, :acct, :d, :c)"
            ),
            {
                "id": str(uuid.uuid4()),
                "je_id": str(je_id),
                "acct": str(account_id),
                "d": debit,
                "c": credit,
            },
        )
    await db.flush()

    now = datetime.now(timezone.utc)
    await db.execute(
        text(
            "UPDATE journal_entries SET status = 'POSTED', "
            "approved_by = :user_id, posted_at = :now WHERE id = :id"
        ),
        {"id": str(je_id), "user_id": str(user_id), "now": now},
    )
    await db.flush()
    return je_id


async def _create_employee(
    db: AsyncSession, client_id: uuid.UUID, name: str = "John Doe"
) -> uuid.UUID:
    eid = uuid.uuid4()
    await db.execute(
        text(
            "INSERT INTO employees "
            "(id, client_id, first_name, last_name, hire_date, filing_status, "
            "allowances, pay_type, pay_rate, is_active) "
            "VALUES (:id, :cid, :first, :last, :hire_date, 'SINGLE', 0, 'SALARY', 50000, true)"
        ),
        {
            "id": str(eid),
            "cid": str(client_id),
            "first": name.split()[0],
            "last": name.split()[-1],
            "hire_date": date(2023, 1, 1),
        },
    )
    await db.flush()
    return eid


async def _create_finalized_payroll(
    db: AsyncSession,
    client_id: uuid.UUID,
    user_id: uuid.UUID,
    employee_id: uuid.UUID,
    pay_date: date,
    state_wh: Decimal = Decimal("150.00"),
) -> uuid.UUID:
    run_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    await db.execute(
        text(
            "INSERT INTO payroll_runs "
            "(id, client_id, pay_period_start, pay_period_end, pay_date, "
            "status, finalized_by, finalized_at) "
            "VALUES (:id, :cid, :start, :end, :pay_date, "
            "'FINALIZED', :uid, :now)"
        ),
        {
            "id": str(run_id),
            "cid": str(client_id),
            "start": date(pay_date.year, pay_date.month, 1),
            "end": pay_date,
            "pay_date": pay_date,
            "uid": str(user_id),
            "now": now,
        },
    )
    await db.flush()

    item_id = uuid.uuid4()
    await db.execute(
        text(
            "INSERT INTO payroll_items "
            "(id, payroll_run_id, employee_id, gross_pay, federal_withholding, "
            "state_withholding, social_security, medicare, ga_suta, futa, net_pay) "
            "VALUES (:id, :rid, :eid, 2000, 300, :state_wh, 124, 29, 54, 12, 1481)"
        ),
        {
            "id": str(item_id),
            "rid": str(run_id),
            "eid": str(employee_id),
            "state_wh": state_wh,
        },
    )
    await db.flush()
    return run_id


# ---------------------------------------------------------------------------
# X1 — G-7 Tests
# ---------------------------------------------------------------------------


class TestFormG7:

    @pytest.mark.asyncio
    async def test_empty_g7(self, db_session: AsyncSession):
        cid = await _create_client(db_session)
        result = await FormG7Service.generate(db_session, cid, 2024, 1)
        assert result.quarter == 1
        assert result.total_withholding == Decimal("0.00")
        assert len(result.monthly_details) == 3

    @pytest.mark.asyncio
    async def test_g7_with_payroll(self, db_session: AsyncSession):
        cid = await _create_client(db_session)
        uid = await _create_user(db_session)
        eid = await _create_employee(db_session, cid)

        # Payroll in Jan, Feb, March
        await _create_finalized_payroll(db_session, cid, uid, eid, date(2024, 1, 31), Decimal("100.00"))
        await _create_finalized_payroll(db_session, cid, uid, eid, date(2024, 2, 28), Decimal("120.00"))
        await _create_finalized_payroll(db_session, cid, uid, eid, date(2024, 3, 31), Decimal("110.00"))

        result = await FormG7Service.generate(db_session, cid, 2024, 1)
        assert result.total_withholding == Decimal("330.00")
        assert result.monthly_details[0].georgia_withholding == Decimal("100.00")

    @pytest.mark.asyncio
    async def test_g7_due_date(self, db_session: AsyncSession):
        cid = await _create_client(db_session)
        # Q1: due April 30
        result = await FormG7Service.generate(db_session, cid, 2024, 1)
        assert result.due_date == date(2024, 4, 30)
        # Q4: due January 31 of next year
        result = await FormG7Service.generate(db_session, cid, 2024, 4)
        assert result.due_date == date(2025, 1, 31)


# ---------------------------------------------------------------------------
# X2 — Form 500 Tests
# ---------------------------------------------------------------------------


class TestForm500:

    @pytest.mark.asyncio
    async def test_empty_form_500(self, db_session: AsyncSession):
        cid = await _create_client(db_session)
        result = await Form500Service.generate(db_session, cid, 2024)
        assert result.net_income == Decimal("0.00")

    @pytest.mark.asyncio
    async def test_form_500_with_income(self, db_session: AsyncSession):
        cid = await _create_client(db_session)
        uid = await _create_user(db_session)
        cash = await _create_account(db_session, cid, "1000", "Cash", "ASSET")
        rev = await _create_account(db_session, cid, "4000", "Revenue", "REVENUE")
        exp = await _create_account(db_session, cid, "5000", "Rent", "EXPENSE")

        await _post_journal_entry(db_session, cid, uid, date(2024, 6, 1),
            [(cash, Decimal("5000"), Decimal("0")), (rev, Decimal("0"), Decimal("5000"))])
        await _post_journal_entry(db_session, cid, uid, date(2024, 6, 15),
            [(exp, Decimal("2000"), Decimal("0")), (cash, Decimal("0"), Decimal("2000"))])

        result = await Form500Service.generate(db_session, cid, 2024)
        assert result.gross_revenue == Decimal("5000.00")
        assert result.total_expenses == Decimal("2000.00")
        assert result.net_income == Decimal("3000.00")
        assert "Rent" in result.expense_breakdown


# ---------------------------------------------------------------------------
# X3 — Form 600 Tests
# ---------------------------------------------------------------------------


class TestForm600:

    @pytest.mark.asyncio
    async def test_form_600_c_corp(self, db_session: AsyncSession):
        cid = await _create_client(db_session, "Corp Inc", "C_CORP")
        uid = await _create_user(db_session)
        cash = await _create_account(db_session, cid, "1000", "Cash", "ASSET")
        rev = await _create_account(db_session, cid, "4000", "Sales", "REVENUE")

        await _post_journal_entry(db_session, cid, uid, date(2024, 6, 1),
            [(cash, Decimal("10000"), Decimal("0")), (rev, Decimal("0"), Decimal("10000"))])

        result = await Form600Service.generate(db_session, cid, 2024)
        assert result.entity_type == "C_CORP"
        assert result.taxable_income == Decimal("10000.00")
        assert result.total_assets == Decimal("10000.00")


# ---------------------------------------------------------------------------
# X4 — ST-3 Tests
# ---------------------------------------------------------------------------


class TestFormST3:

    @pytest.mark.asyncio
    async def test_empty_st3(self, db_session: AsyncSession):
        cid = await _create_client(db_session)
        result = await FormST3Service.generate(
            db_session, cid, 2024, date(2024, 1, 1), date(2024, 3, 31),
        )
        assert result.total_gross_sales == Decimal("0.00")

    @pytest.mark.asyncio
    async def test_st3_with_sales(self, db_session: AsyncSession):
        cid = await _create_client(db_session)
        uid = await _create_user(db_session)
        cash = await _create_account(db_session, cid, "1000", "Cash", "ASSET")
        rev = await _create_account(db_session, cid, "4000", "Sales", "REVENUE")

        await _post_journal_entry(db_session, cid, uid, date(2024, 2, 1),
            [(cash, Decimal("7500"), Decimal("0")), (rev, Decimal("0"), Decimal("7500"))])

        result = await FormST3Service.generate(
            db_session, cid, 2024, date(2024, 1, 1), date(2024, 3, 31),
        )
        assert result.total_gross_sales == Decimal("7500.00")


# ---------------------------------------------------------------------------
# X5 — Schedule C Tests
# ---------------------------------------------------------------------------


class TestScheduleC:

    @pytest.mark.asyncio
    async def test_schedule_c_with_data(self, db_session: AsyncSession):
        cid = await _create_client(db_session)
        uid = await _create_user(db_session)
        cash = await _create_account(db_session, cid, "1000", "Cash", "ASSET")
        rev = await _create_account(db_session, cid, "4000", "Revenue", "REVENUE")
        supplies = await _create_account(db_session, cid, "5100", "Supplies", "EXPENSE")

        await _post_journal_entry(db_session, cid, uid, date(2024, 3, 1),
            [(cash, Decimal("8000"), Decimal("0")), (rev, Decimal("0"), Decimal("8000"))])
        await _post_journal_entry(db_session, cid, uid, date(2024, 4, 1),
            [(supplies, Decimal("1500"), Decimal("0")), (cash, Decimal("0"), Decimal("1500"))])

        result = await ScheduleCService.generate(db_session, cid, 2024)
        assert result.gross_receipts == Decimal("8000.00")
        assert result.total_expenses == Decimal("1500.00")
        assert result.net_profit == Decimal("6500.00")
        assert "Supplies" in result.expense_categories


# ---------------------------------------------------------------------------
# X6 — Form 1120-S Tests
# ---------------------------------------------------------------------------


class TestForm1120S:

    @pytest.mark.asyncio
    async def test_form_1120s(self, db_session: AsyncSession):
        cid = await _create_client(db_session, "S-Corp LLC", "S_CORP")
        uid = await _create_user(db_session)
        cash = await _create_account(db_session, cid, "1000", "Cash", "ASSET")
        equity = await _create_account(db_session, cid, "3000", "Equity", "EQUITY")
        rev = await _create_account(db_session, cid, "4000", "Revenue", "REVENUE")

        await _post_journal_entry(db_session, cid, uid, date(2024, 1, 1),
            [(cash, Decimal("10000"), Decimal("0")), (equity, Decimal("0"), Decimal("10000"))])
        await _post_journal_entry(db_session, cid, uid, date(2024, 6, 1),
            [(cash, Decimal("5000"), Decimal("0")), (rev, Decimal("0"), Decimal("5000"))])

        result = await Form1120SService.generate(db_session, cid, 2024)
        assert result.entity_type == "S_CORP"
        assert result.ordinary_business_income == Decimal("5000.00")
        assert result.total_assets == Decimal("15000.00")
        assert result.shareholders_equity == Decimal("10000.00")


# ---------------------------------------------------------------------------
# X7 — Form 1120 Tests
# ---------------------------------------------------------------------------


class TestForm1120:

    @pytest.mark.asyncio
    async def test_form_1120(self, db_session: AsyncSession):
        cid = await _create_client(db_session, "C-Corp Inc", "C_CORP")
        result = await Form1120Service.generate(db_session, cid, 2024)
        assert result.entity_type == "C_CORP"
        assert result.taxable_income == Decimal("0.00")


# ---------------------------------------------------------------------------
# X8 — Form 1065 Tests
# ---------------------------------------------------------------------------


class TestForm1065:

    @pytest.mark.asyncio
    async def test_form_1065(self, db_session: AsyncSession):
        cid = await _create_client(db_session, "Partner LLC", "PARTNERSHIP_LLC")
        uid = await _create_user(db_session)
        cash = await _create_account(db_session, cid, "1000", "Cash", "ASSET")
        rev = await _create_account(db_session, cid, "4000", "Revenue", "REVENUE")

        await _post_journal_entry(db_session, cid, uid, date(2024, 6, 1),
            [(cash, Decimal("3000"), Decimal("0")), (rev, Decimal("0"), Decimal("3000"))])

        result = await Form1065Service.generate(db_session, cid, 2024)
        assert result.entity_type == "PARTNERSHIP_LLC"
        assert result.ordinary_business_income == Decimal("3000.00")


# ---------------------------------------------------------------------------
# X9 — Tax Document Checklist Tests
# ---------------------------------------------------------------------------


class TestTaxChecklist:

    @pytest.mark.asyncio
    async def test_sole_prop_checklist(self, db_session: AsyncSession):
        cid = await _create_client(db_session, entity_type="SOLE_PROP")
        result = await TaxChecklistService.generate(db_session, cid, 2024)
        assert result.entity_type == "SOLE_PROP"
        assert result.total_required > 0
        assert any("Schedule C" in i.document for i in result.items)

    @pytest.mark.asyncio
    async def test_s_corp_checklist(self, db_session: AsyncSession):
        cid = await _create_client(db_session, entity_type="S_CORP")
        result = await TaxChecklistService.generate(db_session, cid, 2024)
        assert result.entity_type == "S_CORP"
        assert any("1120-S" in i.document for i in result.items)

    @pytest.mark.asyncio
    async def test_c_corp_checklist(self, db_session: AsyncSession):
        cid = await _create_client(db_session, entity_type="C_CORP")
        result = await TaxChecklistService.generate(db_session, cid, 2024)
        assert result.entity_type == "C_CORP"
        assert any("1120" in i.document for i in result.items)

    @pytest.mark.asyncio
    async def test_partnership_checklist(self, db_session: AsyncSession):
        cid = await _create_client(db_session, entity_type="PARTNERSHIP_LLC")
        result = await TaxChecklistService.generate(db_session, cid, 2024)
        assert result.entity_type == "PARTNERSHIP_LLC"
        assert any("1065" in i.document for i in result.items)

    @pytest.mark.asyncio
    async def test_checklist_all_needed(self, db_session: AsyncSession):
        cid = await _create_client(db_session)
        result = await TaxChecklistService.generate(db_session, cid, 2024)
        assert result.total_received == 0
        assert all(i.status == "NEEDED" for i in result.items)

    @pytest.mark.asyncio
    async def test_client_isolation(self, db_session: AsyncSession):
        """Client A's checklist should be based on Client A's entity type."""
        cid_sole = await _create_client(db_session, "Sole Prop", "SOLE_PROP")
        cid_corp = await _create_client(db_session, "Corp", "C_CORP")

        sole_result = await TaxChecklistService.generate(db_session, cid_sole, 2024)
        corp_result = await TaxChecklistService.generate(db_session, cid_corp, 2024)

        assert sole_result.entity_type == "SOLE_PROP"
        assert corp_result.entity_type == "C_CORP"
        assert sole_result.total_required != corp_result.total_required
