"""
Tests for Time Tracking API endpoints (PM1).

Tests cover:
- CRUD time entries (create, list, get, update, delete)
- Submit and approve time entries (role enforcement)
- Timer start/stop/active/convert
- Staff rates (CPA_OWNER only)
- Utilization report

Uses mock DB and patched service layer.
"""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.auth.dependencies import CurrentUser, get_current_user
from app.main import app


# ---------------------------------------------------------------------------
# Helpers — mock objects that look like ORM models
# ---------------------------------------------------------------------------

def _make_time_entry(**overrides):
    entry_id = overrides.get("id", uuid.uuid4())
    client_id = overrides.get("client_id", uuid.uuid4())
    user_id = overrides.get("user_id", uuid.uuid4())
    return MagicMock(
        id=entry_id,
        client_id=client_id,
        user_id=user_id,
        date=overrides.get("entry_date", date(2026, 3, 1)),
        entry_date=overrides.get("entry_date", date(2026, 3, 1)),
        duration_minutes=overrides.get("duration_minutes", 60),
        description=overrides.get("description", "Test time entry"),
        is_billable=overrides.get("is_billable", True),
        hourly_rate=overrides.get("hourly_rate", Decimal("150.00")),
        amount=overrides.get("amount", Decimal("150.00")),
        status=overrides.get("status", "DRAFT"),
        service_type=overrides.get("service_type", "Tax Prep"),
        workflow_task_id=overrides.get("workflow_task_id", None),
        deleted_at=None,
        created_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
    )


def _make_timer(**overrides):
    return MagicMock(
        id=overrides.get("id", uuid.uuid4()),
        user_id=overrides.get("user_id", uuid.uuid4()),
        client_id=overrides.get("client_id", uuid.uuid4()),
        description=overrides.get("description", "Working on taxes"),
        service_type=overrides.get("service_type", None),
        started_at=overrides.get("started_at", datetime(2026, 3, 1, 9, 0, tzinfo=timezone.utc)),
        stopped_at=overrides.get("stopped_at", None),
        is_running=overrides.get("is_running", True),
        created_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
    )


def _make_staff_rate(**overrides):
    return MagicMock(
        id=overrides.get("id", uuid.uuid4()),
        user_id=overrides.get("user_id", uuid.uuid4()),
        rate_name=overrides.get("rate_name", "Standard"),
        hourly_rate=overrides.get("hourly_rate", Decimal("175.00")),
        effective_date=overrides.get("effective_date", date(2026, 1, 1)),
        end_date=overrides.get("end_date", None),
        created_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
    )


# ---------------------------------------------------------------------------
# Time Entry CRUD
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_create_time_entry(client: AsyncClient, cpa_owner_headers):
    """POST /api/v1/time-entries creates a time entry."""
    mock_entry = _make_time_entry()
    with patch(
        "app.routers.time_tracking.TimeTrackingService.create_time_entry",
        new_callable=AsyncMock,
    ) as mock_create:
        mock_create.return_value = mock_entry
        response = await client.post(
            "/api/v1/time-entries",
            headers=cpa_owner_headers,
            json={
                "client_id": str(uuid.uuid4()),
                "entry_date": "2026-03-01",
                "duration_minutes": 60,
                "description": "Test time entry",
                "is_billable": True,
                "hourly_rate": "150.00",
            },
        )
    assert response.status_code == 201
    data = response.json()
    assert data["duration_minutes"] == 60
    assert data["status"] == "DRAFT"


