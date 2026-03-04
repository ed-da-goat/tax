"""
Tests for the Audit Trail Viewer (Module O1).

Covers:
- List audit log entries with pagination
- Filter by table_name, action, date range
- Get single entry by ID
- Get record history for a specific record (ordered by created_at)
- No POST/PUT/DELETE endpoints exist (405 Method Not Allowed)
- Both CPA_OWNER and ASSOCIATE can read
- Unauthenticated requests are rejected
"""

import uuid
from datetime import datetime, timezone, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
async def _insert_audit_entry(
    db: AsyncSession,
    *,
    table_name: str = "clients",
    record_id: uuid.UUID | None = None,
    action: str = "INSERT",
    old_values: dict | None = None,
    new_values: dict | None = None,
    user_id: uuid.UUID | None = None,
    created_at: datetime | None = None,
) -> uuid.UUID:
    """Insert a test audit log entry directly via SQL and return its ID."""
    entry_id = uuid.uuid4()
    record_id = record_id or uuid.uuid4()
    created_at = created_at or datetime.now(timezone.utc)

    import json

    old_json = None if old_values is None else json.dumps(old_values)
    new_json = None if new_values is None else json.dumps(new_values)

    await db.execute(
        text(
            """
            INSERT INTO audit_log (id, table_name, record_id, action,
                                   old_values, new_values, user_id, created_at)
            VALUES (:id, :table_name, :record_id,
                    CAST(:action AS audit_action),
                    CAST(:old_values AS jsonb),
                    CAST(:new_values AS jsonb),
                    :user_id, :created_at)
            """
        ),
        {
            "id": entry_id,
            "table_name": table_name,
            "record_id": record_id,
            "action": action,
            "old_values": old_json,
            "new_values": new_json,
            "user_id": user_id,
            "created_at": created_at,
        },
    )
    await db.flush()
    return entry_id


# ---------------------------------------------------------------------------
# Test: list returns entries
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_list_audit_log_returns_entries(
    db_session: AsyncSession,
    db_client: AsyncClient,
    cpa_owner_headers: dict,
):
    """GET /api/v1/audit-log returns audit log entries."""
    await _insert_audit_entry(db_session, table_name="clients", action="INSERT")
    await _insert_audit_entry(db_session, table_name="users", action="UPDATE")

    resp = await db_client.get("/api/v1/audit-log", headers=cpa_owner_headers)
    assert resp.status_code == 200

    data = resp.json()
    assert data["total"] >= 2
    assert len(data["items"]) >= 2


