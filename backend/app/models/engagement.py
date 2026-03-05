"""
SQLAlchemy ORM model for engagement letters & proposals (PM3).
"""

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date, DateTime, Enum, ForeignKey, Integer, Numeric,
    String, Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin, TimestampMixin


class EngagementStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SENT = "SENT"
    VIEWED = "VIEWED"
    SIGNED = "SIGNED"
    DECLINED = "DECLINED"
    EXPIRED = "EXPIRED"


class Engagement(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "engagements"

    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    engagement_type: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    terms_and_conditions: Mapped[str | None] = mapped_column(Text, nullable=True)
    fee_type: Mapped[str] = mapped_column(String(20), default="FIXED", nullable=False)
    fixed_fee: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    hourly_rate: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    estimated_hours: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    retainer_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    tax_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[EngagementStatus] = mapped_column(
        Enum(EngagementStatus, name="engagement_status", create_type=False),
        default=EngagementStatus.DRAFT, nullable=False
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    signed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    signature_data: Mapped[str | None] = mapped_column(Text, nullable=True)
