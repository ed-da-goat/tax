"""
Tests for Bank Reconciliation (module T3).

Compliance tests:
- CLIENT ISOLATION (rule #4): Bank accounts scoped to client_id
- APPROVAL WORKFLOW (rule #5): CPA_OWNER required for completing reconciliation
- ROLE ENFORCEMENT (rule #6): Defense in depth
- AUDIT TRAIL (rule #2): Soft deletes only

Uses real PostgreSQL session (rolled back after each test).
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser
from app.models.bank_account import BankTransaction, ReconciliationStatus
from app.schemas.bank_reconciliation import (
    BankAccountCreate,
    BankAccountUpdate,
    BankTransactionCreate,
    BankTransactionType,
    ReconciliationCreate,
)
from app.services.bank_reconciliation import (
    BankAccountService,
    BankTransactionService,
    ReconciliationService,
)
from tests.conftest import CPA_OWNER_USER, ASSOCIATE_USER, CPA_OWNER_USER_ID, ASSOCIATE_USER_ID


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


async def _create_test_user(db: AsyncSession, user_id: str | None = None, role: str = "CPA_OWNER") -> str:
    uid = user_id or str(uuid.uuid4())
    await db.execute(
        text(
            "INSERT INTO users (id, email, password_hash, full_name, role, is_active) "
            "VALUES (:id, :email, :password_hash, :full_name, :role, true)"
        ),
        {
            "id": uid,
            "email": f"user_{uid[:8]}@test.com",
            "password_hash": "$2b$12$test_hash_placeholder_for_testing",
            "full_name": f"Test User {uid[:8]}",
            "role": role,
        },
    )
    await db.flush()
    return uid


# ---------------------------------------------------------------------------
# Bank Account CRUD tests
# ---------------------------------------------------------------------------


class TestBankAccountCRUD:

    @pytest.mark.asyncio
    async def test_create_bank_account(self, db_session: AsyncSession):
        client_id = await _create_test_client(db_session)
        data = BankAccountCreate(
            account_name="Business Checking",
            institution_name="First Georgia Bank",
        )
        account = await BankAccountService.create(db_session, client_id, data)

        assert account.client_id == client_id
        assert account.account_name == "Business Checking"
        assert account.institution_name == "First Georgia Bank"
        assert account.deleted_at is None

    @pytest.mark.asyncio
    async def test_get_bank_account(self, db_session: AsyncSession):
        client_id = await _create_test_client(db_session)
        data = BankAccountCreate(account_name="Checking")
        created = await BankAccountService.create(db_session, client_id, data)

        fetched = await BankAccountService.get(db_session, client_id, created.id)
        assert fetched is not None
        assert fetched.id == created.id

    @pytest.mark.asyncio
    async def test_client_isolation(self, db_session: AsyncSession):
        """Client A's bank accounts are not visible to Client B."""
        client_a = await _create_test_client(db_session)
        client_b = await _create_test_client(db_session)

        data = BankAccountCreate(account_name="A's Checking")
        account = await BankAccountService.create(db_session, client_a, data)

        # Client B cannot see Client A's bank account
        result = await BankAccountService.get(db_session, client_b, account.id)
        assert result is None

    @pytest.mark.asyncio
    async def test_list_bank_accounts(self, db_session: AsyncSession):
        client_id = await _create_test_client(db_session)

        await BankAccountService.create(
            db_session, client_id,
            BankAccountCreate(account_name="Checking"),
        )
        await BankAccountService.create(
            db_session, client_id,
            BankAccountCreate(account_name="Savings"),
        )

        accounts, total = await BankAccountService.list(db_session, client_id)
        assert total == 2
        assert len(accounts) == 2

    @pytest.mark.asyncio
    async def test_update_bank_account(self, db_session: AsyncSession):
        client_id = await _create_test_client(db_session)
        account = await BankAccountService.create(
            db_session, client_id,
            BankAccountCreate(account_name="Old Name"),
        )

        updated = await BankAccountService.update(
            db_session, client_id, account.id,
            BankAccountUpdate(account_name="New Name"),
        )
        assert updated is not None
        assert updated.account_name == "New Name"

    @pytest.mark.asyncio
    async def test_soft_delete_bank_account(self, db_session: AsyncSession):
        client_id = await _create_test_client(db_session)
        account = await BankAccountService.create(
            db_session, client_id,
            BankAccountCreate(account_name="To Delete"),
        )

        deleted = await BankAccountService.soft_delete(db_session, client_id, account.id)
        assert deleted is not None
        assert deleted.deleted_at is not None

        # Should not be visible anymore
        result = await BankAccountService.get(db_session, client_id, account.id)
        assert result is None


# ---------------------------------------------------------------------------
# Bank Transaction tests
# ---------------------------------------------------------------------------


