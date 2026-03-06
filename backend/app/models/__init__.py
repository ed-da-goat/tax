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
from app.models.check_sequence import ClientCheckSequence
from app.models.employee_bank_account import EmployeeBankAccount, AccountType, PrenoteStatus
from app.models.direct_deposit_batch import DirectDepositBatch, DDBatchStatus
from app.models.tax_filing import TaxFilingSubmission, TaxFilingStatus, TaxFilingProvider

# Phase 9-12 models
from app.models.time_entry import TimeEntry, TimeEntryStatus, StaffRate, TimerSession
from app.models.service_invoice import ServiceInvoice, ServiceInvoiceLine, ServiceInvoicePayment, ServiceInvoiceStatus, PaymentMethod
from app.models.engagement import Engagement, EngagementStatus
from app.models.contact import Contact
from app.models.workflow import (
    Workflow, WorkflowStatus, WorkflowStage, WorkflowTask, TaskStatusEnum,
    TaskPriority, RecurrenceType, TaskComment, Reminder, ReminderType,
    ReminderChannel, DueDate,
)
from app.models.portal import (
    PortalUser, Message, MessageAttachment, Questionnaire, QuestionnaireStatus,
    QuestionnaireQuestion, QuestionType, QuestionnaireResponse,
    SignatureRequest, SignatureStatus,
)
from app.models.fixed_asset import FixedAsset, DepreciationEntry, DepreciationMethod, AssetStatus
from app.models.budget import Budget, BudgetLine
from app.models.password_reset_token import PasswordResetToken
from app.models.recurring_template import (
    RecurringTemplate, RecurringTemplateLine,
    RecurringFrequency, RecurringSourceType, RecurringTemplateStatus,
)

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
    "ClientCheckSequence",
    "EmployeeBankAccount", "AccountType", "PrenoteStatus",
    "DirectDepositBatch", "DDBatchStatus",
    "TaxFilingSubmission", "TaxFilingStatus", "TaxFilingProvider",
    # Phase 9-12
    "TimeEntry", "TimeEntryStatus", "StaffRate", "TimerSession",
    "ServiceInvoice", "ServiceInvoiceLine", "ServiceInvoicePayment", "ServiceInvoiceStatus", "PaymentMethod",
    "Engagement", "EngagementStatus",
    "Contact",
    "Workflow", "WorkflowStatus", "WorkflowStage", "WorkflowTask", "TaskStatusEnum",
    "TaskPriority", "RecurrenceType", "TaskComment", "Reminder", "ReminderType",
    "ReminderChannel", "DueDate",
    "PortalUser", "Message", "MessageAttachment", "Questionnaire", "QuestionnaireStatus",
    "QuestionnaireQuestion", "QuestionType", "QuestionnaireResponse",
    "SignatureRequest", "SignatureStatus",
    "FixedAsset", "DepreciationEntry", "DepreciationMethod", "AssetStatus",
    "Budget", "BudgetLine",
    "RecurringTemplate", "RecurringTemplateLine",
    "RecurringFrequency", "RecurringSourceType", "RecurringTemplateStatus",
    "PasswordResetToken",
]
