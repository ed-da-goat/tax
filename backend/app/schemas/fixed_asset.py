"""Pydantic schemas for fixed asset management (AN3)."""

from datetime import date as date_type
from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from pydantic import Field

from app.schemas import BaseSchema, RecordSchema


class DepreciationMethodEnum(str, Enum):
    STRAIGHT_LINE = "STRAIGHT_LINE"
    MACRS_GDS = "MACRS_GDS"
    MACRS_ADS = "MACRS_ADS"
    SECTION_179 = "SECTION_179"
    BONUS = "BONUS"
    NONE = "NONE"


class AssetStatusEnum(str, Enum):
    ACTIVE = "ACTIVE"
    FULLY_DEPRECIATED = "FULLY_DEPRECIATED"
    DISPOSED = "DISPOSED"
    TRANSFERRED = "TRANSFERRED"


class FixedAssetCreate(BaseSchema):
    asset_name: str = Field(..., min_length=1, max_length=255)
    asset_number: str | None = None
    description: str | None = None
    category: str | None = None
    acquisition_date: date_type
    acquisition_cost: Decimal = Field(..., gt=0)
    depreciation_method: DepreciationMethodEnum = DepreciationMethodEnum.MACRS_GDS
    useful_life_years: int | None = None
    salvage_value: Decimal = Decimal("0")
    macrs_class: str | None = None
    bonus_depreciation_pct: Decimal = Decimal("0")
    section_179_amount: Decimal = Decimal("0")
    asset_account_id: UUID | None = None
    depreciation_expense_account_id: UUID | None = None
    accumulated_depreciation_account_id: UUID | None = None
    location: str | None = None
    serial_number: str | None = None


class FixedAssetUpdate(BaseSchema):
    asset_name: str | None = None
    description: str | None = None
    category: str | None = None
    location: str | None = None
    serial_number: str | None = None


class FixedAssetDispose(BaseSchema):
    disposal_date: date_type
    disposal_amount: Decimal = Decimal("0")
    disposal_method: str = "SOLD"


class DepreciationEntryResponse(RecordSchema):
    asset_id: UUID
    period_start: date_type
    period_end: date_type
    fiscal_year: int
    depreciation_amount: Decimal
    accumulated_total: Decimal
    book_value_end: Decimal
    is_posted: bool
    journal_entry_id: UUID | None = None
    posted_at: datetime | None = None


class FixedAssetResponse(RecordSchema):
    client_id: UUID
    asset_name: str
    asset_number: str | None = None
    description: str | None = None
    category: str | None = None
    acquisition_date: date_type
    acquisition_cost: Decimal
    depreciation_method: DepreciationMethodEnum
    useful_life_years: int | None = None
    salvage_value: Decimal
    macrs_class: str | None = None
    bonus_depreciation_pct: Decimal | None = None
    section_179_amount: Decimal | None = None
    accumulated_depreciation: Decimal
    book_value: Decimal
    status: AssetStatusEnum
    disposal_date: date_type | None = None
    disposal_amount: Decimal | None = None
    disposal_method: str | None = None
    gain_loss: Decimal | None = None
    location: str | None = None
    serial_number: str | None = None
    depreciation_schedule: list[DepreciationEntryResponse] = []
    deleted_at: datetime | None = None


class FixedAssetList(BaseSchema):
    items: list[FixedAssetResponse]
    total: int


class DepreciationSummary(BaseSchema):
    client_id: UUID
    fiscal_year: int
    total_assets: int
    total_cost: Decimal
    total_accumulated_depreciation: Decimal
    total_book_value: Decimal
    current_year_depreciation: Decimal
