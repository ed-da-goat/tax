"""Pydantic schemas for firm-to-client service invoicing (PM2)."""

from datetime import date as date_type
from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from pydantic import Field

from app.schemas import BaseSchema, RecordSchema


class ServiceInvoiceStatus(str, Enum):
    DRAFT = "DRAFT"
    SENT = "SENT"
    VIEWED = "VIEWED"
    PAID = "PAID"
    PARTIAL = "PARTIAL"
    OVERDUE = "OVERDUE"
    VOID = "VOID"


class PaymentMethodEnum(str, Enum):
    CHECK = "CHECK"
    ACH = "ACH"
    CREDIT_CARD = "CREDIT_CARD"
    CASH = "CASH"
    OTHER = "OTHER"


class ServiceInvoiceLineCreate(BaseSchema):
    description: str
    quantity: Decimal = Field(default=Decimal("1"), gt=0)
    unit_price: Decimal
    service_type: str | None = None
    time_entry_id: UUID | None = None


class ServiceInvoiceCreate(BaseSchema):
    client_id: UUID
    invoice_date: date_type
    due_date: date_type
    lines: list[ServiceInvoiceLineCreate] = Field(..., min_length=1)
    notes: str | None = None
    terms: str | None = None
    discount_amount: Decimal = Decimal("0")
    is_recurring: bool = False
    recurrence_interval: str | None = None
    engagement_id: UUID | None = None


class ServiceInvoiceUpdate(BaseSchema):
    due_date: date_type | None = None
    notes: str | None = None
    terms: str | None = None
    discount_amount: Decimal | None = None


class ServiceInvoiceLineResponse(RecordSchema):
    invoice_id: UUID
    description: str
    quantity: Decimal
    unit_price: Decimal
    amount: Decimal
    service_type: str | None = None
    time_entry_id: UUID | None = None


class ServiceInvoicePaymentCreate(BaseSchema):
    payment_date: date_type
    amount: Decimal = Field(..., gt=0)
    payment_method: PaymentMethodEnum = PaymentMethodEnum.CHECK
    reference_number: str | None = None
    notes: str | None = None


class ServiceInvoicePaymentResponse(RecordSchema):
    invoice_id: UUID
    payment_date: date_type
    amount: Decimal
    payment_method: PaymentMethodEnum
    reference_number: str | None = None
    notes: str | None = None


class ServiceInvoiceResponse(RecordSchema):
    client_id: UUID
    invoice_number: str
    invoice_date: date_type
    due_date: date_type
    subtotal: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    amount_paid: Decimal
    balance_due: Decimal
    status: ServiceInvoiceStatus
    notes: str | None = None
    terms: str | None = None
    is_recurring: bool
    recurrence_interval: str | None = None
    engagement_id: UUID | None = None
    sent_at: datetime | None = None
    viewed_at: datetime | None = None
    lines: list[ServiceInvoiceLineResponse] = []
    payments: list[ServiceInvoicePaymentResponse] = []
    deleted_at: datetime | None = None


class ServiceInvoiceList(BaseSchema):
    items: list[ServiceInvoiceResponse]
    total: int
