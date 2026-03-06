"""
Tests for Workflow Engine endpoints (WF1-WF4).

Covers:
- CRUD workflows (create, list, get, update, delete)
- Tasks (create, update)
- Task comments
- Due dates (create, list, complete)
- Reminders (list, mark read)
- Kanban board view
- Stages listing
- Process recurring (CPA_OWNER only)
- Permission checks: ASSOCIATE cannot delete workflows or process recurring
"""

import uuid
from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.auth.dependencies import CurrentUser, get_current_user
from app.main import app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
CPA_OWNER_ID = uuid.uuid4()
ASSOCIATE_ID = uuid.uuid4()
NOW = datetime.now(timezone.utc)


def _override_as_cpa_owner():
    async def _dep():
        return CurrentUser(user_id=str(CPA_OWNER_ID), role="CPA_OWNER")
    return _dep


def _override_as_associate():
    async def _dep():
        return CurrentUser(user_id=str(ASSOCIATE_ID), role="ASSOCIATE")
    return _dep


def _make_workflow(wf_id=None, **overrides):
    """Build a namespace that matches WorkflowResponse schema exactly."""
    return SimpleNamespace(
        id=wf_id or uuid.uuid4(),
        client_id=overrides.get("client_id", uuid.uuid4()),
        name=overrides.get("name", "Tax Prep 2026"),
        description=overrides.get("description", ""),
        workflow_type=overrides.get("workflow_type", "tax_return"),
        status=overrides.get("status", "ACTIVE"),
        is_template=overrides.get("is_template", False),
        template_id=overrides.get("template_id", None),
        assigned_to=overrides.get("assigned_to", None),
        due_date=overrides.get("due_date", date(2026, 4, 15)),
        start_date=overrides.get("start_date", date(2026, 1, 1)),
        completed_at=overrides.get("completed_at", None),
        recurrence=overrides.get("recurrence", "NONE"),
        next_recurrence_date=overrides.get("next_recurrence_date", None),
        tax_year=overrides.get("tax_year", 2026),
        current_stage=overrides.get("current_stage", "Preparation"),
        stage_order=overrides.get("stage_order", 0),
        tasks=overrides.get("tasks", []),
        deleted_at=overrides.get("deleted_at", None),
        created_at=NOW,
        updated_at=NOW,
    )


def _make_task(task_id=None, **overrides):
    """Build a namespace that matches TaskResponse schema exactly."""
    return SimpleNamespace(
        id=task_id or uuid.uuid4(),
        workflow_id=overrides.get("workflow_id", uuid.uuid4()),
        title=overrides.get("title", "Gather W-2s"),
        description=overrides.get("description", None),
        assigned_to=overrides.get("assigned_to", None),
        status=overrides.get("status", "NOT_STARTED"),
        priority=overrides.get("priority", "MEDIUM"),
        due_date=overrides.get("due_date", None),
        completed_at=overrides.get("completed_at", None),
        sort_order=overrides.get("sort_order", 0),
        depends_on=overrides.get("depends_on", None),
        created_at=NOW,
        updated_at=NOW,
    )


def _make_comment(comment_id=None, **overrides):
    return SimpleNamespace(
        id=comment_id or uuid.uuid4(),
        task_id=overrides.get("task_id", uuid.uuid4()),
        user_id=overrides.get("user_id", CPA_OWNER_ID),
        content=overrides.get("content", "Looks good"),
        created_at=NOW,
        updated_at=NOW,
    )


def _make_due_date(dd_id=None, **overrides):
    return SimpleNamespace(
        id=dd_id or uuid.uuid4(),
        client_id=overrides.get("client_id", uuid.uuid4()),
        title=overrides.get("title", "Q1 Filing"),
        due_date=overrides.get("due_date", date(2026, 4, 15)),
        form_type=overrides.get("form_type", "G-7"),
        filing_type=overrides.get("filing_type", None),
        tax_year=overrides.get("tax_year", 2026),
        is_completed=overrides.get("is_completed", False),
        completed_at=overrides.get("completed_at", None),
        completed_by=overrides.get("completed_by", None),
        notes=overrides.get("notes", ""),
        remind_days_before=overrides.get("remind_days_before", 7),
        deleted_at=overrides.get("deleted_at", None),
        created_at=NOW,
        updated_at=NOW,
    )


