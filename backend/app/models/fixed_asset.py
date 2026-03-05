"""
SQLAlchemy ORM models for fixed asset management (AN3).

Tables: fixed_assets, depreciation_entries
"""

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean, Date, DateTime, Enum, ForeignKey, Integer, Numeric,
    String, Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin


class DepreciationMethod(str, enum.Enum):
    STRAIGHT_LINE = "STRAIGHT_LINE"
    MACRS_GDS = "MACRS_GDS"
    MACRS_ADS = "MACRS_ADS"
    SECTION_179 = "SECTION_179"
    BONUS = "BONUS"
    NONE = "NONE"


class AssetStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    FULLY_DEPRECIATED = "FULLY_DEPRECIATED"
    DISPOSED = "DISPOSED"
    TRANSFERRED = "TRANSFERRED"


class FixedAsset(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "fixed_assets"

    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False
    )
    asset_name: Mapped[str] = mapped_column(String(255), nullable=False)
    asset_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    acquisition_date: Mapped[date] = mapped_column(Date, nullable=False)
    acquisition_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    depreciation_method: Mapped[DepreciationMethod] = mapped_column(
        Enum(DepreciationMethod, name="depreciation_method", create_type=False),
        default=DepreciationMethod.MACRS_GDS, nullable=False
    )
    useful_life_years: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salvage_value: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"), nullable=False)
    macrs_class: Mapped[str | None] = mapped_column(String(20), nullable=True)
    bonus_depreciation_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), default=Decimal("0"))
    section_179_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    accumulated_depreciation: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=Decimal("0"), nullable=False
    )
    book_value: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    status: Mapped[AssetStatus] = mapped_column(
        Enum(AssetStatus, name="asset_status", create_type=False),
        default=AssetStatus.ACTIVE, nullable=False
    )
    disposal_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    disposal_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    disposal_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    gain_loss: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    asset_account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chart_of_accounts.id"), nullable=True
    )
    depreciation_expense_account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chart_of_accounts.id"), nullable=True
    )
    accumulated_depreciation_account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chart_of_accounts.id"), nullable=True
    )
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    serial_number: Mapped[str | None] = mapped_column(String(100), nullable=True)

    depreciation_schedule: Mapped[list["DepreciationEntry"]] = relationship(
        back_populates="asset", cascade="all, delete-orphan", lazy="selectin"
    )


class DepreciationEntry(Base, TimestampMixin):
    __tablename__ = "depreciation_entries"

    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fixed_assets.id", ondelete="CASCADE"), nullable=False
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False)
    depreciation_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    accumulated_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    book_value_end: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    is_posted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    journal_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("journal_entries.id"), nullable=True
    )
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    asset: Mapped["FixedAsset"] = relationship(back_populates="depreciation_schedule")
