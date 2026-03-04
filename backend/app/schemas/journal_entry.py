"""
Pydantic schemas for Journal Entries (module F3 — General Ledger).

Request/response models for journal entry CRUD and workflow operations.
All entries are scoped to a client_id for client isolation compliance.

Compliance (CLAUDE.md rule #1): Double-entry validation at schema level.
Compliance (CLAUDE.md rule #5): Status workflow enforced via service layer.
"""

import enum
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field, model_validator

from app.schemas import BaseSchema, RecordSchema


class JournalEntryStatus(str, enum.Enum):
    """Journal entry status matching the PostgreSQL enum."""

    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    POSTED = "POSTED"
    VOID = "VOID"


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class JournalEntryLineCreate(BaseSchema):
    """Schema for a single line item when creating a journal entry."""

    account_id: UUID
    debit: Decimal = Field(default=Decimal("0.00"), ge=0)
    credit: Decimal = Field(default=Decimal("0.00"), ge=0)
    description: str | None = None

    @model_validator(mode="after")
    def validate_debit_xor_credit(self) -> "JournalEntryLineCreate":
        """Each line must have EITHER debit > 0 OR credit > 0, not both, not neither."""
        if self.debit > 0 and self.credit > 0:
            raise ValueError("A line cannot have both debit and credit. Use separate lines.")
        if self.debit == 0 and self.credit == 0:
            raise ValueError("A line must have either a debit or credit amount greater than zero.")
        return self


class JournalEntryCreate(BaseSchema):
    """Schema for creating a new journal entry with lines."""

    client_id: UUID
    entry_date: date
    description: str | None = None
    reference_number: str | None = Field(None, max_length=100)
    lines: list[JournalEntryLineCreate] = Field(..., min_length=2)

    @model_validator(mode="after")
    def validate_balanced_entry(self) -> "JournalEntryCreate":
        """
        DOUBLE-ENTRY ENFORCEMENT (app level):
        Total debits must equal total credits across all lines.
        DB trigger is the backup enforcement.
        """
        total_debits = sum(line.debit for line in self.lines)
        total_credits = sum(line.credit for line in self.lines)
        if total_debits != total_credits:
            raise ValueError(
                f"Journal entry is unbalanced: debits ({total_debits}) != credits ({total_credits}). "
                f"Double-entry requires equal debits and credits."
            )
        return self


class JournalEntryUpdate(BaseSchema):
    """Schema for updating a journal entry (only description and reference_number)."""

    description: str | None = None
    reference_number: str | None = Field(None, max_length=100)


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class JournalEntryLineResponse(RecordSchema):
    """Schema for returning a single journal entry line."""

    journal_entry_id: UUID
    account_id: UUID
    debit: Decimal
    credit: Decimal
    description: str | None = None


class JournalEntryResponse(RecordSchema):
    """Schema for returning a single journal entry with its lines."""

    client_id: UUID
    entry_date: date
    description: str | None = None
    reference_number: str | None = None
    status: JournalEntryStatus
    created_by: UUID
    approved_by: UUID | None = None
    posted_at: datetime | None = None
    lines: list[JournalEntryLineResponse] = []


class JournalEntryList(BaseSchema):
    """Paginated list of journal entries."""

    items: list[JournalEntryResponse]
    total: int
    skip: int
    limit: int


class TrialBalanceRow(BaseSchema):
    """A single row in the trial balance report."""

    client_id: UUID
    account_number: str
    account_name: str
    account_type: str
    sub_type: str | None = None
    total_debits: Decimal
    total_credits: Decimal
    balance: Decimal


class TrialBalanceResponse(BaseSchema):
    """Trial balance report for a client."""

    client_id: UUID
    rows: list[TrialBalanceRow]
    total_debits: Decimal
    total_credits: Decimal
