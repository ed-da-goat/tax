"""
Client statement service (C5).

Generates account statements showing open invoices, recent payments,
and current balance for a client over a date range.
"""

import uuid
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.reporting import ReportingService


class StatementService:

    @staticmethod
    async def generate_statement(
        db: AsyncSession,
        client_id: uuid.UUID,
        start_date: date,
        end_date: date,
    ) -> dict[str, Any]:
        """Generate a client account statement for a date range."""

        # Open invoices (SENT or OVERDUE as of end_date)
        r = await db.execute(text(
            "SELECT id, invoice_number, customer_name, invoice_date, due_date, "
            "       total_amount, status "
            "FROM invoices "
            "WHERE client_id = :cid AND deleted_at IS NULL "
            "  AND status IN ('SENT', 'OVERDUE') "
            "  AND invoice_date <= :end "
            "ORDER BY due_date"
        ), {"cid": str(client_id), "end": end_date})
        open_invoices = [
            {
                "id": str(row.id),
                "invoice_number": row.invoice_number,
                "customer_name": row.customer_name,
                "invoice_date": row.invoice_date.isoformat(),
                "due_date": row.due_date.isoformat() if row.due_date else None,
                "total_amount": float(row.total_amount),
                "status": row.status,
            }
            for row in r.all()
        ]

        # Payments received in the period
        r = await db.execute(text(
            "SELECT ip.id, ip.payment_date, ip.amount, ip.reference_number, "
            "       i.invoice_number, i.customer_name "
            "FROM invoice_payments ip "
            "JOIN invoices i ON i.id = ip.invoice_id "
            "WHERE i.client_id = :cid AND ip.deleted_at IS NULL "
            "  AND ip.payment_date >= :start AND ip.payment_date <= :end "
            "ORDER BY ip.payment_date"
        ), {"cid": str(client_id), "start": start_date, "end": end_date})
        payments = [
            {
                "id": str(row.id),
                "payment_date": row.payment_date.isoformat(),
                "amount": float(row.amount),
                "reference_number": row.reference_number,
                "invoice_number": row.invoice_number,
                "customer_name": row.customer_name,
            }
            for row in r.all()
        ]

        # Summary totals
        total_outstanding = sum(inv["total_amount"] for inv in open_invoices)
        total_payments = sum(p["amount"] for p in payments)

        # Client info
        r = await db.execute(text(
            "SELECT name, email, phone FROM clients WHERE id = :cid AND deleted_at IS NULL"
        ), {"cid": str(client_id)})
        client = r.one_or_none()

        return {
            "client_id": str(client_id),
            "client_name": client.name if client else "Unknown",
            "client_email": client.email if client else None,
            "period": f"{start_date.isoformat()} to {end_date.isoformat()}",
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "open_invoices": open_invoices,
            "payments": payments,
            "total_outstanding": total_outstanding,
            "total_payments": total_payments,
            "invoice_count": len(open_invoices),
        }

    @staticmethod
    async def generate_statement_pdf(
        db: AsyncSession,
        client_id: uuid.UUID,
        start_date: date,
        end_date: date,
    ) -> bytes:
        """Generate a PDF client statement."""
        data = await StatementService.generate_statement(db, client_id, start_date, end_date)

        invoice_rows = ""
        for inv in data["open_invoices"]:
            invoice_rows += f"""
            <tr>
                <td>{inv['invoice_number'] or '-'}</td>
                <td>{inv['customer_name'] or '-'}</td>
                <td>{inv['invoice_date']}</td>
                <td>{inv['due_date'] or '-'}</td>
                <td style="text-align:right">${inv['total_amount']:,.2f}</td>
                <td>{inv['status']}</td>
            </tr>"""

        payment_rows = ""
        for p in data["payments"]:
            payment_rows += f"""
            <tr>
                <td>{p['payment_date']}</td>
                <td>{p['invoice_number'] or '-'}</td>
                <td>{p['reference_number'] or '-'}</td>
                <td style="text-align:right">${p['amount']:,.2f}</td>
            </tr>"""

        html = f"""
        <html>
        <head><style>
            body {{ font-family: -apple-system, sans-serif; font-size: 11px; color: #1e1e2d; margin: 40px; }}
            h1 {{ font-size: 20px; margin-bottom: 4px; }}
            h2 {{ font-size: 14px; color: #6b7280; margin-bottom: 20px; }}
            h3 {{ font-size: 13px; margin: 24px 0 8px; }}
            table {{ width: 100%; border-collapse: collapse; margin-bottom: 16px; }}
            th, td {{ padding: 6px 8px; border-bottom: 1px solid #e0e2e7; text-align: left; }}
            th {{ background: #f5f6f8; font-weight: 600; font-size: 10px; text-transform: uppercase; }}
            .summary {{ display: flex; gap: 32px; margin: 16px 0; }}
            .summary-item {{ }}
            .summary-label {{ font-size: 10px; color: #6b7280; text-transform: uppercase; }}
            .summary-value {{ font-size: 18px; font-weight: 700; }}
        </style></head>
        <body>
            <h1>Account Statement</h1>
            <h2>{data['client_name']} &mdash; {data['period']}</h2>

            <div class="summary">
                <div class="summary-item">
                    <div class="summary-label">Outstanding</div>
                    <div class="summary-value">${data['total_outstanding']:,.2f}</div>
                </div>
                <div class="summary-item">
                    <div class="summary-label">Payments Received</div>
                    <div class="summary-value">${data['total_payments']:,.2f}</div>
                </div>
                <div class="summary-item">
                    <div class="summary-label">Open Invoices</div>
                    <div class="summary-value">{data['invoice_count']}</div>
                </div>
            </div>

            <h3>Open Invoices</h3>
            <table>
                <thead><tr><th>Invoice #</th><th>Customer</th><th>Date</th><th>Due</th><th style="text-align:right">Amount</th><th>Status</th></tr></thead>
                <tbody>{invoice_rows if invoice_rows else '<tr><td colspan="6" style="text-align:center;color:#6b7280">No open invoices</td></tr>'}</tbody>
            </table>

            <h3>Payments Received</h3>
            <table>
                <thead><tr><th>Date</th><th>Invoice</th><th>Reference</th><th style="text-align:right">Amount</th></tr></thead>
                <tbody>{payment_rows if payment_rows else '<tr><td colspan="4" style="text-align:center;color:#6b7280">No payments in period</td></tr>'}</tbody>
            </table>

            <p style="color:#6b7280; font-size:10px; margin-top:32px;">Generated by Georgia CPA Firm Accounting System</p>
        </body></html>
        """

        from weasyprint import HTML
        return HTML(string=html).write_pdf()
