"""
Pydantic schemas for Direct Deposit (Phase 8A).

Includes employee bank account management and NACHA batch tracking.
"""

import enum
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field, field_validator

from app.schemas import BaseSchema, RecordSchema


class AccountType(str, enum.Enum):
    CHECKING = "CHECKING"
    SAVINGS = "SAVINGS"


class PrenoteStatus(str, enum.Enum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"


class DDBatchStatus(str, enum.Enum):
    GENERATED = "GENERATED"
    DOWNLOADED = "DOWNLOADED"
    SUBMITTED = "SUBMITTED"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"


# ---------------------------------------------------------------------------
# Employee Bank Account schemas
# ---------------------------------------------------------------------------

class EmployeeBankAccountCreate(BaseSchema):
    """Enroll an employee in direct deposit."""
    account_holder_name: str = Field(..., min_length=1, max_length=255)
    account_number: str = Field(
        ..., min_length=4, max_length=17,
        description="Bank account number (will be encrypted at rest)",
    )
    routing_number: str = Field(
        ..., min_length=9, max_length=9,
        description="9-digit ABA routing number",
    )
    account_type: AccountType = Field(default=AccountType.CHECKING)
    is_primary: bool = Field(default=True)
    enrollment_date: date | None = None
    authorization_on_file: bool = Field(
        default=False,
        description="Must be True to generate NACHA files (written consent required)",
    )

    @field_validator("routing_number")
    @classmethod
    def validate_routing_number(cls, v: str) -> str:
        if not v.isdigit() or len(v) != 9:
            raise ValueError("Routing number must be exactly 9 digits")
        # ABA routing number checksum validation
        digits = [int(d) for d in v]
        checksum = (
            3 * (digits[0] + digits[3] + digits[6])
            + 7 * (digits[1] + digits[4] + digits[7])
            + (digits[2] + digits[5] + digits[8])
        )
        if checksum % 10 != 0:
            raise ValueError("Invalid ABA routing number (checksum failed)")
        return v

    @field_validator("account_number")
    @classmethod
    def validate_account_number(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("Account number must contain only digits")
        return v


class EmployeeBankAccountUpdate(BaseSchema):
    account_holder_name: str | None = Field(None, min_length=1, max_length=255)
    account_number: str | None = Field(None, min_length=4, max_length=17)
    routing_number: str | None = Field(None, min_length=9, max_length=9)
    account_type: AccountType | None = None
    is_primary: bool | None = None
    authorization_on_file: bool | None = None

    @field_validator("routing_number")
    @classmethod
    def validate_routing_number(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not v.isdigit() or len(v) != 9:
            raise ValueError("Routing number must be exactly 9 digits")
        digits = [int(d) for d in v]
        checksum = (
            3 * (digits[0] + digits[3] + digits[6])
            + 7 * (digits[1] + digits[4] + digits[7])
            + (digits[2] + digits[5] + digits[8])
        )
        if checksum % 10 != 0:
            raise ValueError("Invalid ABA routing number (checksum failed)")
        return v


class EmployeeBankAccountResponse(RecordSchema):
    employee_id: UUID
    client_id: UUID
    account_holder_name: str
    account_number_masked: str = Field(
        description="Last 4 digits only, e.g. '****1234'",
    )
    routing_number: str
    account_type: AccountType
    is_primary: bool
    enrollment_date: date | None = None
    authorization_on_file: bool
    prenote_status: PrenoteStatus
    prenote_sent_at: datetime | None = None
    prenote_verified_at: datetime | None = None


class EmployeeBankAccountList(BaseSchema):
    items: list[EmployeeBankAccountResponse]
    total: int


# ---------------------------------------------------------------------------
# Direct Deposit Batch schemas
# ---------------------------------------------------------------------------

class DDBatchResponse(RecordSchema):
    payroll_run_id: UUID
    client_id: UUID
    batch_number: int
    entry_count: int
    total_credit_amount: Decimal
    company_name: str
    company_id: str
    status: DDBatchStatus
    generated_at: datetime
    downloaded_at: datetime | None = None
    submitted_at: datetime | None = None
    confirmed_at: datetime | None = None
    generated_by: UUID | None = None


class DDBatchList(BaseSchema):
    items: list[DDBatchResponse]
    total: int


class NACHAGenerateRequest(BaseSchema):
    """Configuration for NACHA file generation."""
    company_name: str = Field(..., min_length=1, max_length=16)
    company_id: str = Field(
        ..., min_length=1, max_length=10,
        description="Company identification number (EIN or DUNS)",
    )
    odfi_routing_number: str = Field(
        ..., min_length=9, max_length=9,
        description="9-digit routing number of the Originating DFI (your bank)",
    )
    odfi_name: str = Field(
        ..., min_length=1, max_length=23,
        description="Name of the Originating DFI",
    )
    effective_entry_date: date = Field(
        description="Date the entries should be settled (1-2 business days from now)",
    )
    file_id_modifier: str = Field(
        default="A",
        min_length=1, max_length=1,
        description="A-Z or 0-9, increment if multiple files per day",
    )