class TestBankTransactions:

    @pytest.mark.asyncio
    async def test_create_transaction(self, db_session: AsyncSession):
        client_id = await _create_test_client(db_session)
        account = await BankAccountService.create(
            db_session, client_id,
            BankAccountCreate(account_name="Checking"),
        )

        txn = await BankTransactionService.create(
            db_session, client_id, account.id,
            BankTransactionCreate(
                transaction_date=date.today(),
                description="Client payment",
                amount=Decimal("1500.00"),
                transaction_type=BankTransactionType.CREDIT,
            ),
        )

        assert txn.amount == Decimal("1500.00")
        assert txn.transaction_type == "CREDIT"
        assert txn.is_reconciled is False

    @pytest.mark.asyncio
    async def test_bulk_import(self, db_session: AsyncSession):
        client_id = await _create_test_client(db_session)
        account = await BankAccountService.create(
            db_session, client_id,
            BankAccountCreate(account_name="Checking"),
        )

        txns_data = [
            BankTransactionCreate(
                transaction_date=date.today() - timedelta(days=i),
                description=f"Transaction {i}",
                amount=Decimal(f"{100 + i}.00"),
                transaction_type=BankTransactionType.DEBIT,
            )
            for i in range(5)
        ]

        created = await BankTransactionService.bulk_import(
            db_session, client_id, account.id, txns_data,
        )
        assert len(created) == 5

    @pytest.mark.asyncio
    async def test_list_transactions_with_filters(self, db_session: AsyncSession):
        client_id = await _create_test_client(db_session)
        account = await BankAccountService.create(
            db_session, client_id,
            BankAccountCreate(account_name="Checking"),
        )

        today = date.today()
        await BankTransactionService.create(
            db_session, client_id, account.id,
            BankTransactionCreate(
                transaction_date=today,
                amount=Decimal("100.00"),
                transaction_type=BankTransactionType.CREDIT,
            ),
        )
        await BankTransactionService.create(
            db_session, client_id, account.id,
            BankTransactionCreate(
                transaction_date=today - timedelta(days=30),
                amount=Decimal("200.00"),
                transaction_type=BankTransactionType.DEBIT,
            ),
        )

        # Filter by date range
        txns, total = await BankTransactionService.list(
            db_session, client_id, account.id,
            date_from=today - timedelta(days=1),
        )
        assert total == 1
        assert txns[0].amount == Decimal("100.00")


# ---------------------------------------------------------------------------
# Reconciliation tests
# ---------------------------------------------------------------------------


