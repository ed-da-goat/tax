"""
Tests for Journal Entries / General Ledger (module F3).

HIGH COMPLIANCE RISK — TDD approach: these tests were written before implementation.

Compliance tests:
- DOUBLE-ENTRY (rule #1): Debits must equal credits, enforced at app + DB levels
- AUDIT TRAIL (rule #2): Soft deletes only; void creates reversing entry
- CLIENT ISOLATION (rule #4): Client A entries never visible via Client B queries
- APPROVAL WORKFLOW (rule #5): ASSOCIATE enters DRAFT, only CPA_OWNER posts
- ROLE ENFORCEMENT (rule #6): Defense in depth at route + function level

Uses real PostgreSQL session (rolled back after each test) via db_session
and db_client fixtures from conftest.py.
"""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from httpx import AsyncClient
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, verify_role
from app.schemas.journal_entry import JournalEntryCreate, JournalEntryLineCreate
from app.services.journal_entry import JournalEntryService
from tests.conftest import CPA_OWNER_USER, CPA_OWNER_USER_ID, ASSOCIATE_USER


# ---------------------------------------------------------------------------
# Helpers: create prerequisite records in the DB
# ---------------------------------------------------------------------------


async def _create_test_client(db: AsyncSession, client_id: uuid.UUID | None = None) -> uuid.UUID:
    """Insert a minimal client row and return its UUID."""
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


async def _create_test_user(db: AsyncSession, user_id: str | None = None) -> str:
    """Insert a minimal user row and return its UUID string."""
    uid = user_id or str(uuid.uuid4())
    await db.execute(
        text(
            "INSERT INTO users (id, email, password_hash, full_name, role, is_active) "
            "VALUES (:id, :email, :password_hash, :full_name, 'CPA_OWNER', true)"
        ),
        {
            "id": uid,
            "email": f"user_{uid[:8]}@test.com",
            "password_hash": "$2b$12$test_hash_placeholder_for_testing",
            "full_name": f"Test User {uid[:8]}",
        },
    )
    await db.flush()
    return uid


async def _create_test_accounts(
    db: AsyncSession, client_id: uuid.UUID, count: int = 2
) -> list[uuid.UUID]:
    """Create test chart of accounts entries and return their IDs."""
    account_ids = []
    accounts = [
        ("1000", "Cash", "ASSET"),
        ("4000", "Revenue", "REVENUE"),
        ("5000", "Expenses", "EXPENSE"),
        ("2000", "Accounts Payable", "LIABILITY"),
        ("3000", "Owner Equity", "EQUITY"),
    ]
    for i in range(min(count, len(accounts))):
        acct_id = uuid.uuid4()
        num, name, atype = accounts[i]
        await db.execute(
            text(
                "INSERT INTO chart_of_accounts (id, client_id, account_number, account_name, account_type, is_active) "
                "VALUES (:id, :client_id, :account_number, :account_name, :account_type, true)"
            ),
            {
                "id": str(acct_id),
                "client_id": str(client_id),
                "account_number": num,
                "account_name": name,
                "account_type": atype,
            },
        )
        account_ids.append(acct_id)
    await db.flush()
    return account_ids


async def _setup_full_context(db: AsyncSession) -> tuple[uuid.UUID, list[uuid.UUID], str]:
    """Create client, accounts, and user. Returns (client_id, account_ids, user_id)."""
    client_id = await _create_test_client(db)
    user_id = await _create_test_user(db, CPA_OWNER_USER_ID)
    account_ids = await _create_test_accounts(db, client_id, 2)
    return client_id, account_ids, user_id


# ---------------------------------------------------------------------------
# Schema validation tests (pure Pydantic, no DB required)
# ---------------------------------------------------------------------------


