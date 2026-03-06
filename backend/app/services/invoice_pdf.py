"""
Invoice and Bill PDF generation (D4).

Generates professional PDF documents from invoice/bill data using WeasyPrint.
"""

from decimal import Decimal


def generate_invoice_pdf(invoice, client_name: str) -> bytes:
    """Generate a PDF for a single invoice."""
    line_rows = ""
    for line in invoice.lines:
        if hasattr(line, 'deleted_at') and line.deleted_at:
            continue
        line_rows += f"""
        <tr>
            <td>{line.description or '-'}</td>
            <td style="text-align:right">{float(line.quantity):.2f}</td>
            <td style="text-align:right">${float(line.unit_price):,.2f}</td>
            <td style="text-align:right">${float(line.amount):,.2f}</td>
        </tr>"""

    payment_rows = ""
    total_paid = Decimal("0")
    for p in (invoice.payments or []):
        if hasattr(p, 'deleted_at') and p.deleted_at:
            continue
        total_paid += p.amount
        payment_rows += f"""
        <tr>
            <td>{p.payment_date.isoformat()}</td>
            <td>{p.payment_method or '-'}</td>
            <td>{p.reference_number or '-'}</td>
            <td style="text-align:right">${float(p.amount):,.2f}</td>
        </tr>"""

    balance_due = float(invoice.total_amount) - float(total_paid)

    html = f"""
    <html>
    <head><style>
        body {{ font-family: -apple-system, sans-serif; font-size: 11px; color: #1e1e2d; margin: 40px; }}
        h1 {{ font-size: 24px; margin-bottom: 4px; color: #1e1e2d; }}
        .header {{ display: flex; justify-content: space-between; margin-bottom: 32px; }}
        .header-left {{ }}
        .header-right {{ text-align: right; }}
        .meta {{ font-size: 12px; color: #6b7280; margin-bottom: 4px; }}
        .meta strong {{ color: #1e1e2d; }}
        table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
        th, td {{ padding: 8px 10px; border-bottom: 1px solid #e0e2e7; text-align: left; font-size: 11px; }}
        th {{ background: #f5f6f8; font-weight: 600; font-size: 10px; text-transform: uppercase; letter-spacing: 0.5px; }}
        .totals {{ text-align: right; margin-top: 16px; }}
        .totals-row {{ display: flex; justify-content: flex-end; gap: 40px; margin-bottom: 4px; font-size: 13px; }}
        .totals-row.total {{ font-weight: 700; font-size: 16px; border-top: 2px solid #1e1e2d; padding-top: 8px; }}
        .badge {{ display: inline-block; padding: 2px 10px; border-radius: 10px; font-size: 10px; font-weight: 600; text-transform: uppercase; }}
        .badge-sent {{ background: #eff6ff; color: #1e40af; }}
        .badge-paid {{ background: #f0fdf4; color: #166534; }}
        .badge-draft {{ background: #f3f4f6; color: #6b7280; }}
        .badge-overdue {{ background: #fff7ed; color: #9a3412; }}
        .badge-void {{ background: #fef2f2; color: #991b1b; }}
        .footer {{ margin-top: 40px; font-size: 10px; color: #6b7280; border-top: 1px solid #e0e2e7; padding-top: 12px; }}
    </style></head>
    <body>
        <div class="header">
            <div class="header-left">
                <h1>INVOICE</h1>
                <p class="meta"><strong>#{invoice.invoice_number or '-'}</strong></p>
            </div>
            <div class="header-right">
                <p class="meta"><strong>{client_name}</strong></p>
                <p class="meta">Georgia CPA Firm</p>
            </div>
        </div>

        <div style="display: flex; gap: 60px; margin-bottom: 24px;">
            <div>
                <p class="meta">Bill To</p>
                <p style="font-weight: 600; font-size: 13px;">{invoice.customer_name}</p>
            </div>
            <div>
                <p class="meta">Invoice Date</p>
                <p style="font-weight: 500;">{invoice.invoice_date.isoformat()}</p>
            </div>
            <div>
                <p class="meta">Due Date</p>
                <p style="font-weight: 500;">{invoice.due_date.isoformat() if invoice.due_date else 'N/A'}</p>
            </div>
            <div>
                <p class="meta">Status</p>
                <span class="badge badge-{invoice.status.value.lower()}">{invoice.status.value}</span>
            </div>
        </div>

        <table>
            <thead><tr><th>Description</th><th style="text-align:right">Qty</th><th style="text-align:right">Unit Price</th><th style="text-align:right">Amount</th></tr></thead>
            <tbody>{line_rows if line_rows else '<tr><td colspan="4" style="text-align:center;color:#6b7280">No line items</td></tr>'}</tbody>
        </table>

        <div class="totals">
            <div class="totals-row"><span>Subtotal:</span><span>${float(invoice.total_amount):,.2f}</span></div>
            {"<div class='totals-row'><span>Paid:</span><span>$" + f"{float(total_paid):,.2f}" + "</span></div>" if total_paid > 0 else ""}
            <div class="totals-row total"><span>Balance Due:</span><span>${balance_due:,.2f}</span></div>
        </div>

        {f'<h3 style="font-size: 13px; margin-top: 32px;">Payments</h3><table><thead><tr><th>Date</th><th>Method</th><th>Reference</th><th style="text-align:right">Amount</th></tr></thead><tbody>{payment_rows}</tbody></table>' if payment_rows else ''}

        <div class="footer">Generated by Georgia CPA Firm Accounting System</div>
    </body></html>
    """

    from weasyprint import HTML
    return HTML(string=html).write_pdf()


