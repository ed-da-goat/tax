"""
Email delivery service (C4).

Sends transactional emails via SMTP (aiosmtplib).
Supports HTML body and file attachments (PDF invoices, statements, etc.).
"""

import logging
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path
from typing import Any

import aiosmtplib

from app.config import settings

logger = logging.getLogger(__name__)


def _is_configured() -> bool:
    """Check if SMTP settings are present."""
    return bool(settings.SMTP_HOST and settings.SMTP_FROM_EMAIL)


async def send_email(
    to: str | list[str],
    subject: str,
    html_body: str,
    text_body: str | None = None,
    attachments: list[dict[str, Any]] | None = None,
) -> dict:
    """
    Send an email via SMTP.

    Args:
        to: recipient email(s)
        subject: email subject
        html_body: HTML email content
        text_body: optional plain text fallback
        attachments: list of {"filename": str, "content": bytes, "mime_type": str}
    """
    if not _is_configured():
        logger.warning("SMTP not configured — email not sent (subject: %s)", subject)
        return {"sent": False, "reason": "SMTP not configured"}

    recipients = [to] if isinstance(to, str) else to

    msg = EmailMessage()
    msg["From"] = formataddr((settings.SMTP_FROM_NAME, settings.SMTP_FROM_EMAIL))
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject

    if text_body:
        msg.set_content(text_body)
        msg.add_alternative(html_body, subtype="html")
    else:
        msg.set_content(html_body, subtype="html")

    if attachments:
        for att in attachments:
            maintype, subtype = att.get("mime_type", "application/octet-stream").split("/", 1)
            msg.add_attachment(
                att["content"],
                maintype=maintype,
                subtype=subtype,
                filename=att["filename"],
            )

    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER or None,
            password=settings.SMTP_PASSWORD or None,
            start_tls=settings.SMTP_USE_TLS,
        )
        logger.info("Email sent to %s: %s", recipients, subject)
        return {"sent": True, "to": recipients, "subject": subject}
    except Exception as e:
        logger.error("Failed to send email to %s: %s", recipients, str(e))
        return {"sent": False, "error": str(e)}


# --- Template helpers ---

def render_invoice_email(
    client_name: str, invoice_number: str, total: float, due_date: str,
) -> tuple[str, str]:
    """Return (subject, html_body) for an invoice email."""
    subject = f"Invoice #{invoice_number} from {settings.SMTP_FROM_NAME}"
    html = f"""
    <div style="font-family: -apple-system, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #1e1e2d;">Invoice #{invoice_number}</h2>
        <p>Dear {client_name},</p>
        <p>Please find attached your invoice for <strong>${total:,.2f}</strong>.</p>
        <p>Due date: <strong>{due_date}</strong></p>
        <p>If you have any questions, please don't hesitate to reach out.</p>
        <hr style="border: none; border-top: 1px solid #e0e2e7; margin: 24px 0;" />
        <p style="color: #6b7280; font-size: 12px;">{settings.SMTP_FROM_NAME}</p>
    </div>
    """
    return subject, html


def render_statement_email(client_name: str, period: str, balance: float) -> tuple[str, str]:
    """Return (subject, html_body) for a statement email."""
    subject = f"Account Statement — {period}"
    html = f"""
    <div style="font-family: -apple-system, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #1e1e2d;">Account Statement</h2>
        <p>Dear {client_name},</p>
        <p>Please find attached your account statement for <strong>{period}</strong>.</p>
        <p>Current balance: <strong>${balance:,.2f}</strong></p>
        <hr style="border: none; border-top: 1px solid #e0e2e7; margin: 24px 0;" />
        <p style="color: #6b7280; font-size: 12px;">{settings.SMTP_FROM_NAME}</p>
    </div>
    """
    return subject, html


def render_portal_invitation(client_name: str, login_url: str) -> tuple[str, str]:
    """Return (subject, html_body) for a portal invitation email."""
    subject = f"Welcome to {settings.SMTP_FROM_NAME} Client Portal"
    html = f"""
    <div style="font-family: -apple-system, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #1e1e2d;">Client Portal Access</h2>
        <p>Dear {client_name},</p>
        <p>You have been invited to access the client portal.</p>
        <p><a href="{login_url}" style="display: inline-block; padding: 10px 24px;
            background: #2563eb; color: white; text-decoration: none; border-radius: 6px;">
            Access Portal
        </a></p>
        <hr style="border: none; border-top: 1px solid #e0e2e7; margin: 24px 0;" />
        <p style="color: #6b7280; font-size: 12px;">{settings.SMTP_FROM_NAME}</p>
    </div>
    """
    return subject, html


def render_backup_alert(status: str, details: str) -> tuple[str, str]:
    """Return (subject, html_body) for a backup status alert."""
    subject = f"Backup {status} — {settings.SMTP_FROM_NAME}"
    color = "#16a34a" if status == "SUCCESS" else "#dc2626"
    html = f"""
    <div style="font-family: -apple-system, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: {color};">Backup {status}</h2>
        <pre style="background: #f5f6f8; padding: 16px; border-radius: 6px; font-size: 12px;">{details}</pre>
        <p style="color: #6b7280; font-size: 12px;">{settings.SMTP_FROM_NAME}</p>
    </div>
    """
    return subject, html