@pytest.mark.anyio
async def test_list_time_entries(client: AsyncClient, cpa_owner_headers):
    """GET /api/v1/time-entries lists entries with total."""
    entries = [_make_time_entry() for _ in range(3)]
    with patch(
        "app.routers.time_tracking.TimeTrackingService.list_time_entries",
        new_callable=AsyncMock,
    ) as mock_list:
        mock_list.return_value = (entries, 3)
        response = await client.get("/api/v1/time-entries", headers=cpa_owner_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3


@pytest.mark.anyio
async def test_get_time_entry(client: AsyncClient, cpa_owner_headers):
    """GET /api/v1/time-entries/{id} returns a single entry."""
    entry_id = uuid.uuid4()
    mock_entry = _make_time_entry(id=entry_id)
    with patch(
        "app.routers.time_tracking.TimeTrackingService.get_time_entry",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.return_value = mock_entry
        response = await client.get(
            f"/api/v1/time-entries/{entry_id}", headers=cpa_owner_headers
        )
    assert response.status_code == 200
    assert response.json()["id"] == str(entry_id)


@pytest.mark.anyio
async def test_update_time_entry(client: AsyncClient, cpa_owner_headers):
    """PUT /api/v1/time-entries/{id} updates an entry."""
    entry_id = uuid.uuid4()
    mock_entry = _make_time_entry(id=entry_id, duration_minutes=120)
    with patch(
        "app.routers.time_tracking.TimeTrackingService.update_time_entry",
        new_callable=AsyncMock,
    ) as mock_update:
        mock_update.return_value = mock_entry
        response = await client.put(
            f"/api/v1/time-entries/{entry_id}",
            headers=cpa_owner_headers,
            json={"duration_minutes": 120},
        )
    assert response.status_code == 200
    assert response.json()["duration_minutes"] == 120


@pytest.mark.anyio
async def test_delete_time_entry(client: AsyncClient, cpa_owner_headers):
    """DELETE /api/v1/time-entries/{id} soft-deletes an entry."""
    entry_id = uuid.uuid4()
    with patch(
        "app.routers.time_tracking.TimeTrackingService.delete_time_entry",
        new_callable=AsyncMock,
    ) as mock_delete:
        mock_delete.return_value = None
        response = await client.delete(
            f"/api/v1/time-entries/{entry_id}", headers=cpa_owner_headers
        )
    assert response.status_code == 204


# ---------------------------------------------------------------------------
# Submit / Approve
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_submit_time_entries(client: AsyncClient, cpa_owner_headers):
    """POST /api/v1/time-entries/submit submits entries for approval."""
    entries = [_make_time_entry(status="SUBMITTED") for _ in range(2)]
    entry_ids = [str(e.id) for e in entries]
    with patch(
        "app.routers.time_tracking.TimeTrackingService.submit_time_entries",
        new_callable=AsyncMock,
    ) as mock_submit:
        mock_submit.return_value = entries
        response = await client.post(
            "/api/v1/time-entries/submit",
            headers=cpa_owner_headers,
            json=entry_ids,
        )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all(item["status"] == "SUBMITTED" for item in data)


@pytest.mark.anyio
async def test_approve_time_entries_cpa_owner(client: AsyncClient, cpa_owner_headers):
    """POST /api/v1/time-entries/approve succeeds for CPA_OWNER."""
    entries = [_make_time_entry(status="APPROVED") for _ in range(2)]
    entry_ids = [str(e.id) for e in entries]
    with patch(
        "app.routers.time_tracking.TimeTrackingService.approve_time_entries",
        new_callable=AsyncMock,
    ) as mock_approve:
        mock_approve.return_value = entries
        response = await client.post(
            "/api/v1/time-entries/approve",
            headers=cpa_owner_headers,
            json=entry_ids,
        )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all(item["status"] == "APPROVED" for item in data)


@pytest.mark.anyio
async def test_approve_time_entries_associate_forbidden(client: AsyncClient, associate_headers):
    """POST /api/v1/time-entries/approve returns 403 for ASSOCIATE."""
    response = await client.post(
        "/api/v1/time-entries/approve",
        headers=associate_headers,
        json=[str(uuid.uuid4())],
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Timers
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_start_timer(client: AsyncClient, cpa_owner_headers):
    """POST /api/v1/timers starts a new timer."""
    mock_timer = _make_timer()
    with patch(
        "app.routers.time_tracking.TimeTrackingService.start_timer",
        new_callable=AsyncMock,
    ) as mock_start:
        mock_start.return_value = mock_timer
        response = await client.post(
            "/api/v1/timers",
            headers=cpa_owner_headers,
            json={"client_id": str(uuid.uuid4()), "description": "Working on taxes"},
        )
    assert response.status_code == 201
    assert response.json()["is_running"] is True


@pytest.mark.anyio
async def test_stop_timer(client: AsyncClient, cpa_owner_headers):
    """POST /api/v1/timers/{id}/stop stops a running timer."""
    timer_id = uuid.uuid4()
    mock_timer = _make_timer(
        id=timer_id,
        is_running=False,
        stopped_at=datetime(2026, 3, 1, 10, 30, tzinfo=timezone.utc),
    )
    with patch(
        "app.routers.time_tracking.TimeTrackingService.stop_timer",
        new_callable=AsyncMock,
    ) as mock_stop:
        mock_stop.return_value = mock_timer
        response = await client.post(
            f"/api/v1/timers/{timer_id}/stop", headers=cpa_owner_headers
        )
    assert response.status_code == 200
    assert response.json()["is_running"] is False


@pytest.mark.anyio
async def test_get_active_timer(client: AsyncClient, cpa_owner_headers):
    """GET /api/v1/timers/active returns the active timer or null."""
    mock_timer = _make_timer()
    with patch(
        "app.routers.time_tracking.TimeTrackingService.get_active_timer",
        new_callable=AsyncMock,
    ) as mock_active:
        mock_active.return_value = mock_timer
        response = await client.get("/api/v1/timers/active", headers=cpa_owner_headers)
    assert response.status_code == 200
    assert response.json()["is_running"] is True


@pytest.mark.anyio
async def test_get_active_timer_none(client: AsyncClient, cpa_owner_headers):
    """GET /api/v1/timers/active returns null when no timer is running."""
    with patch(
        "app.routers.time_tracking.TimeTrackingService.get_active_timer",
        new_callable=AsyncMock,
    ) as mock_active:
        mock_active.return_value = None
        response = await client.get("/api/v1/timers/active", headers=cpa_owner_headers)
    assert response.status_code == 200
    assert response.json() is None


@pytest.mark.anyio
async def test_convert_timer_to_entry(client: AsyncClient, cpa_owner_headers):
    """POST /api/v1/timers/{id}/convert converts a timer to a time entry."""
    timer_id = uuid.uuid4()
    mock_entry = _make_time_entry()
    with patch(
        "app.routers.time_tracking.TimeTrackingService.convert_timer_to_entry",
        new_callable=AsyncMock,
    ) as mock_convert:
        mock_convert.return_value = mock_entry
        response = await client.post(
            f"/api/v1/timers/{timer_id}/convert", headers=cpa_owner_headers
        )
    assert response.status_code == 200
    assert "duration_minutes" in response.json()


# ---------------------------------------------------------------------------
# Staff Rates
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_set_staff_rate_cpa_owner(client: AsyncClient, cpa_owner_headers):
    """POST /api/v1/staff-rates sets a rate (CPA_OWNER only)."""
    mock_rate = _make_staff_rate()
    with patch(
        "app.routers.time_tracking.TimeTrackingService.set_staff_rate",
        new_callable=AsyncMock,
    ) as mock_set:
        mock_set.return_value = mock_rate
        response = await client.post(
            "/api/v1/staff-rates",
            headers=cpa_owner_headers,
            json={
                "user_id": str(uuid.uuid4()),
                "hourly_rate": "175.00",
                "effective_date": "2026-01-01",
            },
        )
    assert response.status_code == 201
    assert response.json()["rate_name"] == "Standard"


@pytest.mark.anyio
async def test_set_staff_rate_associate_forbidden(client: AsyncClient, associate_headers):
    """POST /api/v1/staff-rates returns 403 for ASSOCIATE."""
    response = await client.post(
        "/api/v1/staff-rates",
        headers=associate_headers,
        json={
            "user_id": str(uuid.uuid4()),
            "hourly_rate": "175.00",
            "effective_date": "2026-01-01",
        },
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Utilization Report
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_utilization_report(client: AsyncClient, cpa_owner_headers):
    """GET /api/v1/reports/utilization returns utilization data."""
    mock_report = [
        {
            "user_id": str(uuid.uuid4()),
            "user_name": "Edward Ahrens",
            "total_hours": Decimal("160"),
            "billable_hours": Decimal("128"),
            "non_billable_hours": Decimal("32"),
            "utilization_pct": Decimal("80.00"),
            "total_amount": Decimal("19200.00"),
            "period_start": date(2026, 2, 1),
            "period_end": date(2026, 2, 28),
        }
    ]
    with patch(
        "app.routers.time_tracking.TimeTrackingService.utilization_report",
        new_callable=AsyncMock,
    ) as mock_util:
        mock_util.return_value = mock_report
        response = await client.get(
            "/api/v1/reports/utilization",
            headers=cpa_owner_headers,
            params={"date_from": "2026-02-01", "date_to": "2026-02-28"},
        )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["user_name"] == "Edward Ahrens"
