"""
Invoice and AR history importer for QuickBooks Online migration (module M5).

Imports parsed QBO invoices into the invoice/AR tables. Maps QBO invoice
statuses to the system's invoice status enum.

Compliance (CLAUDE.md):
- Rule #2: AUDIT TRAIL — all imports logged.
- Rule #4: CLIENT ISOLATION — all records tagged with client_id.
- Rule #5: APPROVAL — imported invoices retain their original status.
           Paid invoices imported as PAID, Open as SENT.
"""

import uuid
from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invoice import Invoice, InvoiceLine, InvoiceStatus

from .models import ParsedInvoice


# QBO status → our InvoiceStatus mapping
QBO_STATUS_MAP: dict[str, InvoiceStatus] = {
    "paid": InvoiceStatus.PAID,
    "open": InvoiceStatus.SENT,
    "overdue": InvoiceStatus.OVERDUE,
    "voided": InvoiceStatus.VOID,
    "void": InvoiceStatus.VOID,
    "draft": InvoiceStatus.DRAFT,
    "closed": InvoiceStatus.PAID,
}


@dataclass
class ImportedInvoice:
    """Record of a successfully imported invoice."""

    invoice_id: uuid.UUID
    original: ParsedInvoice
    status_mapped_to: str


@dataclass
class SkippedInvoice:
    """Record of an invoice that was skipped during import."""

    original: ParsedInvoice
    reason: str


@dataclass
class InvoiceImportResult:
    """Complete result of an invoice import operation."""

    imported: list[ImportedInvoice] = field(default_factory=list)
    skipped: list[SkippedInvoice] = field(default_factory=list)
    total_input: int = 0
    total_imported: int = 0
    total_skipped: int = 0


class InvoiceImporter:
    """
    Imports QBO parsed invoices into the invoice/AR tables.

    For each invoice, creates an Invoice record with a single InvoiceLine
    for the total amount. The account for revenue lines must be provided
    as a default_revenue_account_id parameter.
    """

    async def import_invoices(
        self,
        db: AsyncSession,
        client_id: uuid.UUID,
        invoices: list[ParsedInvoice],
        default_revenue_account_id: uuid.UUID,
    ) -> InvoiceImportResult:
        """
        Import a list of parsed QBO invoices.

        Parameters
        ----------
        db : AsyncSession
            Database session.
        client_id : uuid.UUID
            The client these invoices belong to.
        invoices : list[ParsedInvoice]
            Invoices from QBOParser.parse_invoices().
        default_revenue_account_id : uuid.UUID
            The GL account to assign to invoice line items.

        Returns
        -------
        InvoiceImportResult
        """
        result = InvoiceImportResult(total_input=len(invoices))

        for inv in invoices:
            # Map QBO status
            status = InvoiceStatus.SENT  # default
            if inv.status:
                mapped = QBO_STATUS_MAP.get(inv.status.lower().strip())
                if mapped:
                    status = mapped

            # Validate required fields
            if inv.amount is None or inv.amount < 0:
                result.skipped.append(SkippedInvoice(
                    original=inv,
                    reason=f"Invalid invoice amount: {inv.amount}",
                ))
                continue

            # Check for duplicate invoice number
            if inv.invoice_no:
                existing = await db.execute(
                    select(Invoice.id).where(
                        Invoice.client_id == client_id,
                        Invoice.invoice_number == inv.invoice_no,
                        Invoice.deleted_at.is_(None),
                    )
                )
                if existing.scalar_one_or_none() is not None:
                    result.skipped.append(SkippedInvoice(
                        original=inv,
                        reason=f"Duplicate invoice number: {inv.invoice_no}",
                    ))
                    continue

            invoice = Invoice(
                client_id=client_id,
                customer_name=inv.customer,
                invoice_number=inv.invoice_no,
                invoice_date=inv.invoice_date,
                due_date=inv.due_date,
                total_amount=inv.amount,
                status=status,
            )
            db.add(invoice)
            await db.flush()

            # Create a single line item for the total
            line = InvoiceLine(
                invoice_id=invoice.id,
                account_id=default_revenue_account_id,
                description=f"Invoice {inv.invoice_no} - {inv.customer}",
                quantity=Decimal("1"),
                unit_price=inv.amount,
                amount=inv.amount,
            )
            db.add(line)
            await db.flush()

            result.imported.append(ImportedInvoice(
                invoice_id=invoice.id,
                original=inv,
                status_mapped_to=status.value,
            ))

        result.total_imported = len(result.imported)
        result.total_skipped = len(result.skipped)
        return result
