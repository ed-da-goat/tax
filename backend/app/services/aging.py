"""
AR/AP Aging Report service.

Groups outstanding invoices/bills into aging buckets (Current, 1-30, 31-60,
61-90, 90+) with per-customer/vendor breakdowns.

Compliance (CLAUDE.md):
- Rule #4: CLIENT ISOLATION — every query filters by client_id.
"""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.aging import (
    AgingBucketSummary,
    AgingDetail,
    APAgingReport,
    ARAgingReport,
)

BUCKET_LABELS = ["Current", "1-30", "31-60", "61-90", "90+"]


def _classify_bucket(days_past_due: int) -> str:
    if days_past_due <= 0:
        return "Current"
    elif days_past_due <= 30:
        return "1-30"
    elif days_past_due <= 60:
        return "31-60"
    elif days_past_due <= 90:
        return "61-90"
    else:
        return "90+"


class AgingService:
    """Generates AR and AP aging reports."""

    @staticmethod
    async def get_ar_aging(
        db: AsyncSession,
        client_id: uuid.UUID,
        as_of_date: date,
    ) -> ARAgingReport:
        """
        AR aging: outstanding invoices (SENT or OVERDUE).

        Compliance (rule #4): ALWAYS filters by client_id.
        """
        stmt = text(
            "SELECT "
            "    i.id, "
            "    i.invoice_number, "
            "    i.customer_name, "
            "    i.invoice_date, "
            "    i.due_date, "
            "    i.total_amount, "
            "    COALESCE(("
            "        SELECT SUM(ip.amount) FROM invoice_payments ip "
            "        WHERE ip.invoice_id = i.id AND ip.deleted_at IS NULL"
            "    ), 0) AS amount_paid "
            "FROM invoices i "
            "WHERE i.client_id = :client_id "
            "    AND i.deleted_at IS NULL "
            "    AND i.status IN ('SENT', 'OVERDUE') "
            "ORDER BY i.due_date"
        )
        result = await db.execute(stmt, {"client_id": str(client_id)})
        rows = result.all()

        details = []
        bucket_totals: dict[str, Decimal] = {b: Decimal("0.00") for b in BUCKET_LABELS}
        bucket_counts: dict[str, int] = {b: 0 for b in BUCKET_LABELS}

        for row in rows:
            outstanding = row.total_amount - row.amount_paid
            if outstanding <= 0:
                continue

            days = max((as_of_date - row.due_date).days, 0)
            bucket = _classify_bucket(days)

            details.append(AgingDetail(
                id=row.id,
                number=row.invoice_number,
                counterparty=row.customer_name,
                date_issued=row.invoice_date,
                due_date=row.due_date,
                total_amount=row.total_amount,
                amount_paid=row.amount_paid,
                outstanding=outstanding,
                days_past_due=days,
                bucket=bucket,
            ))
            bucket_totals[bucket] += outstanding
            bucket_counts[bucket] += 1

        buckets = [
            AgingBucketSummary(bucket=b, total=bucket_totals[b], count=bucket_counts[b])
            for b in BUCKET_LABELS
        ]
        total_outstanding = sum(d.outstanding for d in details)

        return ARAgingReport(
            client_id=client_id,
            as_of_date=as_of_date,
            details=details,
            buckets=buckets,
            total_outstanding=total_outstanding,
        )

    @staticmethod
    async def get_ap_aging(
        db: AsyncSession,
        client_id: uuid.UUID,
        as_of_date: date,
    ) -> APAgingReport:
        """
        AP aging: outstanding bills (APPROVED status).

        Compliance (rule #4): ALWAYS filters by client_id.
        """
        stmt = text(
            "SELECT "
            "    b.id, "
            "    b.bill_number, "
            "    v.name AS vendor_name, "
            "    b.bill_date, "
            "    b.due_date, "
            "    b.total_amount, "
            "    COALESCE(("
            "        SELECT SUM(bp.amount) FROM bill_payments bp "
            "        WHERE bp.bill_id = b.id AND bp.deleted_at IS NULL"
            "    ), 0) AS amount_paid "
            "FROM bills b "
            "INNER JOIN vendors v ON v.id = b.vendor_id "
            "WHERE b.client_id = :client_id "
            "    AND b.deleted_at IS NULL "
            "    AND b.status = 'APPROVED' "
            "ORDER BY b.due_date"
        )
        result = await db.execute(stmt, {"client_id": str(client_id)})
        rows = result.all()

        details = []
        bucket_totals: dict[str, Decimal] = {b: Decimal("0.00") for b in BUCKET_LABELS}
        bucket_counts: dict[str, int] = {b: 0 for b in BUCKET_LABELS}

        for row in rows:
            outstanding = row.total_amount - row.amount_paid
            if outstanding <= 0:
                continue

            days = max((as_of_date - row.due_date).days, 0)
            bucket = _classify_bucket(days)

            details.append(AgingDetail(
                id=row.id,
                number=row.bill_number,
                counterparty=row.vendor_name,
                date_issued=row.bill_date,
                due_date=row.due_date,
                total_amount=row.total_amount,
                amount_paid=row.amount_paid,
                outstanding=outstanding,
                days_past_due=days,
                bucket=bucket,
            ))
            bucket_totals[bucket] += outstanding
            bucket_counts[bucket] += 1

        buckets = [
            AgingBucketSummary(bucket=b, total=bucket_totals[b], count=bucket_counts[b])
            for b in BUCKET_LABELS
        ]
        total_outstanding = sum(d.outstanding for d in details)

        return APAgingReport(
            client_id=client_id,
            as_of_date=as_of_date,
            details=details,
            buckets=buckets,
            total_outstanding=total_outstanding,
        )

    @staticmethod
    async def generate_aging_pdf(
        report: ARAgingReport | APAgingReport,
    ) -> bytes:
        """Generate a PDF from an aging report."""
        from weasyprint import HTML

        html = _build_aging_html(report)
        return HTML(string=html).write_pdf()


