"""
Bulk import service (E3).

CSV upload for time entries, bills, and invoices with validation and error reporting.
"""

import csv
import io
import uuid
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Bill, BillLine, BillStatus,
    Invoice, InvoiceLine, InvoiceStatus,
    ChartOfAccounts, Vendor,
)


MAX_IMPORT_ROWS = 5000


class BulkImportService:

    @staticmethod
    async def import_bills_csv(
        db: AsyncSession,
        client_id: uuid.UUID,
        csv_content: str,
    ) -> dict[str, Any]:
        """
        Import bills from CSV. Expected columns:
        vendor_name, bill_number, bill_date (YYYY-MM-DD), due_date, description, amount, account_number
        """
        rows = list(csv.DictReader(io.StringIO(csv_content)))
        if len(rows) > MAX_IMPORT_ROWS:
            raise ValueError(f"CSV exceeds maximum of {MAX_IMPORT_ROWS} rows ({len(rows)} provided)")

        errors = []
        created = []
        row_num = 1

        # Pre-load vendors and accounts for this client
        v_result = await db.execute(
            select(Vendor).where(Vendor.client_id == client_id, Vendor.deleted_at.is_(None))
        )
        vendors = {v.name.lower(): v for v in v_result.scalars().all()}

        a_result = await db.execute(
            select(ChartOfAccounts).where(ChartOfAccounts.client_id == client_id, ChartOfAccounts.deleted_at.is_(None))
        )
        accounts = {a.account_number: a for a in a_result.scalars().all()}

        for row in rows:
            row_num += 1
            try:
                vendor_name = row.get("vendor_name", "").strip()
                vendor = vendors.get(vendor_name.lower())
                if not vendor:
                    errors.append({"row": row_num, "error": f"Vendor not found: {vendor_name}"})
                    continue

                acct_num = row.get("account_number", "").strip()
                account = accounts.get(acct_num)
                if not account:
                    errors.append({"row": row_num, "error": f"Account not found: {acct_num}"})
                    continue

                amount = Decimal(row.get("amount", "0").strip())
                bill_date = date.fromisoformat(row.get("bill_date", "").strip())
                due_date = date.fromisoformat(row.get("due_date", "").strip())

                bill = Bill(
                    client_id=client_id,
                    vendor_id=vendor.id,
                    bill_number=row.get("bill_number", "").strip() or None,
                    bill_date=bill_date,
                    due_date=due_date,
                    total_amount=amount,
                    status=BillStatus.DRAFT,
                )
                db.add(bill)
                await db.flush()

                db.add(BillLine(
                    bill_id=bill.id,
                    account_id=account.id,
                    description=row.get("description", "").strip() or None,
                    amount=amount,
                ))
                created.append({"bill_id": str(bill.id), "bill_number": bill.bill_number})

            except (ValueError, InvalidOperation, KeyError) as e:
                errors.append({"row": row_num, "error": str(e)})

        await db.flush()
        return {"imported": len(created), "errors": errors, "bills": created}

    @staticmethod
    async def import_invoices_csv(
        db: AsyncSession,
        client_id: uuid.UUID,
        csv_content: str,
    ) -> dict[str, Any]:
        """
        Import invoices from CSV. Expected columns:
        customer_name, invoice_number, invoice_date (YYYY-MM-DD), due_date, description, quantity, unit_price, account_number
        """
        rows = list(csv.DictReader(io.StringIO(csv_content)))
        if len(rows) > MAX_IMPORT_ROWS:
            raise ValueError(f"CSV exceeds maximum of {MAX_IMPORT_ROWS} rows ({len(rows)} provided)")

        errors = []
        created = []
        row_num = 1

        a_result = await db.execute(
            select(ChartOfAccounts).where(ChartOfAccounts.client_id == client_id, ChartOfAccounts.deleted_at.is_(None))
        )
        accounts = {a.account_number: a for a in a_result.scalars().all()}

        for row in rows:
            row_num += 1
            try:
                acct_num = row.get("account_number", "").strip()
                account = accounts.get(acct_num)
                if not account:
                    errors.append({"row": row_num, "error": f"Account not found: {acct_num}"})
                    continue

                qty = Decimal(row.get("quantity", "1").strip())
                price = Decimal(row.get("unit_price", "0").strip())
                amount = qty * price
                inv_date = date.fromisoformat(row.get("invoice_date", "").strip())
                due_date = date.fromisoformat(row.get("due_date", "").strip())

                invoice = Invoice(
                    client_id=client_id,
                    customer_name=row.get("customer_name", "").strip(),
                    invoice_number=row.get("invoice_number", "").strip() or None,
                    invoice_date=inv_date,
                    due_date=due_date,
                    total_amount=amount,
                    status=InvoiceStatus.DRAFT,
                )
                db.add(invoice)
                await db.flush()

                db.add(InvoiceLine(
                    invoice_id=invoice.id,
                    account_id=account.id,
                    description=row.get("description", "").strip() or None,
                    quantity=qty,
                    unit_price=price,
                    amount=amount,
                ))
                created.append({"invoice_id": str(invoice.id), "invoice_number": invoice.invoice_number})

            except (ValueError, InvalidOperation, KeyError) as e:
                errors.append({"row": row_num, "error": str(e)})

        await db.flush()
        return {"imported": len(created), "errors": errors, "invoices": created}

    @staticmethod
    def generate_template(entity_type: str) -> str:
        """Generate a CSV template with headers for the given entity type."""
        templates = {
            "bills": "vendor_name,bill_number,bill_date,due_date,description,amount,account_number\n",
            "invoices": "customer_name,invoice_number,invoice_date,due_date,description,quantity,unit_price,account_number\n",
        }
        return templates.get(entity_type, "")