def generate_bill_pdf(bill, client_name: str, vendor_name: str) -> bytes:
    """Generate a PDF for a single bill."""
    line_rows = ""
    for line in bill.lines:
        if hasattr(line, 'deleted_at') and line.deleted_at:
            continue
        line_rows += f"""
        <tr>
            <td>{line.description or '-'}</td>
            <td style="text-align:right">${float(line.amount):,.2f}</td>
        </tr>"""

    payment_rows = ""
    total_paid = Decimal("0")
    for p in (bill.payments or []):
        if hasattr(p, 'deleted_at') and p.deleted_at:
            continue
        total_paid += p.amount
        payment_rows += f"""
        <tr>
            <td>{p.payment_date.isoformat()}</td>
            <td>{p.payment_method or '-'}</td>
            <td>{p.reference_number or '-'}</td>
            <td style="text-align:right">${float(p.amount):,.2f}</td>
        </tr>"""

    balance_due = float(bill.total_amount) - float(total_paid)

    html = f"""
    <html>
    <head><style>
        body {{ font-family: -apple-system, sans-serif; font-size: 11px; color: #1e1e2d; margin: 40px; }}
        h1 {{ font-size: 24px; margin-bottom: 4px; }}
        .header {{ display: flex; justify-content: space-between; margin-bottom: 32px; }}
        .meta {{ font-size: 12px; color: #6b7280; margin-bottom: 4px; }}
        .meta strong {{ color: #1e1e2d; }}
        table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
        th, td {{ padding: 8px 10px; border-bottom: 1px solid #e0e2e7; text-align: left; font-size: 11px; }}
        th {{ background: #f5f6f8; font-weight: 600; font-size: 10px; text-transform: uppercase; letter-spacing: 0.5px; }}
        .totals {{ text-align: right; margin-top: 16px; }}
        .totals-row {{ display: flex; justify-content: flex-end; gap: 40px; margin-bottom: 4px; font-size: 13px; }}
        .totals-row.total {{ font-weight: 700; font-size: 16px; border-top: 2px solid #1e1e2d; padding-top: 8px; }}
        .badge {{ display: inline-block; padding: 2px 10px; border-radius: 10px; font-size: 10px; font-weight: 600; text-transform: uppercase; }}
        .footer {{ margin-top: 40px; font-size: 10px; color: #6b7280; border-top: 1px solid #e0e2e7; padding-top: 12px; }}
    </style></head>
    <body>
        <div class="header">
            <div>
                <h1>BILL</h1>
                <p class="meta"><strong>#{bill.bill_number or '-'}</strong></p>
            </div>
            <div style="text-align: right;">
                <p class="meta"><strong>{client_name}</strong></p>
            </div>
        </div>

        <div style="display: flex; gap: 60px; margin-bottom: 24px;">
            <div>
                <p class="meta">Vendor</p>
                <p style="font-weight: 600; font-size: 13px;">{vendor_name}</p>
            </div>
            <div>
                <p class="meta">Bill Date</p>
                <p style="font-weight: 500;">{bill.bill_date.isoformat()}</p>
            </div>
            <div>
                <p class="meta">Due Date</p>
                <p style="font-weight: 500;">{bill.due_date.isoformat()}</p>
            </div>
            <div>
                <p class="meta">Status</p>
                <span class="badge">{bill.status.value}</span>
            </div>
        </div>

        <table>
            <thead><tr><th>Description</th><th style="text-align:right">Amount</th></tr></thead>
            <tbody>{line_rows if line_rows else '<tr><td colspan="2" style="text-align:center;color:#6b7280">No line items</td></tr>'}</tbody>
        </table>

        <div class="totals">
            <div class="totals-row"><span>Total:</span><span>${float(bill.total_amount):,.2f}</span></div>
            {"<div class='totals-row'><span>Paid:</span><span>$" + f"{float(total_paid):,.2f}" + "</span></div>" if total_paid > 0 else ""}
            <div class="totals-row total"><span>Balance Due:</span><span>${balance_due:,.2f}</span></div>
        </div>

        {f'<h3 style="font-size: 13px; margin-top: 32px;">Payments</h3><table><thead><tr><th>Date</th><th>Method</th><th>Reference</th><th style="text-align:right">Amount</th></tr></thead><tbody>{payment_rows}</tbody></table>' if payment_rows else ''}

        <div class="footer">Generated by Georgia CPA Firm Accounting System</div>
    </body></html>
    """

    from weasyprint import HTML
    return HTML(string=html).write_pdf()
