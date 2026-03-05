"""Pydantic schemas for time tracking (PM1)."""

from datetime import date as date_type
from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from pydantic import Field

from app.schemas import BaseSchema, RecordSchema


class TimeEntryStatus(str, Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    BILLED = "BILLED"


class TimeEntryCreate(BaseSchema):
    client_id: UUID
    entry_date: date_type
    duration_minutes: int = Field(..., gt=0)
    description: str | None = None
    is_billable: bool = True
    hourly_rate: Decimal | None = None
    service_type: str | None = None
    workflow_task_id: UUID | None = None


class TimeEntryUpdate(BaseSchema):
    client_id: UUID | None = None
    entry_date: date_type | None = None
    duration_minutes: int | None = Field(None, gt=0)
    description: str | None = None
    is_billable: bool | None = None
    hourly_rate: Decimal | None = None
    service_type: str | None = None
    workflow_task_id: UUID | None = None


class TimeEntryResponse(RecordSchema):
    client_id: UUID
    user_id: UUID
    entry_date: date_type = Field(alias="date")
    duration_minutes: int
    description: str | None = None
    is_billable: bool
    hourly_rate: Decimal | None = None
    amount: Decimal | None = None
    status: TimeEntryStatus
    service_type: str | None = None
    workflow_task_id: UUID | None = None
    deleted_at: datetime | None = None

    model_config = {"from_attributes": True, "populate_by_name": True}


class TimeEntryList(BaseSchema):
    items: list[TimeEntryResponse]
    total: int


class TimerSessionCreate(BaseSchema):
    client_id: UUID | None = None
    description: str | None = None
    service_type: str | None = None


class TimerSessionResponse(RecordSchema):
    user_id: UUID
    client_id: UUID | None = None
    description: str | None = None
    service_type: str | None = None
    started_at: datetime
    stopped_at: datetime | None = None
    is_running: bool


class StaffRateCreate(BaseSchema):
    user_id: UUID
    rate_name: str = "Standard"
    hourly_rate: Decimal = Field(..., gt=0)
    effective_date: date_type
    end_date: date_type | None = None


class StaffRateResponse(RecordSchema):
    user_id: UUID
    rate_name: str
    hourly_rate: Decimal
    effective_date: date_type
    end_date: date_type | None = None


class UtilizationReport(BaseSchema):
    user_id: UUID
    user_name: str
    total_hours: Decimal
    billable_hours: Decimal
    non_billable_hours: Decimal
    utilization_pct: Decimal
    total_amount: Decimal
    period_start: date_type
    period_end: date_type
