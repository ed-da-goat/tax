"""
Workflow engine API endpoints (WF1-WF4).

Endpoints cover workflows, tasks, Kanban board, stages, due dates, reminders.
"""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, get_current_user, require_role
from app.database import get_db
from app.schemas.workflow import (
    WorkflowCreate, WorkflowUpdate, WorkflowResponse, WorkflowList,
    TaskCreate, TaskUpdate, TaskResponse,
    TaskCommentCreate, TaskCommentResponse,
    WorkflowStageResponse, KanbanColumn,
    DueDateCreate, DueDateUpdate, DueDateResponse, DueDateList,
    ReminderResponse, ReminderList,
)
from app.services.workflow_service import WorkflowService

router = APIRouter()


# --- Workflows ---
@router.post("/workflows", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    data: WorkflowCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    wf = await WorkflowService.create_workflow(db, data, current_user)
    return WorkflowResponse.model_validate(wf)


@router.get("/workflows", response_model=WorkflowList)
async def list_workflows(
    client_id: UUID | None = None,
    status_filter: str | None = Query(None, alias="status"),
    workflow_type: str | None = None,
    assigned_to: UUID | None = None,
    is_template: bool | None = None,
    skip: int = 0, limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    items, total = await WorkflowService.list_workflows(
        db, client_id, status_filter, workflow_type, assigned_to, is_template, skip, limit
    )
    return WorkflowList(
        items=[WorkflowResponse.model_validate(w) for w in items],
        total=total,
    )


@router.get("/workflows/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    wf = await WorkflowService.get_workflow(db, workflow_id)
    return WorkflowResponse.model_validate(wf)


@router.put("/workflows/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(
    workflow_id: UUID,
    data: WorkflowUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    wf = await WorkflowService.update_workflow(db, workflow_id, data, current_user)
    return WorkflowResponse.model_validate(wf)


@router.delete("/workflows/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("CPA_OWNER")),
):
    await WorkflowService.delete_workflow(db, workflow_id, current_user)


# --- Kanban Board ---
@router.get("/kanban/{workflow_type}", response_model=list[KanbanColumn])
async def get_kanban_board(
    workflow_type: str,
    client_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    columns = await WorkflowService.get_kanban(db, workflow_type, client_id)
    return [KanbanColumn(**col) for col in columns]


# --- Stages ---
@router.get("/stages/{workflow_type}", response_model=list[WorkflowStageResponse])
async def get_stages(
    workflow_type: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    stages = await WorkflowService.get_stages(db, workflow_type)
    return [WorkflowStageResponse.model_validate(s) for s in stages]


# --- Tasks ---
@router.post("/workflows/{workflow_id}/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def add_task(
    workflow_id: UUID,
    data: TaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    task = await WorkflowService.add_task(db, workflow_id, data, current_user)
    return TaskResponse.model_validate(task)


@router.put("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: UUID,
    data: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    task = await WorkflowService.update_task(db, task_id, data, current_user)
    return TaskResponse.model_validate(task)


# --- Task Comments ---
@router.post("/tasks/{task_id}/comments", response_model=TaskCommentResponse, status_code=status.HTTP_201_CREATED)
async def add_comment(
    task_id: UUID,
    data: TaskCommentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    comment = await WorkflowService.add_comment(db, task_id, data, current_user)
    return TaskCommentResponse.model_validate(comment)


# --- Due Dates ---
@router.post("/due-dates", response_model=DueDateResponse, status_code=status.HTTP_201_CREATED)
async def create_due_date(
    data: DueDateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    dd = await WorkflowService.create_due_date(db, data, current_user)
    return DueDateResponse.model_validate(dd)


@router.get("/due-dates", response_model=DueDateList)
async def list_due_dates(
    client_id: UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    completed: bool | None = None,
    skip: int = 0, limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    items, total = await WorkflowService.list_due_dates(
        db, client_id, date_from, date_to, completed, skip, limit
    )
    return DueDateList(
        items=[DueDateResponse.model_validate(d) for d in items],
        total=total,
    )


@router.post("/due-dates/{due_date_id}/complete", response_model=DueDateResponse)
async def complete_due_date(
    due_date_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    dd = await WorkflowService.complete_due_date(db, due_date_id, current_user)
    return DueDateResponse.model_validate(dd)


# --- Reminders ---
@router.get("/reminders", response_model=ReminderList)
async def get_reminders(
    unread_only: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    items = await WorkflowService.get_reminders(db, current_user.user_id, unread_only)
    return ReminderList(
        items=[ReminderResponse.model_validate(r) for r in items],
        total=len(items),
    )


@router.post("/reminders/{reminder_id}/read", response_model=ReminderResponse)
async def mark_reminder_read(
    reminder_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    reminder = await WorkflowService.mark_reminder_read(db, reminder_id, current_user)
    return ReminderResponse.model_validate(reminder)


# --- Recurring Processing ---
@router.post("/workflows/process-recurring", response_model=list[WorkflowResponse])
async def process_recurring(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("CPA_OWNER")),
):
    created = await WorkflowService.process_recurring_workflows(db)
    return [WorkflowResponse.model_validate(w) for w in created]
