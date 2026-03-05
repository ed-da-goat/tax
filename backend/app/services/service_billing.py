"""
Service layer for firm-to-client service invoicing (PM2).
"""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, verify_role
from app.models.service_invoice import (
    ServiceInvoice, ServiceInvoiceLine, ServiceInvoicePayment,
    ServiceInvoiceStatus, PaymentMethod,
)
from app.models.time_entry import TimeEntry, TimeEntryStatus
from app.schemas.service_invoice import (
    ServiceInvoiceCreate, ServiceInvoiceUpdate, ServiceInvoicePaymentCreate,
)


class ServiceBillingService:

    @staticmethod
    async def _next_invoice_number(db: AsyncSession) -> str:
        result = await db.execute(
            select(func.count(ServiceInvoice.id))
        )
        count = (result.scalar() or 0) + 1
        return f"SI-{count:05d}"

    @staticmethod
    async def create_invoice(
        db: AsyncSession, data: ServiceInvoiceCreate, current_user: CurrentUser,
    ) -> ServiceInvoice:
        verify_role(current_user, "CPA_OWNER")

        invoice_number = await ServiceBillingService._next_invoice_number(db)
        invoice = ServiceInvoice(
            client_id=data.client_id,
            invoice_number=invoice_number,
            invoice_date=data.invoice_date,
            due_date=data.due_date,
            status=ServiceInvoiceStatus.DRAFT,
            notes=data.notes,
            terms=data.terms,
            discount_amount=data.discount_amount,
            is_recurring=data.is_recurring,
            recurrence_interval=data.recurrence_interval,
            engagement_id=data.engagement_id,
        )
        db.add(invoice)
        await db.flush()

        subtotal = Decimal("0")
        for line_data in data.lines:
            amount = line_data.quantity * line_data.unit_price
            line = ServiceInvoiceLine(
                invoice_id=invoice.id,
                description=line_data.description,
                quantity=line_data.quantity,
                unit_price=line_data.unit_price,
                amount=amount,
                service_type=line_data.service_type,
                time_entry_id=line_data.time_entry_id,
            )
            db.add(line)
            subtotal += amount

        invoice.subtotal = subtotal
        invoice.total_amount = subtotal - data.discount_amount
        invoice.balance_due = invoice.total_amount

        await db.commit()
        await db.refresh(invoice)
        return invoice

    @staticmethod
    async def create_invoice_from_time(
        db: AsyncSession, client_id: uuid.UUID,
        date_from: date, date_to: date,
        current_user: CurrentUser,
    ) -> ServiceInvoice:
        """Create an invoice from approved time entries."""
        verify_role(current_user, "CPA_OWNER")

        result = await db.execute(
            select(TimeEntry).where(
                TimeEntry.client_id == client_id,
                TimeEntry.status == TimeEntryStatus.APPROVED,
                TimeEntry.is_billable.is_(True),
                TimeEntry.date >= date_from,
                TimeEntry.date <= date_to,
                TimeEntry.deleted_at.is_(None),
            ).order_by(TimeEntry.date)
        )
        entries = list(result.scalars().all())
        if not entries:
            raise HTTPException(status_code=400, detail="No billable approved time entries found")

        lines = []
        for entry in entries:
            hours = Decimal(entry.duration_minutes) / Decimal("60")
            rate = entry.hourly_rate or Decimal("0")
            lines.append(ServiceInvoiceLine(
                description=f"{entry.service_type or 'Professional Services'} — {entry.date} ({hours:.1f}h)",
                quantity=hours,
                unit_price=rate,
                amount=entry.amount or (hours * rate),
                time_entry_id=entry.id,
                service_type=entry.service_type,
            ))

        invoice_number = await ServiceBillingService._next_invoice_number(db)
        subtotal = sum(l.amount for l in lines)
        invoice = ServiceInvoice(
            client_id=client_id,
            invoice_number=invoice_number,
            invoice_date=date.today(),
            due_date=date.today(),
            subtotal=subtotal,
            total_amount=subtotal,
            balance_due=subtotal,
            status=ServiceInvoiceStatus.DRAFT,
        )
        db.add(invoice)
        await db.flush()

        for line in lines:
            line.invoice_id = invoice.id
            db.add(line)

        for entry in entries:
            entry.status = TimeEntryStatus.BILLED

        await db.commit()
        await db.refresh(invoice)
        return invoice

    @staticmethod
    async def list_invoices(
        db: AsyncSession,
        client_id: uuid.UUID | None = None,
        status_filter: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[ServiceInvoice], int]:
        query = select(ServiceInvoice).where(ServiceInvoice.deleted_at.is_(None))
        count_q = select(func.count(ServiceInvoice.id)).where(ServiceInvoice.deleted_at.is_(None))

        if client_id:
            query = query.where(ServiceInvoice.client_id == client_id)
            count_q = count_q.where(ServiceInvoice.client_id == client_id)
        if status_filter:
            query = query.where(ServiceInvoice.status == status_filter)
            count_q = count_q.where(ServiceInvoice.status == status_filter)

        total = (await db.execute(count_q)).scalar() or 0
        result = await db.execute(
            query.order_by(ServiceInvoice.invoice_date.desc()).offset(skip).limit(limit)
        )
        return list(result.scalars().unique().all()), total

    @staticmethod
    async def get_invoice(
        db: AsyncSession, invoice_id: uuid.UUID,
    ) -> ServiceInvoice:
        result = await db.execute(
            select(ServiceInvoice).where(
                ServiceInvoice.id == invoice_id,
                ServiceInvoice.deleted_at.is_(None),
            )
        )
        invoice = result.scalar_one_or_none()
        if not invoice:
            raise HTTPException(status_code=404, detail="Service invoice not found")
        return invoice

    @staticmethod
    async def send_invoice(
        db: AsyncSession, invoice_id: uuid.UUID, current_user: CurrentUser,
    ) -> ServiceInvoice:
        verify_role(current_user, "CPA_OWNER")
        invoice = await ServiceBillingService.get_invoice(db, invoice_id)
        if invoice.status != ServiceInvoiceStatus.DRAFT:
            raise HTTPException(status_code=400, detail="Invoice must be in DRAFT status to send")
        invoice.status = ServiceInvoiceStatus.SENT
        invoice.sent_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(invoice)
        return invoice

    @staticmethod
    async def record_payment(
        db: AsyncSession, invoice_id: uuid.UUID,
        data: ServiceInvoicePaymentCreate, current_user: CurrentUser,
    ) -> ServiceInvoice:
        verify_role(current_user, "CPA_OWNER")
        invoice = await ServiceBillingService.get_invoice(db, invoice_id)

        if invoice.status == ServiceInvoiceStatus.VOID:
            raise HTTPException(status_code=400, detail="Cannot pay voided invoice")

        payment = ServiceInvoicePayment(
            invoice_id=invoice.id,
            payment_date=data.payment_date,
            amount=data.amount,
            payment_method=PaymentMethod(data.payment_method.value),
            reference_number=data.reference_number,
            notes=data.notes,
        )
        db.add(payment)

        invoice.amount_paid += data.amount
        invoice.balance_due = invoice.total_amount - invoice.amount_paid

        if invoice.balance_due <= 0:
            invoice.status = ServiceInvoiceStatus.PAID
            invoice.balance_due = Decimal("0")
        else:
            invoice.status = ServiceInvoiceStatus.PARTIAL

        await db.commit()
        await db.refresh(invoice)
        return invoice

    @staticmethod
    async def void_invoice(
        db: AsyncSession, invoice_id: uuid.UUID, current_user: CurrentUser,
    ) -> ServiceInvoice:
        verify_role(current_user, "CPA_OWNER")
        invoice = await ServiceBillingService.get_invoice(db, invoice_id)
        if invoice.status == ServiceInvoiceStatus.VOID:
            raise HTTPException(status_code=400, detail="Already voided")
        invoice.status = ServiceInvoiceStatus.VOID
        await db.commit()
        await db.refresh(invoice)
        return invoice
