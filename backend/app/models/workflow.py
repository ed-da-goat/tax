"""
SQLAlchemy ORM models for workflow engine (WF1-WF4).

Tables: workflows, workflow_stages, workflow_tasks, task_comments,
        reminders, due_dates
"""

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean, Date, DateTime, Enum, ForeignKey, Integer,
    String, Text, text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin


class WorkflowStatus(str, enum.Enum):
    TEMPLATE = "TEMPLATE"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"


class TaskStatusEnum(str, enum.Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING_CLIENT = "WAITING_CLIENT"
    IN_REVIEW = "IN_REVIEW"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"


class TaskPriority(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


class RecurrenceType(str, enum.Enum):
    NONE = "NONE"
    WEEKLY = "WEEKLY"
    BIWEEKLY = "BIWEEKLY"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    ANNUALLY = "ANNUALLY"


class ReminderType(str, enum.Enum):
    DEADLINE = "DEADLINE"
    FOLLOW_UP = "FOLLOW_UP"
    OVERDUE = "OVERDUE"
    CUSTOM = "CUSTOM"


class ReminderChannel(str, enum.Enum):
    IN_APP = "IN_APP"
    EMAIL = "EMAIL"


class Workflow(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "workflows"

    client_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    workflow_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[WorkflowStatus] = mapped_column(
        Enum(WorkflowStatus, name="workflow_status", create_type=False),
        default=WorkflowStatus.TEMPLATE, nullable=False
    )
    is_template: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflows.id"), nullable=True
    )
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    recurrence: Mapped[RecurrenceType] = mapped_column(
        Enum(RecurrenceType, name="recurrence_type", create_type=False),
        default=RecurrenceType.NONE, nullable=False
    )
    next_recurrence_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    tax_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_stage: Mapped[str] = mapped_column(String(100), default="Not Started", nullable=False)
    stage_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    tasks: Mapped[list["WorkflowTask"]] = relationship(
        back_populates="workflow", cascade="all, delete-orphan", lazy="selectin"
    )


class WorkflowStage(Base, TimestampMixin):
    __tablename__ = "workflow_stages"

    workflow_type: Mapped[str] = mapped_column(String(100), nullable=False)
    stage_name: Mapped[str] = mapped_column(String(100), nullable=False)
    stage_order: Mapped[int] = mapped_column(Integer, nullable=False)
    color: Mapped[str | None] = mapped_column(String(7), default="#6B7280")
    is_completion_stage: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class WorkflowTask(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "workflow_tasks"

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    status: Mapped[TaskStatusEnum] = mapped_column(
        Enum(TaskStatusEnum, name="task_status", create_type=False),
        default=TaskStatusEnum.NOT_STARTED, nullable=False
    )
    priority: Mapped[TaskPriority] = mapped_column(
        Enum(TaskPriority, name="task_priority", create_type=False),
        default=TaskPriority.MEDIUM, nullable=False
    )
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    depends_on: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_tasks.id"), nullable=True
    )

    workflow: Mapped["Workflow"] = relationship(back_populates="tasks")
    comments: Mapped[list["TaskComment"]] = relationship(
        back_populates="task", cascade="all, delete-orphan", lazy="selectin"
    )


class TaskComment(Base, TimestampMixin):
    __tablename__ = "task_comments"

    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_tasks.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)

    task: Mapped["WorkflowTask"] = relationship(back_populates="comments")


class Reminder(Base, TimestampMixin):
    __tablename__ = "reminders"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    client_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id"), nullable=True
    )
    workflow_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflows.id"), nullable=True
    )
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_tasks.id"), nullable=True
    )
    reminder_type: Mapped[ReminderType] = mapped_column(
        Enum(ReminderType, name="reminder_type", create_type=False), nullable=False
    )
    channel: Mapped[ReminderChannel] = mapped_column(
        Enum(ReminderChannel, name="reminder_channel", create_type=False),
        default=ReminderChannel.IN_APP, nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    remind_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DueDate(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "due_dates"

    client_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    form_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    filing_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tax_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    remind_days_before: Mapped[int | None] = mapped_column(Integer, default=7, nullable=True)
