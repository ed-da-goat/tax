"""
SQLAlchemy ORM models for time tracking (PM1).

Tables: time_entries, staff_rates, timer_sessions
"""

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean, Date, DateTime, Enum, ForeignKey, Integer, Numeric,
    String, Text, text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin


class TimeEntryStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    BILLED = "BILLED"


class TimeEntry(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "time_entries"

    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    workflow_task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_tasks.id"), nullable=True
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_billable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    hourly_rate: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    status: Mapped[TimeEntryStatus] = mapped_column(
        Enum(TimeEntryStatus, name="time_entry_status", create_type=False),
        default=TimeEntryStatus.DRAFT, nullable=False
    )
    service_type: Mapped[str | None] = mapped_column(String(100), nullable=True)


class StaffRate(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "staff_rates"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    rate_name: Mapped[str] = mapped_column(String(100), default="Standard", nullable=False)
    hourly_rate: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)


class TimerSession(Base, TimestampMixin):
    __tablename__ = "timer_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    client_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id"), nullable=True
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    service_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )
    stopped_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_running: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
