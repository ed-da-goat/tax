"""
Check printing PDF generation service.

Generates printable check PDFs from bill payment data with
amount-to-words conversion.

Compliance (CLAUDE.md):
- Rule #4: CLIENT ISOLATION — checks are scoped to client's bill payments.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class CheckData:
    """All data needed to render a check PDF."""

    payer_name: str
    payer_address: str | None
    payee_name: str
    check_number: int
    check_date: date
    amount: Decimal
    memo: str | None = None


def amount_to_words(amount: Decimal) -> str:
    """
    Convert a decimal dollar amount to words for check writing.

    Examples:
        1234.56 -> "One Thousand Two Hundred Thirty-Four and 56/100"
        0.50 -> "Zero and 50/100"
    """
    ones = [
        "", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
        "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen",
        "Sixteen", "Seventeen", "Eighteen", "Nineteen",
    ]
    tens = [
        "", "", "Twenty", "Thirty", "Forty", "Fifty",
        "Sixty", "Seventy", "Eighty", "Ninety",
    ]

    def _int_to_words(n: int) -> str:
        if n == 0:
            return "Zero"
        if n < 0:
            return "Negative " + _int_to_words(-n)

        parts = []
        if n >= 1_000_000:
            millions = n // 1_000_000
            parts.append(_int_to_words(millions) + " Million")
            n %= 1_000_000
        if n >= 1_000:
            thousands = n // 1_000
            parts.append(_int_to_words(thousands) + " Thousand")
            n %= 1_000
        if n >= 100:
            hundreds = n // 100
            parts.append(ones[hundreds] + " Hundred")
            n %= 100
        if n >= 20:
            t = n // 10
            o = n % 10
            if o:
                parts.append(tens[t] + "-" + ones[o])
            else:
                parts.append(tens[t])
        elif n > 0:
            parts.append(ones[n])

        return " ".join(parts)

    dollars = int(amount)
    cents = int(round((amount - dollars) * 100))
    dollar_words = _int_to_words(dollars)
    return f"{dollar_words} and {cents:02d}/100"


def _format_currency(amount: Decimal) -> str:
    return f"${amount:,.2f}"


def _format_date(d: date) -> str:
    return d.strftime("%m/%d/%Y")


class CheckPrintingService:
    """Generates printable check PDFs."""

    @staticmethod
    def generate_check_pdf(data: CheckData) -> bytes:
        """Generate a single check PDF."""
        from weasyprint import HTML

        html = _build_check_html(data)
        return HTML(string=html).write_pdf()


def _build_check_html(data: CheckData) -> str:
    words = amount_to_words(data.amount)

    return f"""<!DOCTYPE html>
<html><head><style>
    @page {{ size: letter; margin: 0.5in; }}
    body {{ font-family: 'Courier New', monospace; font-size: 11pt; color: #000; }}
    .check {{ border: 2px solid #000; padding: 20px; width: 7.5in; position: relative; }}
    .check-number {{ position: absolute; top: 15px; right: 20px; font-size: 14pt; font-weight: bold; }}
    .payer {{ margin-bottom: 20px; }}
    .payer-name {{ font-size: 14pt; font-weight: bold; }}
    .payer-addr {{ font-size: 9pt; color: #444; }}
    .date-line {{ text-align: right; margin-bottom: 15px; }}
    .pay-to {{ margin-bottom: 10px; }}
    .pay-to-label {{ font-size: 8pt; color: #666; }}
    .pay-to-name {{ font-size: 13pt; font-weight: bold; border-bottom: 1px solid #000; padding-bottom: 2px; display: inline-block; min-width: 400px; }}
    .amount-box {{ border: 2px solid #000; padding: 5px 10px; display: inline-block; font-size: 14pt; font-weight: bold; float: right; margin-top: -30px; }}
    .amount-words {{ border-bottom: 1px solid #000; padding: 5px 0; margin-bottom: 15px; font-size: 10pt; min-height: 20px; }}
    .memo-line {{ margin-top: 30px; }}
    .memo-label {{ font-size: 8pt; color: #666; }}
    .memo-value {{ border-bottom: 1px solid #000; display: inline-block; min-width: 300px; padding-bottom: 2px; }}
    .signature-line {{ float: right; border-bottom: 1px solid #000; width: 250px; margin-top: 20px; text-align: center; padding-top: 30px; font-size: 8pt; color: #666; }}
    .stub {{ border-top: 1px dashed #999; margin-top: 40px; padding-top: 15px; font-size: 9pt; }}
    .stub-title {{ font-weight: bold; margin-bottom: 5px; }}
    .footer {{ text-align: center; font-size: 7pt; color: #999; margin-top: 20px; }}
</style></head>
<body>
<div class="check">
    <div class="check-number">No. {data.check_number}</div>
    <div class="payer">
        <div class="payer-name">{data.payer_name}</div>
        <div class="payer-addr">{data.payer_address or ''}</div>
    </div>
    <div class="date-line">Date: {_format_date(data.check_date)}</div>
    <div class="pay-to">
        <div class="pay-to-label">PAY TO THE ORDER OF</div>
        <div class="pay-to-name">{data.payee_name}</div>
        <div class="amount-box">{_format_currency(data.amount)}</div>
    </div>
    <div class="amount-words">{words} ******</div>
    <div class="memo-line">
        <span class="memo-label">MEMO </span>
        <span class="memo-value">{data.memo or ''}</span>
    </div>
    <div class="signature-line">Authorized Signature</div>
    <div style="clear:both;"></div>
</div>

<div class="stub">
    <div class="stub-title">CHECK STUB — RETAIN FOR YOUR RECORDS</div>
    <table style="width:100%; font-size:9pt;">
        <tr>
            <td>Check No: {data.check_number}</td>
            <td>Date: {_format_date(data.check_date)}</td>
            <td>Amount: {_format_currency(data.amount)}</td>
        </tr>
        <tr>
            <td>Pay To: {data.payee_name}</td>
            <td colspan="2">Memo: {data.memo or 'N/A'}</td>
        </tr>
    </table>
</div>

<div class="footer">Generated by Georgia CPA Accounting System</div>
</body></html>"""
