"""
Tests for Bill / Accounts Payable (module T1).

Compliance tests:
- DOUBLE-ENTRY (rule #1): Approval creates balanced journal entry
- AUDIT TRAIL (rule #2): Soft deletes / void pattern
- CLIENT ISOLATION (rule #4): Bill queries scoped by client_id
- APPROVAL WORKFLOW (rule #5): DRAFT -> PENDING_APPROVAL -> APPROVED -> PAID
- ROLE ENFORCEMENT (rule #6): ASSOCIATE cannot approve or void

Uses real PostgreSQL session (rolled back after each test) via db_session fixture.
"""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser
from app.models.bill import BillStatus
from app.schemas.bill import BillCreate, BillLineCreate, BillPaymentCreate
from app.services.bill import BillService
from tests.conftest import CPA_OWNER_USER, CPA_OWNER_USER_ID, ASSOCIATE_USER


# ---------------------------------------------------------------------------
# Helpers
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
    db: AsyncSession, client_id: uuid.UUID, count: int = 3
) -> list[uuid.UUID]:
    """Create test chart of accounts entries and return their IDs.

    Returns [expense_account_id, ap_account_id, expense2_account_id, ...]
    Account 2000 is the AP liability account used by BillService.approve_bill.
    """
    account_ids = []
    accounts = [
        ("5000", "Office Expenses", "EXPENSE"),
        ("2000", "Accounts Payable", "LIABILITY"),
        ("5100", "Rent Expense", "EXPENSE"),
        ("1000", "Cash", "ASSET"),
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


async def _create_test_vendor(db: AsyncSession, client_id: uuid.UUID) -> uuid.UUID:
    """Insert a minimal vendor row and return its UUID."""
    vid = uuid.uuid4()
    await db.execute(
        text(
            "INSERT INTO vendors (id, client_id, name) "
            "VALUES (:id, :client_id, :name)"
        ),
        {"id": str(vid), "client_id": str(client_id), "name": f"Test Vendor {vid}"},
    )
    await db.flush()
    return vid


async def _setup_full_context(db: AsyncSession) -> tuple[uuid.UUID, list[uuid.UUID], str, uuid.UUID]:
    """Create client, accounts (expense + AP + expense2), user, and vendor.

    Returns (client_id, account_ids, user_id, vendor_id).
    """
    client_id = await _create_test_client(db)
    user_id = await _create_test_user(db, CPA_OWNER_USER_ID)
    account_ids = await _create_test_accounts(db, client_id, 4)
    vendor_id = await _create_test_vendor(db, client_id)
    return client_id, account_ids, user_id, vendor_id


def _make_bill_data(
    account_id: uuid.UUID,
    vendor_id: uuid.UUID,
    amount: Decimal = Decimal("500.00"),
) -> BillCreate:
    """Create a simple BillCreate with one line."""
    return BillCreate(
        vendor_id=vendor_id,
        bill_number="INV-001",
        bill_date=date(2024, 6, 1),
        due_date=date(2024, 7, 1),
        lines=[
            BillLineCreate(
                account_id=account_id,
                description="Office supplies",
                amount=amount,
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Schema validation tests
# ---------------------------------------------------------------------------


class TestBillSchemaValidation:
    """Test Pydantic schema validation for bill creation."""

    def test_valid_bill_create(self) -> None:
        """A valid BillCreate passes validation."""
        data = BillCreate(
            vendor_id=uuid.uuid4(),
            bill_date=date(2024, 6, 1),
            due_date=date(2024, 7, 1),
            lines=[
                BillLineCreate(account_id=uuid.uuid4(), description="test", amount=Decimal("100.00")),
            ],
        )
        assert len(data.lines) == 1

    def test_bill_requires_at_least_one_line(self) -> None:
        """BillCreate must have at least one line item."""
        with pytest.raises(ValidationError, match="too_short"):
            BillCreate(
                vendor_id=uuid.uuid4(),
                bill_date=date(2024, 6, 1),
                due_date=date(2024, 7, 1),
                lines=[],
            )

    def test_bill_line_amount_must_be_positive(self) -> None:
        """Bill line amount must be > 0."""
        with pytest.raises(ValidationError, match="greater_than"):
            BillLineCreate(account_id=uuid.uuid4(), amount=Decimal("0.00"))

    def test_due_date_not_before_bill_date(self) -> None:
        """due_date cannot be before bill_date."""
        with pytest.raises(ValidationError, match="due_date"):
            BillCreate(
                vendor_id=uuid.uuid4(),
                bill_date=date(2024, 7, 1),
                due_date=date(2024, 6, 1),
                lines=[
                    BillLineCreate(account_id=uuid.uuid4(), amount=Decimal("100.00")),
                ],
            )


# ---------------------------------------------------------------------------
# Bill CRUD tests
# ---------------------------------------------------------------------------


class TestBillCRUD:
    """Test bill creation, retrieval, and listing."""

    @pytest.mark.asyncio
    async def test_create_bill(self, db_session: AsyncSession) -> None:
        """Create a bill with lines; status starts as DRAFT."""
        client_id, account_ids, _, vendor_id = await _setup_full_context(db_session)
        expense_id = account_ids[0]

        data = _make_bill_data(expense_id, vendor_id)
        bill = await BillService.create_bill(db_session, client_id, data, CPA_OWNER_USER)

        assert bill.id is not None
        assert bill.client_id == client_id
        assert bill.status == BillStatus.DRAFT
        assert bill.total_amount == Decimal("500.00")
        assert len(bill.lines) == 1
        assert bill.lines[0].amount == Decimal("500.00")

    @pytest.mark.asyncio
    async def test_create_bill_multi_line(self, db_session: AsyncSession) -> None:
        """Create a bill with multiple lines; total_amount is the sum."""
        client_id, account_ids, _, vendor_id = await _setup_full_context(db_session)

        data = BillCreate(
            vendor_id=vendor_id,
            bill_number="MULTI-001",
            bill_date=date(2024, 6, 1),
            due_date=date(2024, 7, 1),
            lines=[
                BillLineCreate(account_id=account_ids[0], amount=Decimal("200.00")),
                BillLineCreate(account_id=account_ids[2], amount=Decimal("300.00")),
            ],
        )
        bill = await BillService.create_bill(db_session, client_id, data, CPA_OWNER_USER)
        assert bill.total_amount == Decimal("500.00")
        assert len(bill.lines) == 2

    @pytest.mark.asyncio
    async def test_get_bill(self, db_session: AsyncSession) -> None:
        """Retrieve a bill by ID."""
        client_id, account_ids, _, vendor_id = await _setup_full_context(db_session)
        data = _make_bill_data(account_ids[0], vendor_id)
        bill = await BillService.create_bill(db_session, client_id, data, CPA_OWNER_USER)

        fetched = await BillService.get_bill(db_session, client_id, bill.id)
        assert fetched is not None
        assert fetched.id == bill.id

    @pytest.mark.asyncio
    async def test_get_bill_not_found(self, db_session: AsyncSession) -> None:
        """get_bill returns None for non-existent bill."""
        client_id = await _create_test_client(db_session)
        assert await BillService.get_bill(db_session, client_id, uuid.uuid4()) is None

    @pytest.mark.asyncio
    async def test_list_bills(self, db_session: AsyncSession) -> None:
        """List bills for a client."""
        client_id, account_ids, _, vendor_id = await _setup_full_context(db_session)
        for i in range(3):
            await BillService.create_bill(
                db_session, client_id,
                _make_bill_data(account_ids[0], vendor_id, amount=Decimal(f"{(i+1)*100}.00")),
                CPA_OWNER_USER,
            )

        bills, total = await BillService.list_bills(db_session, client_id)
        assert total == 3
        assert len(bills) == 3

    @pytest.mark.asyncio
    async def test_list_bills_status_filter(self, db_session: AsyncSession) -> None:
        """Filter bills by status."""
        client_id, account_ids, _, vendor_id = await _setup_full_context(db_session)
        bill = await BillService.create_bill(
            db_session, client_id, _make_bill_data(account_ids[0], vendor_id), CPA_OWNER_USER,
        )
        await BillService.submit_for_approval(db_session, client_id, bill.id, CPA_OWNER_USER)

        # DRAFT filter should return 0
        drafts, draft_count = await BillService.list_bills(
            db_session, client_id, status_filter=BillStatus.DRAFT
        )
        assert draft_count == 0

        # PENDING filter should return 1
        pending, pending_count = await BillService.list_bills(
            db_session, client_id, status_filter=BillStatus.PENDING_APPROVAL
        )
        assert pending_count == 1


# ---------------------------------------------------------------------------
# Approval workflow tests
# ---------------------------------------------------------------------------


class TestBillApprovalWorkflow:
    """Test the full bill status workflow: DRAFT -> PENDING -> APPROVED -> PAID."""

    @pytest.mark.asyncio
    async def test_submit_for_approval(self, db_session: AsyncSession) -> None:
        """DRAFT -> PENDING_APPROVAL transition."""
        client_id, account_ids, _, vendor_id = await _setup_full_context(db_session)
        bill = await BillService.create_bill(
            db_session, client_id, _make_bill_data(account_ids[0], vendor_id), CPA_OWNER_USER,
        )
        assert bill.status == BillStatus.DRAFT

        submitted = await BillService.submit_for_approval(
            db_session, client_id, bill.id, CPA_OWNER_USER
        )
        assert submitted.status == BillStatus.PENDING_APPROVAL

    @pytest.mark.asyncio
    async def test_cannot_submit_non_draft(self, db_session: AsyncSession) -> None:
        """Cannot submit a bill that is not in DRAFT status."""
        client_id, account_ids, _, vendor_id = await _setup_full_context(db_session)
        bill = await BillService.create_bill(
            db_session, client_id, _make_bill_data(account_ids[0], vendor_id), CPA_OWNER_USER,
        )
        await BillService.submit_for_approval(db_session, client_id, bill.id, CPA_OWNER_USER)

        with pytest.raises(HTTPException) as exc_info:
            await BillService.submit_for_approval(db_session, client_id, bill.id, CPA_OWNER_USER)
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_approve_bill(self, db_session: AsyncSession) -> None:
        """PENDING_APPROVAL -> APPROVED transition (CPA_OWNER)."""
        client_id, account_ids, _, vendor_id = await _setup_full_context(db_session)
        bill = await BillService.create_bill(
            db_session, client_id, _make_bill_data(account_ids[0], vendor_id), CPA_OWNER_USER,
        )
        await BillService.submit_for_approval(db_session, client_id, bill.id, CPA_OWNER_USER)

        approved = await BillService.approve_bill(
            db_session, client_id, bill.id, CPA_OWNER_USER
        )
        assert approved.status == BillStatus.APPROVED

    @pytest.mark.asyncio
    async def test_approve_creates_journal_entry(self, db_session: AsyncSession) -> None:
        """Approving a bill must create a balanced journal entry in the GL."""
        client_id, account_ids, _, vendor_id = await _setup_full_context(db_session)
        expense_id, ap_id = account_ids[0], account_ids[1]

        bill = await BillService.create_bill(
            db_session, client_id,
            _make_bill_data(expense_id, vendor_id, amount=Decimal("750.00")),
            CPA_OWNER_USER,
        )
        await BillService.submit_for_approval(db_session, client_id, bill.id, CPA_OWNER_USER)
        await BillService.approve_bill(db_session, client_id, bill.id, CPA_OWNER_USER)

        # Verify journal entry was created
        from sqlalchemy import text as sql_text
        result = await db_session.execute(
            sql_text(
                "SELECT je.status, "
                "       SUM(jel.debit) as total_debits, "
                "       SUM(jel.credit) as total_credits "
                "FROM journal_entries je "
                "JOIN journal_entry_lines jel ON jel.journal_entry_id = je.id "
                "WHERE je.client_id = :client_id "
                "  AND je.description LIKE '%Bill%' "
                "GROUP BY je.id, je.status"
            ),
            {"client_id": str(client_id)},
        )
        row = result.first()
        assert row is not None
        assert row.status == "POSTED"
        assert row.total_debits == Decimal("750.00")
        assert row.total_credits == Decimal("750.00")

    @pytest.mark.asyncio
    async def test_cannot_approve_non_pending(self, db_session: AsyncSession) -> None:
        """Cannot approve a bill that is not PENDING_APPROVAL."""
        client_id, account_ids, _, vendor_id = await _setup_full_context(db_session)
        bill = await BillService.create_bill(
            db_session, client_id, _make_bill_data(account_ids[0], vendor_id), CPA_OWNER_USER,
        )
        # Still DRAFT — should fail
        with pytest.raises(HTTPException) as exc_info:
            await BillService.approve_bill(db_session, client_id, bill.id, CPA_OWNER_USER)
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_full_workflow_to_paid(self, db_session: AsyncSession) -> None:
        """Complete workflow: DRAFT -> PENDING -> APPROVED -> PAID."""
        client_id, account_ids, _, vendor_id = await _setup_full_context(db_session)
        bill = await BillService.create_bill(
            db_session, client_id,
            _make_bill_data(account_ids[0], vendor_id, amount=Decimal("1000.00")),
            CPA_OWNER_USER,
        )
        await BillService.submit_for_approval(db_session, client_id, bill.id, CPA_OWNER_USER)
        await BillService.approve_bill(db_session, client_id, bill.id, CPA_OWNER_USER)

        paid = await BillService.record_payment(
            db_session, client_id, bill.id,
            BillPaymentCreate(
                payment_date=date(2024, 7, 1),
                amount=Decimal("1000.00"),
                payment_method="CHECK",
                reference_number="CHK-001",
            ),
            CPA_OWNER_USER,
        )
        assert paid.status == BillStatus.PAID


# ---------------------------------------------------------------------------
# Payment tests
# ---------------------------------------------------------------------------


class TestBillPayments:
    """Test payment recording and partial payments."""

    @pytest.mark.asyncio
    async def test_partial_payment(self, db_session: AsyncSession) -> None:
        """Partial payment keeps bill in APPROVED status."""
        client_id, account_ids, _, vendor_id = await _setup_full_context(db_session)
        bill = await BillService.create_bill(
            db_session, client_id,
            _make_bill_data(account_ids[0], vendor_id, amount=Decimal("1000.00")),
            CPA_OWNER_USER,
        )
        await BillService.submit_for_approval(db_session, client_id, bill.id, CPA_OWNER_USER)
        await BillService.approve_bill(db_session, client_id, bill.id, CPA_OWNER_USER)

        partial = await BillService.record_payment(
            db_session, client_id, bill.id,
            BillPaymentCreate(
                payment_date=date(2024, 7, 1),
                amount=Decimal("400.00"),
                payment_method="CHECK",
            ),
            CPA_OWNER_USER,
        )
        assert partial.status == BillStatus.APPROVED

    @pytest.mark.asyncio
    async def test_full_payment_sets_paid(self, db_session: AsyncSession) -> None:
        """Full payment transitions bill to PAID."""
        client_id, account_ids, _, vendor_id = await _setup_full_context(db_session)
        bill = await BillService.create_bill(
            db_session, client_id,
            _make_bill_data(account_ids[0], vendor_id, amount=Decimal("500.00")),
            CPA_OWNER_USER,
        )
        await BillService.submit_for_approval(db_session, client_id, bill.id, CPA_OWNER_USER)
        await BillService.approve_bill(db_session, client_id, bill.id, CPA_OWNER_USER)

        # Two partial payments summing to full amount
        await BillService.record_payment(
            db_session, client_id, bill.id,
            BillPaymentCreate(payment_date=date(2024, 7, 1), amount=Decimal("300.00")),
            CPA_OWNER_USER,
        )
        paid = await BillService.record_payment(
            db_session, client_id, bill.id,
            BillPaymentCreate(payment_date=date(2024, 7, 15), amount=Decimal("200.00")),
            CPA_OWNER_USER,
        )
        assert paid.status == BillStatus.PAID

    @pytest.mark.asyncio
    async def test_overpayment_rejected(self, db_session: AsyncSession) -> None:
        """Payment exceeding remaining balance is rejected."""
        client_id, account_ids, _, vendor_id = await _setup_full_context(db_session)
        bill = await BillService.create_bill(
            db_session, client_id,
            _make_bill_data(account_ids[0], vendor_id, amount=Decimal("500.00")),
            CPA_OWNER_USER,
        )
        await BillService.submit_for_approval(db_session, client_id, bill.id, CPA_OWNER_USER)
        await BillService.approve_bill(db_session, client_id, bill.id, CPA_OWNER_USER)

        with pytest.raises(HTTPException) as exc_info:
            await BillService.record_payment(
                db_session, client_id, bill.id,
                BillPaymentCreate(payment_date=date(2024, 7, 1), amount=Decimal("600.00")),
                CPA_OWNER_USER,
            )
        assert exc_info.value.status_code == 400
        assert "exceeds" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_cannot_pay_draft_bill(self, db_session: AsyncSession) -> None:
        """Cannot record payment on a DRAFT bill."""
        client_id, account_ids, _, vendor_id = await _setup_full_context(db_session)
        bill = await BillService.create_bill(
            db_session, client_id, _make_bill_data(account_ids[0], vendor_id), CPA_OWNER_USER,
        )
        with pytest.raises(HTTPException) as exc_info:
            await BillService.record_payment(
                db_session, client_id, bill.id,
                BillPaymentCreate(payment_date=date(2024, 7, 1), amount=Decimal("100.00")),
                CPA_OWNER_USER,
            )
        assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# Void tests
# ---------------------------------------------------------------------------


class TestBillVoid:
    """Test bill void functionality."""

    @pytest.mark.asyncio
    async def test_void_approved_bill(self, db_session: AsyncSession) -> None:
        """CPA_OWNER can void an APPROVED bill."""
        client_id, account_ids, _, vendor_id = await _setup_full_context(db_session)
        bill = await BillService.create_bill(
            db_session, client_id, _make_bill_data(account_ids[0], vendor_id), CPA_OWNER_USER,
        )
        await BillService.submit_for_approval(db_session, client_id, bill.id, CPA_OWNER_USER)
        await BillService.approve_bill(db_session, client_id, bill.id, CPA_OWNER_USER)

        voided = await BillService.void_bill(db_session, client_id, bill.id, CPA_OWNER_USER)
        assert voided.status == BillStatus.VOID

    @pytest.mark.asyncio
    async def test_void_paid_bill(self, db_session: AsyncSession) -> None:
        """CPA_OWNER can void a PAID bill."""
        client_id, account_ids, _, vendor_id = await _setup_full_context(db_session)
        bill = await BillService.create_bill(
            db_session, client_id,
            _make_bill_data(account_ids[0], vendor_id, amount=Decimal("200.00")),
            CPA_OWNER_USER,
        )
        await BillService.submit_for_approval(db_session, client_id, bill.id, CPA_OWNER_USER)
        await BillService.approve_bill(db_session, client_id, bill.id, CPA_OWNER_USER)
        await BillService.record_payment(
            db_session, client_id, bill.id,
            BillPaymentCreate(payment_date=date(2024, 7, 1), amount=Decimal("200.00")),
            CPA_OWNER_USER,
        )

        voided = await BillService.void_bill(db_session, client_id, bill.id, CPA_OWNER_USER)
        assert voided.status == BillStatus.VOID

    @pytest.mark.asyncio
    async def test_cannot_void_draft_bill(self, db_session: AsyncSession) -> None:
        """Cannot void a DRAFT bill."""
        client_id, account_ids, _, vendor_id = await _setup_full_context(db_session)
        bill = await BillService.create_bill(
            db_session, client_id, _make_bill_data(account_ids[0], vendor_id), CPA_OWNER_USER,
        )
        with pytest.raises(HTTPException) as exc_info:
            await BillService.void_bill(db_session, client_id, bill.id, CPA_OWNER_USER)
        assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# Role enforcement tests
# ---------------------------------------------------------------------------


class TestBillRoleEnforcement:
    """Test that ASSOCIATE cannot approve or void bills (defense in depth)."""

    @pytest.mark.asyncio
    async def test_associate_cannot_approve(self, db_session: AsyncSession) -> None:
        """ASSOCIATE gets 403 when trying to approve a bill."""
        client_id, account_ids, _, vendor_id = await _setup_full_context(db_session)
        bill = await BillService.create_bill(
            db_session, client_id, _make_bill_data(account_ids[0], vendor_id), ASSOCIATE_USER,
        )
        await BillService.submit_for_approval(db_session, client_id, bill.id, ASSOCIATE_USER)

        with pytest.raises(HTTPException) as exc_info:
            await BillService.approve_bill(db_session, client_id, bill.id, ASSOCIATE_USER)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_associate_cannot_void(self, db_session: AsyncSession) -> None:
        """ASSOCIATE gets 403 when trying to void a bill."""
        client_id, account_ids, _, vendor_id = await _setup_full_context(db_session)
        bill = await BillService.create_bill(
            db_session, client_id, _make_bill_data(account_ids[0], vendor_id), CPA_OWNER_USER,
        )
        await BillService.submit_for_approval(db_session, client_id, bill.id, CPA_OWNER_USER)
        await BillService.approve_bill(db_session, client_id, bill.id, CPA_OWNER_USER)

        with pytest.raises(HTTPException) as exc_info:
            await BillService.void_bill(db_session, client_id, bill.id, ASSOCIATE_USER)
        assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# Client isolation tests
# ---------------------------------------------------------------------------


class TestBillClientIsolation:
    """Test that bill queries enforce client_id isolation."""

    @pytest.mark.asyncio
    async def test_bill_client_isolation_get(self, db_session: AsyncSession) -> None:
        """Client B cannot see Client A's bills."""
        client_a, account_ids, _, vendor_id = await _setup_full_context(db_session)
        client_b = await _create_test_client(db_session)

        bill = await BillService.create_bill(
            db_session, client_a, _make_bill_data(account_ids[0], vendor_id), CPA_OWNER_USER,
        )

        # Client B cannot see it
        assert await BillService.get_bill(db_session, client_b, bill.id) is None

    @pytest.mark.asyncio
    async def test_bill_client_isolation_list(self, db_session: AsyncSession) -> None:
        """Client B's list does not include Client A's bills."""
        client_a, account_ids, _, vendor_id = await _setup_full_context(db_session)
        client_b = await _create_test_client(db_session)

        await BillService.create_bill(
            db_session, client_a, _make_bill_data(account_ids[0], vendor_id), CPA_OWNER_USER,
        )

        bills_b, total_b = await BillService.list_bills(db_session, client_b)
        assert total_b == 0

    @pytest.mark.asyncio
    async def test_bill_client_isolation_submit(self, db_session: AsyncSession) -> None:
        """Cannot submit Client A's bill using Client B's client_id."""
        client_a, account_ids, _, vendor_id = await _setup_full_context(db_session)
        client_b = await _create_test_client(db_session)

        bill = await BillService.create_bill(
            db_session, client_a, _make_bill_data(account_ids[0], vendor_id), CPA_OWNER_USER,
        )

        result = await BillService.submit_for_approval(db_session, client_b, bill.id, CPA_OWNER_USER)
        assert result is None
