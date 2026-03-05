"""
Pydantic schemas for Tax E-Filing (Phase 8B).

Includes submission tracking for TaxBandits API (1099/W-2),
Georgia FSET (G-7), and manual filing records.
"""

import enum
from datetime import date, datetime
from uuid import UUID

from pydantic import Field

from app.schemas import BaseSchema, RecordSchema


class TaxFilingStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    ERROR = "ERROR"


class TaxFilingProvider(str, enum.Enum):
    TAXBANDITS = "TAXBANDITS"
    GA_FSET = "GA_FSET"
    MANUAL = "MANUAL"


# ---------------------------------------------------------------------------
# Tax Filing Submission schemas
# ---------------------------------------------------------------------------

class TaxFilingCreate(BaseSchema):
    """Create a new tax filing submission record."""
    form_type: str = Field(
        ..., min_length=1, max_length=20,
        description="Form type: '941', '940', 'G-7', 'W-2', '1099-NEC', etc.",
    )
    tax_year: int = Field(..., ge=2024, le=2030)
    tax_quarter: int | None = Field(None, ge=1, le=4)
    filing_period_start: date | None = None
    filing_period_end: date | None = None
    provider: TaxFilingProvider = Field(default=TaxFilingProvider.MANUAL)
    submission_data: dict | None = Field(
        None,
        description="JSON snapshot of data to submit (for audit trail)",
    )


class TaxFilingUpdate(BaseSchema):
    """Update a tax filing submission (status changes, provider responses)."""
    status: TaxFilingStatus | None = None
    provider_submission_id: str | None = Field(None, max_length=100)
    provider_reference: str | None = Field(None, max_length=255)
    rejection_reason: str | None = None
    response_data: dict | None = None


class TaxFilingResponse(RecordSchema):
    client_id: UUID
    form_type: str
    tax_year: int
    tax_quarter: int | None = None
    filing_period_start: date | None = None
    filing_period_end: date | None = None
    provider: TaxFilingProvider
    provider_submission_id: str | None = None
    provider_reference: str | None = None
    status: TaxFilingStatus
    submitted_at: datetime | None = None
    accepted_at: datetime | None = None
    rejected_at: datetime | None = None
    rejection_reason: str | None = None
    submitted_by: UUID | None = None


class TaxFilingList(BaseSchema):
    items: list[TaxFilingResponse]
    total: int


# ---------------------------------------------------------------------------
# TaxBandits-specific schemas
# ---------------------------------------------------------------------------

class TaxBanditsConfig(BaseSchema):
    """Configuration for TaxBandits API integration."""
    # COMPLIANCE REVIEW NEEDED: API keys must be stored securely
    # These are provided per request, not stored in DB
    client_id: str = Field(..., description="TaxBandits API Client ID")
    client_secret: str = Field(..., description="TaxBandits API Client Secret")
    is_sandbox: bool = Field(
        default=True,
        description="Use sandbox environment for testing",
    )


class TaxBanditsW2Submit(BaseSchema):
    """Submit W-2 data through TaxBandits API."""
    tax_year: int = Field(..., ge=2024, le=2030)
    # W-2 data is pulled from existing payroll runs — no need to re-enter


class TaxBandits1099Submit(BaseSchema):
    """Submit 1099-NEC data through TaxBandits API."""
    tax_year: int = Field(..., ge=2024, le=2030)
    # 1099 data is pulled from existing vendor payments — no need to re-enter


# ---------------------------------------------------------------------------
# Georgia FSET-specific schemas
# ---------------------------------------------------------------------------

class GAFSETConfig(BaseSchema):
    """Configuration for Georgia DOR FSET (SFTP + XML) integration."""
    # COMPLIANCE REVIEW NEEDED: SFTP credentials must be stored securely
    sftp_host: str = Field(default="fset.dor.ga.gov")
    sftp_username: str = Field(..., description="FSET SFTP username")
    sftp_password: str = Field(..., description="FSET SFTP password")
    is_test: bool = Field(
        default=True,
        description="Use test credentials and test endpoint",
    )


class GAFSETG7Submit(BaseSchema):
    """Submit Georgia G-7 withholding return via FSET."""
    tax_year: int = Field(..., ge=2024, le=2030)
    tax_quarter: int = Field(..., ge=1, le=4)
