"""
1099-NEC data aggregation and PDF generation service.

Sums bill payments to 1099-eligible vendors for a tax year.
Generates substitute 1099-NEC PDFs for vendors receiving >= $600.

Compliance (CLAUDE.md):
- Rule #4: CLIENT ISOLATION — every query filters by client_id.
"""

import uuid
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.form_1099 import Form1099NECData, Form1099NECSummaryResponse

# IRS filing threshold for 1099-NEC
FILING_THRESHOLD = Decimal("600.00")


def _format_currency(amount: Decimal) -> str:
    return f"${amount:,.2f}"


class Form1099NECService:
    """Generates 1099-NEC data and PDFs."""

    @staticmethod
    async def get_1099_data(
        db: AsyncSession,
        client_id: uuid.UUID,
        tax_year: int,
    ) -> Form1099NECSummaryResponse:
        """
        Aggregate payments to 1099-eligible vendors for a tax year.

        Only includes vendors with total payments >= $600.
        Only includes payments from PAID bills within the tax year.
        Compliance (rule #4): ALWAYS filters by client_id.
        """
        # Get payer info
        client_stmt = text(
            "SELECT name, address, city, state, zip "
            "FROM clients WHERE id = :client_id AND deleted_at IS NULL"
        )
        client_result = await db.execute(client_stmt, {"client_id": str(client_id)})
        client_row = client_result.one_or_none()
        if client_row is None:
            from fastapi import HTTPException, status
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

        payer_addr_parts = [p for p in [client_row.address, client_row.city, client_row.state, client_row.zip] if p]
        payer_address = ", ".join(payer_addr_parts) if payer_addr_parts else None

        # Sum payments per 1099-eligible vendor
        stmt = text(
            "SELECT "
            "    v.id AS vendor_id, "
            "    v.name AS vendor_name, "
            "    v.address, "
            "    v.city, "
            "    v.state, "
            "    v.zip, "
            "    COALESCE(SUM(bp.amount), 0) AS total_paid "
            "FROM vendors v "
            "INNER JOIN bills b ON b.vendor_id = v.id "
            "    AND b.client_id = :client_id "
            "    AND b.deleted_at IS NULL "
            "INNER JOIN bill_payments bp ON bp.bill_id = b.id "
            "    AND bp.deleted_at IS NULL "
            "    AND EXTRACT(YEAR FROM bp.payment_date) = :tax_year "
            "WHERE v.client_id = :client_id "
            "    AND v.deleted_at IS NULL "
            "    AND v.is_1099_eligible = TRUE "
            "GROUP BY v.id, v.name, v.address, v.city, v.state, v.zip "
            "HAVING COALESCE(SUM(bp.amount), 0) >= :threshold "
            "ORDER BY v.name"
        )
        result = await db.execute(stmt, {
            "client_id": str(client_id),
            "tax_year": tax_year,
            "threshold": FILING_THRESHOLD,
        })
        rows = result.all()

        forms = []
        total_comp = Decimal("0.00")

        for row in rows:
            form = Form1099NECData(
                vendor_id=row.vendor_id,
                vendor_name=row.vendor_name,
                vendor_address=row.address,
                vendor_city=row.city,
                vendor_state=row.state,
                vendor_zip=row.zip,
                tax_year=tax_year,
                box1_nonemployee_compensation=row.total_paid,
            )
            forms.append(form)
            total_comp += row.total_paid

        return Form1099NECSummaryResponse(
            client_id=client_id,
            tax_year=tax_year,
            payer_name=client_row.name,
            payer_address=payer_address,
            forms=forms,
            total_nonemployee_compensation=total_comp,
        )

    @staticmethod
    def generate_1099_pdf(
        form: Form1099NECData,
        payer_name: str,
        payer_address: str | None,
    ) -> bytes:
        """Generate a single substitute 1099-NEC PDF."""
        from weasyprint import HTML

        html = _build_1099_html(form, payer_name, payer_address)
        return HTML(string=html).write_pdf()

    @staticmethod
    def generate_batch_1099_pdf(summary: Form1099NECSummaryResponse) -> bytes:
        """Generate a batch PDF with all 1099-NECs for a tax year."""
        from weasyprint import HTML

        pages = []
        for form in summary.forms:
            pages.append(_build_1099_html(form, summary.payer_name, summary.payer_address))

        if not pages:
            pages.append(
                "<html><body><h1>No 1099-NEC Data</h1>"
                "<p>No eligible vendor payments found for this tax year.</p></body></html>"
            )

        combined = "<html><head>" + _1099_styles() + "</head><body>"
        for i, page_body in enumerate(pages):
            if i > 0:
                combined += '<div style="page-break-before: always;"></div>'
            body_start = page_body.find("<body>")
            body_end = page_body.find("</body>")
            if body_start >= 0 and body_end >= 0:
                combined += page_body[body_start + 6:body_end]
            else:
                combined += page_body
        combined += "</body></html>"

        return HTML(string=combined).write_pdf()


def _1099_styles() -> str:
    return """<style>
    @page { size: letter; margin: 0.5in; }
    body { font-family: Arial, sans-serif; font-size: 9pt; color: #333; }
    .form-1099 { border: 2px solid #000; padding: 15px; }
    .form-header { text-align: center; font-size: 14pt; font-weight: bold; margin-bottom: 10px; }
    .form-subtitle { text-align: center; font-size: 8pt; color: #666; margin-bottom: 15px; }
    .info-section { margin-bottom: 12px; padding: 8px; background: #f5f5f5; }
    .info-label { font-size: 7pt; color: #666; text-transform: uppercase; }
    .info-value { font-size: 10pt; }
    .box { border: 1px solid #999; padding: 10px; margin-top: 10px; }
    .box-label { font-size: 7pt; color: #666; }
    .box-value { font-size: 16pt; font-weight: bold; font-family: monospace; }
    .footer { text-align: center; font-size: 7pt; color: #999; margin-top: 15px; }
</style>"""


def _build_1099_html(
    form: Form1099NECData,
    payer_name: str,
    payer_address: str | None,
) -> str:
    vendor_addr_parts = [p for p in [form.vendor_address, form.vendor_city, form.vendor_state, form.vendor_zip] if p]
    vendor_addr = ", ".join(vendor_addr_parts) if vendor_addr_parts else "N/A"

    return f"""<!DOCTYPE html>
<html><head>{_1099_styles()}</head>
<body>
<div class="form-1099">
    <div class="form-header">1099-NEC Nonemployee Compensation {form.tax_year}</div>
    <div class="form-subtitle">Substitute Form 1099-NEC &mdash; For recipient information only</div>

    <div class="info-section">
        <div class="info-label">Payer</div>
        <div class="info-value">{payer_name}</div>
        <div class="info-value" style="font-size:8pt;">{payer_address or 'N/A'}</div>
    </div>
    <div class="info-section">
        <div class="info-label">Recipient</div>
        <div class="info-value">{form.vendor_name}</div>
        <div class="info-value" style="font-size:8pt;">{vendor_addr}</div>
    </div>

    <div class="box">
        <div class="box-label">1 - Nonemployee compensation</div>
        <div class="box-value">{_format_currency(form.box1_nonemployee_compensation)}</div>
    </div>
</div>
<div class="footer">Substitute Form 1099-NEC &mdash; Generated by Georgia CPA Accounting System</div>
</body></html>"""
