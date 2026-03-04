"""
Tests for Transaction History Importer (module M4).

Validates that QBO transactions are correctly imported as double-entry
journal entries with proper account resolution and error handling.

Uses real PostgreSQL session (rolled back after each test).
"""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.migration.models import ParsedTransaction
from app.services.migration.transaction_importer import (
    TransactionImporter,
    ImportResult,
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
            "VALUES (:id, :email, :password_hash, :full_name, 'CPA_OWNER', true)"
        ),
        {
            "id": user_id,
            "email": f"user_{user_id[:8]}@test.com",
            "password_hash": "$2b$12$test_hash",
            "full_name": "Test CPA",
        },
    )
    await db.flush()


async def _create_accounts(db: AsyncSession, client_id: uuid.UUID) -> dict[str, uuid.UUID]:
    """Create standard test accounts and return name -> id mapping."""
    accounts = {
        "Checking": ("1000", "ASSET"),
        "Accounts Receivable": ("1200", "ASSET"),
        "Service Revenue": ("4000", "REVENUE"),
        "Office Supplies": ("5100", "EXPENSE"),
        "Rent Expense": ("6100", "EXPENSE"),
    }
    result = {}
    for name, (num, atype) in accounts.items():
        aid = uuid.uuid4()
        await db.execute(
            text(
                "INSERT INTO chart_of_accounts (id, client_id, account_number, account_name, account_type, is_active) "
                "VALUES (:id, :client_id, :num, :name, :atype, true)"
            ),
            {"id": str(aid), "client_id": str(client_id), "num": num, "name": name, "atype": atype},
        )
        result[name] = aid
    await db.flush()
    return result


