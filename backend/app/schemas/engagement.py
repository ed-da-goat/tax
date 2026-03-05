"""Pydantic schemas for engagement letters & proposals (PM3)."""

from datetime import date as date_type
from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from pydantic import Field

from app.schemas import BaseSchema, RecordSchema


class EngagementStatus(str, Enum):
    DRAFT = "DRAFT"
    SENT = "SENT"
    VIEWED = "VIEWED"
    SIGNED = "SIGNED"
    DECLINED = "DECLINED"
    EXPIRED = "EXPIRED"


class EngagementCreate(BaseSchema):
    client_id: UUID
    title: str = Field(..., min_length=1, max_length=255)
    engagement_type: str
    description: str | None = None
    terms_and_conditions: str | None = None
    fee_type: str = "FIXED"
    fixed_fee: Decimal | None = None
    hourly_rate: Decimal | None = None
    estimated_hours: Decimal | None = None
    retainer_amount: Decimal | None = None
    start_date: date_type| None = None
    end_date: date_type| None = None
    tax_year: int | None = None


class EngagementUpdate(BaseSchema):
    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    terms_and_conditions: str | None = None
    fee_type: str | None = None
    fixed_fee: Decimal | None = None
    hourly_rate: Decimal | None = None
    estimated_hours: Decimal | None = None
    retainer_amount: Decimal | None = None
    start_date: date_type| None = None
    end_date: date_type| None = None
    tax_year: int | None = None


class EngagementResponse(RecordSchema):
    client_id: UUID
    title: str
    engagement_type: str
    description: str | None = None
    terms_and_conditions: str | None = None
    fee_type: str
    fixed_fee: Decimal | None = None
    hourly_rate: Decimal | None = None
    estimated_hours: Decimal | None = None
    retainer_amount: Decimal | None = None
    start_date: date_type| None = None
    end_date: date_type| None = None
    tax_year: int | None = None
    status: EngagementStatus
    sent_at: datetime | None = None
    signed_at: datetime | None = None
    signed_by: str | None = None
    deleted_at: datetime | None = None


class EngagementList(BaseSchema):
    items: list[EngagementResponse]
    total: int
