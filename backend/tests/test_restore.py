"""
Tests for Soft Delete Restoration endpoints (E5).

Covers:
- GET  /api/v1/archived?type=...           — list archived records
- POST /api/v1/archived/{type}/{id}/restore — restore a record
- Permission checks (CPA_OWNER only)
- Error cases (invalid entity type, not found)
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.auth.dependencies import CurrentUser, get_current_user
from app.main import app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
CPA_OWNER_ID = uuid.uuid4()
ASSOCIATE_ID = uuid.uuid4()


def _override_as_cpa_owner():
    async def _dep():
        return CurrentUser(user_id=str(CPA_OWNER_ID), role="CPA_OWNER")
    return _dep


def _override_as_associate():
    async def _dep():
        return CurrentUser(user_id=str(ASSOCIATE_ID), role="ASSOCIATE")
    return _dep


# ---------------------------------------------------------------------------
# Tests: List Archived
# ---------------------------------------------------------------------------


class TestListArchived:

    @patch("app.routers.restore.RestoreService")
    async def test_list_archived_clients(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            mock_svc.list_archived = AsyncMock(return_value=[
                {"id": str(uuid.uuid4()), "name": "Old Client", "deleted_at": "2026-01-15"},
            ])

            response = await client.get("/api/v1/archived?type=client")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["name"] == "Old Client"
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    @patch("app.routers.restore.RestoreService")
    async def test_list_archived_with_client_id_filter(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            mock_svc.list_archived = AsyncMock(return_value=[])

            cid = uuid.uuid4()
            response = await client.get(f"/api/v1/archived?type=vendor&client_id={cid}")
            assert response.status_code == 200
            assert response.json() == []
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    @patch("app.routers.restore.RestoreService")
    async def test_list_archived_invalid_type(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            mock_svc.list_archived = AsyncMock(
                side_effect=ValueError("Unsupported entity type: widget")
            )

            response = await client.get("/api/v1/archived?type=widget")
            assert response.status_code == 400
            assert "Unsupported entity type" in response.json()["detail"]
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    async def test_associate_cannot_list_archived(self, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_associate()
        try:
            response = await client.get("/api/v1/archived?type=client")
            assert response.status_code == 403
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    @patch("app.routers.restore.RestoreService")
    async def test_list_archived_empty(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            mock_svc.list_archived = AsyncMock(return_value=[])

            response = await client.get("/api/v1/archived?type=employee")
            assert response.status_code == 200
            assert response.json() == []
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    async def test_list_archived_missing_type_param(self, client: AsyncClient):
        """type is a required query param."""
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            response = await client.get("/api/v1/archived")
            assert response.status_code == 422  # validation error
        finally:
            app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------------------------
# Tests: Restore Record
# ---------------------------------------------------------------------------


class TestRestoreRecord:

    @patch("app.routers.restore.RestoreService")
    async def test_restore_record_success(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            record_id = uuid.uuid4()
            mock_svc.restore = AsyncMock(return_value={
                "status": "restored",
                "entity_type": "client",
                "id": str(record_id),
            })

            response = await client.post(
                f"/api/v1/archived/client/{record_id}/restore"
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "restored"
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    @patch("app.routers.restore.RestoreService")
    async def test_restore_invalid_entity_type(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            mock_svc.restore = AsyncMock(
                side_effect=ValueError("Unsupported entity type: gadget")
            )

            record_id = uuid.uuid4()
            response = await client.post(
                f"/api/v1/archived/gadget/{record_id}/restore"
            )
            assert response.status_code == 400
            assert "Unsupported entity type" in response.json()["detail"]
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    async def test_associate_cannot_restore(self, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_associate()
        try:
            record_id = uuid.uuid4()
            response = await client.post(
                f"/api/v1/archived/client/{record_id}/restore"
            )
            assert response.status_code == 403
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    @patch("app.routers.restore.RestoreService")
    async def test_restore_vendor(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            record_id = uuid.uuid4()
            mock_svc.restore = AsyncMock(return_value={
                "status": "restored",
                "entity_type": "vendor",
                "id": str(record_id),
            })

            response = await client.post(
                f"/api/v1/archived/vendor/{record_id}/restore"
            )
            assert response.status_code == 200
            data = response.json()
            assert data["entity_type"] == "vendor"
        finally:
            app.dependency_overrides.pop(get_current_user, None)