class TestJournalEntrySchemaValidation:
    """Test Pydantic schema validation for journal entry creation."""

    def test_balanced_entry_passes_validation(self) -> None:
        """A journal entry with equal debits and credits passes validation."""
        data = JournalEntryCreate(
            client_id=uuid.uuid4(),
            entry_date=date(2024, 1, 15),
            description="Test entry",
            lines=[
                JournalEntryLineCreate(account_id=uuid.uuid4(), debit=Decimal("100.00"), credit=Decimal("0.00")),
                JournalEntryLineCreate(account_id=uuid.uuid4(), debit=Decimal("0.00"), credit=Decimal("100.00")),
            ],
        )
        assert len(data.lines) == 2

    def test_unbalanced_entry_fails_validation(self) -> None:
        """A journal entry where debits != credits must fail validation."""
        with pytest.raises(ValidationError, match="unbalanced"):
            JournalEntryCreate(
                client_id=uuid.uuid4(),
                entry_date=date(2024, 1, 15),
                description="Unbalanced",
                lines=[
                    JournalEntryLineCreate(account_id=uuid.uuid4(), debit=Decimal("100.00"), credit=Decimal("0.00")),
                    JournalEntryLineCreate(account_id=uuid.uuid4(), debit=Decimal("0.00"), credit=Decimal("50.00")),
                ],
            )

    def test_single_line_fails_validation(self) -> None:
        """A journal entry with only one line must fail (need at least 2)."""
        with pytest.raises(ValidationError):
            JournalEntryCreate(
                client_id=uuid.uuid4(),
                entry_date=date(2024, 1, 15),
                lines=[
                    JournalEntryLineCreate(account_id=uuid.uuid4(), debit=Decimal("100.00"), credit=Decimal("0.00")),
                ],
            )

    def test_zero_lines_fails_validation(self) -> None:
        """A journal entry with zero lines must fail."""
        with pytest.raises(ValidationError):
            JournalEntryCreate(
                client_id=uuid.uuid4(),
                entry_date=date(2024, 1, 15),
                lines=[],
            )

    def test_line_with_both_debit_and_credit_fails(self) -> None:
        """A line with both debit > 0 and credit > 0 must fail."""
        with pytest.raises(ValidationError, match="both debit and credit"):
            JournalEntryLineCreate(
                account_id=uuid.uuid4(),
                debit=Decimal("100.00"),
                credit=Decimal("50.00"),
            )

    def test_line_with_zero_debit_and_zero_credit_fails(self) -> None:
        """A line with debit=0 and credit=0 must fail."""
        with pytest.raises(ValidationError, match="either a debit or credit"):
            JournalEntryLineCreate(
                account_id=uuid.uuid4(),
                debit=Decimal("0.00"),
                credit=Decimal("0.00"),
            )

    def test_zero_value_entry_fails(self) -> None:
        """Zero-value lines should fail the XOR constraint."""
        with pytest.raises(ValidationError):
            JournalEntryLineCreate(
                account_id=uuid.uuid4(),
                debit=Decimal("0"),
                credit=Decimal("0"),
            )

    def test_large_value_entry_passes(self) -> None:
        """Large realistic value for a GA small business (e.g. $10M) should pass."""
        data = JournalEntryCreate(
            client_id=uuid.uuid4(),
            entry_date=date(2024, 12, 31),
            description="Large transaction",
            lines=[
                JournalEntryLineCreate(account_id=uuid.uuid4(), debit=Decimal("10000000.00"), credit=Decimal("0.00")),
                JournalEntryLineCreate(account_id=uuid.uuid4(), debit=Decimal("0.00"), credit=Decimal("10000000.00")),
            ],
        )
        assert sum(l.debit for l in data.lines) == Decimal("10000000.00")

    def test_multi_line_balanced_entry(self) -> None:
        """Entry with multiple debit and credit lines that balance should pass."""
        data = JournalEntryCreate(
            client_id=uuid.uuid4(),
            entry_date=date(2024, 6, 15),
            description="Multi-line entry",
            lines=[
                JournalEntryLineCreate(account_id=uuid.uuid4(), debit=Decimal("300.00"), credit=Decimal("0.00")),
                JournalEntryLineCreate(account_id=uuid.uuid4(), debit=Decimal("200.00"), credit=Decimal("0.00")),
                JournalEntryLineCreate(account_id=uuid.uuid4(), debit=Decimal("0.00"), credit=Decimal("400.00")),
                JournalEntryLineCreate(account_id=uuid.uuid4(), debit=Decimal("0.00"), credit=Decimal("100.00")),
            ],
        )
        assert len(data.lines) == 4


# ---------------------------------------------------------------------------
# Service-layer tests (direct DB, no HTTP)
# ---------------------------------------------------------------------------


class TestJournalEntryServiceCreate:
    """Tests for JournalEntryService.create_entry."""

    async def test_create_balanced_entry_succeeds(self, db_session: AsyncSession) -> None:
        """Creating a balanced journal entry succeeds and returns the entry with lines."""
        client_id, account_ids, user_id = await _setup_full_context(db_session)
        user = CurrentUser(user_id=user_id, role="CPA_OWNER")

        data = JournalEntryCreate(
            client_id=client_id,
            entry_date=date(2024, 1, 15),
            description="Test balanced entry",
            reference_number="JE-001",
            lines=[
                JournalEntryLineCreate(account_id=account_ids[0], debit=Decimal("500.00"), credit=Decimal("0.00")),
                JournalEntryLineCreate(account_id=account_ids[1], debit=Decimal("0.00"), credit=Decimal("500.00")),
            ],
        )

        entry = await JournalEntryService.create_entry(db_session, data, user)

        assert entry.client_id == client_id
        assert entry.status.value == "DRAFT"
        assert entry.description == "Test balanced entry"
        assert entry.reference_number == "JE-001"
        assert len(entry.lines) == 2
        assert entry.created_by == uuid.UUID(user_id)
        assert entry.approved_by is None
        assert entry.posted_at is None

    async def test_create_entry_status_is_draft(self, db_session: AsyncSession) -> None:
        """New entries always start as DRAFT regardless of role."""
        client_id, account_ids, user_id = await _setup_full_context(db_session)
        user = CurrentUser(user_id=user_id, role="CPA_OWNER")

        data = JournalEntryCreate(
            client_id=client_id,
            entry_date=date(2024, 1, 15),
            lines=[
                JournalEntryLineCreate(account_id=account_ids[0], debit=Decimal("100.00"), credit=Decimal("0.00")),
                JournalEntryLineCreate(account_id=account_ids[1], debit=Decimal("0.00"), credit=Decimal("100.00")),
            ],
        )

        entry = await JournalEntryService.create_entry(db_session, data, user)
        assert entry.status.value == "DRAFT"


