"""
Service layer for workflow engine (WF1-WF4).

Workflow pipelines, tasks, Kanban boards, recurring jobs, due dates, reminders.
"""

import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, verify_role
from app.models.workflow import (
    Workflow, WorkflowStatus, WorkflowStage, WorkflowTask, TaskStatusEnum,
    TaskComment, Reminder, ReminderType, ReminderChannel, DueDate,
    RecurrenceType,
)
from app.schemas.workflow import (
    WorkflowCreate, WorkflowUpdate, TaskCreate, TaskUpdate,
    TaskCommentCreate, DueDateCreate, DueDateUpdate,
)


class WorkflowService:

    # --- Workflows ---
    @staticmethod
    async def create_workflow(
        db: AsyncSession, data: WorkflowCreate, current_user: CurrentUser,
    ) -> Workflow:
        status = WorkflowStatus.TEMPLATE if data.is_template else WorkflowStatus.ACTIVE

        # If creating from template, copy tasks
        template_tasks = []
        if data.template_id:
            template = await WorkflowService.get_workflow(db, data.template_id)
            template_tasks = list(template.tasks)

        workflow = Workflow(
            client_id=data.client_id,
            name=data.name,
            description=data.description,
            workflow_type=data.workflow_type,
            status=status,
            is_template=data.is_template,
            template_id=data.template_id,
            assigned_to=data.assigned_to,
            due_date=data.due_date,
            start_date=data.start_date or date.today(),
            recurrence=RecurrenceType(data.recurrence.value),
            tax_year=data.tax_year,
        )
        db.add(workflow)
        await db.flush()

        # Copy tasks from template
        for t in template_tasks:
            task = WorkflowTask(
                workflow_id=workflow.id,
                title=t.title,
                description=t.description,
                priority=t.priority,
                sort_order=t.sort_order,
            )
            db.add(task)

        # Create deadline reminder if due date set
        if workflow.due_date and workflow.assigned_to:
            reminder = Reminder(
                user_id=workflow.assigned_to,
                client_id=workflow.client_id,
                workflow_id=workflow.id,
                reminder_type=ReminderType.DEADLINE,
                channel=ReminderChannel.IN_APP,
                title=f"Deadline: {workflow.name}",
                message=f"Workflow '{workflow.name}' is due on {workflow.due_date}",
                remind_at=datetime.combine(
                    workflow.due_date - timedelta(days=7),
                    datetime.min.time(),
                    tzinfo=timezone.utc,
                ),
            )
            db.add(reminder)

        await db.commit()
        await db.refresh(workflow)
        return workflow

    @staticmethod
    async def list_workflows(
        db: AsyncSession,
        client_id: uuid.UUID | None = None,
        status_filter: str | None = None,
        workflow_type: str | None = None,
        assigned_to: uuid.UUID | None = None,
        is_template: bool | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[Workflow], int]:
        query = select(Workflow).where(Workflow.deleted_at.is_(None))
        count_q = select(func.count(Workflow.id)).where(Workflow.deleted_at.is_(None))

        if client_id:
            query = query.where(Workflow.client_id == client_id)
            count_q = count_q.where(Workflow.client_id == client_id)
        if status_filter:
            query = query.where(Workflow.status == status_filter)
            count_q = count_q.where(Workflow.status == status_filter)
        if workflow_type:
            query = query.where(Workflow.workflow_type == workflow_type)
            count_q = count_q.where(Workflow.workflow_type == workflow_type)
        if assigned_to:
            query = query.where(Workflow.assigned_to == assigned_to)
            count_q = count_q.where(Workflow.assigned_to == assigned_to)
        if is_template is not None:
            query = query.where(Workflow.is_template == is_template)
            count_q = count_q.where(Workflow.is_template == is_template)

        total = (await db.execute(count_q)).scalar() or 0
        result = await db.execute(
            query.order_by(Workflow.due_date.asc().nullslast(), Workflow.created_at.desc())
            .offset(skip).limit(limit)
        )
        return list(result.scalars().unique().all()), total

    @staticmethod
    async def get_workflow(db: AsyncSession, workflow_id: uuid.UUID) -> Workflow:
        result = await db.execute(
            select(Workflow).where(
                Workflow.id == workflow_id, Workflow.deleted_at.is_(None)
            )
        )
        wf = result.scalar_one_or_none()
        if not wf:
            raise HTTPException(status_code=404, detail="Workflow not found")
        return wf

    @staticmethod
    async def update_workflow(
        db: AsyncSession, workflow_id: uuid.UUID,
        data: WorkflowUpdate, current_user: CurrentUser,
    ) -> Workflow:
        wf = await WorkflowService.get_workflow(db, workflow_id)
        update_data = data.model_dump(exclude_unset=True)

        if "current_stage" in update_data:
            # Look up the stage order
            stage_result = await db.execute(
                select(WorkflowStage).where(
                    WorkflowStage.workflow_type == wf.workflow_type,
                    WorkflowStage.stage_name == update_data["current_stage"],
                )
            )
            stage = stage_result.scalar_one_or_none()
            if stage:
                wf.stage_order = stage.stage_order
                if stage.is_completion_stage:
                    wf.status = WorkflowStatus.COMPLETED
                    wf.completed_at = datetime.now(timezone.utc)

        for field, value in update_data.items():
            setattr(wf, field, value)

        await db.commit()
        await db.refresh(wf)
        return wf

    @staticmethod
    async def delete_workflow(
        db: AsyncSession, workflow_id: uuid.UUID, current_user: CurrentUser,
    ) -> None:
        verify_role(current_user, "CPA_OWNER")
        wf = await WorkflowService.get_workflow(db, workflow_id)
        wf.deleted_at = datetime.now(timezone.utc)
        await db.commit()

    # --- Kanban Board ---
    @staticmethod
    async def get_kanban(
        db: AsyncSession, workflow_type: str,
        client_id: uuid.UUID | None = None,
    ) -> list[dict]:
        stages_result = await db.execute(
            select(WorkflowStage).where(
                WorkflowStage.workflow_type == workflow_type
            ).order_by(WorkflowStage.stage_order)
        )
        stages = list(stages_result.scalars().all())

        columns = []
        for stage in stages:
            wf_query = select(Workflow).where(
                Workflow.workflow_type == workflow_type,
                Workflow.current_stage == stage.stage_name,
                Workflow.is_template.is_(False),
                Workflow.deleted_at.is_(None),
            )
            if client_id:
                wf_query = wf_query.where(Workflow.client_id == client_id)

            wf_result = await db.execute(wf_query.order_by(Workflow.due_date.asc().nullslast()))
            workflows = list(wf_result.scalars().unique().all())

            columns.append({
                "stage_name": stage.stage_name,
                "stage_order": stage.stage_order,
                "color": stage.color,
                "workflows": workflows,
                "count": len(workflows),
            })
        return columns

    # --- Stages ---
    @staticmethod
    async def get_stages(db: AsyncSession, workflow_type: str) -> list[WorkflowStage]:
        result = await db.execute(
            select(WorkflowStage).where(
                WorkflowStage.workflow_type == workflow_type
            ).order_by(WorkflowStage.stage_order)
        )
        return list(result.scalars().all())

    # --- Tasks ---
    @staticmethod
    async def add_task(
        db: AsyncSession, workflow_id: uuid.UUID,
        data: TaskCreate, current_user: CurrentUser,
    ) -> WorkflowTask:
        await WorkflowService.get_workflow(db, workflow_id)
        task = WorkflowTask(
            workflow_id=workflow_id,
            title=data.title,
            description=data.description,
            assigned_to=data.assigned_to,
            priority=data.priority,
            due_date=data.due_date,
            sort_order=data.sort_order,
            depends_on=data.depends_on,
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)
        return task

    @staticmethod
    async def update_task(
        db: AsyncSession, task_id: uuid.UUID,
        data: TaskUpdate, current_user: CurrentUser,
    ) -> WorkflowTask:
        result = await db.execute(
            select(WorkflowTask).where(
                WorkflowTask.id == task_id, WorkflowTask.deleted_at.is_(None)
            )
        )
        task = result.scalar_one_or_none()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        update_data = data.model_dump(exclude_unset=True)
        if "status" in update_data and update_data["status"] == TaskStatusEnum.COMPLETED.value:
            task.completed_at = datetime.now(timezone.utc)

        for field, value in update_data.items():
            setattr(task, field, value)

        await db.commit()
        await db.refresh(task)
        return task

    @staticmethod
    async def add_comment(
        db: AsyncSession, task_id: uuid.UUID,
        data: TaskCommentCreate, current_user: CurrentUser,
    ) -> TaskComment:
        comment = TaskComment(
            task_id=task_id,
            user_id=current_user.user_id,
            content=data.content,
        )
        db.add(comment)
        await db.commit()
        await db.refresh(comment)
        return comment

    # --- Due Dates ---
    @staticmethod
    async def create_due_date(
        db: AsyncSession, data: DueDateCreate, current_user: CurrentUser,
    ) -> DueDate:
        dd = DueDate(**data.model_dump())
        db.add(dd)
        await db.commit()
        await db.refresh(dd)
        return dd

    @staticmethod
    async def list_due_dates(
        db: AsyncSession,
        client_id: uuid.UUID | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        completed: bool | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[DueDate], int]:
        query = select(DueDate).where(DueDate.deleted_at.is_(None))
        count_q = select(func.count(DueDate.id)).where(DueDate.deleted_at.is_(None))

        if client_id:
            query = query.where(DueDate.client_id == client_id)
            count_q = count_q.where(DueDate.client_id == client_id)
        if date_from:
            query = query.where(DueDate.due_date >= date_from)
            count_q = count_q.where(DueDate.due_date >= date_from)
        if date_to:
            query = query.where(DueDate.due_date <= date_to)
            count_q = count_q.where(DueDate.due_date <= date_to)
        if completed is not None:
            query = query.where(DueDate.is_completed == completed)
            count_q = count_q.where(DueDate.is_completed == completed)

        total = (await db.execute(count_q)).scalar() or 0
        result = await db.execute(
            query.order_by(DueDate.due_date.asc()).offset(skip).limit(limit)
        )
        return list(result.scalars().all()), total

    @staticmethod
    async def complete_due_date(
        db: AsyncSession, due_date_id: uuid.UUID, current_user: CurrentUser,
    ) -> DueDate:
        result = await db.execute(
            select(DueDate).where(DueDate.id == due_date_id, DueDate.deleted_at.is_(None))
        )
        dd = result.scalar_one_or_none()
        if not dd:
            raise HTTPException(status_code=404, detail="Due date not found")
        dd.is_completed = True
        dd.completed_at = datetime.now(timezone.utc)
        dd.completed_by = current_user.user_id
        await db.commit()
        await db.refresh(dd)
        return dd

    # --- Reminders ---
    @staticmethod
    async def get_reminders(
        db: AsyncSession, user_id: uuid.UUID,
        unread_only: bool = False,
    ) -> list[Reminder]:
        query = select(Reminder).where(Reminder.user_id == user_id)
        if unread_only:
            query = query.where(Reminder.is_read.is_(False))
        result = await db.execute(query.order_by(Reminder.remind_at.desc()))
        return list(result.scalars().all())

    @staticmethod
    async def mark_reminder_read(
        db: AsyncSession, reminder_id: uuid.UUID, current_user: CurrentUser,
    ) -> Reminder:
        result = await db.execute(
            select(Reminder).where(Reminder.id == reminder_id)
        )
        reminder = result.scalar_one_or_none()
        if not reminder:
            raise HTTPException(status_code=404, detail="Reminder not found")
        reminder.is_read = True
        reminder.read_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(reminder)
        return reminder

    # --- Recurring Job Processing ---
    @staticmethod
    async def process_recurring_workflows(db: AsyncSession) -> list[Workflow]:
        """Create new workflow instances from recurring templates."""
        result = await db.execute(
            select(Workflow).where(
                Workflow.recurrence != RecurrenceType.NONE,
                Workflow.status == WorkflowStatus.COMPLETED,
                Workflow.next_recurrence_date.isnot(None),
                Workflow.next_recurrence_date <= date.today(),
                Workflow.deleted_at.is_(None),
            )
        )
        recurring = list(result.scalars().unique().all())
        created = []

        for wf in recurring:
            new_wf = Workflow(
                client_id=wf.client_id,
                name=wf.name,
                description=wf.description,
                workflow_type=wf.workflow_type,
                status=WorkflowStatus.ACTIVE,
                is_template=False,
                template_id=wf.template_id or wf.id,
                assigned_to=wf.assigned_to,
                recurrence=wf.recurrence,
                tax_year=(wf.tax_year + 1) if wf.tax_year else None,
            )

            # Calculate next due date based on recurrence
            delta_map = {
                RecurrenceType.WEEKLY: timedelta(weeks=1),
                RecurrenceType.BIWEEKLY: timedelta(weeks=2),
                RecurrenceType.MONTHLY: timedelta(days=30),
                RecurrenceType.QUARTERLY: timedelta(days=91),
                RecurrenceType.ANNUALLY: timedelta(days=365),
            }
            delta = delta_map.get(wf.recurrence, timedelta(days=30))
            new_wf.due_date = wf.next_recurrence_date + delta
            new_wf.start_date = wf.next_recurrence_date

            db.add(new_wf)
            await db.flush()

            # Copy tasks
            for t in wf.tasks:
                task = WorkflowTask(
                    workflow_id=new_wf.id,
                    title=t.title,
                    description=t.description,
                    priority=t.priority,
                    sort_order=t.sort_order,
                )
                db.add(task)

            # Update original's next recurrence
            wf.next_recurrence_date = new_wf.due_date
            created.append(new_wf)

        await db.commit()
        return created
