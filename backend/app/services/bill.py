"""
Business logic for Bill management (Module T1 — Accounts Payable).

Compliance (CLAUDE.md):
- Rule #1: DOUBLE-ENTRY — bill approval creates a balanced journal entry
    (debit expense accounts, credit AP).
- Rule #2: AUDIT TRAIL — soft deletes only. Void creates reversing JE.
- Rule #4: CLIENT ISOLATION — every query filters by client_id.
- Rule #5: APPROVAL WORKFLOW — bills start DRAFT, only CPA_OWNER approves.
- Rule #6: Role checks at function level (defense in depth).

Bills do NOT affect the GL until APPROVED. On approval, a journal entry is
created: debit each expense account (from bill lines), credit AP account.
"""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, verify_role
from app.models.bill import Bill, BillLine, BillPayment, BillStatus
from app.models.journal_entry import JournalEntry, JournalEntryLine, JournalEntryStatus
from app.schemas.bill import BillCreate, BillPaymentCreate


class BillService:
    """Business logic for bill CRUD and workflow operations."""

    @staticmethod
    async def create_bill(
        db: AsyncSession,
        client_id: uuid.UUID,
        data: BillCreate,
        current_user: CurrentUser,
    ) -> Bill:
        """
        Create a bill with line items. Status starts as DRAFT.

        Compliance (rule #5): Never auto-post on entry.
        total_amount is computed from the sum of line amounts.
        """
        total = sum(line.amount for line in data.lines)

        bill = Bill(
            client_id=client_id,
            vendor_id=data.vendor_id,
            bill_number=data.bill_number,
            bill_date=data.bill_date,
            due_date=data.due_date,
            total_amount=total,
            status=BillStatus.DRAFT,
        )
        db.add(bill)
        await db.flush()

        for line_data in data.lines:
            line = BillLine(
                bill_id=bill.id,
                account_id=line_data.account_id,
                description=line_data.description,
                amount=line_data.amount,
            )
            db.add(line)

        await db.flush()
        await db.refresh(bill)
        return bill

    @staticmethod
    async def get_bill(
        db: AsyncSession,
        client_id: uuid.UUID,
        bill_id: uuid.UUID,
    ) -> Bill | None:
        """
        Retrieve a single bill with lines and payments, filtered by client_id.

        Compliance (rule #4): ALWAYS filters by client_id.
        """
        stmt = select(Bill).where(
            Bill.id == bill_id,
            Bill.client_id == client_id,
            Bill.deleted_at.is_(None),
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_bills(
        db: AsyncSession,
        client_id: uuid.UUID,
        status_filter: BillStatus | None = None,
        vendor_id: uuid.UUID | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Bill], int]:
        """
        List bills for a client with optional filters and pagination.

        Compliance (rule #4): ALWAYS filters by client_id.
        Always excludes soft-deleted records.
        """
        base = select(Bill).where(
            Bill.client_id == client_id,
            Bill.deleted_at.is_(None),
        )

        if status_filter is not None:
            base = base.where(Bill.status == status_filter)
        if vendor_id is not None:
            base = base.where(Bill.vendor_id == vendor_id)
        if date_from is not None:
            base = base.where(Bill.bill_date >= date_from)
        if date_to is not None:
            base = base.where(Bill.bill_date <= date_to)

        count_stmt = select(func.count()).select_from(base.subquery())
        total_result = await db.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = base.order_by(Bill.bill_date.desc(), Bill.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(stmt)
        bills = list(result.scalars().all())

        return bills, total

    @staticmethod
    async def submit_for_approval(
        db: AsyncSession,
        client_id: uuid.UUID,
        bill_id: uuid.UUID,
        current_user: CurrentUser,
    ) -> Bill | None:
        """
        Transition a bill from DRAFT to PENDING_APPROVAL.

        Any role can submit for approval.
        Compliance (rule #4): ALWAYS filters by client_id.
        """
        bill = await BillService.get_bill(db, client_id, bill_id)
        if bill is None:
            return None

        if bill.status != BillStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot submit bill in status '{bill.status.value}'. Only DRAFT bills can be submitted.",
            )

        bill.status = BillStatus.PENDING_APPROVAL
        bill.updated_at = datetime.now(timezone.utc)
        await db.flush()
        await db.refresh(bill)
        return bill

    @staticmethod
    async def _find_ap_account(db: AsyncSession, client_id: uuid.UUID) -> uuid.UUID:
        """
        Find the Accounts Payable account for a client.

        Looks for an account with account_number '2000' or account_name
        containing 'Accounts Payable' in the client's chart of accounts.
        """
        from app.models.chart_of_accounts import ChartOfAccounts

        stmt = select(ChartOfAccounts.id).where(
            ChartOfAccounts.client_id == client_id,
            ChartOfAccounts.deleted_at.is_(None),
            ChartOfAccounts.is_active.is_(True),
            ChartOfAccounts.account_type == "LIABILITY",
            ChartOfAccounts.account_number == "2000",
        )
        result = await db.execute(stmt)
        account_id = result.scalar_one_or_none()

        if account_id is None:
            # Fallback: look for any liability account named Accounts Payable
            stmt2 = select(ChartOfAccounts.id).where(
                ChartOfAccounts.client_id == client_id,
                ChartOfAccounts.deleted_at.is_(None),
                ChartOfAccounts.is_active.is_(True),
                ChartOfAccounts.account_type == "LIABILITY",
                ChartOfAccounts.account_name.ilike("%accounts payable%"),
            )
            result2 = await db.execute(stmt2)
            account_id = result2.scalar_one_or_none()

        if account_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No Accounts Payable account found for this client. "
                       "Please create a LIABILITY account with account_number '2000'.",
            )

        return account_id

    @staticmethod
    async def approve_bill(
        db: AsyncSession,
        client_id: uuid.UUID,
        bill_id: uuid.UUID,
        current_user: CurrentUser,
    ) -> Bill | None:
        """
        Approve a bill: PENDING_APPROVAL -> APPROVED. CPA_OWNER only.

        Creates a journal entry: debit each expense account (from bill lines),
        credit AP account for the total.

        Compliance (rule #5): Only CPA_OWNER can approve.
        Compliance (rule #6): Role check at function level (defense in depth).
        Compliance (rule #1): Journal entry is balanced (debits == credits).
        """
        verify_role(current_user, "CPA_OWNER")

        bill = await BillService.get_bill(db, client_id, bill_id)
        if bill is None:
            return None

        if bill.status != BillStatus.PENDING_APPROVAL:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot approve bill in status '{bill.status.value}'. "
                       f"Only PENDING_APPROVAL bills can be approved.",
            )

        # Find the AP account for this client
        ap_account_id = await BillService._find_ap_account(db, client_id)

        # Create journal entry: debit expense accounts, credit AP
        je = JournalEntry(
            client_id=client_id,
            entry_date=bill.bill_date,
            description=f"Bill {bill.bill_number or bill.id} approved — AP entry",
            reference_number=f"BILL-{bill.bill_number or str(bill.id)[:8]}",
            status=JournalEntryStatus.DRAFT,
            created_by=uuid.UUID(current_user.user_id),
        )
        db.add(je)
        await db.flush()

        # Debit each expense account
        for line in bill.lines:
            if line.deleted_at is not None:
                continue
            je_line = JournalEntryLine(
                journal_entry_id=je.id,
                account_id=line.account_id,
                debit=line.amount,
                credit=Decimal("0.00"),
                description=line.description or f"Bill line: {bill.bill_number}",
            )
            db.add(je_line)

        # Credit AP for total
        ap_line = JournalEntryLine(
            journal_entry_id=je.id,
            account_id=ap_account_id,
            debit=Decimal("0.00"),
            credit=bill.total_amount,
            description=f"AP credit for bill {bill.bill_number or bill.id}",
        )
        db.add(ap_line)
        await db.flush()

        # Post the journal entry immediately (CPA_OWNER is approving)
        je.status = JournalEntryStatus.POSTED
        je.approved_by = uuid.UUID(current_user.user_id)
        je.posted_at = datetime.now(timezone.utc)

        # Update bill status
        bill.status = BillStatus.APPROVED
        bill.updated_at = datetime.now(timezone.utc)
        await db.flush()
        await db.refresh(bill)
        return bill

    @staticmethod
    async def record_payment(
        db: AsyncSession,
        client_id: uuid.UUID,
        bill_id: uuid.UUID,
        data: BillPaymentCreate,
        current_user: CurrentUser,
    ) -> Bill | None:
        """
        Record a payment against an APPROVED bill.

        If total payments >= bill total, status transitions to PAID.
        """
        bill = await BillService.get_bill(db, client_id, bill_id)
        if bill is None:
            return None

        if bill.status not in (BillStatus.APPROVED, BillStatus.PAID):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot record payment on bill in status '{bill.status.value}'. "
                       f"Bill must be APPROVED first.",
            )

        # Calculate existing payments (exclude soft-deleted)
        existing_paid = sum(
            p.amount for p in bill.payments if p.deleted_at is None
        )
        remaining = bill.total_amount - existing_paid

        if data.amount > remaining:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Payment amount ({data.amount}) exceeds remaining balance ({remaining}).",
            )

        payment = BillPayment(
            bill_id=bill.id,
            payment_date=data.payment_date,
            amount=data.amount,
            payment_method=data.payment_method,
            reference_number=data.reference_number,
        )
        db.add(payment)

        # Check if fully paid
        total_paid = existing_paid + data.amount
        if total_paid >= bill.total_amount:
            bill.status = BillStatus.PAID

        bill.updated_at = datetime.now(timezone.utc)
        await db.flush()
        await db.refresh(bill)
        return bill

    @staticmethod
    async def void_bill(
        db: AsyncSession,
        client_id: uuid.UUID,
        bill_id: uuid.UUID,
        current_user: CurrentUser,
    ) -> Bill | None:
        """
        Void a bill: APPROVED or PAID -> VOID. CPA_OWNER only.

        Compliance (rule #5): Only CPA_OWNER can void.
        Compliance (rule #6): Role check at function level (defense in depth).
        Compliance (rule #2): Soft delete pattern — status changed, not deleted.
        """
        verify_role(current_user, "CPA_OWNER")

        bill = await BillService.get_bill(db, client_id, bill_id)
        if bill is None:
            return None

        if bill.status not in (BillStatus.APPROVED, BillStatus.PAID):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot void bill in status '{bill.status.value}'. "
                       f"Only APPROVED or PAID bills can be voided.",
            )

        bill.status = BillStatus.VOID
        bill.updated_at = datetime.now(timezone.utc)
        await db.flush()
        await db.refresh(bill)
        return bill
