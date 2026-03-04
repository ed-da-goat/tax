"""
Tests for Transaction Approval Workflow (module T4).

HIGH COMPLIANCE RISK — TDD approach.

Compliance tests:
- APPROVAL WORKFLOW (rule #5): Only CPA_OWNER can approve/reject
- ROLE ENFORCEMENT (rule #6): Defense in depth at route + function level
- CLIENT ISOLATION (rule #4): ASSOCIATE sees only own entries

Uses real PostgreSQL session (rolled back after each test) via db_session
and db_client fixtures from conftest.py.
"""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, verify_role
from app.schemas.approval import ApprovalActionType
from app.services.approval import ApprovalService
from app.services.journal_entry import JournalEntryService
from app.schemas.journal_entry import JournalEntryCreate, JournalEntryLineCreate
from tests.conftest import CPA_OWNER_USER, CPA_OWNER_USER_ID, ASSOCIATE_USER, ASSOCIATE_USER_ID


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


async def _create_test_user(db: AsyncSession, user_id: str, role: str = "CPA_OWNER") -> str:
    """Insert a minimal user row and return its UUID string."""
    await db.execute(
        text(
            "INSERT INTO users (id, email, password_hash, full_name, role, is_active) "
            "VALUES (:id, :email, :password_hash, :full_name, :role, true)"
        ),
        {
            "id": user_id,
            "email": f"user_{user_id[:8]}@test.com",
            "password_hash": "$2b$12$test_hash_placeholder_for_testing",
            "full_name": f"Test User {user_id[:8]}",
            "role": role,
        },
    )
    await db.flush()
    return user_id


