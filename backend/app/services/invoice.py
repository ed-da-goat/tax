"""
Service layer for Invoices / Accounts Receivable (module T2).

Compliance (CLAUDE.md):
- Rule #2: AUDIT TRAIL — soft deletes only. Void creates reversing journal entry.
- Rule #4: CLIENT ISOLATION — every query filters by client_id.
- Rule #5: APPROVAL WORKFLOW — ASSOCIATE enters DRAFT. Only CPA_OWNER approves/sends.
- Rule #6: Role checks at function level (defense in depth).

Invoices do not affect the GL until approved and sent (status = SENT).
On approval: debit AR, credit revenue accounts.
On payment: debit cash, credit AR.
On void: reversing journal entry created.
"""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, verify_role
from app.models.invoice import Invoice, InvoiceLine, InvoicePayment, InvoiceStatus
from app.models.journal_entry import JournalEntry, JournalEntryLine, JournalEntryStatus
from app.schemas.invoice import InvoiceCreate, InvoicePaymentCreate


class InvoiceService:
    """Business logic for invoice CRUD and workflow operations."""

    @staticmethod
    async def create_invoice(
        db: AsyncSession,
        client_id: uuid.UUID,
        data: InvoiceCreate,
        current_user: CurrentUser,
    ) -> Invoice:
        """
        Create an invoice with line items. Status starts as DRAFT.

        Auto-calculates line amounts (quantity * unit_price) and total_amount.
        Compliance (rule #5): Never auto-post on entry.
        """
        invoice = Invoice(
            client_id=client_id,
            customer_name=data.customer_name,
            invoice_number=data.invoice_number,
            invoice_date=data.invoice_date,
            due_date=data.due_date,
            status=InvoiceStatus.DRAFT,
            total_amount=Decimal("0.00"),
        )
        db.add(invoice)
        await db.flush()

        total = Decimal("0.00")
        for line_data in data.lines:
            amount = line_data.quantity * line_data.unit_price
            line = InvoiceLine(
                invoice_id=invoice.id,
                account_id=line_data.account_id,
                description=line_data.description,
                quantity=line_data.quantity,
                unit_price=line_data.unit_price,
                amount=amount,
            )
            db.add(line)
            total += amount

        invoice.total_amount = total
        await db.flush()
        await db.refresh(invoice)
        return invoice

    @staticmethod
    async def get_invoice(
        db: AsyncSession,
        client_id: uuid.UUID,
        invoice_id: uuid.UUID,
    ) -> Invoice | None:
        """
        Retrieve a single invoice by ID, filtered by client_id.

        Compliance (rule #4): ALWAYS filters by client_id so that
        Client A cannot retrieve Client B's invoices.
        """
        stmt = select(Invoice).where(
            Invoice.id == invoice_id,
            Invoice.client_id == client_id,
            Invoice.deleted_at.is_(None),
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_invoices(
        db: AsyncSession,
        client_id: uuid.UUID,
        status_filter: InvoiceStatus | None = None,
        customer_name: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Invoice], int]:
        """
        List invoices for a client with optional filters and pagination.

        Compliance (rule #4): ALWAYS filters by client_id.
        Always excludes soft-deleted records.
        """
        base = select(Invoice).where(
            Invoice.client_id == client_id,
            Invoice.deleted_at.is_(None),
        )

        if status_filter is not None:
            base = base.where(Invoice.status == status_filter)
        if customer_name is not None:
            base = base.where(Invoice.customer_name.ilike(f"%{customer_name}%"))
        if date_from is not None:
            base = base.where(Invoice.invoice_date >= date_from)
        if date_to is not None:
            base = base.where(Invoice.invoice_date <= date_to)

        # Total count
        count_stmt = select(func.count()).select_from(base.subquery())
        total_result = await db.execute(count_stmt)
        total = total_result.scalar_one()

        # Paginated results
        stmt = base.order_by(
            Invoice.invoice_date.desc(), Invoice.created_at.desc()
        ).offset(skip).limit(limit)
        result = await db.execute(stmt)
        invoices = list(result.scalars().all())

        return invoices, total

    @staticmethod
    async def submit_for_approval(
        db: AsyncSession,
        client_id: uuid.UUID,
        invoice_id: uuid.UUID,
        current_user: CurrentUser,
    ) -> Invoice | None:
        """
        Transition an invoice from DRAFT to PENDING_APPROVAL.

        Any role can submit for approval.
        Compliance (rule #4): ALWAYS filters by client_id.
        """
        invoice = await InvoiceService.get_invoice(db, client_id, invoice_id)
        if invoice is None:
            return None

        if invoice.status != InvoiceStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot submit invoice in status '{invoice.status.value}'. Only DRAFT invoices can be submitted.",
            )

        invoice.status = InvoiceStatus.PENDING_APPROVAL
        invoice.updated_at = datetime.now(timezone.utc)
        await db.flush()
        await db.refresh(invoice)
        return invoice

    @staticmethod
    async def approve_and_send(
        db: AsyncSession,
        client_id: uuid.UUID,
        invoice_id: uuid.UUID,
        current_user: CurrentUser,
        ar_account_id: uuid.UUID,
    ) -> Invoice | None:
        """
        Approve and send an invoice (PENDING_APPROVAL -> SENT). CPA_OWNER only.

        Creates journal entry: debit AR account, credit revenue accounts (from invoice lines).
        Defense in depth: function-level role check.

        Compliance (rule #5): Only CPA_OWNER can approve.
        Compliance (rule #6): Role check at function level.
        """
        verify_role(current_user, "CPA_OWNER")

        invoice = await InvoiceService.get_invoice(db, client_id, invoice_id)
        if invoice is None:
            return None

        if invoice.status != InvoiceStatus.PENDING_APPROVAL:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot approve invoice in status '{invoice.status.value}'. Only PENDING_APPROVAL invoices can be approved.",
            )

        # Create journal entry: debit AR, credit revenue accounts
        je = JournalEntry(
            client_id=client_id,
            entry_date=invoice.invoice_date,
            description=f"Invoice {invoice.invoice_number or invoice.id}: {invoice.customer_name}",
            reference_number=invoice.invoice_number,
            status=JournalEntryStatus.DRAFT,
            created_by=uuid.UUID(current_user.user_id),
        )
        db.add(je)
        await db.flush()

        # Debit AR for total amount
        ar_line = JournalEntryLine(
            journal_entry_id=je.id,
            account_id=ar_account_id,
            debit=invoice.total_amount,
            credit=Decimal("0.00"),
            description=f"AR - Invoice {invoice.invoice_number or invoice.id}",
        )
        db.add(ar_line)

        # Credit each revenue account from invoice lines
        for inv_line in invoice.lines:
            if inv_line.deleted_at is not None:
                continue
            credit_line = JournalEntryLine(
                journal_entry_id=je.id,
                account_id=inv_line.account_id,
                debit=Decimal("0.00"),
                credit=inv_line.amount,
                description=inv_line.description or f"Revenue - Invoice {invoice.invoice_number or invoice.id}",
            )
            db.add(credit_line)

        await db.flush()

        # Post the journal entry directly (CPA_OWNER approved)
        je.status = JournalEntryStatus.POSTED
        je.approved_by = uuid.UUID(current_user.user_id)
        je.posted_at = datetime.now(timezone.utc)

        invoice.status = InvoiceStatus.SENT
        invoice.updated_at = datetime.now(timezone.utc)

        await db.flush()
        await db.refresh(invoice)
        return invoice

    @staticmethod
    async def record_payment(
        db: AsyncSession,
        client_id: uuid.UUID,
        invoice_id: uuid.UUID,
        data: InvoicePaymentCreate,
        current_user: CurrentUser,
        cash_account_id: uuid.UUID,
        ar_account_id: uuid.UUID,
    ) -> Invoice | None:
        """
        Record a payment against an invoice. If fully paid, status -> PAID.

        Creates journal entry: debit cash, credit AR.

        Compliance (rule #4): ALWAYS filters by client_id.
        """
        invoice = await InvoiceService.get_invoice(db, client_id, invoice_id)
        if invoice is None:
            return None

        if invoice.status not in (InvoiceStatus.SENT, InvoiceStatus.OVERDUE):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot record payment for invoice in status '{invoice.status.value}'. Invoice must be SENT or OVERDUE.",
            )

        # Calculate existing payments
        existing_payments = sum(
            p.amount for p in invoice.payments if p.deleted_at is None
        )
        remaining = invoice.total_amount - existing_payments

        if data.amount > remaining:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Payment amount ({data.amount}) exceeds remaining balance ({remaining}).",
            )

        # Create payment record
        payment = InvoicePayment(
            invoice_id=invoice.id,
            payment_date=data.payment_date,
            amount=data.amount,
            payment_method=data.payment_method,
            reference_number=data.reference_number,
        )
        db.add(payment)

        # Create journal entry: debit cash, credit AR
        je = JournalEntry(
            client_id=client_id,
            entry_date=data.payment_date,
            description=f"Payment for Invoice {invoice.invoice_number or invoice.id}",
            reference_number=data.reference_number,
            status=JournalEntryStatus.DRAFT,
            created_by=uuid.UUID(current_user.user_id),
        )
        db.add(je)
        await db.flush()

        cash_line = JournalEntryLine(
            journal_entry_id=je.id,
            account_id=cash_account_id,
            debit=data.amount,
            credit=Decimal("0.00"),
            description=f"Cash received - Invoice {invoice.invoice_number or invoice.id}",
        )
        db.add(cash_line)

        ar_credit = JournalEntryLine(
            journal_entry_id=je.id,
            account_id=ar_account_id,
            debit=Decimal("0.00"),
            credit=data.amount,
            description=f"AR reduction - Invoice {invoice.invoice_number or invoice.id}",
        )
        db.add(ar_credit)

        await db.flush()

        # Post the journal entry
        je.status = JournalEntryStatus.POSTED
        je.approved_by = uuid.UUID(current_user.user_id)
        je.posted_at = datetime.now(timezone.utc)

        # Check if fully paid
        total_paid = existing_payments + data.amount
        if total_paid >= invoice.total_amount:
            invoice.status = InvoiceStatus.PAID

        invoice.updated_at = datetime.now(timezone.utc)

        await db.flush()
        await db.refresh(invoice)
        return invoice

    @staticmethod
    async def mark_overdue(
        db: AsyncSession,
        client_id: uuid.UUID,
        invoice_id: uuid.UUID,
    ) -> Invoice | None:
        """
        Transition a SENT invoice to OVERDUE (for invoices past due_date).

        Compliance (rule #4): ALWAYS filters by client_id.
        """
        invoice = await InvoiceService.get_invoice(db, client_id, invoice_id)
        if invoice is None:
            return None

        if invoice.status != InvoiceStatus.SENT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot mark invoice as overdue in status '{invoice.status.value}'. Only SENT invoices can be marked overdue.",
            )

        invoice.status = InvoiceStatus.OVERDUE
        invoice.updated_at = datetime.now(timezone.utc)
        await db.flush()
        await db.refresh(invoice)
        return invoice

    @staticmethod
    async def void_invoice(
        db: AsyncSession,
        client_id: uuid.UUID,
        invoice_id: uuid.UUID,
        current_user: CurrentUser,
        ar_account_id: uuid.UUID,
    ) -> Invoice | None:
        """
        Void an invoice. CPA_OWNER only. Creates reversing journal entry.

        Compliance (rule #2): Never hard delete. Void + reverse instead.
        Compliance (rule #5): Only CPA_OWNER can void.
        Compliance (rule #6): Role check at function level.
        """
        verify_role(current_user, "CPA_OWNER")

        invoice = await InvoiceService.get_invoice(db, client_id, invoice_id)
        if invoice is None:
            return None

        if invoice.status not in (InvoiceStatus.SENT, InvoiceStatus.OVERDUE):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot void invoice in status '{invoice.status.value}'. Only SENT or OVERDUE invoices can be voided.",
            )

        # Create reversing journal entry: credit AR, debit revenue accounts
        je = JournalEntry(
            client_id=client_id,
            entry_date=date.today(),
            description=f"VOID Invoice {invoice.invoice_number or invoice.id}: {invoice.customer_name}",
            reference_number=f"VOID-{invoice.invoice_number}" if invoice.invoice_number else None,
            status=JournalEntryStatus.DRAFT,
            created_by=uuid.UUID(current_user.user_id),
        )
        db.add(je)
        await db.flush()

        # Credit AR (reverse the debit)
        ar_line = JournalEntryLine(
            journal_entry_id=je.id,
            account_id=ar_account_id,
            debit=Decimal("0.00"),
            credit=invoice.total_amount,
            description=f"Reverse AR - Void Invoice {invoice.invoice_number or invoice.id}",
        )
        db.add(ar_line)

        # Debit each revenue account (reverse the credits)
        for inv_line in invoice.lines:
            if inv_line.deleted_at is not None:
                continue
            debit_line = JournalEntryLine(
                journal_entry_id=je.id,
                account_id=inv_line.account_id,
                debit=inv_line.amount,
                credit=Decimal("0.00"),
                description=f"Reverse revenue - Void Invoice {invoice.invoice_number or invoice.id}",
            )
            db.add(debit_line)

        await db.flush()

        # Post the reversing entry
        je.status = JournalEntryStatus.POSTED
        je.approved_by = uuid.UUID(current_user.user_id)
        je.posted_at = datetime.now(timezone.utc)

        invoice.status = InvoiceStatus.VOID
        invoice.updated_at = datetime.now(timezone.utc)

        await db.flush()
        await db.refresh(invoice)
        return invoice