def _make_reminder(rem_id=None, **overrides):
    return SimpleNamespace(
        id=rem_id or uuid.uuid4(),
        user_id=overrides.get("user_id", CPA_OWNER_ID),
        client_id=overrides.get("client_id", None),
        workflow_id=overrides.get("workflow_id", None),
        task_id=overrides.get("task_id", None),
        reminder_type=overrides.get("reminder_type", "DUE_DATE"),
        channel=overrides.get("channel", "IN_APP"),
        title=overrides.get("title", "Deadline approaching"),
        message=overrides.get("message", "Q1 due in 7 days"),
        remind_at=overrides.get("remind_at", NOW),
        is_sent=overrides.get("is_sent", False),
        is_read=overrides.get("is_read", False),
        created_at=NOW,
        updated_at=NOW,
    )


# ---------------------------------------------------------------------------
# Tests: Workflow CRUD
# ---------------------------------------------------------------------------


class TestCreateWorkflow:

    @patch("app.routers.workflows.WorkflowService")
    async def test_create_workflow_success(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            wf = _make_workflow()
            mock_svc.create_workflow = AsyncMock(return_value=wf)

            response = await client.post(
                "/api/v1/workflows",
                json={
                    "name": "Tax Prep 2026",
                    "workflow_type": "tax_return",
                    "client_id": str(uuid.uuid4()),
                },
            )
            assert response.status_code == 201
            data = response.json()
            assert data["name"] == "Tax Prep 2026"
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    @patch("app.routers.workflows.WorkflowService")
    async def test_associate_can_create_workflow(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_associate()
        try:
            wf = _make_workflow()
            mock_svc.create_workflow = AsyncMock(return_value=wf)

            response = await client.post(
                "/api/v1/workflows",
                json={
                    "name": "Tax Prep 2026",
                    "workflow_type": "tax_return",
                    "client_id": str(uuid.uuid4()),
                },
            )
            assert response.status_code == 201
        finally:
            app.dependency_overrides.pop(get_current_user, None)


class TestListWorkflows:

    @patch("app.routers.workflows.WorkflowService")
    async def test_list_workflows(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            wf1 = _make_workflow(name="WF1")
            wf2 = _make_workflow(name="WF2")
            mock_svc.list_workflows = AsyncMock(return_value=([wf1, wf2], 2))

            response = await client.get("/api/v1/workflows")
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 2
            assert len(data["items"]) == 2
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    @patch("app.routers.workflows.WorkflowService")
    async def test_list_workflows_with_filters(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            mock_svc.list_workflows = AsyncMock(return_value=([], 0))

            cid = str(uuid.uuid4())
            response = await client.get(
                f"/api/v1/workflows?client_id={cid}&status=ACTIVE&workflow_type=tax_return"
            )
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 0
        finally:
            app.dependency_overrides.pop(get_current_user, None)


class TestGetWorkflow:

    @patch("app.routers.workflows.WorkflowService")
    async def test_get_workflow(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            wf_id = uuid.uuid4()
            wf = _make_workflow(wf_id=wf_id)
            mock_svc.get_workflow = AsyncMock(return_value=wf)

            response = await client.get(f"/api/v1/workflows/{wf_id}")
            assert response.status_code == 200
            assert response.json()["id"] == str(wf_id)
        finally:
            app.dependency_overrides.pop(get_current_user, None)


class TestUpdateWorkflow:

    @patch("app.routers.workflows.WorkflowService")
    async def test_update_workflow(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            wf_id = uuid.uuid4()
            wf = _make_workflow(wf_id=wf_id, name="Updated WF")
            mock_svc.update_workflow = AsyncMock(return_value=wf)

            response = await client.put(
                f"/api/v1/workflows/{wf_id}",
                json={"name": "Updated WF"},
            )
            assert response.status_code == 200
            assert response.json()["name"] == "Updated WF"
        finally:
            app.dependency_overrides.pop(get_current_user, None)


class TestDeleteWorkflow:

    @patch("app.routers.workflows.WorkflowService")
    async def test_cpa_owner_can_delete(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            mock_svc.delete_workflow = AsyncMock(return_value=None)

            wf_id = uuid.uuid4()
            response = await client.delete(f"/api/v1/workflows/{wf_id}")
            assert response.status_code == 204
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    async def test_associate_cannot_delete(self, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_associate()
        try:
            wf_id = uuid.uuid4()
            response = await client.delete(f"/api/v1/workflows/{wf_id}")
            assert response.status_code == 403
        finally:
            app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------------------------
# Tests: Kanban & Stages
# ---------------------------------------------------------------------------


class TestKanban:

    @patch("app.routers.workflows.WorkflowService")
    async def test_get_kanban_board(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            mock_svc.get_kanban = AsyncMock(return_value=[
                {"stage_name": "Intake", "stage_order": 0, "color": None, "workflows": [], "count": 0},
                {"stage_name": "Preparation", "stage_order": 1, "color": None, "workflows": [], "count": 0},
            ])

            response = await client.get("/api/v1/kanban/tax_return")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["stage_name"] == "Intake"
        finally:
            app.dependency_overrides.pop(get_current_user, None)


class TestStages:

    @patch("app.routers.workflows.WorkflowService")
    async def test_get_stages(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            stage1 = SimpleNamespace(
                id=uuid.uuid4(),
                workflow_type="tax_return",
                stage_name="Intake",
                stage_order=0,
                color=None,
                is_completion_stage=False,
            )
            mock_svc.get_stages = AsyncMock(return_value=[stage1])

            response = await client.get("/api/v1/stages/tax_return")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["stage_name"] == "Intake"
        finally:
            app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------------------------
# Tests: Tasks
# ---------------------------------------------------------------------------


class TestTasks:

    @patch("app.routers.workflows.WorkflowService")
    async def test_add_task(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            task = _make_task()
            mock_svc.add_task = AsyncMock(return_value=task)

            wf_id = uuid.uuid4()
            response = await client.post(
                f"/api/v1/workflows/{wf_id}/tasks",
                json={"title": "Gather W-2s"},
            )
            assert response.status_code == 201
            assert response.json()["title"] == "Gather W-2s"
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    @patch("app.routers.workflows.WorkflowService")
    async def test_update_task(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            task = _make_task(status="COMPLETED")
            mock_svc.update_task = AsyncMock(return_value=task)

            task_id = uuid.uuid4()
            response = await client.put(
                f"/api/v1/tasks/{task_id}",
                json={"status": "COMPLETED"},
            )
            assert response.status_code == 200
            assert response.json()["status"] == "COMPLETED"
        finally:
            app.dependency_overrides.pop(get_current_user, None)


class TestTaskComments:

    @patch("app.routers.workflows.WorkflowService")
    async def test_add_comment(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            comment = _make_comment()
            mock_svc.add_comment = AsyncMock(return_value=comment)

            task_id = uuid.uuid4()
            response = await client.post(
                f"/api/v1/tasks/{task_id}/comments",
                json={"content": "Looks good"},
            )
            assert response.status_code == 201
            assert response.json()["content"] == "Looks good"
        finally:
            app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------------------------
# Tests: Due Dates
# ---------------------------------------------------------------------------


class TestDueDates:

    @patch("app.routers.workflows.WorkflowService")
    async def test_create_due_date(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            dd = _make_due_date()
            mock_svc.create_due_date = AsyncMock(return_value=dd)

            response = await client.post(
                "/api/v1/due-dates",
                json={
                    "client_id": str(uuid.uuid4()),
                    "title": "Q1 Filing",
                    "due_date": "2026-04-15",
                },
            )
            assert response.status_code == 201
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    @patch("app.routers.workflows.WorkflowService")
    async def test_list_due_dates(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            dd1 = _make_due_date()
            mock_svc.list_due_dates = AsyncMock(return_value=([dd1], 1))

            response = await client.get("/api/v1/due-dates")
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    @patch("app.routers.workflows.WorkflowService")
    async def test_complete_due_date(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            dd = _make_due_date(is_completed=True, completed_at=NOW)
            mock_svc.complete_due_date = AsyncMock(return_value=dd)

            dd_id = uuid.uuid4()
            response = await client.post(f"/api/v1/due-dates/{dd_id}/complete")
            assert response.status_code == 200
            assert response.json()["is_completed"] is True
        finally:
            app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------------------------
# Tests: Reminders
# ---------------------------------------------------------------------------


class TestReminders:

    @patch("app.routers.workflows.WorkflowService")
    async def test_get_reminders(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            rem = _make_reminder()
            mock_svc.get_reminders = AsyncMock(return_value=[rem])

            response = await client.get("/api/v1/reminders")
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    @patch("app.routers.workflows.WorkflowService")
    async def test_mark_reminder_read(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            rem = _make_reminder(is_read=True)
            mock_svc.mark_reminder_read = AsyncMock(return_value=rem)

            rem_id = uuid.uuid4()
            response = await client.post(f"/api/v1/reminders/{rem_id}/read")
            assert response.status_code == 200
            assert response.json()["is_read"] is True
        finally:
            app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------------------------
# Tests: Process Recurring (CPA_OWNER only)
# ---------------------------------------------------------------------------


class TestProcessRecurring:

    @patch("app.routers.workflows.WorkflowService")
    async def test_cpa_owner_can_process_recurring(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            wf = _make_workflow()
            mock_svc.process_recurring_workflows = AsyncMock(return_value=[wf])

            response = await client.post("/api/v1/workflows/process-recurring")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    async def test_associate_cannot_process_recurring(self, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_associate()
        try:
            response = await client.post("/api/v1/workflows/process-recurring")
            assert response.status_code == 403
        finally:
            app.dependency_overrides.pop(get_current_user, None)
