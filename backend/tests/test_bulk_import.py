"""
Tests for Bulk Import endpoints (E3).

Covers:
- POST /api/v1/clients/{id}/import/bills — import bills from CSV
- POST /api/v1/clients/{id}/import/invoices — import invoices from CSV
- GET  /api/v1/import/template/{type} — download CSV template
- Permission checks (requires authentication)
- Error cases (unknown template type)
"""

import io
import uuid
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


SAMPLE_BILLS_CSV = (
    "vendor_name,amount,due_date,description\n"
    "Office Depot,125.50,2026-04-01,Office supplies\n"
    "Georgia Power,200.00,2026-04-15,Electric bill\n"
)

SAMPLE_INVOICES_CSV = (
    "client_name,amount,due_date,description\n"
    "Acme Corp,5000.00,2026-05-01,Tax prep services\n"
)


# ---------------------------------------------------------------------------
# Tests: Import Bills
# ---------------------------------------------------------------------------


class TestImportBills:

    @patch("app.routers.bulk_import.BulkImportService")
    async def test_import_bills_success(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            mock_svc.import_bills_csv = AsyncMock(return_value={
                "imported": 2,
                "skipped": 0,
                "errors": [],
            })

            cid = uuid.uuid4()
            response = await client.post(
                f"/api/v1/clients/{cid}/import/bills",
                files={"file": ("bills.csv", SAMPLE_BILLS_CSV.encode(), "text/csv")},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["imported"] == 2
            assert data["skipped"] == 0
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    @patch("app.routers.bulk_import.BulkImportService")
    async def test_import_bills_with_errors(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            mock_svc.import_bills_csv = AsyncMock(return_value={
                "imported": 1,
                "skipped": 1,
                "errors": ["Row 3: invalid amount"],
            })

            cid = uuid.uuid4()
            response = await client.post(
                f"/api/v1/clients/{cid}/import/bills",
                files={"file": ("bills.csv", SAMPLE_BILLS_CSV.encode(), "text/csv")},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["imported"] == 1
            assert len(data["errors"]) == 1
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    @patch("app.routers.bulk_import.BulkImportService")
    async def test_associate_can_import_bills(self, mock_svc, client: AsyncClient):
        """Associates can import bills (they enter draft data)."""
        app.dependency_overrides[get_current_user] = _override_as_associate()
        try:
            mock_svc.import_bills_csv = AsyncMock(return_value={
                "imported": 2, "skipped": 0, "errors": [],
            })

            cid = uuid.uuid4()
            response = await client.post(
                f"/api/v1/clients/{cid}/import/bills",
                files={"file": ("bills.csv", SAMPLE_BILLS_CSV.encode(), "text/csv")},
            )
            assert response.status_code == 200
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    async def test_import_bills_unauthenticated(self, client: AsyncClient):
        app.dependency_overrides.pop(get_current_user, None)
        cid = uuid.uuid4()
        response = await client.post(
            f"/api/v1/clients/{cid}/import/bills",
            files={"file": ("bills.csv", SAMPLE_BILLS_CSV.encode(), "text/csv")},
        )
        assert response.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Tests: Import Invoices
# ---------------------------------------------------------------------------


class TestImportInvoices:

    @patch("app.routers.bulk_import.BulkImportService")
    async def test_import_invoices_success(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            mock_svc.import_invoices_csv = AsyncMock(return_value={
                "imported": 1, "skipped": 0, "errors": [],
            })

            cid = uuid.uuid4()
            response = await client.post(
                f"/api/v1/clients/{cid}/import/invoices",
                files={"file": ("invoices.csv", SAMPLE_INVOICES_CSV.encode(), "text/csv")},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["imported"] == 1
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    @patch("app.routers.bulk_import.BulkImportService")
    async def test_import_invoices_with_errors(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            mock_svc.import_invoices_csv = AsyncMock(return_value={
                "imported": 0, "skipped": 1, "errors": ["Row 2: missing amount"],
            })

            cid = uuid.uuid4()
            response = await client.post(
                f"/api/v1/clients/{cid}/import/invoices",
                files={"file": ("invoices.csv", SAMPLE_INVOICES_CSV.encode(), "text/csv")},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["imported"] == 0
            assert len(data["errors"]) == 1
        finally:
            app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------------------------
# Tests: Download Template
# ---------------------------------------------------------------------------


class TestDownloadTemplate:

    @patch("app.routers.bulk_import.BulkImportService")
    async def test_download_bills_template(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            mock_svc.generate_template = MagicMock(
                return_value="vendor_name,amount,due_date,description\n"
            )

            response = await client.get("/api/v1/import/template/bills")
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/csv; charset=utf-8"
            assert "bills-template.csv" in response.headers.get("content-disposition", "")
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    @patch("app.routers.bulk_import.BulkImportService")
    async def test_download_invoices_template(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            mock_svc.generate_template = MagicMock(
                return_value="client_name,amount,due_date,description\n"
            )

            response = await client.get("/api/v1/import/template/invoices")
            assert response.status_code == 200
            assert "invoices-template.csv" in response.headers.get("content-disposition", "")
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    @patch("app.routers.bulk_import.BulkImportService")
    async def test_download_unknown_template_type(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            mock_svc.generate_template = MagicMock(return_value=None)

            response = await client.get("/api/v1/import/template/unknown_type")
            assert response.status_code == 400
            assert "Unknown entity type" in response.json()["detail"]
        finally:
            app.dependency_overrides.pop(get_current_user, None)
