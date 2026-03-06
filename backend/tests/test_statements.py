"""
Tests for Client Statements endpoints (C5).

Covers:
- GET  /api/v1/clients/{id}/statements          — generate statement data
- GET  /api/v1/clients/{id}/statements/pdf       — download PDF (CPA_OWNER only)
- POST /api/v1/clients/{id}/statements/send      — email statement (CPA_OWNER only)
- Permission checks

Note: send_email and render_statement_email are lazy-imported inside the
send endpoint, so we patch them at their source modules.
"""

import uuid
from datetime import date
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
CLIENT_ID = uuid.uuid4()

START_DATE = "2026-01-01"
END_DATE = "2026-03-31"


def _override_as_cpa_owner():
    async def _dep():
        return CurrentUser(user_id=str(CPA_OWNER_ID), role="CPA_OWNER")
    return _dep


def _override_as_associate():
    async def _dep():
        return CurrentUser(user_id=str(ASSOCIATE_ID), role="ASSOCIATE")
    return _dep


SAMPLE_STATEMENT = {
    "client_id": str(CLIENT_ID),
    "client_name": "Acme Corp",
    "period": "2026-01-01 to 2026-03-31",
    "total_outstanding": 5000.00,
    "invoices": [
        {"id": str(uuid.uuid4()), "amount": 3000.00, "due_date": "2026-02-15", "status": "SENT"},
        {"id": str(uuid.uuid4()), "amount": 2000.00, "due_date": "2026-03-15", "status": "OVERDUE"},
    ],
    "payments": [],
}


# ---------------------------------------------------------------------------
# Tests: Get Statement Data
# ---------------------------------------------------------------------------


class TestGetStatement:

    @patch("app.routers.statements.StatementService")
    async def test_get_statement_success(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            mock_svc.generate_statement = AsyncMock(return_value=SAMPLE_STATEMENT)

            response = await client.get(
                f"/api/v1/clients/{CLIENT_ID}/statements"
                f"?start_date={START_DATE}&end_date={END_DATE}"
            )
            assert response.status_code == 200
            data = response.json()
            assert data["client_name"] == "Acme Corp"
            assert data["total_outstanding"] == 5000.00
            assert len(data["invoices"]) == 2
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    @patch("app.routers.statements.StatementService")
    async def test_associate_can_view_statement(self, mock_svc, client: AsyncClient):
        """Associates can view statement data (read-only)."""
        app.dependency_overrides[get_current_user] = _override_as_associate()
        try:
            mock_svc.generate_statement = AsyncMock(return_value=SAMPLE_STATEMENT)

            response = await client.get(
                f"/api/v1/clients/{CLIENT_ID}/statements"
                f"?start_date={START_DATE}&end_date={END_DATE}"
            )
            assert response.status_code == 200
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    async def test_get_statement_missing_dates(self, client: AsyncClient):
        """start_date and end_date are required."""
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            response = await client.get(
                f"/api/v1/clients/{CLIENT_ID}/statements"
            )
            assert response.status_code == 422  # validation error
        finally:
            app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------------------------
# Tests: Get Statement PDF
# ---------------------------------------------------------------------------


class TestGetStatementPDF:

    @patch("app.routers.statements.StatementService")
    async def test_get_pdf_cpa_owner(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            mock_svc.generate_statement_pdf = AsyncMock(return_value=b"%PDF-1.4 fake pdf content")

            response = await client.get(
                f"/api/v1/clients/{CLIENT_ID}/statements/pdf"
                f"?start_date={START_DATE}&end_date={END_DATE}"
            )
            assert response.status_code == 200
            assert response.headers["content-type"] == "application/pdf"
            assert "statement-" in response.headers.get("content-disposition", "")
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    async def test_associate_cannot_get_pdf(self, client: AsyncClient):
        """PDF export requires CPA_OWNER role."""
        app.dependency_overrides[get_current_user] = _override_as_associate()
        try:
            response = await client.get(
                f"/api/v1/clients/{CLIENT_ID}/statements/pdf"
                f"?start_date={START_DATE}&end_date={END_DATE}"
            )
            assert response.status_code == 403
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    async def test_get_pdf_missing_dates(self, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            response = await client.get(
                f"/api/v1/clients/{CLIENT_ID}/statements/pdf"
            )
            assert response.status_code == 422
        finally:
            app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------------------------
# Tests: Send Statement Email
# ---------------------------------------------------------------------------


class TestSendStatementEmail:

    @patch("app.services.email.send_email", new_callable=AsyncMock)
    @patch("app.services.email.render_statement_email")
    @patch("app.routers.statements.StatementService")
    async def test_send_statement_success(
        self, mock_svc, mock_render, mock_send, client: AsyncClient
    ):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            mock_svc.generate_statement = AsyncMock(return_value=SAMPLE_STATEMENT)
            mock_svc.generate_statement_pdf = AsyncMock(return_value=b"%PDF-1.4 fake")
            mock_render.return_value = ("Account Statement", "<html>Statement</html>")
            mock_send.return_value = {"status": "sent", "to": "client@example.com"}

            response = await client.post(
                f"/api/v1/clients/{CLIENT_ID}/statements/send"
                f"?to_email=client@example.com&start_date={START_DATE}&end_date={END_DATE}"
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "sent"
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    async def test_associate_cannot_send_statement(self, client: AsyncClient):
        """Sending statements requires CPA_OWNER role."""
        app.dependency_overrides[get_current_user] = _override_as_associate()
        try:
            response = await client.post(
                f"/api/v1/clients/{CLIENT_ID}/statements/send"
                f"?to_email=client@example.com&start_date={START_DATE}&end_date={END_DATE}"
            )
            assert response.status_code == 403
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    async def test_send_statement_missing_email(self, client: AsyncClient):
        """to_email is required."""
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            response = await client.post(
                f"/api/v1/clients/{CLIENT_ID}/statements/send"
                f"?start_date={START_DATE}&end_date={END_DATE}"
            )
            assert response.status_code == 422
        finally:
            app.dependency_overrides.pop(get_current_user, None)