class TestJournalEntryServiceWorkflow:
    """Tests for the status workflow: DRAFT -> PENDING_APPROVAL -> POSTED -> VOID."""

    async def test_submit_for_approval(self, db_session: AsyncSession) -> None:
        """DRAFT -> PENDING_APPROVAL works for any role."""
        client_id, account_ids, user_id = await _setup_full_context(db_session)
        user = CurrentUser(user_id=user_id, role="CPA_OWNER")

        data = JournalEntryCreate(
            client_id=client_id,
            entry_date=date(2024, 1, 15),
            lines=[
                JournalEntryLineCreate(account_id=account_ids[0], debit=Decimal("100.00"), credit=Decimal("0.00")),
                JournalEntryLineCreate(account_id=account_ids[1], debit=Decimal("0.00"), credit=Decimal("100.00")),
            ],
        )
        entry = await JournalEntryService.create_entry(db_session, data, user)
        assert entry.status.value == "DRAFT"

        submitted = await JournalEntryService.submit_for_approval(db_session, client_id, entry.id, user)
        assert submitted is not None
        assert submitted.status.value == "PENDING_APPROVAL"

    async def test_approve_and_post(self, db_session: AsyncSession) -> None:
        """PENDING_APPROVAL -> POSTED works for CPA_OWNER."""
        client_id, account_ids, user_id = await _setup_full_context(db_session)
        user = CurrentUser(user_id=user_id, role="CPA_OWNER")

        data = JournalEntryCreate(
            client_id=client_id,
            entry_date=date(2024, 1, 15),
            lines=[
                JournalEntryLineCreate(account_id=account_ids[0], debit=Decimal("100.00"), credit=Decimal("0.00")),
                JournalEntryLineCreate(account_id=account_ids[1], debit=Decimal("0.00"), credit=Decimal("100.00")),
            ],
        )
        entry = await JournalEntryService.create_entry(db_session, data, user)
        await JournalEntryService.submit_for_approval(db_session, client_id, entry.id, user)

        posted = await JournalEntryService.approve_and_post(db_session, client_id, entry.id, user)
        assert posted is not None
        assert posted.status.value == "POSTED"
        assert posted.approved_by == uuid.UUID(user_id)
        assert posted.posted_at is not None

    async def test_full_lifecycle_draft_to_void(self, db_session: AsyncSession) -> None:
        """Full lifecycle: DRAFT -> PENDING_APPROVAL -> POSTED -> VOID."""
        client_id, account_ids, user_id = await _setup_full_context(db_session)
        user = CurrentUser(user_id=user_id, role="CPA_OWNER")

        data = JournalEntryCreate(
            client_id=client_id,
            entry_date=date(2024, 1, 15),
            lines=[
                JournalEntryLineCreate(account_id=account_ids[0], debit=Decimal("250.00"), credit=Decimal("0.00")),
                JournalEntryLineCreate(account_id=account_ids[1], debit=Decimal("0.00"), credit=Decimal("250.00")),
            ],
        )

        entry = await JournalEntryService.create_entry(db_session, data, user)
        assert entry.status.value == "DRAFT"

        await JournalEntryService.submit_for_approval(db_session, client_id, entry.id, user)
        await JournalEntryService.approve_and_post(db_session, client_id, entry.id, user)

        result = await JournalEntryService.void_entry(db_session, client_id, entry.id, user)
        assert result is not None
        voided, reversing = result
        assert voided.status.value == "VOID"
        assert reversing.status.value == "POSTED"

    async def test_void_creates_reversing_entry(self, db_session: AsyncSession) -> None:
        """Voiding a posted entry creates a reversing entry with swapped debits/credits."""
        client_id, account_ids, user_id = await _setup_full_context(db_session)
        user = CurrentUser(user_id=user_id, role="CPA_OWNER")

        data = JournalEntryCreate(
            client_id=client_id,
            entry_date=date(2024, 1, 15),
            description="Original entry",
            lines=[
                JournalEntryLineCreate(account_id=account_ids[0], debit=Decimal("300.00"), credit=Decimal("0.00")),
                JournalEntryLineCreate(account_id=account_ids[1], debit=Decimal("0.00"), credit=Decimal("300.00")),
            ],
        )
        entry = await JournalEntryService.create_entry(db_session, data, user)
        await JournalEntryService.submit_for_approval(db_session, client_id, entry.id, user)
        await JournalEntryService.approve_and_post(db_session, client_id, entry.id, user)

        result = await JournalEntryService.void_entry(db_session, client_id, entry.id, user)
        assert result is not None
        _voided, reversing = result

        # Reversing entry should have swapped debits/credits
        assert len(reversing.lines) == 2
        reversing_lines = sorted(reversing.lines, key=lambda l: str(l.account_id))
        original_lines = sorted(entry.lines, key=lambda l: str(l.account_id))

        for orig, rev in zip(original_lines, reversing_lines):
            assert rev.debit == orig.credit
            assert rev.credit == orig.debit
            assert rev.account_id == orig.account_id