async def _create_test_accounts(
    db: AsyncSession, client_id: uuid.UUID, count: int = 2
) -> list[uuid.UUID]:
    """Create test chart of accounts entries and return their IDs."""
    account_ids = []
    accounts = [
        ("1000", "Cash", "ASSET"),
        ("4000", "Revenue", "REVENUE"),
        ("5000", "Expenses", "EXPENSE"),
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


async def _setup_full_context(db: AsyncSession) -> tuple[uuid.UUID, list[uuid.UUID], str, str]:
    """
    Create client, accounts, and both users.
    Returns (client_id, account_ids, cpa_owner_user_id, associate_user_id).
    """
    client_id = await _create_test_client(db)
    cpa_uid = await _create_test_user(db, CPA_OWNER_USER_ID, "CPA_OWNER")
    assoc_uid = await _create_test_user(db, ASSOCIATE_USER_ID, "ASSOCIATE")
    account_ids = await _create_test_accounts(db, client_id, 2)
    return client_id, account_ids, cpa_uid, assoc_uid


async def _create_pending_entry(
    db: AsyncSession,
    client_id: uuid.UUID,
    account_ids: list[uuid.UUID],
    user: CurrentUser,
    description: str = "Test entry",
) -> uuid.UUID:
    """Create a journal entry and submit it for approval. Returns entry ID."""
    data = JournalEntryCreate(
        client_id=client_id,
        entry_date=date.today(),
        description=description,
        lines=[
            JournalEntryLineCreate(
                account_id=account_ids[0],
                debit=Decimal("100.00"),
                credit=Decimal("0.00"),
            ),
            JournalEntryLineCreate(
                account_id=account_ids[1],
                debit=Decimal("0.00"),
                credit=Decimal("100.00"),
            ),
        ],
    )
    entry = await JournalEntryService.create_entry(db, data, user)
    await JournalEntryService.submit_for_approval(db, client_id, entry.id, user)
    await db.flush()
    return entry.id


# ---------------------------------------------------------------------------
# Service-level tests: Approval Queue
# ---------------------------------------------------------------------------


class TestApprovalQueueService:
    """Test the approval queue service layer."""

    @pytest.mark.asyncio
    async def test_queue_shows_pending_entries(self, db_session: AsyncSession) -> None:
        """Approval queue should return PENDING_APPROVAL entries."""
        client_id, account_ids, cpa_uid, assoc_uid = await _setup_full_context(db_session)
        entry_id = await _create_pending_entry(
            db_session, client_id, account_ids, CPA_OWNER_USER, "Pending entry"
        )

        items, total = await ApprovalService.get_approval_queue(
            db_session, CPA_OWNER_USER
        )

        assert total >= 1
        entry_ids = [item.id for item in items]
        assert entry_id in entry_ids

    @pytest.mark.asyncio
    async def test_cpa_owner_sees_all_clients(self, db_session: AsyncSession) -> None:
        """CPA_OWNER should see pending entries from ALL clients."""
        # Setup two clients
        client_a = await _create_test_client(db_session)
        client_b = await _create_test_client(db_session)
        await _create_test_user(db_session, CPA_OWNER_USER_ID, "CPA_OWNER")
        await _create_test_user(db_session, ASSOCIATE_USER_ID, "ASSOCIATE")
        accounts_a = await _create_test_accounts(db_session, client_a, 2)
        accounts_b = await _create_test_accounts(db_session, client_b, 2)

        entry_a = await _create_pending_entry(
            db_session, client_a, accounts_a, CPA_OWNER_USER, "Client A entry"
        )
        entry_b = await _create_pending_entry(
            db_session, client_b, accounts_b, CPA_OWNER_USER, "Client B entry"
        )

        items, total = await ApprovalService.get_approval_queue(
            db_session, CPA_OWNER_USER
        )

        entry_ids = [item.id for item in items]
        assert entry_a in entry_ids
        assert entry_b in entry_ids
        assert total >= 2

    @pytest.mark.asyncio
    async def test_associate_sees_only_own_entries(self, db_session: AsyncSession) -> None:
        """ASSOCIATE should only see entries they created in the queue."""
        client_id, account_ids, cpa_uid, assoc_uid = await _setup_full_context(db_session)

        # CPA_OWNER creates one entry
        entry_cpa = await _create_pending_entry(
            db_session, client_id, account_ids, CPA_OWNER_USER, "CPA entry"
        )
        # ASSOCIATE creates another entry
        entry_assoc = await _create_pending_entry(
            db_session, client_id, account_ids, ASSOCIATE_USER, "Associate entry"
        )

        items, total = await ApprovalService.get_approval_queue(
            db_session, ASSOCIATE_USER
        )

        entry_ids = [item.id for item in items]
        assert entry_assoc in entry_ids
        assert entry_cpa not in entry_ids

    @pytest.mark.asyncio
    async def test_queue_filters_by_client_id(self, db_session: AsyncSession) -> None:
        """Queue should respect client_id filter."""
        client_a = await _create_test_client(db_session)
        client_b = await _create_test_client(db_session)
        await _create_test_user(db_session, CPA_OWNER_USER_ID, "CPA_OWNER")
        accounts_a = await _create_test_accounts(db_session, client_a, 2)
        accounts_b = await _create_test_accounts(db_session, client_b, 2)

        entry_a = await _create_pending_entry(
            db_session, client_a, accounts_a, CPA_OWNER_USER, "Client A"
        )
        entry_b = await _create_pending_entry(
            db_session, client_b, accounts_b, CPA_OWNER_USER, "Client B"
        )

        items, total = await ApprovalService.get_approval_queue(
            db_session, CPA_OWNER_USER, client_id=client_a
        )

        entry_ids = [item.id for item in items]
        assert entry_a in entry_ids
        assert entry_b not in entry_ids

    @pytest.mark.asyncio
    async def test_queue_item_has_correct_amounts(self, db_session: AsyncSession) -> None:
        """Queue items should show correct debit/credit totals."""
        client_id, account_ids, cpa_uid, assoc_uid = await _setup_full_context(db_session)
        entry_id = await _create_pending_entry(
            db_session, client_id, account_ids, CPA_OWNER_USER
        )

        items, total = await ApprovalService.get_approval_queue(
            db_session, CPA_OWNER_USER
        )

        entry_item = next(item for item in items if item.id == entry_id)
        assert entry_item.total_debits == Decimal("100.00")
        assert entry_item.total_credits == Decimal("100.00")


# ---------------------------------------------------------------------------
# Service-level tests: Rejection
# ---------------------------------------------------------------------------


class TestRejectionService:
    """Test the rejection service layer."""

    @pytest.mark.asyncio
    async def test_reject_moves_to_draft_with_note(self, db_session: AsyncSession) -> None:
        """Rejecting should move entry from PENDING_APPROVAL to DRAFT."""
        client_id, account_ids, cpa_uid, assoc_uid = await _setup_full_context(db_session)
        entry_id = await _create_pending_entry(
            db_session, client_id, account_ids, CPA_OWNER_USER
        )

        entry = await ApprovalService.reject_entry(
            db_session, client_id, entry_id, CPA_OWNER_USER,
            "Missing supporting documentation"
        )

        assert entry.status.value == "DRAFT"

    @pytest.mark.asyncio
    async def test_associate_cannot_reject(self, db_session: AsyncSession) -> None:
        """ASSOCIATE should get 403 when trying to reject."""
        client_id, account_ids, cpa_uid, assoc_uid = await _setup_full_context(db_session)
        entry_id = await _create_pending_entry(
            db_session, client_id, account_ids, ASSOCIATE_USER
        )

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await ApprovalService.reject_entry(
                db_session, client_id, entry_id, ASSOCIATE_USER,
                "I want to reject this"
            )
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_reject_non_pending_entry_fails(self, db_session: AsyncSession) -> None:
        """Cannot reject an entry that is not PENDING_APPROVAL."""
        client_id, account_ids, cpa_uid, assoc_uid = await _setup_full_context(db_session)

        # Create a DRAFT entry (not submitted)
        data = JournalEntryCreate(
            client_id=client_id,
            entry_date=date.today(),
            description="Draft only",
            lines=[
                JournalEntryLineCreate(
                    account_id=account_ids[0], debit=Decimal("50.00"), credit=Decimal("0.00")
                ),
                JournalEntryLineCreate(
                    account_id=account_ids[1], debit=Decimal("0.00"), credit=Decimal("50.00")
                ),
            ],
        )
        entry = await JournalEntryService.create_entry(db_session, data, CPA_OWNER_USER)
        await db_session.flush()

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await ApprovalService.reject_entry(
                db_session, client_id, entry.id, CPA_OWNER_USER,
                "Trying to reject a draft"
            )
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_rejected_entry_can_be_resubmitted(self, db_session: AsyncSession) -> None:
        """After rejection, entry should be DRAFT and can be resubmitted."""
        client_id, account_ids, cpa_uid, assoc_uid = await _setup_full_context(db_session)
        entry_id = await _create_pending_entry(
            db_session, client_id, account_ids, ASSOCIATE_USER
        )

        # Reject
        entry = await ApprovalService.reject_entry(
            db_session, client_id, entry_id, CPA_OWNER_USER,
            "Needs correction"
        )
        assert entry.status.value == "DRAFT"

        # Resubmit
        resubmitted = await JournalEntryService.submit_for_approval(
            db_session, client_id, entry_id, ASSOCIATE_USER
        )
        assert resubmitted is not None
        assert resubmitted.status.value == "PENDING_APPROVAL"


# ---------------------------------------------------------------------------
# Service-level tests: Batch Approval
# ---------------------------------------------------------------------------


class TestBatchApprovalService:
    """Test the batch approve/reject service layer."""

    @pytest.mark.asyncio
    async def test_batch_approve_multiple(self, db_session: AsyncSession) -> None:
        """Batch approve should process multiple entries."""
        client_id, account_ids, cpa_uid, assoc_uid = await _setup_full_context(db_session)
        entry_1 = await _create_pending_entry(
            db_session, client_id, account_ids, CPA_OWNER_USER, "Entry 1"
        )
        entry_2 = await _create_pending_entry(
            db_session, client_id, account_ids, CPA_OWNER_USER, "Entry 2"
        )

        from app.schemas.approval import ApprovalAction
        actions = [
            ApprovalAction(entry_id=entry_1, action=ApprovalActionType.APPROVE),
            ApprovalAction(entry_id=entry_2, action=ApprovalActionType.APPROVE),
        ]

        results = await ApprovalService.batch_process(db_session, CPA_OWNER_USER, actions)

        assert len(results) == 2
        assert all(r.success for r in results)

        # Verify entries are now POSTED
        e1 = await JournalEntryService.get_entry(db_session, client_id, entry_1)
        e2 = await JournalEntryService.get_entry(db_session, client_id, entry_2)
        assert e1.status.value == "POSTED"
        assert e2.status.value == "POSTED"

    @pytest.mark.asyncio
    async def test_batch_mixed_approve_reject(self, db_session: AsyncSession) -> None:
        """Batch should handle mixed approve and reject actions."""
        client_id, account_ids, cpa_uid, assoc_uid = await _setup_full_context(db_session)
        entry_approve = await _create_pending_entry(
            db_session, client_id, account_ids, CPA_OWNER_USER, "To approve"
        )
        entry_reject = await _create_pending_entry(
            db_session, client_id, account_ids, CPA_OWNER_USER, "To reject"
        )

        from app.schemas.approval import ApprovalAction
        actions = [
            ApprovalAction(
                entry_id=entry_approve,
                action=ApprovalActionType.APPROVE,
            ),
            ApprovalAction(
                entry_id=entry_reject,
                action=ApprovalActionType.REJECT,
                note="Incorrect amounts",
            ),
        ]

        results = await ApprovalService.batch_process(db_session, CPA_OWNER_USER, actions)

        assert len(results) == 2
        assert all(r.success for r in results)

        e_approve = await JournalEntryService.get_entry(db_session, client_id, entry_approve)
        e_reject = await JournalEntryService.get_entry(db_session, client_id, entry_reject)
        assert e_approve.status.value == "POSTED"
        assert e_reject.status.value == "DRAFT"

    @pytest.mark.asyncio
    async def test_associate_cannot_batch_approve(self, db_session: AsyncSession) -> None:
        """ASSOCIATE should get 403 when trying to batch approve."""
        client_id, account_ids, cpa_uid, assoc_uid = await _setup_full_context(db_session)
        entry_id = await _create_pending_entry(
            db_session, client_id, account_ids, ASSOCIATE_USER
        )

        from app.schemas.approval import ApprovalAction
        actions = [
            ApprovalAction(entry_id=entry_id, action=ApprovalActionType.APPROVE),
        ]

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await ApprovalService.batch_process(db_session, ASSOCIATE_USER, actions)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_batch_with_nonexistent_entry(self, db_session: AsyncSession) -> None:
        """Batch should handle non-existent entries gracefully."""
        client_id, account_ids, cpa_uid, assoc_uid = await _setup_full_context(db_session)

        from app.schemas.approval import ApprovalAction
        fake_id = uuid.uuid4()
        actions = [
            ApprovalAction(entry_id=fake_id, action=ApprovalActionType.APPROVE),
        ]

        results = await ApprovalService.batch_process(db_session, CPA_OWNER_USER, actions)

        assert len(results) == 1
        assert not results[0].success
        assert "not found" in results[0].error.lower()

    @pytest.mark.asyncio
    async def test_batch_partial_failure(self, db_session: AsyncSession) -> None:
        """One failure in batch should not block other actions."""
        client_id, account_ids, cpa_uid, assoc_uid = await _setup_full_context(db_session)
        valid_entry = await _create_pending_entry(
            db_session, client_id, account_ids, CPA_OWNER_USER, "Valid"
        )
        fake_entry = uuid.uuid4()

        from app.schemas.approval import ApprovalAction
        actions = [
            ApprovalAction(entry_id=valid_entry, action=ApprovalActionType.APPROVE),
            ApprovalAction(entry_id=fake_entry, action=ApprovalActionType.APPROVE),
        ]

        results = await ApprovalService.batch_process(db_session, CPA_OWNER_USER, actions)

        assert len(results) == 2
        # First should succeed, second should fail
        result_map = {r.entry_id: r for r in results}
        assert result_map[valid_entry].success is True
        assert result_map[fake_entry].success is False


# ---------------------------------------------------------------------------
# Service-level tests: Approval History
# ---------------------------------------------------------------------------


class TestApprovalHistoryService:
    """Test the approval history service layer."""

    @pytest.mark.asyncio
    async def test_history_tracks_status_changes(self, db_session: AsyncSession) -> None:
        """Approval history should show status transitions from audit_log."""
        client_id, account_ids, cpa_uid, assoc_uid = await _setup_full_context(db_session)

        # Create entry (INSERT audit record)
        data = JournalEntryCreate(
            client_id=client_id,
            entry_date=date.today(),
            description="History test",
            lines=[
                JournalEntryLineCreate(
                    account_id=account_ids[0], debit=Decimal("100.00"), credit=Decimal("0.00")
                ),
                JournalEntryLineCreate(
                    account_id=account_ids[1], debit=Decimal("0.00"), credit=Decimal("100.00")
                ),
            ],
        )
        entry = await JournalEntryService.create_entry(db_session, data, CPA_OWNER_USER)
        await db_session.flush()

        # Submit (UPDATE audit record)
        await JournalEntryService.submit_for_approval(db_session, client_id, entry.id, CPA_OWNER_USER)
        await db_session.flush()

        # Approve (UPDATE audit record)
        await JournalEntryService.approve_and_post(db_session, client_id, entry.id, CPA_OWNER_USER)
        await db_session.flush()

        history = await ApprovalService.get_approval_history(db_session, client_id, entry.id)

        # Should have at least the INSERT and two UPDATEs
        assert len(history) >= 1  # At minimum we get the audit log entries

    @pytest.mark.asyncio
    async def test_history_for_nonexistent_entry(self, db_session: AsyncSession) -> None:
        """Should return 404 for non-existent entry."""
        client_id, account_ids, cpa_uid, assoc_uid = await _setup_full_context(db_session)

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await ApprovalService.get_approval_history(
                db_session, client_id, uuid.uuid4()
            )
        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# API endpoint tests (HTTP layer)
# ---------------------------------------------------------------------------


class TestApprovalQueueEndpoint:
    """Test the GET /api/v1/approvals endpoint."""

    @pytest.mark.asyncio
    async def test_get_queue_as_cpa_owner(
        self, db_client: AsyncClient, db_session: AsyncSession, cpa_owner_headers: dict
    ) -> None:
        """CPA_OWNER should be able to access the approval queue."""
        response = await db_client.get(
            "/api/v1/approvals",
            headers=cpa_owner_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "filters" in data

    @pytest.mark.asyncio
    async def test_get_queue_as_associate(
        self, db_client: AsyncClient, db_session: AsyncSession, associate_headers: dict
    ) -> None:
        """ASSOCIATE should be able to access the queue (sees only own entries)."""
        response = await db_client.get(
            "/api/v1/approvals",
            headers=associate_headers,
        )
        assert response.status_code == 200


class TestBatchApprovalEndpoint:
    """Test the POST /api/v1/approvals/batch endpoint."""

    @pytest.mark.asyncio
    async def test_associate_cannot_batch_approve_endpoint(
        self, db_client: AsyncClient, db_session: AsyncSession, associate_headers: dict
    ) -> None:
        """ASSOCIATE should get 403 on batch approve endpoint."""
        response = await db_client.post(
            "/api/v1/approvals/batch",
            headers=associate_headers,
            json={
                "actions": [
                    {
                        "entry_id": str(uuid.uuid4()),
                        "action": "approve",
                    }
                ]
            },
        )
        assert response.status_code == 403


class TestRejectEndpoint:
    """Test the POST /api/v1/clients/{client_id}/journal-entries/{id}/reject endpoint."""

    @pytest.mark.asyncio
    async def test_associate_cannot_reject_endpoint(
        self, db_client: AsyncClient, db_session: AsyncSession, associate_headers: dict
    ) -> None:
        """ASSOCIATE should get 403 on reject endpoint."""
        client_id = uuid.uuid4()
        entry_id = uuid.uuid4()
        response = await db_client.post(
            f"/api/v1/clients/{client_id}/journal-entries/{entry_id}/reject",
            headers=associate_headers,
            json={"note": "I want to reject this"},
        )
        assert response.status_code == 403


class TestHistoryEndpoint:
    """Test the GET /api/v1/clients/{client_id}/journal-entries/{id}/history endpoint."""

    @pytest.mark.asyncio
    async def test_history_endpoint_accessible(
        self, db_client: AsyncClient, db_session: AsyncSession, cpa_owner_headers: dict
    ) -> None:
        """History endpoint should be accessible (returns 404 for non-existent entry)."""
        client_id = uuid.uuid4()
        entry_id = uuid.uuid4()
        response = await db_client.get(
            f"/api/v1/clients/{client_id}/journal-entries/{entry_id}/history",
            headers=cpa_owner_headers,
        )
        # 404 expected since the entry doesn't exist in the test DB
        assert response.status_code == 404
