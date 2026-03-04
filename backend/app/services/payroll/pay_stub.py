"""
Pay stub PDF generator (module P5).

Generates professional PDF pay stubs using WeasyPrint from payroll
item data. Output includes employee info, earnings, deductions,
employer taxes, and net pay.

Compliance (CLAUDE.md):
- Rule #4: CLIENT ISOLATION — pay stubs are scoped to a client's employee.
- TECH STACK: PDF generation via WeasyPrint per CLAUDE.md spec.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path


@dataclass(frozen=True)
class PayStubData:
    """All data needed to render a pay stub PDF."""

    # Required fields (no defaults)
    company_name: str
    employee_name: str

    # Company / client info
    company_address: str | None = None

    # Employee info
    employee_id_display: str = ""

    # Pay period
    pay_period_start: date = date.today()
    pay_period_end: date = date.today()
    pay_date: date = date.today()

    # Earnings
    hours_worked: Decimal | None = None
    pay_rate: Decimal = Decimal("0.00")
    pay_type: str = "HOURLY"
    gross_pay: Decimal = Decimal("0.00")

    # Employee deductions
    federal_withholding: Decimal = Decimal("0.00")
    state_withholding: Decimal = Decimal("0.00")
    social_security: Decimal = Decimal("0.00")
    medicare: Decimal = Decimal("0.00")

    # Employer-paid taxes (informational)
    employer_ss: Decimal = Decimal("0.00")
    employer_medicare: Decimal = Decimal("0.00")
    ga_suta: Decimal = Decimal("0.00")
    futa: Decimal = Decimal("0.00")

    # Net pay
    net_pay: Decimal = Decimal("0.00")

    # YTD totals (optional)
    ytd_gross: Decimal | None = None
    ytd_federal_withholding: Decimal | None = None
    ytd_state_withholding: Decimal | None = None
    ytd_social_security: Decimal | None = None
    ytd_medicare: Decimal | None = None
    ytd_net_pay: Decimal | None = None


def _format_currency(amount: Decimal | None) -> str:
    """Format a decimal as USD currency string."""
    if amount is None:
        return "-"
    return f"${amount:,.2f}"


def _format_date(d: date) -> str:
    """Format a date as MM/DD/YYYY."""
    return d.strftime("%m/%d/%Y")


def _build_html(data: PayStubData) -> str:
    """Build the HTML content for a pay stub."""
    total_deductions = (
        data.federal_withholding
        + data.state_withholding
        + data.social_security
        + data.medicare
    )
    total_employer_taxes = (
        data.employer_ss + data.employer_medicare + data.ga_suta + data.futa
    )

    earnings_desc = "Hourly" if data.pay_type == "HOURLY" else "Salary"
    hours_cell = ""
    if data.hours_worked is not None:
        hours_cell = f"<td>{data.hours_worked}</td>"
    else:
        hours_cell = "<td>-</td>"

    rate_cell = _format_currency(data.pay_rate)
    if data.pay_type == "SALARY":
        rate_cell = _format_currency(data.pay_rate) + "/yr"

    # YTD section
    ytd_rows = ""
    if data.ytd_gross is not None:
        ytd_rows = f"""
        <tr class="section-header"><td colspan="4">Year-to-Date Totals</td></tr>
        <tr><td>Gross Pay</td><td colspan="3">{_format_currency(data.ytd_gross)}</td></tr>
        <tr><td>Federal Withholding</td><td colspan="3">{_format_currency(data.ytd_federal_withholding)}</td></tr>
        <tr><td>State Withholding (GA)</td><td colspan="3">{_format_currency(data.ytd_state_withholding)}</td></tr>
        <tr><td>Social Security</td><td colspan="3">{_format_currency(data.ytd_social_security)}</td></tr>
        <tr><td>Medicare</td><td colspan="3">{_format_currency(data.ytd_medicare)}</td></tr>
        <tr class="total-row"><td>Net Pay</td><td colspan="3">{_format_currency(data.ytd_net_pay)}</td></tr>
        """

    return f"""<!DOCTYPE html>