class TestJournalEntryServiceRoleEnforcement:
    """Tests for role enforcement at the service/function level (defense in depth)."""

    async def test_associate_cannot_approve(self, db_session: AsyncSession) -> None:
        """ASSOCIATE must not be able to approve/post entries (403 at function level)."""
        from fastapi import HTTPException

        client_id, account_ids, user_id = await _setup_full_context(db_session)
        owner = CurrentUser(user_id=user_id, role="CPA_OWNER")
        associate = CurrentUser(user_id=user_id, role="ASSOCIATE")

        data = JournalEntryCreate(
            client_id=client_id,
            entry_date=date(2024, 1, 15),
            lines=[
                JournalEntryLineCreate(account_id=account_ids[0], debit=Decimal("100.00"), credit=Decimal("0.00")),
                JournalEntryLineCreate(account_id=account_ids[1], debit=Decimal("0.00"), credit=Decimal("100.00")),
            ],
        )
        entry = await JournalEntryService.create_entry(db_session, data, owner)
        await JournalEntryService.submit_for_approval(db_session, client_id, entry.id, owner)

        with pytest.raises(HTTPException) as exc_info:
            await JournalEntryService.approve_and_post(db_session, client_id, entry.id, associate)
        assert exc_info.value.status_code == 403

    async def test_associate_cannot_void(self, db_session: AsyncSession) -> None:
        """ASSOCIATE must not be able to void entries (403 at function level)."""
        from fastapi import HTTPException

        client_id, account_ids, user_id = await _setup_full_context(db_session)
        owner = CurrentUser(user_id=user_id, role="CPA_OWNER")
        associate = CurrentUser(user_id=user_id, role="ASSOCIATE")

        data = JournalEntryCreate(
            client_id=client_id,
            entry_date=date(2024, 1, 15),
            lines=[
                JournalEntryLineCreate(account_id=account_ids[0], debit=Decimal("100.00"), credit=Decimal("0.00")),
                JournalEntryLineCreate(account_id=account_ids[1], debit=Decimal("0.00"), credit=Decimal("100.00")),
            ],
        )
        entry = await JournalEntryService.create_entry(db_session, data, owner)
        await JournalEntryService.submit_for_approval(db_session, client_id, entry.id, owner)
        await JournalEntryService.approve_and_post(db_session, client_id, entry.id, owner)

        with pytest.raises(HTTPException) as exc_info:
            await JournalEntryService.void_entry(db_session, client_id, entry.id, associate)
        assert exc_info.value.status_code == 403

    async def test_cannot_submit_posted_entry(self, db_session: AsyncSession) -> None:
        """Cannot submit an already-posted entry for approval."""
        from fastapi import HTTPException

        client_id, account_ids, user_id = await _setup_full_context(db_session)
        user = CurrentUser(user_id=user_id, role="CPA_OWNER")

        data = JournalEntryCreate(
            client_id=client_id,
            entry_date=date(2024, 1, 15),
            lines=[
                JournalEntryLineCreate(account_id=account_ids[0], debit=Decimal("100.00"), credit=Decimal("0.00")),
                JournalEntryLineCreate(account_id=account_ids[1], debit=Decimal("0.00"), credit=Decimal("100.00")),
            ],
        )
        entry = await JournalEntryService.create_entry(db_session, data, user)
        await JournalEntryService.submit_for_approval(db_session, client_id, entry.id, user)
        await JournalEntryService.approve_and_post(db_session, client_id, entry.id, user)

        with pytest.raises(HTTPException) as exc_info:
            await JournalEntryService.submit_for_approval(db_session, client_id, entry.id, user)
        assert exc_info.value.status_code == 400

    async def test_cannot_void_draft_entry(self, db_session: AsyncSession) -> None:
        """Cannot void a DRAFT entry (must be POSTED first)."""
        from fastapi import HTTPException

        client_id, account_ids, user_id = await _setup_full_context(db_session)
        user = CurrentUser(user_id=user_id, role="CPA_OWNER")

        data = JournalEntryCreate(
            client_id=client_id,
            entry_date=date(2024, 1, 15),
            lines=[
                JournalEntryLineCreate(account_id=account_ids[0], debit=Decimal("100.00"), credit=Decimal("0.00")),
                JournalEntryLineCreate(account_id=account_ids[1], debit=Decimal("0.00"), credit=Decimal("100.00")),
            ],
        )
        entry = await JournalEntryService.create_entry(db_session, data, user)

        with pytest.raises(HTTPException) as exc_info:
            await JournalEntryService.void_entry(db_session, client_id, entry.id, user)
        assert exc_info.value.status_code == 400


class TestJournalEntryServiceClientIsolation:
    """
    CRITICAL COMPLIANCE TEST (rule #4):
    Client A entries must NEVER be visible when querying Client B.
    """

    async def test_get_entry_wrong_client_returns_none(self, db_session: AsyncSession) -> None:
        """get_entry returns None when queried with wrong client_id."""
        client_a, account_ids_a, user_id = await _setup_full_context(db_session)
        client_b = await _create_test_client(db_session)
        user = CurrentUser(user_id=user_id, role="CPA_OWNER")

        data = JournalEntryCreate(
            client_id=client_a,
            entry_date=date(2024, 1, 15),
            lines=[
                JournalEntryLineCreate(account_id=account_ids_a[0], debit=Decimal("100.00"), credit=Decimal("0.00")),
                JournalEntryLineCreate(account_id=account_ids_a[1], debit=Decimal("0.00"), credit=Decimal("100.00")),
            ],
        )
        entry = await JournalEntryService.create_entry(db_session, data, user)

        # Same client retrieves it
        found = await JournalEntryService.get_entry(db_session, client_a, entry.id)
        assert found is not None

        # Different client cannot see it
        not_found = await JournalEntryService.get_entry(db_session, client_b, entry.id)
        assert not_found is None

    async def test_list_entries_scoped_to_client(self, db_session: AsyncSession) -> None:
        """list_entries only returns entries belonging to the queried client."""
        client_a, account_ids_a, user_id = await _setup_full_context(db_session)
        client_b = await _create_test_client(db_session)
        account_ids_b = await _create_test_accounts(db_session, client_b, 2)
        user = CurrentUser(user_id=user_id, role="CPA_OWNER")

        # Create entries for both clients
        for cid, aids in [(client_a, account_ids_a), (client_b, account_ids_b)]:
            data = JournalEntryCreate(
                client_id=cid,
                entry_date=date(2024, 1, 15),
                lines=[
                    JournalEntryLineCreate(account_id=aids[0], debit=Decimal("100.00"), credit=Decimal("0.00")),
                    JournalEntryLineCreate(account_id=aids[1], debit=Decimal("0.00"), credit=Decimal("100.00")),
                ],
            )
            await JournalEntryService.create_entry(db_session, data, user)

        entries_a, total_a = await JournalEntryService.list_entries(db_session, client_a)
        entries_b, total_b = await JournalEntryService.list_entries(db_session, client_b)

        assert total_a == 1
        assert total_b == 1
        assert entries_a[0].client_id == client_a
        assert entries_b[0].client_id == client_b


