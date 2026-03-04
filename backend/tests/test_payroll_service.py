"""
Tests for Payroll Service and Approval Gate (module P6).

Tests payroll run creation, tax calculation integration, approval workflow,
and CPA_OWNER defense-in-depth checks.

Compliance tests:
- Rule #4: CLIENT ISOLATION
- Rule #5: APPROVAL WORKFLOW (DRAFT -> PENDING_APPROVAL -> FINALIZED)
- Rule #6: PAYROLL GATE (CPA_OWNER at function level)

Uses real PostgreSQL session (rolled back after each test).
"""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser
from app.schemas.payroll import PayrollItemCreate, PayrollRunCreate
from app.services.payroll.payroll_service import PayrollService
from tests.conftest import (
    ASSOCIATE_USER,
    ASSOCIATE_USER_ID,
    CPA_OWNER_USER,
    CPA_OWNER_USER_ID,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _create_test_client(db: AsyncSession, client_id: uuid.UUID | None = None) -> uuid.UUID:
    cid = client_id or uuid.uuid4()
    await db.execute(
        text(
            "INSERT INTO clients (id, name, entity_type, is_active) "
            "VALUES (:id, :name, 'SOLE_PROP', true)"
        ),
        {"id": str(cid), "name": f"Test Client {cid}"},
    )
    await db.flush()
    return cid


async def _create_test_employee(
    db: AsyncSession,
    client_id: uuid.UUID,
    first_name: str = "John",
    last_name: str = "Smith",
    pay_type: str = "HOURLY",
    pay_rate: Decimal = Decimal("25.00"),
    filing_status: str = "SINGLE",
    allowances: int = 1,
) -> uuid.UUID:
    eid = uuid.uuid4()
    await db.execute(
        text(
            "INSERT INTO employees (id, client_id, first_name, last_name, "
            "filing_status, allowances, pay_rate, pay_type, hire_date, is_active) "
            "VALUES (:id, :client_id, :first, :last, :filing, :allow, :rate, :ptype, :hdate, true)"
        ),
        {
            "id": str(eid),
            "client_id": str(client_id),
            "first": first_name,
            "last": last_name,
            "filing": filing_status,
            "allow": allowances,
            "rate": str(pay_rate),
            "ptype": pay_type,
            "hdate": date(2024, 1, 15),
        },
    )
    await db.flush()
    return eid


async def _create_test_user(db: AsyncSession, user_id: str) -> None:
    await db.execute(
        text(
            "INSERT INTO users (id, email, password_hash, full_name, role, is_active) "
            "VALUES (:id, :email, :pw, :name, 'CPA_OWNER', true)"
        ),
        {
            "id": user_id,
            "email": f"user_{user_id[:8]}@test.com",
            "pw": "$2b$12$test_hash",
            "name": "Test CPA",
        },
    )
    await db.flush()


# ---------------------------------------------------------------------------
# Creation tests
# ---------------------------------------------------------------------------


class TestPayrollRunCreation:

    @pytest.mark.asyncio
    async def test_create_hourly_payroll_run(self, db_session: AsyncSession):
        client_id = await _create_test_client(db_session)
        emp_id = await _create_test_employee(db_session, client_id)

        data = PayrollRunCreate(
            pay_period_start=date(2024, 6, 1),
            pay_period_end=date(2024, 6, 15),
            pay_date=date(2024, 6, 20),
            employee_items=[PayrollItemCreate(employee_id=emp_id, hours_worked=Decimal("80"))],
            pay_periods_per_year=26,
            tax_year=2024,
        )
        run = await PayrollService.create_payroll_run(db_session, client_id, data)

        assert run.status == "DRAFT"
        assert run.client_id == client_id
        assert len(run.items) == 1
        item = run.items[0]
        assert item.gross_pay == Decimal("2000.00")  # 80 * $25
        assert item.federal_withholding > Decimal("0")
        assert item.state_withholding > Decimal("0")
        assert item.social_security > Decimal("0")
        assert item.medicare > Decimal("0")
        assert item.net_pay > Decimal("0")
        assert item.net_pay < item.gross_pay

    @pytest.mark.asyncio
    async def test_create_salary_payroll_run(self, db_session: AsyncSession):
        client_id = await _create_test_client(db_session)
        emp_id = await _create_test_employee(
            db_session, client_id,
            first_name="Jane", last_name="Doe",
            pay_type="SALARY", pay_rate=Decimal("75000.00"),
        )

        data = PayrollRunCreate(
            pay_period_start=date(2024, 6, 1),
            pay_period_end=date(2024, 6, 15),
            pay_date=date(2024, 6, 20),
            employee_items=[PayrollItemCreate(employee_id=emp_id)],
            pay_periods_per_year=26,
            tax_year=2024,
        )
        run = await PayrollService.create_payroll_run(db_session, client_id, data)

        item = run.items[0]
        assert item.gross_pay == Decimal("2884.62")  # 75000 / 26

    @pytest.mark.asyncio
    async def test_create_multiple_employees(self, db_session: AsyncSession):
        client_id = await _create_test_client(db_session)
        emp1 = await _create_test_employee(db_session, client_id, first_name="Alice")
        emp2 = await _create_test_employee(db_session, client_id, first_name="Bob")

        data = PayrollRunCreate(
            pay_period_start=date(2024, 6, 1),
            pay_period_end=date(2024, 6, 15),
            pay_date=date(2024, 6, 20),
            employee_items=[
                PayrollItemCreate(employee_id=emp1, hours_worked=Decimal("80")),
                PayrollItemCreate(employee_id=emp2, hours_worked=Decimal("40")),
            ],
            pay_periods_per_year=26,
            tax_year=2024,
        )
        run = await PayrollService.create_payroll_run(db_session, client_id, data)

        assert len(run.items) == 2
        # Alice worked 80 hours, Bob 40
        items_by_emp = {str(i.employee_id): i for i in run.items}
        assert items_by_emp[str(emp1)].gross_pay == Decimal("2000.00")
        assert items_by_emp[str(emp2)].gross_pay == Decimal("1000.00")

    @pytest.mark.asyncio
    async def test_hourly_requires_hours(self, db_session: AsyncSession):
        client_id = await _create_test_client(db_session)
        emp_id = await _create_test_employee(db_session, client_id)

        data = PayrollRunCreate(
            pay_period_start=date(2024, 6, 1),
            pay_period_end=date(2024, 6, 15),
            pay_date=date(2024, 6, 20),
            employee_items=[PayrollItemCreate(employee_id=emp_id)],  # No hours
            pay_periods_per_year=26,
            tax_year=2024,
        )
        with pytest.raises(HTTPException) as exc_info:
            await PayrollService.create_payroll_run(db_session, client_id, data)
        assert exc_info.value.status_code == 400
        assert "Hours worked required" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_nonexistent_employee_raises_404(self, db_session: AsyncSession):
        client_id = await _create_test_client(db_session)
        fake_emp = uuid.uuid4()

        data = PayrollRunCreate(
            pay_period_start=date(2024, 6, 1),
            pay_period_end=date(2024, 6, 15),
            pay_date=date(2024, 6, 20),
            employee_items=[PayrollItemCreate(employee_id=fake_emp, hours_worked=Decimal("80"))],
            pay_periods_per_year=26,
            tax_year=2024,
        )
        with pytest.raises(HTTPException) as exc_info:
            await PayrollService.create_payroll_run(db_session, client_id, data)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_custom_suta_rate(self, db_session: AsyncSession):
        client_id = await _create_test_client(db_session)
        emp_id = await _create_test_employee(db_session, client_id)

        data = PayrollRunCreate(
            pay_period_start=date(2024, 6, 1),
            pay_period_end=date(2024, 6, 15),
            pay_date=date(2024, 6, 20),
            employee_items=[PayrollItemCreate(employee_id=emp_id, hours_worked=Decimal("80"))],
            pay_periods_per_year=26,
            tax_year=2024,
            suta_rate=Decimal("0.015"),
        )
        run = await PayrollService.create_payroll_run(db_session, client_id, data)
        item = run.items[0]
        # SUTA at 1.5% on $2000 = $30.00
        assert item.ga_suta == Decimal("30.00")


# ---------------------------------------------------------------------------
# Approval workflow tests
# ---------------------------------------------------------------------------


class TestPayrollApprovalWorkflow:

    @pytest.mark.asyncio
    async def test_submit_for_approval(self, db_session: AsyncSession):
        client_id = await _create_test_client(db_session)
        emp_id = await _create_test_employee(db_session, client_id)

        data = PayrollRunCreate(
            pay_period_start=date(2024, 6, 1),
            pay_period_end=date(2024, 6, 15),
            pay_date=date(2024, 6, 20),
            employee_items=[PayrollItemCreate(employee_id=emp_id, hours_worked=Decimal("80"))],
        )
        run = await PayrollService.create_payroll_run(db_session, client_id, data)
        assert run.status == "DRAFT"

        submitted = await PayrollService.submit_for_approval(db_session, client_id, run.id)
        assert submitted.status == "PENDING_APPROVAL"

    @pytest.mark.asyncio
    async def test_cannot_submit_non_draft(self, db_session: AsyncSession):
        client_id = await _create_test_client(db_session)
        emp_id = await _create_test_employee(db_session, client_id)
        await _create_test_user(db_session, CPA_OWNER_USER_ID)

        data = PayrollRunCreate(
            pay_period_start=date(2024, 6, 1),
            pay_period_end=date(2024, 6, 15),
            pay_date=date(2024, 6, 20),
            employee_items=[PayrollItemCreate(employee_id=emp_id, hours_worked=Decimal("80"))],
        )
        run = await PayrollService.create_payroll_run(db_session, client_id, data)
        await PayrollService.submit_for_approval(db_session, client_id, run.id)

        with pytest.raises(HTTPException) as exc_info:
            await PayrollService.submit_for_approval(db_session, client_id, run.id)
        assert exc_info.value.status_code == 400


class TestPayrollFinalization:
    """Tests for P6 — payroll approval gate (CPA_OWNER defense in depth)."""

    @pytest.mark.asyncio
    async def test_cpa_owner_can_finalize(self, db_session: AsyncSession):
        client_id = await _create_test_client(db_session)
        emp_id = await _create_test_employee(db_session, client_id)
        await _create_test_user(db_session, CPA_OWNER_USER_ID)

        data = PayrollRunCreate(
            pay_period_start=date(2024, 6, 1),
            pay_period_end=date(2024, 6, 15),
            pay_date=date(2024, 6, 20),
            employee_items=[PayrollItemCreate(employee_id=emp_id, hours_worked=Decimal("80"))],
        )
        run = await PayrollService.create_payroll_run(db_session, client_id, data)
        await PayrollService.submit_for_approval(db_session, client_id, run.id)

        finalized = await PayrollService.finalize(
            db_session, client_id, run.id, CPA_OWNER_USER,
        )
        assert finalized.status == "FINALIZED"
        assert finalized.finalized_by == uuid.UUID(CPA_OWNER_USER_ID)
        assert finalized.finalized_at is not None

    @pytest.mark.asyncio
    async def test_associate_cannot_finalize(self, db_session: AsyncSession):
        """CLAUDE.md rule #6: PAYROLL GATE defense in depth."""
        client_id = await _create_test_client(db_session)
        emp_id = await _create_test_employee(db_session, client_id)

        data = PayrollRunCreate(
            pay_period_start=date(2024, 6, 1),
            pay_period_end=date(2024, 6, 15),
            pay_date=date(2024, 6, 20),
            employee_items=[PayrollItemCreate(employee_id=emp_id, hours_worked=Decimal("80"))],
        )
        run = await PayrollService.create_payroll_run(db_session, client_id, data)
        await PayrollService.submit_for_approval(db_session, client_id, run.id)

        with pytest.raises(HTTPException) as exc_info:
            await PayrollService.finalize(
                db_session, client_id, run.id, ASSOCIATE_USER,
            )
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_cannot_finalize_draft(self, db_session: AsyncSession):
        client_id = await _create_test_client(db_session)
        emp_id = await _create_test_employee(db_session, client_id)

        data = PayrollRunCreate(
            pay_period_start=date(2024, 6, 1),
            pay_period_end=date(2024, 6, 15),
            pay_date=date(2024, 6, 20),
            employee_items=[PayrollItemCreate(employee_id=emp_id, hours_worked=Decimal("80"))],
        )
        run = await PayrollService.create_payroll_run(db_session, client_id, data)
        # Skip submit — still DRAFT

        with pytest.raises(HTTPException) as exc_info:
            await PayrollService.finalize(
                db_session, client_id, run.id, CPA_OWNER_USER,
            )
        assert exc_info.value.status_code == 400


class TestPayrollVoid:

    @pytest.mark.asyncio
    async def test_void_finalized_run(self, db_session: AsyncSession):
        client_id = await _create_test_client(db_session)
        emp_id = await _create_test_employee(db_session, client_id)
        await _create_test_user(db_session, CPA_OWNER_USER_ID)

        data = PayrollRunCreate(
            pay_period_start=date(2024, 6, 1),
            pay_period_end=date(2024, 6, 15),
            pay_date=date(2024, 6, 20),
            employee_items=[PayrollItemCreate(employee_id=emp_id, hours_worked=Decimal("80"))],
        )
        run = await PayrollService.create_payroll_run(db_session, client_id, data)
        await PayrollService.submit_for_approval(db_session, client_id, run.id)
        await PayrollService.finalize(db_session, client_id, run.id, CPA_OWNER_USER)

        voided = await PayrollService.void(db_session, client_id, run.id, CPA_OWNER_USER)
        assert voided.status == "VOID"

    @pytest.mark.asyncio
    async def test_associate_cannot_void(self, db_session: AsyncSession):
        client_id = await _create_test_client(db_session)
        emp_id = await _create_test_employee(db_session, client_id)
        await _create_test_user(db_session, CPA_OWNER_USER_ID)

        data = PayrollRunCreate(
            pay_period_start=date(2024, 6, 1),
            pay_period_end=date(2024, 6, 15),
            pay_date=date(2024, 6, 20),
            employee_items=[PayrollItemCreate(employee_id=emp_id, hours_worked=Decimal("80"))],
        )
        run = await PayrollService.create_payroll_run(db_session, client_id, data)
        await PayrollService.submit_for_approval(db_session, client_id, run.id)
        await PayrollService.finalize(db_session, client_id, run.id, CPA_OWNER_USER)

        with pytest.raises(HTTPException) as exc_info:
            await PayrollService.void(db_session, client_id, run.id, ASSOCIATE_USER)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_cannot_void_non_finalized(self, db_session: AsyncSession):
        client_id = await _create_test_client(db_session)
        emp_id = await _create_test_employee(db_session, client_id)

        data = PayrollRunCreate(
            pay_period_start=date(2024, 6, 1),
            pay_period_end=date(2024, 6, 15),
            pay_date=date(2024, 6, 20),
            employee_items=[PayrollItemCreate(employee_id=emp_id, hours_worked=Decimal("80"))],
        )
        run = await PayrollService.create_payroll_run(db_session, client_id, data)

        with pytest.raises(HTTPException) as exc_info:
            await PayrollService.void(db_session, client_id, run.id, CPA_OWNER_USER)
        assert exc_info.value.status_code == 400


class TestPayrollClientIsolation:
    """CLAUDE.md rule #4: Client A cannot see Client B's payroll."""

    @pytest.mark.asyncio
    async def test_client_isolation(self, db_session: AsyncSession):
        client_a = await _create_test_client(db_session)
        client_b = await _create_test_client(db_session)
        emp_a = await _create_test_employee(db_session, client_a)

        data = PayrollRunCreate(
            pay_period_start=date(2024, 6, 1),
            pay_period_end=date(2024, 6, 15),
            pay_date=date(2024, 6, 20),
            employee_items=[PayrollItemCreate(employee_id=emp_a, hours_worked=Decimal("80"))],
        )
        run = await PayrollService.create_payroll_run(db_session, client_a, data)

        # Client B cannot see Client A's payroll run
        result = await PayrollService.get(db_session, client_b, run.id)
        assert result is None


class TestPayrollSoftDelete:

    @pytest.mark.asyncio
    async def test_soft_delete_draft(self, db_session: AsyncSession):
        client_id = await _create_test_client(db_session)
        emp_id = await _create_test_employee(db_session, client_id)

        data = PayrollRunCreate(
            pay_period_start=date(2024, 6, 1),
            pay_period_end=date(2024, 6, 15),
            pay_date=date(2024, 6, 20),
            employee_items=[PayrollItemCreate(employee_id=emp_id, hours_worked=Decimal("80"))],
        )
        run = await PayrollService.create_payroll_run(db_session, client_id, data)

        deleted = await PayrollService.soft_delete(db_session, client_id, run.id, CPA_OWNER_USER)
        assert deleted.deleted_at is not None

        # Should not be visible
        result = await PayrollService.get(db_session, client_id, run.id)
        assert result is None

    @pytest.mark.asyncio
    async def test_cannot_delete_finalized(self, db_session: AsyncSession):
        client_id = await _create_test_client(db_session)
        emp_id = await _create_test_employee(db_session, client_id)
        await _create_test_user(db_session, CPA_OWNER_USER_ID)

        data = PayrollRunCreate(
            pay_period_start=date(2024, 6, 1),
            pay_period_end=date(2024, 6, 15),
            pay_date=date(2024, 6, 20),
            employee_items=[PayrollItemCreate(employee_id=emp_id, hours_worked=Decimal("80"))],
        )
        run = await PayrollService.create_payroll_run(db_session, client_id, data)
        await PayrollService.submit_for_approval(db_session, client_id, run.id)
        await PayrollService.finalize(db_session, client_id, run.id, CPA_OWNER_USER)

        with pytest.raises(HTTPException) as exc_info:
            await PayrollService.soft_delete(db_session, client_id, run.id, CPA_OWNER_USER)
        assert exc_info.value.status_code == 400
        assert "Void it first" in exc_info.value.detail