# ---------------------------------------------------------------------------
# Test: filter by table_name
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_filter_by_table_name(
    db_session: AsyncSession,
    db_client: AsyncClient,
    cpa_owner_headers: dict,
):
    """Filter audit log by table_name returns only matching entries."""
    unique_table = f"test_table_{uuid.uuid4().hex[:8]}"
    await _insert_audit_entry(db_session, table_name=unique_table, action="INSERT")
    await _insert_audit_entry(db_session, table_name="other_table", action="INSERT")

    resp = await db_client.get(
        "/api/v1/audit-log",
        params={"table_name": unique_table},
        headers=cpa_owner_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["table_name"] == unique_table


# ---------------------------------------------------------------------------
# Test: filter by action
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_filter_by_action(
    db_session: AsyncSession,
    db_client: AsyncClient,
    cpa_owner_headers: dict,
):
    """Filter audit log by action type."""
    unique_table = f"action_test_{uuid.uuid4().hex[:8]}"
    await _insert_audit_entry(db_session, table_name=unique_table, action="DELETE")
    await _insert_audit_entry(db_session, table_name=unique_table, action="INSERT")

    resp = await db_client.get(
        "/api/v1/audit-log",
        params={"table_name": unique_table, "action": "DELETE"},
        headers=cpa_owner_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["action"] == "DELETE"


# ---------------------------------------------------------------------------
# Test: filter by date range
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_filter_by_date_range(
    db_session: AsyncSession,
    db_client: AsyncClient,
    cpa_owner_headers: dict,
):
    """Filter audit log by date_from and date_to."""
    unique_table = f"date_test_{uuid.uuid4().hex[:8]}"
    old_date = datetime(2020, 1, 1, tzinfo=timezone.utc)
    recent_date = datetime(2025, 6, 15, tzinfo=timezone.utc)

    await _insert_audit_entry(
        db_session, table_name=unique_table, action="INSERT", created_at=old_date
    )
    await _insert_audit_entry(
        db_session, table_name=unique_table, action="UPDATE", created_at=recent_date
    )

    resp = await db_client.get(
        "/api/v1/audit-log",
        params={
            "table_name": unique_table,
            "date_from": "2025-01-01T00:00:00Z",
            "date_to": "2025-12-31T23:59:59Z",
        },
        headers=cpa_owner_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["action"] == "UPDATE"


# ---------------------------------------------------------------------------
# Test: get single entry by ID
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_get_single_entry(
    db_session: AsyncSession,
    db_client: AsyncClient,
    cpa_owner_headers: dict,
):
    """GET /api/v1/audit-log/{id} returns a single entry."""
    entry_id = await _insert_audit_entry(
        db_session, table_name="clients", action="INSERT"
    )

    resp = await db_client.get(
        f"/api/v1/audit-log/{entry_id}", headers=cpa_owner_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(entry_id)
    assert data["table_name"] == "clients"
    assert data["action"] == "INSERT"


# ---------------------------------------------------------------------------
# Test: get single entry — not found
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_get_single_entry_not_found(
    db_client: AsyncClient,
    cpa_owner_headers: dict,
):
    """GET /api/v1/audit-log/{id} returns 404 for non-existent entry."""
    fake_id = uuid.uuid4()
    resp = await db_client.get(
        f"/api/v1/audit-log/{fake_id}", headers=cpa_owner_headers
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Test: get record history
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_get_record_history(
    db_session: AsyncSession,
    db_client: AsyncClient,
    cpa_owner_headers: dict,
):
    """GET /api/v1/audit-log/record/{table}/{id} returns chronological history."""
    record_id = uuid.uuid4()
    t1 = datetime(2025, 1, 1, tzinfo=timezone.utc)
    t2 = datetime(2025, 6, 1, tzinfo=timezone.utc)
    t3 = datetime(2025, 12, 1, tzinfo=timezone.utc)

    await _insert_audit_entry(
        db_session,
        table_name="clients",
        record_id=record_id,
        action="INSERT",
        created_at=t1,
    )
    await _insert_audit_entry(
        db_session,
        table_name="clients",
        record_id=record_id,
        action="UPDATE",
        created_at=t3,
    )
    await _insert_audit_entry(
        db_session,
        table_name="clients",
        record_id=record_id,
        action="UPDATE",
        created_at=t2,
    )

    resp = await db_client.get(
        f"/api/v1/audit-log/record/clients/{record_id}",
        headers=cpa_owner_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3
    # Verify chronological order (oldest first)
    assert data[0]["action"] == "INSERT"
    assert data[1]["action"] == "UPDATE"
    assert data[2]["action"] == "UPDATE"
    # Verify ordering by created_at
    dates = [entry["created_at"] for entry in data]
    assert dates == sorted(dates)


# ---------------------------------------------------------------------------
# Test: no POST/PUT/DELETE endpoints (405)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_no_post_endpoint(client: AsyncClient, cpa_owner_headers: dict):
    """POST to audit-log should return 405 Method Not Allowed."""
    resp = await client.post(
        "/api/v1/audit-log", json={}, headers=cpa_owner_headers
    )
    assert resp.status_code == 405


@pytest.mark.asyncio
async def test_no_put_endpoint(client: AsyncClient, cpa_owner_headers: dict):
    """PUT to audit-log/{id} should return 405 Method Not Allowed."""
    fake_id = uuid.uuid4()
    resp = await client.put(
        f"/api/v1/audit-log/{fake_id}", json={}, headers=cpa_owner_headers
    )
    assert resp.status_code == 405


@pytest.mark.asyncio
async def test_no_delete_endpoint(client: AsyncClient, cpa_owner_headers: dict):
    """DELETE to audit-log/{id} should return 405 Method Not Allowed."""
    fake_id = uuid.uuid4()
    resp = await client.delete(
        f"/api/v1/audit-log/{fake_id}", headers=cpa_owner_headers
    )
    assert resp.status_code == 405


# ---------------------------------------------------------------------------
# Test: pagination
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_pagination(
    db_session: AsyncSession,
    db_client: AsyncClient,
    cpa_owner_headers: dict,
):
    """Pagination with skip and limit works correctly."""
    unique_table = f"pag_test_{uuid.uuid4().hex[:8]}"
    for i in range(5):
        await _insert_audit_entry(
            db_session,
            table_name=unique_table,
            action="INSERT",
            created_at=datetime(2025, 1, 1 + i, tzinfo=timezone.utc),
        )

    resp = await db_client.get(
        "/api/v1/audit-log",
        params={"table_name": unique_table, "skip": 0, "limit": 2},
        headers=cpa_owner_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    assert len(data["items"]) == 2
    assert data["skip"] == 0
    assert data["limit"] == 2

    # Page 2
    resp2 = await db_client.get(
        "/api/v1/audit-log",
        params={"table_name": unique_table, "skip": 2, "limit": 2},
        headers=cpa_owner_headers,
    )
    data2 = resp2.json()
    assert len(data2["items"]) == 2

    # Page 3 (last)
    resp3 = await db_client.get(
        "/api/v1/audit-log",
        params={"table_name": unique_table, "skip": 4, "limit": 2},
        headers=cpa_owner_headers,
    )
    data3 = resp3.json()
    assert len(data3["items"]) == 1


# ---------------------------------------------------------------------------
# Test: both roles can read
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_associate_can_read_audit_log(
    db_session: AsyncSession,
    db_client: AsyncClient,
    associate_headers: dict,
):
    """ASSOCIATE role can read audit log entries."""
    await _insert_audit_entry(db_session, table_name="clients", action="INSERT")

    resp = await db_client.get("/api/v1/audit-log", headers=associate_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_cpa_owner_can_read_audit_log(
    db_session: AsyncSession,
    db_client: AsyncClient,
    cpa_owner_headers: dict,
):
    """CPA_OWNER role can read audit log entries."""
    await _insert_audit_entry(db_session, table_name="clients", action="INSERT")

    resp = await db_client.get("/api/v1/audit-log", headers=cpa_owner_headers)
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Test: unauthenticated requests rejected
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_unauthenticated_list_rejected(client: AsyncClient):
    """Unauthenticated GET /api/v1/audit-log returns 403."""
    resp = await client.get("/api/v1/audit-log")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_unauthenticated_single_rejected(client: AsyncClient):
    """Unauthenticated GET /api/v1/audit-log/{id} is rejected."""
    resp = await client.get(f"/api/v1/audit-log/{uuid.uuid4()}")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_unauthenticated_record_history_rejected(client: AsyncClient):
    """Unauthenticated GET /api/v1/audit-log/record/... is rejected."""
    resp = await client.get(f"/api/v1/audit-log/record/clients/{uuid.uuid4()}")
    assert resp.status_code in (401, 403)