class TestJournalEntryServiceTrialBalance:
    """Tests for trial balance (v_trial_balance view)."""

    async def test_trial_balance_only_posted_entries(self, db_session: AsyncSession) -> None:
        """Trial balance should only include posted entries, not draft/pending."""
        client_id, account_ids, user_id = await _setup_full_context(db_session)
        user = CurrentUser(user_id=user_id, role="CPA_OWNER")

        # Create and post one entry
        data1 = JournalEntryCreate(
            client_id=client_id,
            entry_date=date(2024, 1, 15),
            lines=[
                JournalEntryLineCreate(account_id=account_ids[0], debit=Decimal("500.00"), credit=Decimal("0.00")),
                JournalEntryLineCreate(account_id=account_ids[1], debit=Decimal("0.00"), credit=Decimal("500.00")),
            ],
        )
        entry1 = await JournalEntryService.create_entry(db_session, data1, user)
        await JournalEntryService.submit_for_approval(db_session, client_id, entry1.id, user)
        await JournalEntryService.approve_and_post(db_session, client_id, entry1.id, user)

        # Create a DRAFT entry (should NOT appear in trial balance)
        data2 = JournalEntryCreate(
            client_id=client_id,
            entry_date=date(2024, 2, 1),
            lines=[
                JournalEntryLineCreate(account_id=account_ids[0], debit=Decimal("999.00"), credit=Decimal("0.00")),
                JournalEntryLineCreate(account_id=account_ids[1], debit=Decimal("0.00"), credit=Decimal("999.00")),
            ],
        )
        await JournalEntryService.create_entry(db_session, data2, user)

        rows = await JournalEntryService.get_trial_balance(db_session, client_id)

        # Find the rows for our test accounts
        total_debits = sum(r.total_debits for r in rows)
        total_credits = sum(r.total_credits for r in rows)

        # Should only reflect the posted $500 entry, not the $999 draft
        assert total_debits == Decimal("500.00")
        assert total_credits == Decimal("500.00")

    async def test_trial_balance_client_isolation(self, db_session: AsyncSession) -> None:
        """Trial balance for Client A must not include Client B's data."""
        client_a, account_ids_a, user_id = await _setup_full_context(db_session)
        client_b = await _create_test_client(db_session)
        account_ids_b = await _create_test_accounts(db_session, client_b, 2)
        user = CurrentUser(user_id=user_id, role="CPA_OWNER")

        # Post entry for Client A
        data_a = JournalEntryCreate(
            client_id=client_a,
            entry_date=date(2024, 1, 15),
            lines=[
                JournalEntryLineCreate(account_id=account_ids_a[0], debit=Decimal("100.00"), credit=Decimal("0.00")),
                JournalEntryLineCreate(account_id=account_ids_a[1], debit=Decimal("0.00"), credit=Decimal("100.00")),
            ],
        )
        entry_a = await JournalEntryService.create_entry(db_session, data_a, user)
        await JournalEntryService.submit_for_approval(db_session, client_a, entry_a.id, user)
        await JournalEntryService.approve_and_post(db_session, client_a, entry_a.id, user)

        # Trial balance for Client B should show zero
        rows_b = await JournalEntryService.get_trial_balance(db_session, client_b)
        total_debits_b = sum(r.total_debits for r in rows_b)
        assert total_debits_b == Decimal("0")


# ---------------------------------------------------------------------------
# API endpoint tests (HTTP layer with real DB)
# ---------------------------------------------------------------------------