class TestReconciliation:

    @pytest.mark.asyncio
    async def test_create_reconciliation(self, db_session: AsyncSession):
        client_id = await _create_test_client(db_session)
        account = await BankAccountService.create(
            db_session, client_id,
            BankAccountCreate(account_name="Checking"),
        )

        recon = await ReconciliationService.create(
            db_session, client_id, account.id,
            ReconciliationCreate(
                statement_date=date.today(),
                statement_balance=Decimal("10000.00"),
            ),
        )

        assert recon.status == "IN_PROGRESS"
        assert recon.statement_balance == Decimal("10000.00")

    @pytest.mark.asyncio
    async def test_match_transaction(self, db_session: AsyncSession):
        client_id = await _create_test_client(db_session)
        await _create_test_user(db_session, CPA_OWNER_USER_ID)
        account = await BankAccountService.create(
            db_session, client_id,
            BankAccountCreate(account_name="Checking"),
        )

        txn = await BankTransactionService.create(
            db_session, client_id, account.id,
            BankTransactionCreate(
                transaction_date=date.today(),
                amount=Decimal("500.00"),
                transaction_type=BankTransactionType.CREDIT,
            ),
        )

        # Create a dummy journal entry to match against
        je_id = uuid.uuid4()
        await db_session.execute(
            text(
                "INSERT INTO journal_entries (id, client_id, entry_date, description, status, created_by) "
                "VALUES (:id, :client_id, :entry_date, :desc, 'DRAFT', :created_by)"
            ),
            {
                "id": str(je_id),
                "client_id": str(client_id),
                "entry_date": date.today(),
                "desc": "Test JE",
                "created_by": CPA_OWNER_USER_ID,
            },
        )
        await db_session.flush()

        matched = await ReconciliationService.match_transaction(
            db_session, client_id, account.id, txn.id, je_id,
        )

        assert matched.is_reconciled is True
        assert matched.journal_entry_id == je_id
        assert matched.reconciled_at is not None

    @pytest.mark.asyncio
    async def test_unmatch_transaction(self, db_session: AsyncSession):
        client_id = await _create_test_client(db_session)
        await _create_test_user(db_session, CPA_OWNER_USER_ID)
        account = await BankAccountService.create(
            db_session, client_id,
            BankAccountCreate(account_name="Checking"),
        )

        txn = await BankTransactionService.create(
            db_session, client_id, account.id,
            BankTransactionCreate(
                transaction_date=date.today(),
                amount=Decimal("500.00"),
                transaction_type=BankTransactionType.CREDIT,
            ),
        )

        je_id = uuid.uuid4()
        await db_session.execute(
            text(
                "INSERT INTO journal_entries (id, client_id, entry_date, description, status, created_by) "
                "VALUES (:id, :client_id, :entry_date, :desc, 'DRAFT', :created_by)"
            ),
            {
                "id": str(je_id),
                "client_id": str(client_id),
                "entry_date": date.today(),
                "desc": "Test JE",
                "created_by": CPA_OWNER_USER_ID,
            },
        )
        await db_session.flush()

        await ReconciliationService.match_transaction(
            db_session, client_id, account.id, txn.id, je_id,
        )
        unmatched = await ReconciliationService.unmatch_transaction(
            db_session, client_id, account.id, txn.id,
        )

        assert unmatched.is_reconciled is False
        assert unmatched.journal_entry_id is None

    @pytest.mark.asyncio
    async def test_complete_reconciliation_cpa_only(self, db_session: AsyncSession):
        """Only CPA_OWNER can complete a reconciliation."""
        client_id = await _create_test_client(db_session)
        account = await BankAccountService.create(
            db_session, client_id,
            BankAccountCreate(account_name="Checking"),
        )

        recon = await ReconciliationService.create(
            db_session, client_id, account.id,
            ReconciliationCreate(
                statement_date=date.today(),
                statement_balance=Decimal("5000.00"),
            ),
        )

        # ASSOCIATE should be denied
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await ReconciliationService.complete(
                db_session, client_id, account.id, recon.id,
                ASSOCIATE_USER,
            )
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_complete_reconciliation_success(self, db_session: AsyncSession):
        client_id = await _create_test_client(db_session)
        await _create_test_user(db_session, CPA_OWNER_USER_ID)
        account = await BankAccountService.create(
            db_session, client_id,
            BankAccountCreate(account_name="Checking"),
        )

        recon = await ReconciliationService.create(
            db_session, client_id, account.id,
            ReconciliationCreate(
                statement_date=date.today(),
                statement_balance=Decimal("5000.00"),
            ),
        )

        completed = await ReconciliationService.complete(
            db_session, client_id, account.id, recon.id,
            CPA_OWNER_USER,
        )

        assert completed.status == "COMPLETED"
        assert completed.completed_at is not None
        assert completed.completed_by == uuid.UUID(CPA_OWNER_USER_ID)

    @pytest.mark.asyncio
    async def test_cannot_complete_already_completed(self, db_session: AsyncSession):
        client_id = await _create_test_client(db_session)
        await _create_test_user(db_session, CPA_OWNER_USER_ID)
        account = await BankAccountService.create(
            db_session, client_id,
            BankAccountCreate(account_name="Checking"),
        )

        recon = await ReconciliationService.create(
            db_session, client_id, account.id,
            ReconciliationCreate(
                statement_date=date.today(),
                statement_balance=Decimal("5000.00"),
            ),
        )

        await ReconciliationService.complete(
            db_session, client_id, account.id, recon.id,
            CPA_OWNER_USER,
        )

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await ReconciliationService.complete(
                db_session, client_id, account.id, recon.id,
                CPA_OWNER_USER,
            )
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_already_reconciled_cannot_match_again(self, db_session: AsyncSession):
        client_id = await _create_test_client(db_session)
        await _create_test_user(db_session, CPA_OWNER_USER_ID)
        account = await BankAccountService.create(
            db_session, client_id,
            BankAccountCreate(account_name="Checking"),
        )

        txn = await BankTransactionService.create(
            db_session, client_id, account.id,
            BankTransactionCreate(
                transaction_date=date.today(),
                amount=Decimal("500.00"),
                transaction_type=BankTransactionType.CREDIT,
            ),
        )

        je_id = uuid.uuid4()
        await db_session.execute(
            text(
                "INSERT INTO journal_entries (id, client_id, entry_date, description, status, created_by) "
                "VALUES (:id, :client_id, :entry_date, :desc, 'DRAFT', :created_by)"
            ),
            {
                "id": str(je_id),
                "client_id": str(client_id),
                "entry_date": date.today(),
                "desc": "Test JE",
                "created_by": CPA_OWNER_USER_ID,
            },
        )
        await db_session.flush()

        await ReconciliationService.match_transaction(
            db_session, client_id, account.id, txn.id, je_id,
        )

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await ReconciliationService.match_transaction(
                db_session, client_id, account.id, txn.id, je_id,
            )
        assert exc_info.value.status_code == 400