def _txn(
    account: str = "Checking",
    split: str | None = "Service Revenue",
    amount: Decimal = Decimal("100.00"),
    txn_date: date = date(2024, 6, 15),
    txn_type: str = "Deposit",
    name: str | None = "Client A",
    memo: str | None = "Payment received",
    num: str | None = None,
) -> ParsedTransaction:
    return ParsedTransaction(
        date=txn_date,
        transaction_type=txn_type,
        num=num,
        name=name,
        memo=memo,
        account=account,
        split=split,
        amount=amount,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestTransactionImporter:

    @pytest.mark.asyncio
    async def test_import_single_deposit(self, db_session: AsyncSession):
        client_id = await _create_test_client(db_session)
        await _create_test_user(db_session, CPA_OWNER_USER_ID)
        await _create_accounts(db_session, client_id)

        importer = TransactionImporter(CPA_OWNER_USER_ID)
        result = await importer.import_transactions(
            db_session, client_id,
            [_txn(account="Checking", split="Service Revenue", amount=Decimal("500.00"))],
        )

        assert result.total_input == 1
        assert result.total_imported == 1
        assert result.total_skipped == 0

        # Verify journal entry was created
        je_id = result.imported[0].journal_entry_id
        je_row = await db_session.execute(
            text("SELECT * FROM journal_entries WHERE id = :id"),
            {"id": str(je_id)},
        )
        je = je_row.mappings().one()
        assert je["status"] == "POSTED"
        assert str(je["client_id"]) == str(client_id)

    @pytest.mark.asyncio
    async def test_import_creates_balanced_entry(self, db_session: AsyncSession):
        """Verify double-entry: debits = credits."""
        client_id = await _create_test_client(db_session)
        await _create_test_user(db_session, CPA_OWNER_USER_ID)
        await _create_accounts(db_session, client_id)

        importer = TransactionImporter(CPA_OWNER_USER_ID)
        result = await importer.import_transactions(
            db_session, client_id,
            [_txn(amount=Decimal("250.00"))],
        )

        je_id = result.imported[0].journal_entry_id
        lines = await db_session.execute(
            text("SELECT debit, credit FROM journal_entry_lines WHERE journal_entry_id = :id AND deleted_at IS NULL"),
            {"id": str(je_id)},
        )
        rows = lines.mappings().all()
        assert len(rows) == 2
        total_debit = sum(r["debit"] for r in rows)
        total_credit = sum(r["credit"] for r in rows)
        assert total_debit == total_credit == Decimal("250.00")

    @pytest.mark.asyncio
    async def test_import_negative_amount(self, db_session: AsyncSession):
        """Negative amount = credit primary, debit contra."""
        client_id = await _create_test_client(db_session)
        await _create_test_user(db_session, CPA_OWNER_USER_ID)
        await _create_accounts(db_session, client_id)

        importer = TransactionImporter(CPA_OWNER_USER_ID)
        result = await importer.import_transactions(
            db_session, client_id,
            [_txn(account="Checking", split="Office Supplies", amount=Decimal("-75.00"))],
        )

        assert result.total_imported == 1
        je_id = result.imported[0].journal_entry_id
        lines = await db_session.execute(
            text("SELECT debit, credit FROM journal_entry_lines WHERE journal_entry_id = :id AND deleted_at IS NULL"),
            {"id": str(je_id)},
        )
        rows = lines.mappings().all()
        total_debit = sum(r["debit"] for r in rows)
        total_credit = sum(r["credit"] for r in rows)
        assert total_debit == total_credit == Decimal("75.00")

    @pytest.mark.asyncio
    async def test_skip_unknown_account(self, db_session: AsyncSession):
        client_id = await _create_test_client(db_session)
        await _create_test_user(db_session, CPA_OWNER_USER_ID)
        await _create_accounts(db_session, client_id)

        importer = TransactionImporter(CPA_OWNER_USER_ID)
        result = await importer.import_transactions(
            db_session, client_id,
            [_txn(account="Nonexistent Account")],
        )

        assert result.total_imported == 0
        assert result.total_skipped == 1
        assert "not found" in result.skipped[0].reason

    @pytest.mark.asyncio
    async def test_skip_unknown_contra_account(self, db_session: AsyncSession):
        client_id = await _create_test_client(db_session)
        await _create_test_user(db_session, CPA_OWNER_USER_ID)
        await _create_accounts(db_session, client_id)

        importer = TransactionImporter(CPA_OWNER_USER_ID)
        result = await importer.import_transactions(
            db_session, client_id,
            [_txn(split="Nonexistent Contra")],
        )

        assert result.total_imported == 0
        assert result.total_skipped == 1

    @pytest.mark.asyncio
    async def test_skip_zero_amount(self, db_session: AsyncSession):
        client_id = await _create_test_client(db_session)
        await _create_test_user(db_session, CPA_OWNER_USER_ID)
        await _create_accounts(db_session, client_id)

        importer = TransactionImporter(CPA_OWNER_USER_ID)
        result = await importer.import_transactions(
            db_session, client_id,
            [_txn(amount=Decimal("0.00"))],
        )

        assert result.total_imported == 0
        assert result.total_skipped == 1
        assert "Zero amount" in result.skipped[0].reason

    @pytest.mark.asyncio
    async def test_skip_multi_split(self, db_session: AsyncSession):
        client_id = await _create_test_client(db_session)
        await _create_test_user(db_session, CPA_OWNER_USER_ID)
        await _create_accounts(db_session, client_id)

        importer = TransactionImporter(CPA_OWNER_USER_ID)
        result = await importer.import_transactions(
            db_session, client_id,
            [_txn(split="-Split-")],  # QBO multi-split indicator
        )

        assert result.total_imported == 0
        assert result.total_skipped == 1

    @pytest.mark.asyncio
    async def test_import_multiple_transactions(self, db_session: AsyncSession):
        client_id = await _create_test_client(db_session)
        await _create_test_user(db_session, CPA_OWNER_USER_ID)
        await _create_accounts(db_session, client_id)

        importer = TransactionImporter(CPA_OWNER_USER_ID)
        txns = [
            _txn(account="Checking", split="Service Revenue", amount=Decimal("1000.00"),
                 txn_date=date(2024, 1, 15), memo="January revenue"),
            _txn(account="Checking", split="Office Supplies", amount=Decimal("-50.00"),
                 txn_date=date(2024, 1, 20), memo="Office supplies purchase"),
            _txn(account="Checking", split="Rent Expense", amount=Decimal("-2000.00"),
                 txn_date=date(2024, 2, 1), memo="February rent"),
        ]

        result = await importer.import_transactions(db_session, client_id, txns)

        assert result.total_input == 3
        assert result.total_imported == 3
        assert result.total_skipped == 0

    @pytest.mark.asyncio
    async def test_mixed_success_and_skip(self, db_session: AsyncSession):
        client_id = await _create_test_client(db_session)
        await _create_test_user(db_session, CPA_OWNER_USER_ID)
        await _create_accounts(db_session, client_id)

        importer = TransactionImporter(CPA_OWNER_USER_ID)
        txns = [
            _txn(account="Checking", split="Service Revenue", amount=Decimal("100.00")),
            _txn(account="Unknown Account", split="Service Revenue", amount=Decimal("200.00")),
            _txn(account="Checking", split="Service Revenue", amount=Decimal("300.00")),
        ]

        result = await importer.import_transactions(db_session, client_id, txns)

        assert result.total_input == 3
        assert result.total_imported == 2
        assert result.total_skipped == 1

    @pytest.mark.asyncio
    async def test_empty_input(self, db_session: AsyncSession):
        client_id = await _create_test_client(db_session)
        await _create_test_user(db_session, CPA_OWNER_USER_ID)

        importer = TransactionImporter(CPA_OWNER_USER_ID)
        result = await importer.import_transactions(db_session, client_id, [])

        assert result.total_input == 0
        assert result.total_imported == 0
        assert result.total_skipped == 0
