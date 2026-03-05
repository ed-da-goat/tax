"""
Pydantic schemas for Employee Records (module P1).
"""

import enum
from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import Field

from app.schemas import BaseSchema, RecordSchema


class FilingStatus(str, enum.Enum):
    SINGLE = "SINGLE"
    MARRIED = "MARRIED"
    HEAD_OF_HOUSEHOLD = "HEAD_OF_HOUSEHOLD"


class PayType(str, enum.Enum):
    HOURLY = "HOURLY"
    SALARY = "SALARY"


class EmployeeCreate(BaseSchema):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    filing_status: FilingStatus = Field(default=FilingStatus.SINGLE)
    allowances: int = Field(default=0, ge=0)
    pay_rate: Decimal = Field(..., ge=0)
    pay_type: PayType
    hire_date: date
    address: str | None = Field(None, max_length=500)
    city: str | None = Field(None, max_length=100)
    state: str | None = Field(None, max_length=2)
    zip: str | None = Field(None, max_length=10)


class EmployeeUpdate(BaseSchema):
    first_name: str | None = Field(None, min_length=1, max_length=100)
    last_name: str | None = Field(None, min_length=1, max_length=100)
    filing_status: FilingStatus | None = None
    allowances: int | None = Field(None, ge=0)
    pay_rate: Decimal | None = Field(None, ge=0)
    pay_type: PayType | None = None
    hire_date: date | None = None
    termination_date: date | None = None
    is_active: bool | None = None
    address: str | None = Field(None, max_length=500)
    city: str | None = Field(None, max_length=100)
    state: str | None = Field(None, max_length=2)
    zip: str | None = Field(None, max_length=10)


class EmployeeResponse(RecordSchema):
    client_id: UUID
    first_name: str
    last_name: str
    filing_status: FilingStatus
    allowances: int
    pay_rate: Decimal
    pay_type: PayType
    hire_date: date
    termination_date: date | None = None
    is_active: bool
    address: str | None = None
    city: str | None = None
    state: str | None = None
    zip: str | None = None


class EmployeeList(BaseSchema):
    items: list[EmployeeResponse]
    total: int
