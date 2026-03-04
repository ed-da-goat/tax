"""
Pydantic schemas for Bill CRUD and workflow operations (module T1 — Accounts Payable).

Validation rules:
- Bill must have at least one line item
- Each line amount must be > 0
- client_id comes from the URL path parameter, not the request body
- Status transitions enforced at the service level, not schema level

Compliance (CLAUDE.md rule #5): Bills start as DRAFT. Only CPA_OWNER approves.
"""

import enum
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field, model_validator

from app.schemas import BaseSchema, RecordSchema


class BillStatus(str, enum.Enum):
    """Bill status matching the PostgreSQL enum."""

    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    PAID = "PAID"
    VOID = "VOID"


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class BillLineCreate(BaseSchema):
    """Schema for a single line item when creating a bill."""

    account_id: UUID
    description: str | None = None
    amount: Decimal = Field(..., gt=0, max_digits=15, decimal_places=2)


class BillCreate(BaseSchema):
    """Schema for creating a new bill with line items."""

    vendor_id: UUID
    bill_number: str | None = Field(None, max_length=100)
    bill_date: date
    due_date: date
    lines: list[BillLineCreate] = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_due_date_not_before_bill_date(self) -> "BillCreate":
        """Due date must not be before bill date."""
        if self.due_date < self.bill_date:
            raise ValueError("due_date cannot be before bill_date")
        return self


class BillPaymentCreate(BaseSchema):
    """Schema for recording a payment against a bill."""

    payment_date: date
    amount: Decimal = Field(..., gt=0, max_digits=15, decimal_places=2)
    payment_method: str | None = Field(None, max_length=50)
    reference_number: str | None = Field(None, max_length=100)


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class BillLineResponse(RecordSchema):
    """Schema for returning a single bill line item."""

    bill_id: UUID
    account_id: UUID
    description: str | None = None
    amount: Decimal


class BillPaymentResponse(RecordSchema):
    """Schema for returning a single bill payment."""

    bill_id: UUID
    payment_date: date
    amount: Decimal
    payment_method: str | None = None
    reference_number: str | None = None


class BillResponse(RecordSchema):
    """Schema for returning a single bill with nested lines and payments."""

    client_id: UUID
    vendor_id: UUID
    bill_number: str | None = None
    bill_date: date
    due_date: date
    total_amount: Decimal
    status: BillStatus
    lines: list[BillLineResponse] = []
    payments: list[BillPaymentResponse] = []
    deleted_at: datetime | None = None


class BillList(BaseSchema):
    """Paginated list of bills."""

    items: list[BillResponse]
    total: int
    skip: int
    limit: int
