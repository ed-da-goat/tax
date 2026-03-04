"""
Tests for Payroll History Importer (module M6).

Validates that QBO payroll records are correctly imported into
payroll_runs and payroll_items tables with proper employee matching.

Uses real PostgreSQL session (rolled back after each test).
"""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.migration.models import ParsedPayrollRecord
from app.services.migration.payroll_importer import (
    PayrollHistoryImporter,
    PayrollImportResult,
)
from tests.conftest import CPA_OWNER_USER_ID


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _create_test_client(db: AsyncSession) -> uuid.UUID:
    cid = uuid.uuid4()
    await db.execute(
        text(
            "INSERT INTO clients (id, name, entity_type, is_active) "
            "VALUES (:id, :name, 'SOLE_PROP', true)"
        ),
        {"id": str(cid), "name": f"Test Client {cid}"},
    )
    await db.flush()
    return cid


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


async def _create_test_employee(
    db: AsyncSession,
    client_id: uuid.UUID,
    first_name: str = "John",
    last_name: str = "Smith",
) -> uuid.UUID:
    eid = uuid.uuid4()
    await db.execute(
        text(
            "INSERT INTO employees (id, client_id, first_name, last_name, "
            "filing_status, allowances, pay_rate, pay_type, hire_date, is_active) "
            "VALUES (:id, :client_id, :first, :last, 'SINGLE', 0, '25.00', 'HOURLY', '2024-01-15', true)"
        ),
        {
            "id": str(eid),
            "client_id": str(client_id),
            "first": first_name,
            "last": last_name,
        },
    )
    await db.flush()
    return eid


