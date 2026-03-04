"""
Pydantic schemas for Bank Reconciliation (module T3).

Covers bank accounts, bank transactions, and reconciliation sessions.
"""

import enum
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field

from app.schemas import BaseSchema, RecordSchema


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class BankTransactionType(str, enum.Enum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"


class ReconciliationStatus(str, enum.Enum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


# ---------------------------------------------------------------------------
# Bank Account schemas
# ---------------------------------------------------------------------------

class BankAccountCreate(BaseSchema):
    account_name: str = Field(..., min_length=1, max_length=255)
    institution_name: str | None = Field(None, max_length=255)
    account_id: UUID | None = Field(None, description="Linked GL account ID")


class BankAccountUpdate(BaseSchema):
    account_name: str | None = Field(None, min_length=1, max_length=255)
    institution_name: str | None = Field(None, max_length=255)
    account_id: UUID | None = None


class BankAccountResponse(RecordSchema):
    client_id: UUID
    account_name: str
    institution_name: str | None = None
    account_id: UUID | None = None


class BankAccountList(BaseSchema):
    items: list[BankAccountResponse]
    total: int


# ---------------------------------------------------------------------------
# Bank Transaction schemas
# ---------------------------------------------------------------------------

class BankTransactionCreate(BaseSchema):
    transaction_date: date
    description: str | None = None
    amount: Decimal = Field(..., ge=0)
    transaction_type: BankTransactionType


class BankTransactionImport(BaseSchema):
    """Schema for bulk-importing bank statement transactions."""
    transactions: list[BankTransactionCreate] = Field(..., min_length=1)


class BankTransactionResponse(RecordSchema):
    bank_account_id: UUID
    transaction_date: date
    description: str | None = None
    amount: Decimal
    transaction_type: BankTransactionType
    is_reconciled: bool
    reconciled_at: datetime | None = None
    journal_entry_id: UUID | None = None


class BankTransactionList(BaseSchema):
    items: list[BankTransactionResponse]
    total: int


# ---------------------------------------------------------------------------
# Reconciliation schemas
# ---------------------------------------------------------------------------

class ReconciliationCreate(BaseSchema):
    statement_date: date
    statement_balance: Decimal


class ReconciliationMatchRequest(BaseSchema):
    """Match a bank transaction to a journal entry."""
    bank_transaction_id: UUID
    journal_entry_id: UUID


class ReconciliationResponse(RecordSchema):
    bank_account_id: UUID
    statement_date: date
    statement_balance: Decimal
    reconciled_balance: Decimal | None = None
    status: ReconciliationStatus
    completed_at: datetime | None = None
    completed_by: UUID | None = None


class ReconciliationList(BaseSchema):
    items: list[ReconciliationResponse]
    total: int
