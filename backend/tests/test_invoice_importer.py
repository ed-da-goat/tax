"""
Tests for Invoice and AR History Importer (module M5).

Uses real PostgreSQL session (rolled back after each test).
"""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.migration.invoice_importer import InvoiceImporter
from app.services.migration.models import ParsedInvoice
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


async def _create_revenue_account(db: AsyncSession, client_id: uuid.UUID) -> uuid.UUID:
    aid = uuid.uuid4()
    await db.execute(
        text(
            "INSERT INTO chart_of_accounts (id, client_id, account_number, account_name, account_type, is_active) "
            "VALUES (:id, :client_id, '4000', 'Service Revenue', 'REVENUE', true)"
        ),
        {"id": str(aid), "client_id": str(client_id)},
    )
    await db.flush()
    return aid


def _inv(
    customer: str = "Client A",
    invoice_no: str = "INV-001",
    invoice_date: date = date(2024, 6, 1),
    due_date: date = date(2024, 7, 1),
    amount: Decimal = Decimal("1000.00"),
    status: str | None = "Open",
    open_balance: Decimal | None = Decimal("1000.00"),
) -> ParsedInvoice:
    return ParsedInvoice(
        invoice_date=invoice_date,
        invoice_no=invoice_no,
        customer=customer,
        due_date=due_date,
        amount=amount,
        open_balance=open_balance,
        status=status,
    )


class TestInvoiceImporter:

    @pytest.mark.asyncio
    async def test_import_single_invoice(self, db_session: AsyncSession):
        client_id = await _create_test_client(db_session)
        rev_id = await _create_revenue_account(db_session, client_id)

        importer = InvoiceImporter()
        result = await importer.import_invoices(
            db_session, client_id, [_inv()], rev_id,
        )

        assert result.total_input == 1
        assert result.total_imported == 1
        assert result.total_skipped == 0

    @pytest.mark.asyncio
    async def test_status_mapping_paid(self, db_session: AsyncSession):
        client_id = await _create_test_client(db_session)
        rev_id = await _create_revenue_account(db_session, client_id)

        result = await InvoiceImporter().import_invoices(
            db_session, client_id,
            [_inv(status="Paid", invoice_no="P-001")],
            rev_id,
        )

        assert result.imported[0].status_mapped_to == "PAID"

    @pytest.mark.asyncio
    async def test_status_mapping_overdue(self, db_session: AsyncSession):
        client_id = await _create_test_client(db_session)
        rev_id = await _create_revenue_account(db_session, client_id)

        result = await InvoiceImporter().import_invoices(
            db_session, client_id,
            [_inv(status="Overdue", invoice_no="O-001")],
            rev_id,
        )

        assert result.imported[0].status_mapped_to == "OVERDUE"

    @pytest.mark.asyncio
    async def test_status_mapping_void(self, db_session: AsyncSession):
        client_id = await _create_test_client(db_session)
        rev_id = await _create_revenue_account(db_session, client_id)

        result = await InvoiceImporter().import_invoices(
            db_session, client_id,
            [_inv(status="Voided", invoice_no="V-001")],
            rev_id,
        )

        assert result.imported[0].status_mapped_to == "VOID"

    @pytest.mark.asyncio
    async def test_skip_duplicate_invoice_number(self, db_session: AsyncSession):
        client_id = await _create_test_client(db_session)
        rev_id = await _create_revenue_account(db_session, client_id)

        importer = InvoiceImporter()
        await importer.import_invoices(
            db_session, client_id, [_inv(invoice_no="DUP-001")], rev_id,
        )

        # Try importing same invoice number again
        result = await importer.import_invoices(
            db_session, client_id, [_inv(invoice_no="DUP-001")], rev_id,
        )

        assert result.total_skipped == 1
        assert "Duplicate" in result.skipped[0].reason

    @pytest.mark.asyncio
    async def test_skip_negative_amount(self, db_session: AsyncSession):
        client_id = await _create_test_client(db_session)
        rev_id = await _create_revenue_account(db_session, client_id)

        result = await InvoiceImporter().import_invoices(
            db_session, client_id,
            [_inv(amount=Decimal("-100.00"), invoice_no="NEG-001")],
            rev_id,
        )

        assert result.total_skipped == 1
        assert "Invalid" in result.skipped[0].reason

    @pytest.mark.asyncio
    async def test_import_multiple_invoices(self, db_session: AsyncSession):
        client_id = await _create_test_client(db_session)
        rev_id = await _create_revenue_account(db_session, client_id)

        invoices = [
            _inv(customer="Client A", invoice_no="A-001", amount=Decimal("500.00")),
            _inv(customer="Client B", invoice_no="B-001", amount=Decimal("750.00"), status="Paid"),
            _inv(customer="Client C", invoice_no="C-001", amount=Decimal("200.00"), status="Overdue"),
        ]

        result = await InvoiceImporter().import_invoices(
            db_session, client_id, invoices, rev_id,
        )

        assert result.total_input == 3
        assert result.total_imported == 3

    @pytest.mark.asyncio
    async def test_empty_input(self, db_session: AsyncSession):
        client_id = await _create_test_client(db_session)
        rev_id = await _create_revenue_account(db_session, client_id)

        result = await InvoiceImporter().import_invoices(
            db_session, client_id, [], rev_id,
        )

        assert result.total_input == 0
        assert result.total_imported == 0