class TestJournalEntryAPI:
    """Tests for the /api/v1/clients/{client_id}/journal-entries endpoints."""

    async def _setup(self, db_session: AsyncSession) -> tuple[uuid.UUID, list[uuid.UUID]]:
        """Create test client, user, and accounts."""
        client_id, account_ids, _user_id = await _setup_full_context(db_session)
        return client_id, account_ids

    async def test_create_entry_cpa_owner(
        self, db_session: AsyncSession, db_client: AsyncClient, cpa_owner_headers: dict
    ) -> None:
        """CPA_OWNER can create a journal entry via POST."""
        client_id, account_ids = await self._setup(db_session)
        response = await db_client.post(
            f"/api/v1/clients/{client_id}/journal-entries",
            json={
                "client_id": str(client_id),
                "entry_date": "2024-01-15",
                "description": "Test entry",
                "reference_number": "JE-001",
                "lines": [
                    {"account_id": str(account_ids[0]), "debit": "100.00", "credit": "0.00"},
                    {"account_id": str(account_ids[1]), "debit": "0.00", "credit": "100.00"},
                ],
            },
            headers=cpa_owner_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "DRAFT"
        assert data["description"] == "Test entry"
        assert len(data["lines"]) == 2
        assert str(client_id) == data["client_id"]

    async def test_create_entry_associate(
        self, db_session: AsyncSession, db_client: AsyncClient, associate_headers: dict
    ) -> None:
        """ASSOCIATE can create a journal entry (status starts as DRAFT)."""
        # Need a user record for associate too
        from tests.conftest import ASSOCIATE_USER_ID
        await _create_test_user(db_session, ASSOCIATE_USER_ID)
        client_id, account_ids = await self._setup(db_session)

        response = await db_client.post(
            f"/api/v1/clients/{client_id}/journal-entries",
            json={
                "client_id": str(client_id),
                "entry_date": "2024-01-15",
                "description": "Associate entry",
                "lines": [
                    {"account_id": str(account_ids[0]), "debit": "50.00", "credit": "0.00"},
                    {"account_id": str(account_ids[1]), "debit": "0.00", "credit": "50.00"},
                ],
            },
            headers=associate_headers,
        )
        assert response.status_code == 201
        assert response.json()["status"] == "DRAFT"

    async def test_create_unbalanced_entry_fails(
        self, db_session: AsyncSession, db_client: AsyncClient, cpa_owner_headers: dict
    ) -> None:
        """Creating an unbalanced entry returns 422 (schema validation)."""
        client_id, account_ids = await self._setup(db_session)
        response = await db_client.post(
            f"/api/v1/clients/{client_id}/journal-entries",
            json={
                "client_id": str(client_id),
                "entry_date": "2024-01-15",
                "lines": [
                    {"account_id": str(account_ids[0]), "debit": "100.00", "credit": "0.00"},
                    {"account_id": str(account_ids[1]), "debit": "0.00", "credit": "50.00"},
                ],
            },
            headers=cpa_owner_headers,
        )
        assert response.status_code == 422

    async def test_create_single_line_fails(
        self, db_session: AsyncSession, db_client: AsyncClient, cpa_owner_headers: dict
    ) -> None:
        """Creating an entry with only one line returns 422."""
        client_id, account_ids = await self._setup(db_session)
        response = await db_client.post(
            f"/api/v1/clients/{client_id}/journal-entries",
            json={
                "client_id": str(client_id),
                "entry_date": "2024-01-15",
                "lines": [
                    {"account_id": str(account_ids[0]), "debit": "100.00", "credit": "0.00"},
                ],
            },
            headers=cpa_owner_headers,
        )
        assert response.status_code == 422

    async def test_list_entries(
        self, db_session: AsyncSession, db_client: AsyncClient, cpa_owner_headers: dict
    ) -> None:
        """List entries returns entries for the specified client."""
        client_id, account_ids = await self._setup(db_session)

        # Create an entry
        await db_client.post(
            f"/api/v1/clients/{client_id}/journal-entries",
            json={
                "client_id": str(client_id),
                "entry_date": "2024-01-15",
                "lines": [
                    {"account_id": str(account_ids[0]), "debit": "100.00", "credit": "0.00"},
                    {"account_id": str(account_ids[1]), "debit": "0.00", "credit": "100.00"},
                ],
            },
            headers=cpa_owner_headers,
        )

        response = await db_client.get(
            f"/api/v1/clients/{client_id}/journal-entries",
            headers=cpa_owner_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1

    async def test_get_entry(
        self, db_session: AsyncSession, db_client: AsyncClient, cpa_owner_headers: dict
    ) -> None:
        """Get a single entry by ID with its lines."""
        client_id, account_ids = await self._setup(db_session)
        create_resp = await db_client.post(
            f"/api/v1/clients/{client_id}/journal-entries",
            json={
                "client_id": str(client_id),
                "entry_date": "2024-01-15",
                "description": "Get test",
                "lines": [
                    {"account_id": str(account_ids[0]), "debit": "200.00", "credit": "0.00"},
                    {"account_id": str(account_ids[1]), "debit": "0.00", "credit": "200.00"},
                ],
            },
            headers=cpa_owner_headers,
        )
        entry_id = create_resp.json()["id"]

        response = await db_client.get(
            f"/api/v1/clients/{client_id}/journal-entries/{entry_id}",
            headers=cpa_owner_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == entry_id
        assert data["description"] == "Get test"
        assert len(data["lines"]) == 2

    async def test_submit_for_approval_via_api(
        self, db_session: AsyncSession, db_client: AsyncClient, cpa_owner_headers: dict
    ) -> None:
        """Submit endpoint changes status from DRAFT to PENDING_APPROVAL."""
        client_id, account_ids = await self._setup(db_session)
        create_resp = await db_client.post(
            f"/api/v1/clients/{client_id}/journal-entries",
            json={
                "client_id": str(client_id),
                "entry_date": "2024-01-15",
                "lines": [
                    {"account_id": str(account_ids[0]), "debit": "100.00", "credit": "0.00"},
                    {"account_id": str(account_ids[1]), "debit": "0.00", "credit": "100.00"},
                ],
            },
            headers=cpa_owner_headers,
        )
        entry_id = create_resp.json()["id"]

        response = await db_client.post(
            f"/api/v1/clients/{client_id}/journal-entries/{entry_id}/submit",
            headers=cpa_owner_headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "PENDING_APPROVAL"

    async def test_approve_via_api_cpa_owner(
        self, db_session: AsyncSession, db_client: AsyncClient, cpa_owner_headers: dict
    ) -> None:
        """CPA_OWNER can approve and post an entry via the approve endpoint."""
        client_id, account_ids = await self._setup(db_session)
        create_resp = await db_client.post(
            f"/api/v1/clients/{client_id}/journal-entries",
            json={
                "client_id": str(client_id),
                "entry_date": "2024-01-15",
                "lines": [
                    {"account_id": str(account_ids[0]), "debit": "100.00", "credit": "0.00"},
                    {"account_id": str(account_ids[1]), "debit": "0.00", "credit": "100.00"},
                ],
            },
            headers=cpa_owner_headers,
        )
        entry_id = create_resp.json()["id"]

        # Submit for approval
        await db_client.post(
            f"/api/v1/clients/{client_id}/journal-entries/{entry_id}/submit",
            headers=cpa_owner_headers,
        )

        # Approve
        response = await db_client.post(
            f"/api/v1/clients/{client_id}/journal-entries/{entry_id}/approve",
            headers=cpa_owner_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "POSTED"
        assert data["approved_by"] is not None
        assert data["posted_at"] is not None

    async def test_approve_via_api_associate_forbidden(
        self, db_session: AsyncSession, db_client: AsyncClient,
        cpa_owner_headers: dict, associate_headers: dict
    ) -> None:
        """ASSOCIATE cannot approve entries (403)."""
        client_id, account_ids = await self._setup(db_session)
        create_resp = await db_client.post(
            f"/api/v1/clients/{client_id}/journal-entries",
            json={
                "client_id": str(client_id),
                "entry_date": "2024-01-15",
                "lines": [
                    {"account_id": str(account_ids[0]), "debit": "100.00", "credit": "0.00"},
                    {"account_id": str(account_ids[1]), "debit": "0.00", "credit": "100.00"},
                ],
            },
            headers=cpa_owner_headers,
        )
        entry_id = create_resp.json()["id"]

        await db_client.post(
            f"/api/v1/clients/{client_id}/journal-entries/{entry_id}/submit",
            headers=cpa_owner_headers,
        )

        response = await db_client.post(
            f"/api/v1/clients/{client_id}/journal-entries/{entry_id}/approve",
            headers=associate_headers,
        )
        assert response.status_code == 403

    async def test_void_via_api_cpa_owner(
        self, db_session: AsyncSession, db_client: AsyncClient, cpa_owner_headers: dict
    ) -> None:
        """CPA_OWNER can void a posted entry via the void endpoint."""
        client_id, account_ids = await self._setup(db_session)
        create_resp = await db_client.post(
            f"/api/v1/clients/{client_id}/journal-entries",
            json={
                "client_id": str(client_id),
                "entry_date": "2024-01-15",
                "lines": [
                    {"account_id": str(account_ids[0]), "debit": "100.00", "credit": "0.00"},
                    {"account_id": str(account_ids[1]), "debit": "0.00", "credit": "100.00"},
                ],
            },
            headers=cpa_owner_headers,
        )
        entry_id = create_resp.json()["id"]

        await db_client.post(
            f"/api/v1/clients/{client_id}/journal-entries/{entry_id}/submit",
            headers=cpa_owner_headers,
        )
        await db_client.post(
            f"/api/v1/clients/{client_id}/journal-entries/{entry_id}/approve",
            headers=cpa_owner_headers,
        )

        response = await db_client.post(
            f"/api/v1/clients/{client_id}/journal-entries/{entry_id}/void",
            headers=cpa_owner_headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "VOID"

    async def test_void_via_api_associate_forbidden(
        self, db_session: AsyncSession, db_client: AsyncClient,
        cpa_owner_headers: dict, associate_headers: dict
    ) -> None:
        """ASSOCIATE cannot void entries (403)."""
        client_id, account_ids = await self._setup(db_session)
        create_resp = await db_client.post(
            f"/api/v1/clients/{client_id}/journal-entries",
            json={
                "client_id": str(client_id),
                "entry_date": "2024-01-15",
                "lines": [
                    {"account_id": str(account_ids[0]), "debit": "100.00", "credit": "0.00"},
                    {"account_id": str(account_ids[1]), "debit": "0.00", "credit": "100.00"},
                ],
            },
            headers=cpa_owner_headers,
        )
        entry_id = create_resp.json()["id"]

        await db_client.post(
            f"/api/v1/clients/{client_id}/journal-entries/{entry_id}/submit",
            headers=cpa_owner_headers,
        )
        await db_client.post(
            f"/api/v1/clients/{client_id}/journal-entries/{entry_id}/approve",
            headers=cpa_owner_headers,
        )

        response = await db_client.post(
            f"/api/v1/clients/{client_id}/journal-entries/{entry_id}/void",
            headers=associate_headers,
        )
        assert response.status_code == 403

    async def test_client_isolation_via_api(
        self, db_session: AsyncSession, db_client: AsyncClient, cpa_owner_headers: dict
    ) -> None:
        """
        CRITICAL COMPLIANCE TEST (rule #4):
        Client A's journal entries must NEVER be visible via Client B's URL.
        """
        client_a, account_ids_a = await self._setup(db_session)
        client_b = await _create_test_client(db_session)

        # Create entry for Client A
        create_resp = await db_client.post(
            f"/api/v1/clients/{client_a}/journal-entries",
            json={
                "client_id": str(client_a),
                "entry_date": "2024-01-15",
                "lines": [
                    {"account_id": str(account_ids_a[0]), "debit": "100.00", "credit": "0.00"},
                    {"account_id": str(account_ids_a[1]), "debit": "0.00", "credit": "100.00"},
                ],
            },
            headers=cpa_owner_headers,
        )
        entry_a_id = create_resp.json()["id"]

        # List Client B's entries -- should be empty
        list_resp = await db_client.get(
            f"/api/v1/clients/{client_b}/journal-entries",
            headers=cpa_owner_headers,
        )
        assert list_resp.json()["total"] == 0

        # Try to get Client A's entry using Client B's URL
        get_resp = await db_client.get(
            f"/api/v1/clients/{client_b}/journal-entries/{entry_a_id}",
            headers=cpa_owner_headers,
        )
        assert get_resp.status_code == 404

    async def test_get_nonexistent_entry_returns_404(
        self, db_session: AsyncSession, db_client: AsyncClient, cpa_owner_headers: dict
    ) -> None:
        """Getting a non-existent entry returns 404."""
        client_id, _ = await self._setup(db_session)
        fake_id = uuid.uuid4()
        resp = await db_client.get(
            f"/api/v1/clients/{client_id}/journal-entries/{fake_id}",
            headers=cpa_owner_headers,
        )
        assert resp.status_code == 404

    async def test_trial_balance_via_api(
        self, db_session: AsyncSession, db_client: AsyncClient, cpa_owner_headers: dict
    ) -> None:
        """Trial balance endpoint returns correct data for posted entries only."""
        client_id, account_ids = await self._setup(db_session)

        # Create and post an entry
        create_resp = await db_client.post(
            f"/api/v1/clients/{client_id}/journal-entries",
            json={
                "client_id": str(client_id),
                "entry_date": "2024-01-15",
                "lines": [
                    {"account_id": str(account_ids[0]), "debit": "750.00", "credit": "0.00"},
                    {"account_id": str(account_ids[1]), "debit": "0.00", "credit": "750.00"},
                ],
            },
            headers=cpa_owner_headers,
        )
        entry_id = create_resp.json()["id"]

        await db_client.post(
            f"/api/v1/clients/{client_id}/journal-entries/{entry_id}/submit",
            headers=cpa_owner_headers,
        )
        await db_client.post(
            f"/api/v1/clients/{client_id}/journal-entries/{entry_id}/approve",
            headers=cpa_owner_headers,
        )

        # Get trial balance
        tb_resp = await db_client.get(
            f"/api/v1/clients/{client_id}/trial-balance",
            headers=cpa_owner_headers,
        )
        assert tb_resp.status_code == 200
        data = tb_resp.json()
        assert Decimal(data["total_debits"]) == Decimal("750.00")
        assert Decimal(data["total_credits"]) == Decimal("750.00")

    async def test_large_value_via_api(
        self, db_session: AsyncSession, db_client: AsyncClient, cpa_owner_headers: dict
    ) -> None:
        """Large realistic value for a GA small business ($10M) works correctly."""
        client_id, account_ids = await self._setup(db_session)
        response = await db_client.post(
            f"/api/v1/clients/{client_id}/journal-entries",
            json={
                "client_id": str(client_id),
                "entry_date": "2024-12-31",
                "description": "Large transaction",
                "lines": [
                    {"account_id": str(account_ids[0]), "debit": "10000000.00", "credit": "0.00"},
                    {"account_id": str(account_ids[1]), "debit": "0.00", "credit": "10000000.00"},
                ],
            },
            headers=cpa_owner_headers,
        )
        assert response.status_code == 201
        data = response.json()
        lines = data["lines"]
        debit_line = [l for l in lines if Decimal(l["debit"]) > 0][0]
        assert Decimal(debit_line["debit"]) == Decimal("10000000.00")

    async def test_unauthenticated_request_rejected(
        self, db_session: AsyncSession, db_client: AsyncClient
    ) -> None:
        """Requests without auth token are rejected (401 or 403)."""
        client_id, _ = await self._setup(db_session)
        resp = await db_client.get(f"/api/v1/clients/{client_id}/journal-entries")
        assert resp.status_code in (401, 403)

    async def test_list_entries_with_status_filter(
        self, db_session: AsyncSession, db_client: AsyncClient, cpa_owner_headers: dict
    ) -> None:
        """List entries supports status filter."""
        client_id, account_ids = await self._setup(db_session)

        # Create two entries
        for desc in ["Entry 1", "Entry 2"]:
            await db_client.post(
                f"/api/v1/clients/{client_id}/journal-entries",
                json={
                    "client_id": str(client_id),
                    "entry_date": "2024-01-15",
                    "description": desc,
                    "lines": [
                        {"account_id": str(account_ids[0]), "debit": "100.00", "credit": "0.00"},
                        {"account_id": str(account_ids[1]), "debit": "0.00", "credit": "100.00"},
                    ],
                },
                headers=cpa_owner_headers,
            )

        # Submit one for approval
        list_resp = await db_client.get(
            f"/api/v1/clients/{client_id}/journal-entries",
            headers=cpa_owner_headers,
        )
        first_entry_id = list_resp.json()["items"][0]["id"]
        await db_client.post(
            f"/api/v1/clients/{client_id}/journal-entries/{first_entry_id}/submit",
            headers=cpa_owner_headers,
        )

        # Filter by DRAFT — should return 1
        draft_resp = await db_client.get(
            f"/api/v1/clients/{client_id}/journal-entries?status=DRAFT",
            headers=cpa_owner_headers,
        )
        assert draft_resp.json()["total"] == 1

        # Filter by PENDING_APPROVAL — should return 1
        pending_resp = await db_client.get(
            f"/api/v1/clients/{client_id}/journal-entries?status=PENDING_APPROVAL",
            headers=cpa_owner_headers,
        )
        assert pending_resp.json()["total"] == 1
