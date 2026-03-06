"""
W-2 data aggregation and PDF generation service.

Aggregates all FINALIZED payroll runs for a tax year per employee
into W-2 box values. Generates substitute W-2 PDFs via WeasyPrint.

Compliance (CLAUDE.md):
- Rule #4: CLIENT ISOLATION — every query filters by client_id.
- Rule #5: Only FINALIZED payroll runs contribute.
"""

import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.w2 import W2Data, W2SummaryResponse
from app.services.payroll.federal_tax import SS_WAGE_BASES


def _format_currency(amount: Decimal) -> str:
    return f"${amount:,.2f}"


class W2GeneratorService:
    """Generates W-2 data and PDFs for a client's employees."""

    @staticmethod
    async def get_w2_data(
        db: AsyncSession,
        client_id: uuid.UUID,
        tax_year: int,
    ) -> W2SummaryResponse:
        """
        Aggregate all FINALIZED payroll data for a tax year into W-2 boxes.

        Uses pay date method: filters by payroll_runs.pay_date year.
        Compliance (rule #4): ALWAYS filters by client_id.
        """
        # Get employer info
        client_stmt = text(
            "SELECT name, address, city, state, zip "
            "FROM clients WHERE id = :client_id AND deleted_at IS NULL"
        )
        client_result = await db.execute(client_stmt, {"client_id": str(client_id)})
        client_row = client_result.one_or_none()
        if client_row is None:
            from fastapi import HTTPException, status
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

        employer_addr_parts = [p for p in [client_row.address, client_row.city, client_row.state, client_row.zip] if p]
        employer_address = ", ".join(employer_addr_parts) if employer_addr_parts else None

        # Aggregate payroll items per employee for FINALIZED runs in tax year
        stmt = text(
            "SELECT "
            "    e.id AS employee_id, "
            "    e.first_name, "
            "    e.last_name, "
            "    e.address, "
            "    e.city, "
            "    e.state, "
            "    e.zip, "
            "    COALESCE(SUM(pi.gross_pay), 0) AS total_gross, "
            "    COALESCE(SUM(pi.federal_withholding), 0) AS total_federal, "
            "    COALESCE(SUM(pi.social_security), 0) AS total_ss, "
            "    COALESCE(SUM(pi.medicare), 0) AS total_medicare, "
            "    COALESCE(SUM(pi.state_withholding), 0) AS total_state "
            "FROM payroll_items pi "
            "INNER JOIN payroll_runs pr ON pr.id = pi.payroll_run_id "
            "    AND pr.status = 'FINALIZED' "
            "    AND pr.deleted_at IS NULL "
            "    AND pr.client_id = :client_id "
            "    AND EXTRACT(YEAR FROM pr.pay_date) = :tax_year "
            "INNER JOIN employees e ON e.id = pi.employee_id "
            "    AND e.deleted_at IS NULL "
            "WHERE pi.deleted_at IS NULL "
            "GROUP BY e.id, e.first_name, e.last_name, e.address, e.city, e.state, e.zip "
            "ORDER BY e.last_name, e.first_name"
        )
        result = await db.execute(stmt, {
            "client_id": str(client_id),
            "tax_year": tax_year,
        })
        rows = result.all()

        w2s = []
        total_wages = Decimal("0.00")
        total_fed = Decimal("0.00")

        for row in rows:
            gross = row.total_gross
            ss_base = SS_WAGE_BASES.get(tax_year, SS_WAGE_BASES[max(SS_WAGE_BASES.keys())])
            ss_wages = min(gross, ss_base)

            w2 = W2Data(
                employee_id=row.employee_id,
                employee_first_name=row.first_name,
                employee_last_name=row.last_name,
                employee_address=row.address,
                employee_city=row.city,
                employee_state=row.state,
                employee_zip=row.zip,
                tax_year=tax_year,
                box1_wages=gross,
                box2_federal_withheld=row.total_federal,
                box3_ss_wages=ss_wages,
                box4_ss_tax=row.total_ss,
                box5_medicare_wages=gross,
                box6_medicare_tax=row.total_medicare,
                box16_state_wages=gross,
                box17_state_tax=row.total_state,
            )
            w2s.append(w2)
            total_wages += gross
            total_fed += row.total_federal

        return W2SummaryResponse(
            client_id=client_id,
            tax_year=tax_year,
            employer_name=client_row.name,
            employer_address=employer_address,
            w2s=w2s,
            total_wages=total_wages,
            total_federal_withheld=total_fed,
        )

    @staticmethod
    def generate_w2_pdf(w2: W2Data, employer_name: str, employer_address: str | None) -> bytes:
        """Generate a single substitute W-2 PDF."""
        from weasyprint import HTML

        html = _build_w2_html(w2, employer_name, employer_address)
        return HTML(string=html).write_pdf()

    @staticmethod
    def generate_batch_w2_pdf(
        summary: W2SummaryResponse,
    ) -> bytes:
        """Generate a batch PDF with all W-2s for a tax year."""
        from weasyprint import HTML

        pages = []
        for w2 in summary.w2s:
            pages.append(_build_w2_html(w2, summary.employer_name, summary.employer_address))

        if not pages:
            pages.append(
                "<html><body><h1>No W-2 Data</h1>"
                "<p>No finalized payroll found for this tax year.</p></body></html>"
            )

        combined = "<html><head>" + _w2_styles() + "</head><body>"
        for i, page_body in enumerate(pages):
            if i > 0:
                combined += '<div style="page-break-before: always;"></div>'
            # Extract body content
            body_start = page_body.find("<body>")
            body_end = page_body.find("</body>")
            if body_start >= 0 and body_end >= 0:
                combined += page_body[body_start + 6:body_end]
            else:
                combined += page_body
        combined += "</body></html>"

        return HTML(string=combined).write_pdf()


