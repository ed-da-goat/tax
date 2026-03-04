"""
Pydantic schemas for Invoices / Accounts Receivable (module T2).

Request/response models for invoice CRUD, approval workflow, and payments.
All invoices are scoped to a client_id for client isolation compliance.

Compliance (CLAUDE.md rule #4): Client isolation on every query.
Compliance (CLAUDE.md rule #5): Status workflow enforced via service layer.
"""

import enum
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field, model_validator

from app.schemas import BaseSchema, RecordSchema


class InvoiceStatus(str, enum.Enum):
    """Invoice status matching the PostgreSQL enum."""

    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    SENT = "SENT"
    PAID = "PAID"
    VOID = "VOID"
    OVERDUE = "OVERDUE"


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class InvoiceLineCreate(BaseSchema):
    """Schema for a single line item when creating an invoice."""

    account_id: UUID
    description: str | None = None
    quantity: Decimal = Field(default=Decimal("1.00"), gt=0)
    unit_price: Decimal = Field(default=Decimal("0.00"), ge=0)


class InvoiceCreate(BaseSchema):
    """Schema for creating a new invoice with line items."""

    customer_name: str = Field(..., min_length=1, max_length=255)
    invoice_number: str | None = Field(None, max_length=100)
    invoice_date: date
    due_date: date
    lines: list[InvoiceLineCreate] = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_due_date_after_invoice_date(self) -> "InvoiceCreate":
        """Due date must be on or after invoice date."""
        if self.due_date < self.invoice_date:
            raise ValueError("due_date must be on or after invoice_date")
        return self


class InvoicePaymentCreate(BaseSchema):
    """Schema for recording a payment against an invoice."""

    payment_date: date
    amount: Decimal = Field(..., gt=0)
    payment_method: str | None = Field(None, max_length=50)
    reference_number: str | None = Field(None, max_length=100)


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class InvoiceLineResponse(RecordSchema):
    """Schema for returning a single invoice line item."""

    invoice_id: UUID
    account_id: UUID
    description: str | None = None
    quantity: Decimal
    unit_price: Decimal
    amount: Decimal


class InvoicePaymentResponse(RecordSchema):
    """Schema for returning a single invoice payment."""

    invoice_id: UUID
    payment_date: date
    amount: Decimal
    payment_method: str | None = None
    reference_number: str | None = None


class InvoiceResponse(RecordSchema):
    """Schema for returning a single invoice with nested lines and payments."""

    client_id: UUID
    customer_name: str
    invoice_number: str | None = None
    invoice_date: date
    due_date: date
    total_amount: Decimal
    status: InvoiceStatus
    lines: list[InvoiceLineResponse] = []
    payments: list[InvoicePaymentResponse] = []
    deleted_at: datetime | None = None


class InvoiceList(BaseSchema):
    """Paginated list of invoices."""

    items: list[InvoiceResponse]
    total: int
    skip: int
    limit: int
