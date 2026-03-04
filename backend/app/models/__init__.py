"""
SQLAlchemy ORM models package.

All models inherit from Base (defined in base.py) which provides:
- UUID primary key
- created_at, updated_at, deleted_at timestamps
- Soft-delete support (records are never hard-deleted per CLAUDE.md compliance rule #2)

Import models here so Alembic and other tools can discover them.
"""

from app.models.base import Base, SoftDeleteMixin, TimestampMixin
from app.models.client import Client, EntityType
from app.models.user import User
from app.models.permission_log import PermissionLog
from app.models.chart_of_accounts import ChartOfAccounts
from app.models.audit_log import AuditLog, AuditAction
from app.models.journal_entry import JournalEntry, JournalEntryLine, JournalEntryStatus
from app.models.vendor import Vendor
from app.models.bill import Bill, BillLine, BillPayment, BillStatus
from app.models.invoice import Invoice, InvoiceLine, InvoicePayment, InvoiceStatus
from app.models.bank_account import BankAccount, BankTransaction, Reconciliation, BankTransactionType, ReconciliationStatus
from app.models.document import Document
from app.models.employee import Employee, FilingStatus, PayType
from app.models.payroll import PayrollRun, PayrollItem, PayrollRunStatus
from app.models.payroll_tax_table import PayrollTaxTable

__all__ = [
    "Base", "TimestampMixin", "SoftDeleteMixin",
    "Client", "EntityType",
    "User", "PermissionLog",
    "ChartOfAccounts",
    "AuditLog", "AuditAction",
    "JournalEntry", "JournalEntryLine", "JournalEntryStatus",
    "Vendor",
    "Bill", "BillLine", "BillPayment", "BillStatus",
    "Invoice", "InvoiceLine", "InvoicePayment", "InvoiceStatus",
    "BankAccount", "BankTransaction", "Reconciliation", "BankTransactionType", "ReconciliationStatus",
    "Document",
    "Employee", "FilingStatus", "PayType",
    "PayrollRun", "PayrollItem", "PayrollRunStatus",
    "PayrollTaxTable",
]
