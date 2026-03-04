"""
Tests for Invoices / Accounts Receivable (module T2).

MEDIUM COMPLIANCE RISK — tests written alongside implementation.

Compliance tests:
- CLIENT ISOLATION (rule #4): Client A invoices never visible via Client B queries
- APPROVAL WORKFLOW (rule #5): ASSOCIATE enters DRAFT, only CPA_OWNER approves/sends
- ROLE ENFORCEMENT (rule #6): Defense in depth at route + function level
- AUDIT TRAIL (rule #2): Soft deletes only; void creates reversing journal entry
- GL POSTING: Invoices do not affect GL until approved and sent

Uses real PostgreSQL session (rolled back after each test) via db_session
and db_client fixtures from conftest.py.
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from httpx import AsyncClient
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, verify_role
from app.models.invoice import InvoiceStatus
from app.schemas.invoice import InvoiceCreate, InvoiceLineCreate, InvoicePaymentCreate
from app.services.invoice import InvoiceService
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


async def _create_test_user(db: AsyncSession, user_id: str | None = None, role: str = "CPA_OWNER") -> str:
    """Insert a minimal user row and return its UUID string."""
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


async def _create_test_accounts(
    db: AsyncSession, client_id: uuid.UUID, count: int = 4
) -> list[uuid.UUID]:
    """Create test chart of accounts entries and return their IDs.

    Returns accounts in order: [Cash, AR, Revenue, Expenses]
    """
    account_ids = []
    accounts = [
        ("1000", "Cash", "ASSET"),
        ("1200", "Accounts Receivable", "ASSET"),
        ("4000", "Service Revenue", "REVENUE"),
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


async def _setup_full_context(db: AsyncSession) -> tuple[uuid.UUID, list[uuid.UUID], str]:
    """Create client, accounts (Cash, AR, Revenue, Expenses), and user.

    Returns (client_id, account_ids, user_id).
    account_ids[0] = Cash, account_ids[1] = AR, account_ids[2] = Revenue
    """
    client_id = await _create_test_client(db)
    user_id = await _create_test_user(db, CPA_OWNER_USER_ID)
    account_ids = await _create_test_accounts(db, client_id, 4)
    return client_id, account_ids, user_id


def _make_invoice_create(
    revenue_account_id: uuid.UUID,
    customer_name: str = "Acme Corp",
    invoice_number: str = "INV-001",
    lines_count: int = 1,
) -> InvoiceCreate:
    """Build an InvoiceCreate schema for testing."""
    lines = []
    for i in range(lines_count):
        lines.append(
            InvoiceLineCreate(
                account_id=revenue_account_id,
                description=f"Service item {i + 1}",
                quantity=Decimal("2.00"),
                unit_price=Decimal("50.00"),
            )
        )
    return InvoiceCreate(
        customer_name=customer_name,
        invoice_number=invoice_number,
        invoice_date=date(2024, 6, 1),
        due_date=date(2024, 7, 1),
        lines=lines,
    )


# ---------------------------------------------------------------------------
# Schema validation tests (pure Pydantic, no DB required)
# ---------------------------------------------------------------------------


class TestInvoiceSchemaValidation:
    """Test Pydantic schema validation for invoice creation."""

    def test_valid_invoice_passes_validation(self) -> None:
        """A valid invoice with lines passes validation."""
        data = InvoiceCreate(
            customer_name="Acme Corp",
            invoice_number="INV-001",
            invoice_date=date(2024, 6, 1),
            due_date=date(2024, 7, 1),
            lines=[
                InvoiceLineCreate(
                    account_id=uuid.uuid4(),
                    description="Consulting",
                    quantity=Decimal("10.00"),
                    unit_price=Decimal("150.00"),
                ),
            ],
        )
        assert len(data.lines) == 1

    def test_zero_lines_fails_validation(self) -> None:
        """An invoice with zero lines must fail."""
        with pytest.raises(ValidationError):
            InvoiceCreate(
                customer_name="Acme Corp",
                invoice_date=date(2024, 6, 1),
                due_date=date(2024, 7, 1),
                lines=[],
            )

    def test_due_date_before_invoice_date_fails(self) -> None:
        """Due date before invoice date must fail."""
        with pytest.raises(ValidationError, match="due_date"):
            InvoiceCreate(
                customer_name="Acme Corp",
                invoice_date=date(2024, 7, 1),
                due_date=date(2024, 6, 1),
                lines=[
                    InvoiceLineCreate(
                        account_id=uuid.uuid4(),
                        quantity=Decimal("1.00"),
                        unit_price=Decimal("100.00"),
                    ),
                ],
            )

    def test_negative_quantity_fails(self) -> None:
        """Negative quantity must fail."""
        with pytest.raises(ValidationError):
            InvoiceLineCreate(
                account_id=uuid.uuid4(),
                quantity=Decimal("-1.00"),
                unit_price=Decimal("100.00"),
            )

    def test_negative_unit_price_fails(self) -> None:
        """Negative unit price must fail."""
        with pytest.raises(ValidationError):
            InvoiceLineCreate(
                account_id=uuid.uuid4(),
                quantity=Decimal("1.00"),
                unit_price=Decimal("-100.00"),
            )

    def test_payment_amount_must_be_positive(self) -> None:
        """Payment amount must be greater than 0."""
        with pytest.raises(ValidationError):
            InvoicePaymentCreate(
                payment_date=date(2024, 7, 15),
                amount=Decimal("0.00"),
            )

    def test_empty_customer_name_fails(self) -> None:
        """Customer name cannot be empty."""
        with pytest.raises(ValidationError):
            InvoiceCreate(
                customer_name="",
                invoice_date=date(2024, 6, 1),
                due_date=date(2024, 7, 1),
                lines=[
                    InvoiceLineCreate(
                        account_id=uuid.uuid4(),
                        quantity=Decimal("1.00"),
                        unit_price=Decimal("100.00"),
                    ),
                ],
            )

    def test_large_value_invoice_passes(self) -> None:
        """Large realistic value for a GA small business should pass."""
        data = InvoiceCreate(
            customer_name="Large Client",
            invoice_date=date(2024, 12, 31),
            due_date=date(2025, 1, 31),
            lines=[
                InvoiceLineCreate(
                    account_id=uuid.uuid4(),
                    quantity=Decimal("1.00"),
                    unit_price=Decimal("9999999.99"),
                ),
            ],
        )
        assert data.lines[0].unit_price == Decimal("9999999.99")


# ---------------------------------------------------------------------------
# Service-layer tests (require real DB)
# ---------------------------------------------------------------------------


class TestInvoiceCreation:
    """Test invoice creation via service layer."""

    @pytest.mark.asyncio
    async def test_create_invoice_with_lines(self, db_session: AsyncSession) -> None:
        """Creating an invoice should auto-calculate line amounts and total."""
        client_id, accts, user_id = await _setup_full_context(db_session)
        revenue_acct = accts[2]  # Revenue account

        data = _make_invoice_create(revenue_acct, lines_count=2)
        invoice = await InvoiceService.create_invoice(
            db_session, client_id, data, CPA_OWNER_USER
        )

        assert invoice.status == InvoiceStatus.DRAFT
        assert invoice.client_id == client_id
        assert invoice.customer_name == "Acme Corp"
        assert len(invoice.lines) == 2
        # Each line: quantity=2 * unit_price=50 = 100
        assert invoice.lines[0].amount == Decimal("100.00")
        assert invoice.lines[1].amount == Decimal("100.00")
        assert invoice.total_amount == Decimal("200.00")

    @pytest.mark.asyncio
    async def test_create_invoice_status_is_draft(self, db_session: AsyncSession) -> None:
        """New invoices must always start as DRAFT (rule #5)."""
        client_id, accts, user_id = await _setup_full_context(db_session)
        data = _make_invoice_create(accts[2])
        invoice = await InvoiceService.create_invoice(
            db_session, client_id, data, CPA_OWNER_USER
        )
        assert invoice.status == InvoiceStatus.DRAFT


class TestInvoiceApprovalWorkflow:
    """Test the invoice approval workflow: DRAFT -> PENDING -> SENT -> PAID."""

    @pytest.mark.asyncio
    async def test_submit_for_approval(self, db_session: AsyncSession) -> None:
        """DRAFT invoice can be submitted for approval."""
        client_id, accts, user_id = await _setup_full_context(db_session)
        data = _make_invoice_create(accts[2])
        invoice = await InvoiceService.create_invoice(
            db_session, client_id, data, CPA_OWNER_USER
        )

        result = await InvoiceService.submit_for_approval(
            db_session, client_id, invoice.id, CPA_OWNER_USER
        )
        assert result is not None
        assert result.status == InvoiceStatus.PENDING_APPROVAL

    @pytest.mark.asyncio
    async def test_cannot_submit_non_draft(self, db_session: AsyncSession) -> None:
        """Cannot submit an invoice that is not DRAFT."""
        client_id, accts, user_id = await _setup_full_context(db_session)
        data = _make_invoice_create(accts[2])
        invoice = await InvoiceService.create_invoice(
            db_session, client_id, data, CPA_OWNER_USER
        )
        await InvoiceService.submit_for_approval(
            db_session, client_id, invoice.id, CPA_OWNER_USER
        )

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await InvoiceService.submit_for_approval(
                db_session, client_id, invoice.id, CPA_OWNER_USER
            )
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_approve_and_send_creates_journal_entry(self, db_session: AsyncSession) -> None:
        """Approving an invoice should create a GL journal entry (debit AR, credit revenue)."""
        client_id, accts, user_id = await _setup_full_context(db_session)
        ar_acct = accts[1]  # AR
        revenue_acct = accts[2]  # Revenue

        data = _make_invoice_create(revenue_acct)
        invoice = await InvoiceService.create_invoice(
            db_session, client_id, data, CPA_OWNER_USER
        )
        await InvoiceService.submit_for_approval(
            db_session, client_id, invoice.id, CPA_OWNER_USER
        )
        result = await InvoiceService.approve_and_send(
            db_session, client_id, invoice.id, CPA_OWNER_USER, ar_acct
        )

        assert result is not None
        assert result.status == InvoiceStatus.SENT

        # Verify journal entry was created
        je_result = await db_session.execute(
            text(
                "SELECT COUNT(*) FROM journal_entries "
                "WHERE client_id = :cid AND status = 'POSTED' AND deleted_at IS NULL"
            ),
            {"cid": str(client_id)},
        )
        assert je_result.scalar_one() >= 1

    @pytest.mark.asyncio
    async def test_approve_requires_pending_status(self, db_session: AsyncSession) -> None:
        """Cannot approve a DRAFT invoice (must be PENDING_APPROVAL first)."""
        client_id, accts, user_id = await _setup_full_context(db_session)

        data = _make_invoice_create(accts[2])
        invoice = await InvoiceService.create_invoice(
            db_session, client_id, data, CPA_OWNER_USER
        )

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await InvoiceService.approve_and_send(
                db_session, client_id, invoice.id, CPA_OWNER_USER, accts[1]
            )
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_full_workflow_draft_to_paid(self, db_session: AsyncSession) -> None:
        """Complete workflow: DRAFT -> PENDING -> SENT -> PAID."""
        client_id, accts, user_id = await _setup_full_context(db_session)
        cash_acct, ar_acct, revenue_acct = accts[0], accts[1], accts[2]

        data = _make_invoice_create(revenue_acct)
        invoice = await InvoiceService.create_invoice(
            db_session, client_id, data, CPA_OWNER_USER
        )
        assert invoice.status == InvoiceStatus.DRAFT

        await InvoiceService.submit_for_approval(
            db_session, client_id, invoice.id, CPA_OWNER_USER
        )
        assert invoice.status == InvoiceStatus.PENDING_APPROVAL

        await InvoiceService.approve_and_send(
            db_session, client_id, invoice.id, CPA_OWNER_USER, ar_acct
        )
        assert invoice.status == InvoiceStatus.SENT

        payment_data = InvoicePaymentCreate(
            payment_date=date(2024, 7, 15),
            amount=Decimal("100.00"),
            payment_method="CHECK",
            reference_number="CHK-1234",
        )
        result = await InvoiceService.record_payment(
            db_session, client_id, invoice.id, payment_data,
            CPA_OWNER_USER, cash_acct, ar_acct
        )
        assert result is not None
        assert result.status == InvoiceStatus.PAID


class TestInvoicePayments:
    """Test invoice payment recording."""

    @pytest.mark.asyncio
    async def test_partial_payment(self, db_session: AsyncSession) -> None:
        """Partial payment should not change status to PAID."""
        client_id, accts, user_id = await _setup_full_context(db_session)
        cash_acct, ar_acct, revenue_acct = accts[0], accts[1], accts[2]

        data = _make_invoice_create(revenue_acct)
        invoice = await InvoiceService.create_invoice(
            db_session, client_id, data, CPA_OWNER_USER
        )
        await InvoiceService.submit_for_approval(
            db_session, client_id, invoice.id, CPA_OWNER_USER
        )
        await InvoiceService.approve_and_send(
            db_session, client_id, invoice.id, CPA_OWNER_USER, ar_acct
        )

        # Pay only half (total is 100)
        payment_data = InvoicePaymentCreate(
            payment_date=date(2024, 7, 10),
            amount=Decimal("50.00"),
        )
        result = await InvoiceService.record_payment(
            db_session, client_id, invoice.id, payment_data,
            CPA_OWNER_USER, cash_acct, ar_acct
        )
        assert result is not None
        assert result.status == InvoiceStatus.SENT  # Still SENT, not PAID

    @pytest.mark.asyncio
    async def test_full_payment_marks_paid(self, db_session: AsyncSession) -> None:
        """Full payment should change status to PAID."""
        client_id, accts, user_id = await _setup_full_context(db_session)
        cash_acct, ar_acct, revenue_acct = accts[0], accts[1], accts[2]

        data = _make_invoice_create(revenue_acct)
        invoice = await InvoiceService.create_invoice(
            db_session, client_id, data, CPA_OWNER_USER
        )
        await InvoiceService.submit_for_approval(
            db_session, client_id, invoice.id, CPA_OWNER_USER
        )
        await InvoiceService.approve_and_send(
            db_session, client_id, invoice.id, CPA_OWNER_USER, ar_acct
        )

        payment_data = InvoicePaymentCreate(
            payment_date=date(2024, 7, 15),
            amount=Decimal("100.00"),
        )
        result = await InvoiceService.record_payment(
            db_session, client_id, invoice.id, payment_data,
            CPA_OWNER_USER, cash_acct, ar_acct
        )
        assert result is not None
        assert result.status == InvoiceStatus.PAID

    @pytest.mark.asyncio
    async def test_overpayment_rejected(self, db_session: AsyncSession) -> None:
        """Payment exceeding remaining balance should be rejected."""
        client_id, accts, user_id = await _setup_full_context(db_session)
        cash_acct, ar_acct, revenue_acct = accts[0], accts[1], accts[2]

        data = _make_invoice_create(revenue_acct)
        invoice = await InvoiceService.create_invoice(
            db_session, client_id, data, CPA_OWNER_USER
        )
        await InvoiceService.submit_for_approval(
            db_session, client_id, invoice.id, CPA_OWNER_USER
        )
        await InvoiceService.approve_and_send(
            db_session, client_id, invoice.id, CPA_OWNER_USER, ar_acct
        )

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            payment_data = InvoicePaymentCreate(
                payment_date=date(2024, 7, 15),
                amount=Decimal("200.00"),  # Invoice total is 100
            )
            await InvoiceService.record_payment(
                db_session, client_id, invoice.id, payment_data,
                CPA_OWNER_USER, cash_acct, ar_acct
            )
        assert exc_info.value.status_code == 400
        assert "exceeds" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_cannot_pay_draft_invoice(self, db_session: AsyncSession) -> None:
        """Cannot record payment for a DRAFT invoice."""
        client_id, accts, user_id = await _setup_full_context(db_session)
        cash_acct, ar_acct, revenue_acct = accts[0], accts[1], accts[2]

        data = _make_invoice_create(revenue_acct)
        invoice = await InvoiceService.create_invoice(
            db_session, client_id, data, CPA_OWNER_USER
        )

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            payment_data = InvoicePaymentCreate(
                payment_date=date(2024, 7, 15),
                amount=Decimal("50.00"),
            )
            await InvoiceService.record_payment(
                db_session, client_id, invoice.id, payment_data,
                CPA_OWNER_USER, cash_acct, ar_acct
            )
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_payment_creates_journal_entry(self, db_session: AsyncSession) -> None:
        """Payment should create a GL journal entry (debit cash, credit AR)."""
        client_id, accts, user_id = await _setup_full_context(db_session)
        cash_acct, ar_acct, revenue_acct = accts[0], accts[1], accts[2]

        data = _make_invoice_create(revenue_acct)
        invoice = await InvoiceService.create_invoice(
            db_session, client_id, data, CPA_OWNER_USER
        )
        await InvoiceService.submit_for_approval(
            db_session, client_id, invoice.id, CPA_OWNER_USER
        )
        await InvoiceService.approve_and_send(
            db_session, client_id, invoice.id, CPA_OWNER_USER, ar_acct
        )

        # Count JEs before payment
        before = await db_session.execute(
            text(
                "SELECT COUNT(*) FROM journal_entries "
                "WHERE client_id = :cid AND status = 'POSTED' AND deleted_at IS NULL"
            ),
            {"cid": str(client_id)},
        )
        count_before = before.scalar_one()

        payment_data = InvoicePaymentCreate(
            payment_date=date(2024, 7, 15),
            amount=Decimal("100.00"),
        )
        await InvoiceService.record_payment(
            db_session, client_id, invoice.id, payment_data,
            CPA_OWNER_USER, cash_acct, ar_acct
        )

        after = await db_session.execute(
            text(
                "SELECT COUNT(*) FROM journal_entries "
                "WHERE client_id = :cid AND status = 'POSTED' AND deleted_at IS NULL"
            ),
            {"cid": str(client_id)},
        )
        count_after = after.scalar_one()
        assert count_after == count_before + 1


class TestRoleEnforcement:
    """Test that ASSOCIATE cannot approve or void invoices."""

    @pytest.mark.asyncio
    async def test_associate_cannot_approve(self, db_session: AsyncSession) -> None:
        """ASSOCIATE must get 403 when trying to approve an invoice."""
        client_id, accts, _ = await _setup_full_context(db_session)
        # Also create associate user
        await _create_test_user(db_session, ASSOCIATE_USER_ID, role="ASSOCIATE")
        revenue_acct = accts[2]
        ar_acct = accts[1]

        data = _make_invoice_create(revenue_acct)
        invoice = await InvoiceService.create_invoice(
            db_session, client_id, data, ASSOCIATE_USER
        )
        await InvoiceService.submit_for_approval(
            db_session, client_id, invoice.id, ASSOCIATE_USER
        )

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await InvoiceService.approve_and_send(
                db_session, client_id, invoice.id, ASSOCIATE_USER, ar_acct
            )
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_associate_cannot_void(self, db_session: AsyncSession) -> None:
        """ASSOCIATE must get 403 when trying to void an invoice."""
        client_id, accts, _ = await _setup_full_context(db_session)
        await _create_test_user(db_session, ASSOCIATE_USER_ID, role="ASSOCIATE")
        revenue_acct = accts[2]
        ar_acct = accts[1]

        data = _make_invoice_create(revenue_acct)
        invoice = await InvoiceService.create_invoice(
            db_session, client_id, data, CPA_OWNER_USER
        )
        await InvoiceService.submit_for_approval(
            db_session, client_id, invoice.id, CPA_OWNER_USER
        )
        await InvoiceService.approve_and_send(
            db_session, client_id, invoice.id, CPA_OWNER_USER, ar_acct
        )

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await InvoiceService.void_invoice(
                db_session, client_id, invoice.id, ASSOCIATE_USER, ar_acct
            )
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_associate_can_create_invoice(self, db_session: AsyncSession) -> None:
        """ASSOCIATE should be able to create invoices (status DRAFT)."""
        client_id, accts, _ = await _setup_full_context(db_session)
        await _create_test_user(db_session, ASSOCIATE_USER_ID, role="ASSOCIATE")
        revenue_acct = accts[2]

        data = _make_invoice_create(revenue_acct)
        invoice = await InvoiceService.create_invoice(
            db_session, client_id, data, ASSOCIATE_USER
        )
        assert invoice.status == InvoiceStatus.DRAFT


class TestClientIsolation:
    """Test that queries are isolated by client_id (rule #4)."""

    @pytest.mark.asyncio
    async def test_get_invoice_wrong_client_returns_none(self, db_session: AsyncSession) -> None:
        """Getting an invoice with the wrong client_id returns None."""
        client_id, accts, _ = await _setup_full_context(db_session)
        other_client_id = await _create_test_client(db_session)
        revenue_acct = accts[2]

        data = _make_invoice_create(revenue_acct)
        invoice = await InvoiceService.create_invoice(
            db_session, client_id, data, CPA_OWNER_USER
        )

        # Try to fetch with wrong client_id
        result = await InvoiceService.get_invoice(db_session, other_client_id, invoice.id)
        assert result is None

    @pytest.mark.asyncio
    async def test_list_invoices_isolated_by_client(self, db_session: AsyncSession) -> None:
        """Listing invoices for client A should not return client B's invoices."""
        client_a, accts_a, _ = await _setup_full_context(db_session)
        client_b = await _create_test_client(db_session)
        accts_b = await _create_test_accounts(db_session, client_b, 3)
        revenue_a = accts_a[2]
        revenue_b = accts_b[2]

        # Create invoices for both clients
        data_a = _make_invoice_create(revenue_a, customer_name="Client A Customer")
        await InvoiceService.create_invoice(db_session, client_a, data_a, CPA_OWNER_USER)

        data_b = _make_invoice_create(revenue_b, customer_name="Client B Customer", invoice_number="INV-002")
        await InvoiceService.create_invoice(db_session, client_b, data_b, CPA_OWNER_USER)

        # List client A invoices
        invoices_a, total_a = await InvoiceService.list_invoices(db_session, client_a)
        assert total_a == 1
        assert invoices_a[0].customer_name == "Client A Customer"

        # List client B invoices
        invoices_b, total_b = await InvoiceService.list_invoices(db_session, client_b)
        assert total_b == 1
        assert invoices_b[0].customer_name == "Client B Customer"


class TestOverdueDetection:
    """Test marking invoices as overdue."""

    @pytest.mark.asyncio
    async def test_mark_sent_as_overdue(self, db_session: AsyncSession) -> None:
        """A SENT invoice can be marked as OVERDUE."""
        client_id, accts, _ = await _setup_full_context(db_session)
        ar_acct = accts[1]
        revenue_acct = accts[2]

        data = _make_invoice_create(revenue_acct)
        invoice = await InvoiceService.create_invoice(
            db_session, client_id, data, CPA_OWNER_USER
        )
        await InvoiceService.submit_for_approval(
            db_session, client_id, invoice.id, CPA_OWNER_USER
        )
        await InvoiceService.approve_and_send(
            db_session, client_id, invoice.id, CPA_OWNER_USER, ar_acct
        )

        result = await InvoiceService.mark_overdue(db_session, client_id, invoice.id)
        assert result is not None
        assert result.status == InvoiceStatus.OVERDUE

    @pytest.mark.asyncio
    async def test_cannot_mark_draft_as_overdue(self, db_session: AsyncSession) -> None:
        """Cannot mark a DRAFT invoice as overdue."""
        client_id, accts, _ = await _setup_full_context(db_session)

        data = _make_invoice_create(accts[2])
        invoice = await InvoiceService.create_invoice(
            db_session, client_id, data, CPA_OWNER_USER
        )

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await InvoiceService.mark_overdue(db_session, client_id, invoice.id)
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_overdue_invoice_can_receive_payment(self, db_session: AsyncSession) -> None:
        """An OVERDUE invoice should still accept payments."""
        client_id, accts, _ = await _setup_full_context(db_session)
        cash_acct, ar_acct, revenue_acct = accts[0], accts[1], accts[2]

        data = _make_invoice_create(revenue_acct)
        invoice = await InvoiceService.create_invoice(
            db_session, client_id, data, CPA_OWNER_USER
        )
        await InvoiceService.submit_for_approval(
            db_session, client_id, invoice.id, CPA_OWNER_USER
        )
        await InvoiceService.approve_and_send(
            db_session, client_id, invoice.id, CPA_OWNER_USER, ar_acct
        )
        await InvoiceService.mark_overdue(db_session, client_id, invoice.id)

        payment_data = InvoicePaymentCreate(
            payment_date=date(2024, 8, 1),
            amount=Decimal("100.00"),
        )
        result = await InvoiceService.record_payment(
            db_session, client_id, invoice.id, payment_data,
            CPA_OWNER_USER, cash_acct, ar_acct
        )
        assert result is not None
        assert result.status == InvoiceStatus.PAID


class TestVoidInvoice:
    """Test voiding invoices."""

    @pytest.mark.asyncio
    async def test_void_creates_reversing_journal_entry(self, db_session: AsyncSession) -> None:
        """Voiding an invoice should create a reversing GL journal entry."""
        client_id, accts, _ = await _setup_full_context(db_session)
        ar_acct = accts[1]
        revenue_acct = accts[2]

        data = _make_invoice_create(revenue_acct)
        invoice = await InvoiceService.create_invoice(
            db_session, client_id, data, CPA_OWNER_USER
        )
        await InvoiceService.submit_for_approval(
            db_session, client_id, invoice.id, CPA_OWNER_USER
        )
        await InvoiceService.approve_and_send(
            db_session, client_id, invoice.id, CPA_OWNER_USER, ar_acct
        )

        # Count JEs before void
        before = await db_session.execute(
            text(
                "SELECT COUNT(*) FROM journal_entries "
                "WHERE client_id = :cid AND status = 'POSTED' AND deleted_at IS NULL"
            ),
            {"cid": str(client_id)},
        )
        count_before = before.scalar_one()

        result = await InvoiceService.void_invoice(
            db_session, client_id, invoice.id, CPA_OWNER_USER, ar_acct
        )
        assert result is not None
        assert result.status == InvoiceStatus.VOID

        after = await db_session.execute(
            text(
                "SELECT COUNT(*) FROM journal_entries "
                "WHERE client_id = :cid AND status = 'POSTED' AND deleted_at IS NULL"
            ),
            {"cid": str(client_id)},
        )
        count_after = after.scalar_one()
        assert count_after == count_before + 1  # Reversing entry added

    @pytest.mark.asyncio
    async def test_cannot_void_draft_invoice(self, db_session: AsyncSession) -> None:
        """Cannot void a DRAFT invoice."""
        client_id, accts, _ = await _setup_full_context(db_session)

        data = _make_invoice_create(accts[2])
        invoice = await InvoiceService.create_invoice(
            db_session, client_id, data, CPA_OWNER_USER
        )

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await InvoiceService.void_invoice(
                db_session, client_id, invoice.id, CPA_OWNER_USER, accts[1]
            )
        assert exc_info.value.status_code == 400


class TestInvoiceListFilters:
    """Test list_invoices filtering capabilities."""

    @pytest.mark.asyncio
    async def test_filter_by_status(self, db_session: AsyncSession) -> None:
        """Filtering by status should return only matching invoices."""
        client_id, accts, _ = await _setup_full_context(db_session)
        revenue_acct = accts[2]

        # Create two invoices, submit one
        data1 = _make_invoice_create(revenue_acct, invoice_number="INV-A")
        inv1 = await InvoiceService.create_invoice(
            db_session, client_id, data1, CPA_OWNER_USER
        )
        data2 = _make_invoice_create(revenue_acct, invoice_number="INV-B")
        inv2 = await InvoiceService.create_invoice(
            db_session, client_id, data2, CPA_OWNER_USER
        )
        await InvoiceService.submit_for_approval(
            db_session, client_id, inv2.id, CPA_OWNER_USER
        )

        # Filter for DRAFT
        drafts, total = await InvoiceService.list_invoices(
            db_session, client_id, status_filter=InvoiceStatus.DRAFT
        )
        assert total == 1
        assert drafts[0].invoice_number == "INV-A"

    @pytest.mark.asyncio
    async def test_filter_by_customer_name(self, db_session: AsyncSession) -> None:
        """Filtering by customer_name (partial match) should work."""
        client_id, accts, _ = await _setup_full_context(db_session)
        revenue_acct = accts[2]

        data1 = _make_invoice_create(revenue_acct, customer_name="Alpha Inc", invoice_number="INV-1")
        await InvoiceService.create_invoice(db_session, client_id, data1, CPA_OWNER_USER)

        data2 = _make_invoice_create(revenue_acct, customer_name="Beta LLC", invoice_number="INV-2")
        await InvoiceService.create_invoice(db_session, client_id, data2, CPA_OWNER_USER)

        results, total = await InvoiceService.list_invoices(
            db_session, client_id, customer_name="Alpha"
        )
        assert total == 1
        assert results[0].customer_name == "Alpha Inc"

    @pytest.mark.asyncio
    async def test_filter_by_date_range(self, db_session: AsyncSession) -> None:
        """Filtering by date range should return only matching invoices."""
        client_id, accts, _ = await _setup_full_context(db_session)
        revenue_acct = accts[2]

        data = _make_invoice_create(revenue_acct)
        await InvoiceService.create_invoice(db_session, client_id, data, CPA_OWNER_USER)

        # Date range that includes our invoice
        results, total = await InvoiceService.list_invoices(
            db_session, client_id,
            date_from=date(2024, 5, 1),
            date_to=date(2024, 6, 30),
        )
        assert total == 1

        # Date range that excludes our invoice
        results, total = await InvoiceService.list_invoices(
            db_session, client_id,
            date_from=date(2025, 1, 1),
            date_to=date(2025, 12, 31),
        )
        assert total == 0