def _w2_styles() -> str:
    return """<style>
    @page { size: letter; margin: 0.5in; }
    body { font-family: Arial, sans-serif; font-size: 9pt; color: #333; }
    .w2-form { border: 2px solid #000; padding: 15px; }
    .w2-header { text-align: center; font-size: 14pt; font-weight: bold; margin-bottom: 10px; }
    .w2-subtitle { text-align: center; font-size: 8pt; color: #666; margin-bottom: 15px; }
    .box-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
    .box { border: 1px solid #999; padding: 6px; }
    .box-label { font-size: 7pt; color: #666; }
    .box-value { font-size: 11pt; font-weight: bold; font-family: monospace; }
    .info-section { margin-bottom: 12px; padding: 8px; background: #f5f5f5; }
    .info-label { font-size: 7pt; color: #666; text-transform: uppercase; }
    .info-value { font-size: 10pt; }
    .footer { text-align: center; font-size: 7pt; color: #999; margin-top: 15px; }
</style>"""


def _build_w2_html(w2: W2Data, employer_name: str, employer_address: str | None) -> str:
    emp_addr_parts = [p for p in [w2.employee_address, w2.employee_city, w2.employee_state, w2.employee_zip] if p]
    emp_addr = ", ".join(emp_addr_parts) if emp_addr_parts else "N/A"

    return f"""<!DOCTYPE html>
<html><head>{_w2_styles()}</head>
<body>
<div class="w2-form">
    <div class="w2-header">W-2 Wage and Tax Statement {w2.tax_year}</div>
    <div class="w2-subtitle">Substitute Form W-2 &mdash; Not for filing with SSA</div>

    <div class="info-section">
        <div class="info-label">Employer</div>
        <div class="info-value">{employer_name}</div>
        <div class="info-value" style="font-size:8pt;">{employer_address or 'N/A'}</div>
    </div>
    <div class="info-section">
        <div class="info-label">Employee</div>
        <div class="info-value">{w2.employee_first_name} {w2.employee_last_name}</div>
        <div class="info-value" style="font-size:8pt;">{emp_addr}</div>
    </div>

    <div class="box-grid">
        <div class="box"><div class="box-label">1 - Wages, tips, other compensation</div><div class="box-value">{_format_currency(w2.box1_wages)}</div></div>
        <div class="box"><div class="box-label">2 - Federal income tax withheld</div><div class="box-value">{_format_currency(w2.box2_federal_withheld)}</div></div>
        <div class="box"><div class="box-label">3 - Social security wages</div><div class="box-value">{_format_currency(w2.box3_ss_wages)}</div></div>
        <div class="box"><div class="box-label">4 - Social security tax withheld</div><div class="box-value">{_format_currency(w2.box4_ss_tax)}</div></div>
        <div class="box"><div class="box-label">5 - Medicare wages and tips</div><div class="box-value">{_format_currency(w2.box5_medicare_wages)}</div></div>
        <div class="box"><div class="box-label">6 - Medicare tax withheld</div><div class="box-value">{_format_currency(w2.box6_medicare_tax)}</div></div>
        <div class="box"><div class="box-label">16 - State wages, tips, etc. (GA)</div><div class="box-value">{_format_currency(w2.box16_state_wages)}</div></div>
        <div class="box"><div class="box-label">17 - State income tax (GA)</div><div class="box-value">{_format_currency(w2.box17_state_tax)}</div></div>
    </div>
</div>
<div class="footer">Substitute Form W-2 &mdash; Generated by Georgia CPA Accounting System</div>
</body></html>"""
