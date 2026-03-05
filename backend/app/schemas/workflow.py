"""Pydantic schemas for workflow engine (WF1-WF4)."""

from datetime import date as date_type
from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import Field

from app.schemas import BaseSchema, RecordSchema


class WorkflowStatusEnum(str, Enum):
    TEMPLATE = "TEMPLATE"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"


class TaskStatusEnum(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING_CLIENT = "WAITING_CLIENT"
    IN_REVIEW = "IN_REVIEW"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"


class TaskPriorityEnum(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


class RecurrenceEnum(str, Enum):
    NONE = "NONE"
    WEEKLY = "WEEKLY"
    BIWEEKLY = "BIWEEKLY"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    ANNUALLY = "ANNUALLY"


# --- Workflow ---
class WorkflowCreate(BaseSchema):
    client_id: UUID | None = None
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    workflow_type: str
    is_template: bool = False
    template_id: UUID | None = None
    assigned_to: UUID | None = None
    due_date: date_type | None = None
    start_date: date_type | None = None
    recurrence: RecurrenceEnum = RecurrenceEnum.NONE
    tax_year: int | None = None


class WorkflowUpdate(BaseSchema):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    assigned_to: UUID | None = None
    due_date: date_type | None = None
    current_stage: str | None = None
    recurrence: RecurrenceEnum | None = None


class TaskResponse(RecordSchema):
    workflow_id: UUID
    title: str
    description: str | None = None
    assigned_to: UUID | None = None
    status: TaskStatusEnum
    priority: TaskPriorityEnum
    due_date: date_type | None = None
    completed_at: datetime | None = None
    sort_order: int
    depends_on: UUID | None = None


class WorkflowResponse(RecordSchema):
    client_id: UUID | None = None
    name: str
    description: str | None = None
    workflow_type: str
    status: WorkflowStatusEnum
    is_template: bool
    template_id: UUID | None = None
    assigned_to: UUID | None = None
    due_date: date_type | None = None
    start_date: date_type | None = None
    completed_at: datetime | None = None
    recurrence: RecurrenceEnum
    next_recurrence_date: date_type | None = None
    tax_year: int | None = None
    current_stage: str
    stage_order: int
    tasks: list[TaskResponse] = []
    deleted_at: datetime | None = None


class WorkflowList(BaseSchema):
    items: list[WorkflowResponse]
    total: int


# --- Tasks ---
class TaskCreate(BaseSchema):
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    assigned_to: UUID | None = None
    priority: TaskPriorityEnum = TaskPriorityEnum.MEDIUM
    due_date: date_type | None = None
    sort_order: int = 0
    depends_on: UUID | None = None


class TaskUpdate(BaseSchema):
    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    assigned_to: UUID | None = None
    status: TaskStatusEnum | None = None
    priority: TaskPriorityEnum | None = None
    due_date: date_type | None = None
    sort_order: int | None = None


# --- Task Comments ---
class TaskCommentCreate(BaseSchema):
    content: str = Field(..., min_length=1)


class TaskCommentResponse(RecordSchema):
    task_id: UUID
    user_id: UUID
    content: str


# --- Workflow Stages ---
class WorkflowStageResponse(BaseSchema):
    id: UUID
    workflow_type: str
    stage_name: str
    stage_order: int
    color: str | None = None
    is_completion_stage: bool


# --- Due Dates ---
class DueDateCreate(BaseSchema):
    client_id: UUID | None = None
    title: str = Field(..., min_length=1, max_length=255)
    due_date: date_type
    form_type: str | None = None
    filing_type: str | None = None
    tax_year: int | None = None
    notes: str | None = None
    remind_days_before: int = 7


class DueDateUpdate(BaseSchema):
    title: str | None = None
    due_date: date_type | None = None
    notes: str | None = None
    is_completed: bool | None = None


class DueDateResponse(RecordSchema):
    client_id: UUID | None = None
    title: str
    due_date: date_type
    form_type: str | None = None
    filing_type: str | None = None
    tax_year: int | None = None
    is_completed: bool
    completed_at: datetime | None = None
    completed_by: UUID | None = None
    notes: str | None = None
    remind_days_before: int | None = None
    deleted_at: datetime | None = None


class DueDateList(BaseSchema):
    items: list[DueDateResponse]
    total: int


# --- Reminders ---
class ReminderResponse(RecordSchema):
    user_id: UUID
    client_id: UUID | None = None
    workflow_id: UUID | None = None
    task_id: UUID | None = None
    reminder_type: str
    channel: str
    title: str
    message: str | None = None
    remind_at: datetime
    is_sent: bool
    is_read: bool


class ReminderList(BaseSchema):
    items: list[ReminderResponse]
    total: int


# --- Kanban Board ---
class KanbanColumn(BaseSchema):
    stage_name: str
    stage_order: int
    color: str | None = None
    workflows: list[WorkflowResponse] = []
    count: int = 0