def _payroll_record(
    employee: str = "John Smith",
    gross_pay: Decimal = Decimal("2000.00"),
    federal_withholding: Decimal | None = Decimal("250.00"),
    state_withholding: Decimal | None = Decimal("100.00"),
    social_security: Decimal | None = Decimal("124.00"),
    medicare: Decimal | None = Decimal("29.00"),
    net_pay: Decimal | None = Decimal("1497.00"),
    ga_suta: Decimal | None = Decimal("54.00"),
    futa: Decimal | None = Decimal("12.00"),
) -> ParsedPayrollRecord:
    return ParsedPayrollRecord(
        employee=employee,
        gross_pay=gross_pay,
        federal_withholding=federal_withholding,
        state_withholding=state_withholding,
        social_security=social_security,
        medicare=medicare,
        net_pay=net_pay,
        ga_suta=ga_suta,
        futa=futa,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestPayrollHistoryImporter:

    @pytest.mark.asyncio
    async def test_import_single_record(self, db_session: AsyncSession):
        client_id = await _create_test_client(db_session)
        await _create_test_user(db_session, CPA_OWNER_USER_ID)
        await _create_test_employee(db_session, client_id, "John", "Smith")

        importer = PayrollHistoryImporter(CPA_OWNER_USER_ID)
        result = await importer.import_payroll_records(
            db_session, client_id,
            [_payroll_record()],
            pay_period_start=date(2024, 6, 1),
            pay_period_end=date(2024, 6, 15),
            pay_date=date(2024, 6, 20),
        )

        assert result.total_input == 1
        assert result.total_imported == 1
        assert result.total_skipped == 0
        assert result.payroll_run_id is not None

        # Verify run was created as FINALIZED
        run_row = await db_session.execute(
            text("SELECT status FROM payroll_runs WHERE id = :id"),
            {"id": str(result.payroll_run_id)},
        )
        assert run_row.scalar_one() == "FINALIZED"

    @pytest.mark.asyncio
    async def test_import_multiple_employees(self, db_session: AsyncSession):
        client_id = await _create_test_client(db_session)
        await _create_test_user(db_session, CPA_OWNER_USER_ID)
        await _create_test_employee(db_session, client_id, "John", "Smith")
        await _create_test_employee(db_session, client_id, "Jane", "Doe")

        importer = PayrollHistoryImporter(CPA_OWNER_USER_ID)
        result = await importer.import_payroll_records(
            db_session, client_id,
            [
                _payroll_record(employee="John Smith", gross_pay=Decimal("2000.00")),
                _payroll_record(employee="Jane Doe", gross_pay=Decimal("3000.00")),
            ],
            pay_period_start=date(2024, 6, 1),
            pay_period_end=date(2024, 6, 15),
            pay_date=date(2024, 6, 20),
        )

        assert result.total_imported == 2
        assert result.total_skipped == 0

    @pytest.mark.asyncio
    async def test_skip_unknown_employee(self, db_session: AsyncSession):
        client_id = await _create_test_client(db_session)
        await _create_test_user(db_session, CPA_OWNER_USER_ID)
        await _create_test_employee(db_session, client_id, "John", "Smith")

        importer = PayrollHistoryImporter(CPA_OWNER_USER_ID)
        result = await importer.import_payroll_records(
            db_session, client_id,
            [
                _payroll_record(employee="John Smith"),
                _payroll_record(employee="Unknown Person"),
            ],
            pay_period_start=date(2024, 6, 1),
            pay_period_end=date(2024, 6, 15),
            pay_date=date(2024, 6, 20),
        )

        assert result.total_imported == 1
        assert result.total_skipped == 1
        assert "not found" in result.skipped[0].reason

    @pytest.mark.asyncio
    async def test_net_pay_calculated_when_missing(self, db_session: AsyncSession):
        client_id = await _create_test_client(db_session)
        await _create_test_user(db_session, CPA_OWNER_USER_ID)
        await _create_test_employee(db_session, client_id, "John", "Smith")

        importer = PayrollHistoryImporter(CPA_OWNER_USER_ID)
        result = await importer.import_payroll_records(
            db_session, client_id,
            [_payroll_record(net_pay=None)],  # Net pay will be calculated
            pay_period_start=date(2024, 6, 1),
            pay_period_end=date(2024, 6, 15),
            pay_date=date(2024, 6, 20),
        )

        assert result.total_imported == 1
        # Net pay = 2000 - 250 - 100 - 124 - 29 = 1497
        item_row = await db_session.execute(
            text(
                "SELECT net_pay FROM payroll_items WHERE payroll_run_id = :id "
                "AND deleted_at IS NULL"
            ),
            {"id": str(result.payroll_run_id)},
        )
        net_pay = item_row.scalar_one()
        assert net_pay == Decimal("1497.00")

    @pytest.mark.asyncio
    async def test_empty_input(self, db_session: AsyncSession):
        client_id = await _create_test_client(db_session)
        await _create_test_user(db_session, CPA_OWNER_USER_ID)

        importer = PayrollHistoryImporter(CPA_OWNER_USER_ID)
        result = await importer.import_payroll_records(
            db_session, client_id,
            [],
            pay_period_start=date(2024, 6, 1),
            pay_period_end=date(2024, 6, 15),
            pay_date=date(2024, 6, 20),
        )

        assert result.total_input == 0
        assert result.total_imported == 0
        assert result.payroll_run_id is None

    @pytest.mark.asyncio
    async def test_case_insensitive_employee_match(self, db_session: AsyncSession):
        """Employee matching should be case-insensitive."""
        client_id = await _create_test_client(db_session)
        await _create_test_user(db_session, CPA_OWNER_USER_ID)
        await _create_test_employee(db_session, client_id, "John", "Smith")

        importer = PayrollHistoryImporter(CPA_OWNER_USER_ID)
        result = await importer.import_payroll_records(
            db_session, client_id,
            [_payroll_record(employee="john smith")],  # lowercase
            pay_period_start=date(2024, 6, 1),
            pay_period_end=date(2024, 6, 15),
            pay_date=date(2024, 6, 20),
        )

        assert result.total_imported == 1

    @pytest.mark.asyncio
    async def test_null_tax_values_default_to_zero(self, db_session: AsyncSession):
        client_id = await _create_test_client(db_session)
        await _create_test_user(db_session, CPA_OWNER_USER_ID)
        await _create_test_employee(db_session, client_id, "John", "Smith")

        record = ParsedPayrollRecord(
            employee="John Smith",
            gross_pay=Decimal("1000.00"),
            federal_withholding=None,
            state_withholding=None,
            social_security=None,
            medicare=None,
            net_pay=Decimal("1000.00"),
            ga_suta=None,
            futa=None,
        )
        importer = PayrollHistoryImporter(CPA_OWNER_USER_ID)
        result = await importer.import_payroll_records(
            db_session, client_id,
            [record],
            pay_period_start=date(2024, 6, 1),
            pay_period_end=date(2024, 6, 15),
            pay_date=date(2024, 6, 20),
        )

        assert result.total_imported == 1

    @pytest.mark.asyncio
    async def test_mixed_success_and_skip(self, db_session: AsyncSession):
        client_id = await _create_test_client(db_session)
        await _create_test_user(db_session, CPA_OWNER_USER_ID)
        await _create_test_employee(db_session, client_id, "John", "Smith")

        importer = PayrollHistoryImporter(CPA_OWNER_USER_ID)
        result = await importer.import_payroll_records(
            db_session, client_id,
            [
                _payroll_record(employee="John Smith"),
                _payroll_record(employee="Unknown"),
                _payroll_record(employee="Also Unknown"),
            ],
            pay_period_start=date(2024, 6, 1),
            pay_period_end=date(2024, 6, 15),
            pay_date=date(2024, 6, 20),
        )

        assert result.total_input == 3
        assert result.total_imported == 1
        assert result.total_skipped == 2