def _format_currency(amount: Decimal) -> str:
    return f"${amount:,.2f}"


def _build_aging_html(report: ARAgingReport | APAgingReport) -> str:
    is_ar = isinstance(report, ARAgingReport)
    title = "Accounts Receivable Aging Report" if is_ar else "Accounts Payable Aging Report"
    counterparty_label = "Customer" if is_ar else "Vendor"

    bucket_header = "".join(f"<th class='amount'>{b}</th>" for b in BUCKET_LABELS)
    bucket_summary_row = "".join(
        f"<td class='amount'>{_format_currency(b.total)}</td>"
        for b in report.buckets
    )

    detail_rows = ""
    for d in report.details:
        bucket_cells = ""
        for b in BUCKET_LABELS:
            if d.bucket == b:
                bucket_cells += f"<td class='amount'>{_format_currency(d.outstanding)}</td>"
            else:
                bucket_cells += "<td class='amount'>-</td>"
        detail_rows += (
            f"<tr>"
            f"<td>{d.counterparty}</td>"
            f"<td>{d.number or '-'}</td>"
            f"<td>{d.due_date}</td>"
            f"<td class='amount'>{_format_currency(d.total_amount)}</td>"
            f"<td class='amount'>{_format_currency(d.outstanding)}</td>"
            f"{bucket_cells}"
            f"</tr>"
        )

    return f"""<!DOCTYPE html>
<html><head><style>
    @page {{ size: letter landscape; margin: 0.5in; }}
    body {{ font-family: Arial, sans-serif; font-size: 9pt; }}
    h1 {{ font-size: 16pt; border-bottom: 2px solid #333; padding-bottom: 8px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
    th {{ background: #2c3e50; color: white; padding: 6px 8px; text-align: left; font-size: 8pt; }}
    td {{ padding: 5px 8px; border-bottom: 1px solid #eee; font-size: 8pt; }}
    .amount {{ text-align: right; font-family: monospace; }}
    .total-row {{ font-weight: bold; border-top: 2px solid #333; }}
    .footer {{ text-align: center; font-size: 7pt; color: #999; margin-top: 15px; }}
</style></head>
<body>
    <h1>{title}</h1>
    <p>As of: {report.as_of_date}</p>

    <table>
        <tr>
            <th>{counterparty_label}</th>
            <th>Number</th>
            <th>Due Date</th>
            <th class="amount">Total</th>
            <th class="amount">Outstanding</th>
            {bucket_header}
        </tr>
        {detail_rows}
        <tr class="total-row">
            <td colspan="4">Total</td>
            <td class="amount">{_format_currency(report.total_outstanding)}</td>
            {bucket_summary_row}
        </tr>
    </table>

    <div class="footer">Generated by Georgia CPA Accounting System</div>
</body></html>"""