<html>
<head>
<style>
    @page {{ size: letter; margin: 0.75in; }}
    body {{ font-family: Arial, Helvetica, sans-serif; font-size: 10pt; color: #333; }}
    .header {{ display: flex; justify-content: space-between; border-bottom: 2px solid #2c3e50; padding-bottom: 10px; margin-bottom: 15px; }}
    .company-name {{ font-size: 16pt; font-weight: bold; color: #2c3e50; }}
    .stub-title {{ font-size: 12pt; color: #666; text-align: right; }}
    .info-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 15px; }}
    .info-box {{ padding: 8px; background: #f8f9fa; border-radius: 4px; }}
    .info-box label {{ font-weight: bold; font-size: 8pt; color: #666; text-transform: uppercase; display: block; margin-bottom: 2px; }}
    .info-box span {{ font-size: 10pt; }}
    table {{ width: 100%; border-collapse: collapse; margin-bottom: 15px; }}
    th {{ background: #2c3e50; color: white; padding: 6px 8px; text-align: left; font-size: 9pt; }}
    td {{ padding: 5px 8px; border-bottom: 1px solid #eee; font-size: 9pt; }}
    .section-header td {{ background: #ecf0f1; font-weight: bold; font-size: 9pt; padding: 5px 8px; }}
    .total-row td {{ border-top: 2px solid #2c3e50; font-weight: bold; font-size: 10pt; }}
    .net-pay {{ font-size: 14pt; font-weight: bold; color: #2c3e50; text-align: center; padding: 15px; background: #ecf0f1; border-radius: 4px; margin-top: 10px; }}
    .footer {{ text-align: center; font-size: 8pt; color: #999; margin-top: 20px; border-top: 1px solid #eee; padding-top: 10px; }}
</style>
</head>
<body>
    <div class="header">
        <div>
            <div class="company-name">{data.company_name}</div>
            {f'<div>{data.company_address}</div>' if data.company_address else ''}
        </div>
        <div class="stub-title">
            PAY STUB<br>
            Pay Date: {_format_date(data.pay_date)}
        </div>
    </div>

    <div class="info-grid">
        <div class="info-box">
            <label>Employee</label>
            <span>{data.employee_name}</span>
            {f'<br><span style="font-size:8pt;color:#666">ID: {data.employee_id_display}</span>' if data.employee_id_display else ''}
        </div>
        <div class="info-box">
            <label>Pay Period</label>
            <span>{_format_date(data.pay_period_start)} - {_format_date(data.pay_period_end)}</span>
        </div>
    </div>

    <table>
        <tr><th>Description</th><th>Hours</th><th>Rate</th><th>Amount</th></tr>
        <tr class="section-header"><td colspan="4">Earnings</td></tr>
        <tr>
            <td>{earnings_desc}</td>
            {hours_cell}
            <td>{rate_cell}</td>
            <td>{_format_currency(data.gross_pay)}</td>
        </tr>
        <tr class="total-row">
            <td>Gross Pay</td><td></td><td></td>
            <td>{_format_currency(data.gross_pay)}</td>
        </tr>
    </table>

    <table>
        <tr><th>Deduction</th><th colspan="2">Current</th><th>Description</th></tr>
        <tr class="section-header"><td colspan="4">Employee Deductions</td></tr>
        <tr><td>Federal Income Tax</td><td colspan="2">{_format_currency(data.federal_withholding)}</td><td>Federal withholding</td></tr>
        <tr><td>GA State Income Tax</td><td colspan="2">{_format_currency(data.state_withholding)}</td><td>Georgia withholding</td></tr>
        <tr><td>Social Security</td><td colspan="2">{_format_currency(data.social_security)}</td><td>OASDI 6.2%</td></tr>
        <tr><td>Medicare</td><td colspan="2">{_format_currency(data.medicare)}</td><td>Medicare 1.45%</td></tr>
        <tr class="total-row">
            <td>Total Deductions</td><td colspan="2">{_format_currency(total_deductions)}</td><td></td>
        </tr>
    </table>

    <table>
        <tr><th>Employer Tax</th><th colspan="2">Amount</th><th>Description</th></tr>
        <tr class="section-header"><td colspan="4">Employer-Paid Taxes (Informational)</td></tr>
        <tr><td>Social Security</td><td colspan="2">{_format_currency(data.employer_ss)}</td><td>Employer OASDI match</td></tr>
        <tr><td>Medicare</td><td colspan="2">{_format_currency(data.employer_medicare)}</td><td>Employer Medicare match</td></tr>
        <tr><td>GA SUTA</td><td colspan="2">{_format_currency(data.ga_suta)}</td><td>GA State Unemployment</td></tr>
        <tr><td>FUTA</td><td colspan="2">{_format_currency(data.futa)}</td><td>Federal Unemployment</td></tr>
        <tr class="total-row">
            <td>Total Employer Taxes</td><td colspan="2">{_format_currency(total_employer_taxes)}</td><td></td>
        </tr>
    </table>

    {ytd_rows and f'<table><tr><th>Category</th><th colspan="3">YTD Amount</th></tr>{ytd_rows}</table>' or ''}

    <div class="net-pay">
        NET PAY: {_format_currency(data.net_pay)}
    </div>

    <div class="footer">
        This is a confidential document. Generated by Georgia CPA Accounting System.
    </div>
</body>
</html>"""


class PayStubGenerator:
    """
    Generates PDF pay stubs from payroll item data.

    Uses WeasyPrint per CLAUDE.md tech stack specification.
    """

    @staticmethod
    def generate_pdf(data: PayStubData) -> bytes:
        """
        Generate a PDF pay stub and return the raw bytes.

        Parameters
        ----------
        data : PayStubData
            All fields needed to render the pay stub.

        Returns
        -------
        bytes
            PDF file content.
        """
        from weasyprint import HTML  # Lazy import — requires system pango lib

        html_content = _build_html(data)
        html = HTML(string=html_content)
        pdf_bytes = html.write_pdf()
        return pdf_bytes

    @staticmethod
    def generate_pdf_to_file(data: PayStubData, output_path: Path | str) -> Path:
        """
        Generate a PDF pay stub and write it to a file.

        Parameters
        ----------
        data : PayStubData
            All fields needed to render the pay stub.
        output_path : Path or str
            Where to write the PDF file.

        Returns
        -------
        Path
            The path the PDF was written to.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        pdf_bytes = PayStubGenerator.generate_pdf(data)
        output_path.write_bytes(pdf_bytes)
        return output_path
