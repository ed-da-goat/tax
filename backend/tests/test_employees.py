"""
Tests for Employee Records (module P1).

Compliance tests:
- CLIENT ISOLATION (rule #4): Employees scoped to client_id
- AUDIT TRAIL (rule #2): Soft deletes only

Uses real PostgreSQL session (rolled back after each test).
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.employee import (
    EmployeeCreate,
    EmployeeUpdate,
    FilingStatus,
    PayType,
)
from app.services.employee import EmployeeService
from tests.conftest import CPA_OWNER_USER, CPA_OWNER_USER_ID


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


# ---------------------------------------------------------------------------
# CRUD tests
# ---------------------------------------------------------------------------


class TestEmployeeCRUD:

    @pytest.mark.asyncio
    async def test_create_employee(self, db_session: AsyncSession):
        client_id = await _create_test_client(db_session)

        data = EmployeeCreate(
            first_name="John",
            last_name="Smith",
            filing_status=FilingStatus.SINGLE,
            allowances=1,
            pay_rate=Decimal("25.00"),
            pay_type=PayType.HOURLY,
            hire_date=date(2024, 1, 15),
        )
        employee = await EmployeeService.create(db_session, client_id, data)

        assert employee.client_id == client_id
        assert employee.first_name == "John"
        assert employee.last_name == "Smith"
        assert employee.filing_status == "SINGLE"
        assert employee.pay_rate == Decimal("25.00")
        assert employee.pay_type == "HOURLY"
        assert employee.hire_date == date(2024, 1, 15)
        assert employee.is_active is True
        assert employee.termination_date is None

    @pytest.mark.asyncio
    async def test_create_salaried_employee(self, db_session: AsyncSession):
        client_id = await _create_test_client(db_session)

        data = EmployeeCreate(
            first_name="Jane",
            last_name="Doe",
            filing_status=FilingStatus.MARRIED,
            allowances=3,
            pay_rate=Decimal("75000.00"),
            pay_type=PayType.SALARY,
            hire_date=date(2023, 6, 1),
        )
        employee = await EmployeeService.create(db_session, client_id, data)

        assert employee.filing_status == "MARRIED"
        assert employee.pay_type == "SALARY"
        assert employee.pay_rate == Decimal("75000.00")

    @pytest.mark.asyncio
    async def test_get_employee(self, db_session: AsyncSession):
        client_id = await _create_test_client(db_session)
        data = EmployeeCreate(
            first_name="Test",
            last_name="Employee",
            pay_rate=Decimal("20.00"),
            pay_type=PayType.HOURLY,
            hire_date=date.today(),
        )
        created = await EmployeeService.create(db_session, client_id, data)

        fetched = await EmployeeService.get(db_session, client_id, created.id)
        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.first_name == "Test"

    @pytest.mark.asyncio
    async def test_client_isolation(self, db_session: AsyncSession):
        """Client A's employees are not visible to Client B."""
        client_a = await _create_test_client(db_session)
        client_b = await _create_test_client(db_session)

        data = EmployeeCreate(
            first_name="Secret",
            last_name="Employee",
            pay_rate=Decimal("30.00"),
            pay_type=PayType.HOURLY,
            hire_date=date.today(),
        )
        employee = await EmployeeService.create(db_session, client_a, data)

        result = await EmployeeService.get(db_session, client_b, employee.id)
        assert result is None

    @pytest.mark.asyncio
    async def test_list_employees(self, db_session: AsyncSession):
        client_id = await _create_test_client(db_session)

        for name in ["Alice", "Bob", "Charlie"]:
            await EmployeeService.create(
                db_session, client_id,
                EmployeeCreate(
                    first_name=name,
                    last_name="Test",
                    pay_rate=Decimal("20.00"),
                    pay_type=PayType.HOURLY,
                    hire_date=date.today(),
                ),
            )

        employees, total = await EmployeeService.list(db_session, client_id)
        assert total == 3
        assert len(employees) == 3
        # Should be ordered by last_name, first_name
        names = [e.first_name for e in employees]
        assert names == ["Alice", "Bob", "Charlie"]

    @pytest.mark.asyncio
    async def test_list_active_only(self, db_session: AsyncSession):
        client_id = await _create_test_client(db_session)

        active = await EmployeeService.create(
            db_session, client_id,
            EmployeeCreate(
                first_name="Active",
                last_name="Worker",
                pay_rate=Decimal("20.00"),
                pay_type=PayType.HOURLY,
                hire_date=date.today(),
            ),
        )
        terminated = await EmployeeService.create(
            db_session, client_id,
            EmployeeCreate(
                first_name="Former",
                last_name="Worker",
                pay_rate=Decimal("20.00"),
                pay_type=PayType.HOURLY,
                hire_date=date(2022, 1, 1),
            ),
        )
        await EmployeeService.terminate(
            db_session, client_id, terminated.id, date(2024, 12, 31),
        )

        # Active only (default)
        employees, total = await EmployeeService.list(db_session, client_id, active_only=True)
        assert total == 1
        assert employees[0].first_name == "Active"

        # Include inactive
        employees, total = await EmployeeService.list(db_session, client_id, active_only=False)
        assert total == 2

    @pytest.mark.asyncio
    async def test_update_employee(self, db_session: AsyncSession):
        client_id = await _create_test_client(db_session)
        employee = await EmployeeService.create(
            db_session, client_id,
            EmployeeCreate(
                first_name="Old",
                last_name="Name",
                pay_rate=Decimal("20.00"),
                pay_type=PayType.HOURLY,
                hire_date=date.today(),
            ),
        )

        updated = await EmployeeService.update(
            db_session, client_id, employee.id,
            EmployeeUpdate(
                first_name="New",
                pay_rate=Decimal("25.00"),
                filing_status=FilingStatus.MARRIED,
            ),
        )
        assert updated is not None
        assert updated.first_name == "New"
        assert updated.pay_rate == Decimal("25.00")
        assert updated.filing_status == "MARRIED"

    @pytest.mark.asyncio
    async def test_terminate_employee(self, db_session: AsyncSession):
        client_id = await _create_test_client(db_session)
        employee = await EmployeeService.create(
            db_session, client_id,
            EmployeeCreate(
                first_name="Leaving",
                last_name="Employee",
                pay_rate=Decimal("20.00"),
                pay_type=PayType.HOURLY,
                hire_date=date(2023, 1, 1),
            ),
        )

        term_date = date(2024, 12, 31)
        terminated = await EmployeeService.terminate(
            db_session, client_id, employee.id, term_date,
        )

        assert terminated is not None
        assert terminated.is_active is False
        assert terminated.termination_date == term_date

    @pytest.mark.asyncio
    async def test_cannot_terminate_already_terminated(self, db_session: AsyncSession):
        client_id = await _create_test_client(db_session)
        employee = await EmployeeService.create(
            db_session, client_id,
            EmployeeCreate(
                first_name="Already",
                last_name="Gone",
                pay_rate=Decimal("20.00"),
                pay_type=PayType.HOURLY,
                hire_date=date(2023, 1, 1),
            ),
        )

        await EmployeeService.terminate(
            db_session, client_id, employee.id, date(2024, 6, 30),
        )

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await EmployeeService.terminate(
                db_session, client_id, employee.id, date(2024, 12, 31),
            )
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_soft_delete_employee(self, db_session: AsyncSession):
        client_id = await _create_test_client(db_session)
        employee = await EmployeeService.create(
            db_session, client_id,
            EmployeeCreate(
                first_name="Delete",
                last_name="Me",
                pay_rate=Decimal("20.00"),
                pay_type=PayType.HOURLY,
                hire_date=date.today(),
            ),
        )

        deleted = await EmployeeService.soft_delete(db_session, client_id, employee.id)
        assert deleted is not None
        assert deleted.deleted_at is not None

        # Should not be visible anymore
        result = await EmployeeService.get(db_session, client_id, employee.id)
        assert result is None

    @pytest.mark.asyncio
    async def test_head_of_household_filing_status(self, db_session: AsyncSession):
        client_id = await _create_test_client(db_session)
        employee = await EmployeeService.create(
            db_session, client_id,
            EmployeeCreate(
                first_name="Parent",
                last_name="Worker",
                filing_status=FilingStatus.HEAD_OF_HOUSEHOLD,
                allowances=2,
                pay_rate=Decimal("35000.00"),
                pay_type=PayType.SALARY,
                hire_date=date.today(),
            ),
        )

        assert employee.filing_status == "HEAD_OF_HOUSEHOLD"
        assert employee.allowances == 2
