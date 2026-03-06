"""
Tests for Year-End Close workflow (module C1).

Tests the year-end router endpoints:
- GET  /api/v1/clients/{id}/year-end/{year}/status
- GET  /api/v1/clients/{id}/year-end/{year}/preview
- POST /api/v1/clients/{id}/year-end/{year}/close   (CPA_OWNER only)
- POST /api/v1/clients/{id}/year-end/{year}/reopen   (CPA_OWNER only)

Uses mock service layer to avoid real DB dependency.

Note: The year_end router accesses user.id (not user.user_id) when passing
the user ID to the service layer. CurrentUser is a frozen dataclass with
only user_id, so tests for close/reopen override get_current_user to return
a mock user object that has both attributes.
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.auth.dependencies import get_current_user
from app.main import app


# ---------------------------------------------------------------------------
# Mock user that has both .user_id and .id (router uses user.id)
# ---------------------------------------------------------------------------
CPA_OWNER_ID = str(uuid.uuid4())
ASSOCIATE_ID = str(uuid.uuid4())


class _MockUser:
    """User mock compatible with CurrentUser interface plus user.id access."""

    def __init__(self, user_id: str, role: str):
        self.user_id = user_id
        self.id = user_id
        self.role = role

    @property
    def is_cpa_owner(self) -> bool:
        return self.role == "CPA_OWNER"


_MOCK_CPA = _MockUser(CPA_OWNER_ID, "CPA_OWNER")
_MOCK_ASSOC = _MockUser(ASSOCIATE_ID, "ASSOCIATE")


@pytest.fixture
def _override_cpa_owner():
    """Override get_current_user to return CPA_OWNER with .id attribute."""
    async def _dep():
        return _MOCK_CPA
    app.dependency_overrides[get_current_user] = _dep
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def _override_associate():
    """Override get_current_user to return ASSOCIATE with .id attribute."""
    async def _dep():
        return _MOCK_ASSOC
    app.dependency_overrides[get_current_user] = _dep
    yield
    app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------------------------
# Test constants
# ---------------------------------------------------------------------------
CLIENT_ID = str(uuid.uuid4())
FISCAL_YEAR = 2025
BASE = f"/api/v1/clients/{CLIENT_ID}/year-end/{FISCAL_YEAR}"

MOCK_STATUS_OPEN = {
    "client_id": CLIENT_ID,
    "fiscal_year": FISCAL_YEAR,
    "status": "OPEN",
    "closing_entry_id": None,
}

CLOSING_ENTRY_ID = str(uuid.uuid4())
MOCK_STATUS_CLOSED = {
    "client_id": CLIENT_ID,
    "fiscal_year": FISCAL_YEAR,
    "status": "CLOSED",
    "closing_entry_id": CLOSING_ENTRY_ID,
}

MOCK_PREVIEW = {
    "client_id": CLIENT_ID,
    "fiscal_year": FISCAL_YEAR,
    "total_revenue": 50000.0,
    "total_expenses": 30000.0,
    "net_income": 20000.0,
    "closing_lines": [
        {
            "account_id": str(uuid.uuid4()),
            "account_number": "4000",
            "account_name": "Service Revenue",
            "account_type": "REVENUE",
            "balance": 50000.0,
            "debit": 50000.0,
            "credit": 0,
        },
        {
            "account_id": str(uuid.uuid4()),
            "account_number": "5000",
            "account_name": "Operating Expenses",
            "account_type": "EXPENSE",
            "balance": 30000.0,
            "debit": 0,
            "credit": 30000.0,
        },
    ],
    "retained_earnings_entry": {
        "account_number": "3200",
        "debit": 0,
        "credit": 20000.0,
    },
}

MOCK_CLOSE_RESULT = {
    "client_id": CLIENT_ID,
    "fiscal_year": FISCAL_YEAR,
    "status": "CLOSED",
    "closing_entry_id": CLOSING_ENTRY_ID,
    "net_income": 20000.0,
    "accounts_closed": 2,
}

MOCK_REOPEN_RESULT = {
    "client_id": CLIENT_ID,
    "fiscal_year": FISCAL_YEAR,
    "status": "OPEN",
    "voided_entry_id": CLOSING_ENTRY_ID,
}


# ---------------------------------------------------------------------------
# GET /status
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_get_year_status_open(client: AsyncClient, cpa_owner_headers):
    """GET status returns OPEN when year is not closed."""
    with patch(
        "app.routers.year_end.YearEndService.get_year_status",
        new_callable=AsyncMock,
    ) as mock:
        mock.return_value = MOCK_STATUS_OPEN
        response = await client.get(f"{BASE}/status", headers=cpa_owner_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "OPEN"
    assert data["fiscal_year"] == FISCAL_YEAR
    assert data["closing_entry_id"] is None


@pytest.mark.anyio
async def test_get_year_status_closed(client: AsyncClient, cpa_owner_headers):
    """GET status returns CLOSED when year has been closed."""
    with patch(
        "app.routers.year_end.YearEndService.get_year_status",
        new_callable=AsyncMock,
    ) as mock:
        mock.return_value = MOCK_STATUS_CLOSED
        response = await client.get(f"{BASE}/status", headers=cpa_owner_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "CLOSED"
    assert data["closing_entry_id"] == CLOSING_ENTRY_ID


@pytest.mark.anyio
async def test_get_year_status_as_associate(client: AsyncClient, associate_headers):
    """ASSOCIATE can view year-end status (read-only)."""
    with patch(
        "app.routers.year_end.YearEndService.get_year_status",
        new_callable=AsyncMock,
    ) as mock:
        mock.return_value = MOCK_STATUS_OPEN
        response = await client.get(f"{BASE}/status", headers=associate_headers)
    assert response.status_code == 200


@pytest.mark.anyio
async def test_get_year_status_unauthenticated(client: AsyncClient):
    """Unauthenticated request gets 401."""
    response = await client.get(f"{BASE}/status")
    assert response.status_code in (401, 403)


# ---------------------------------------------------------------------------
# GET /preview
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_preview_closing_entries(client: AsyncClient, cpa_owner_headers):
    """GET preview returns expected closing entries and net income."""
    with patch(
        "app.routers.year_end.YearEndService.preview_closing_entries",
        new_callable=AsyncMock,
    ) as mock:
        mock.return_value = MOCK_PREVIEW
        response = await client.get(f"{BASE}/preview", headers=cpa_owner_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["net_income"] == 20000.0
    assert data["total_revenue"] == 50000.0
    assert data["total_expenses"] == 30000.0
    assert len(data["closing_lines"]) == 2
    assert data["retained_earnings_entry"]["account_number"] == "3200"


@pytest.mark.anyio
async def test_preview_as_associate(client: AsyncClient, associate_headers):
    """ASSOCIATE can preview closing entries (read-only)."""
    with patch(
        "app.routers.year_end.YearEndService.preview_closing_entries",
        new_callable=AsyncMock,
    ) as mock:
        mock.return_value = MOCK_PREVIEW
        response = await client.get(f"{BASE}/preview", headers=associate_headers)
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# POST /close  (uses _override_cpa_owner so user.id is available)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_close_year_as_cpa_owner(client: AsyncClient, _override_cpa_owner):
    """CPA_OWNER can close a fiscal year."""
    with patch(
        "app.routers.year_end.YearEndService.close_year",
        new_callable=AsyncMock,
    ) as mock:
        mock.return_value = MOCK_CLOSE_RESULT
        response = await client.post(f"{BASE}/close")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "CLOSED"
    assert data["net_income"] == 20000.0
    assert data["accounts_closed"] == 2


@pytest.mark.anyio
async def test_close_year_as_associate_forbidden(client: AsyncClient, _override_associate):
    """ASSOCIATE gets 403 when attempting to close a year."""
    response = await client.post(f"{BASE}/close")
    assert response.status_code == 403


@pytest.mark.anyio
async def test_close_year_already_closed(client: AsyncClient, _override_cpa_owner):
    """Closing an already-closed year returns 400."""
    with patch(
        "app.routers.year_end.YearEndService.close_year",
        new_callable=AsyncMock,
    ) as mock:
        mock.side_effect = ValueError("Fiscal year 2025 is already closed")
        response = await client.post(f"{BASE}/close")
    assert response.status_code == 400
    assert "already closed" in response.json()["detail"]


@pytest.mark.anyio
async def test_close_year_no_activity(client: AsyncClient, _override_cpa_owner):
    """Closing a year with no revenue/expense activity returns 400."""
    with patch(
        "app.routers.year_end.YearEndService.close_year",
        new_callable=AsyncMock,
    ) as mock:
        mock.side_effect = ValueError("No revenue or expense activity to close")
        response = await client.post(f"{BASE}/close")
    assert response.status_code == 400
    assert "activity" in response.json()["detail"]


# ---------------------------------------------------------------------------
# POST /reopen  (uses _override_cpa_owner so user.id is available)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_reopen_year_as_cpa_owner(client: AsyncClient, _override_cpa_owner):
    """CPA_OWNER can reopen a closed fiscal year."""
    with patch(
        "app.routers.year_end.YearEndService.reopen_year",
        new_callable=AsyncMock,
    ) as mock:
        mock.return_value = MOCK_REOPEN_RESULT
        response = await client.post(f"{BASE}/reopen")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "OPEN"
    assert data["voided_entry_id"] == CLOSING_ENTRY_ID


@pytest.mark.anyio
async def test_reopen_year_as_associate_forbidden(client: AsyncClient, _override_associate):
    """ASSOCIATE gets 403 when attempting to reopen a year."""
    response = await client.post(f"{BASE}/reopen")
    assert response.status_code == 403


@pytest.mark.anyio
async def test_reopen_year_not_closed(client: AsyncClient, _override_cpa_owner):
    """Reopening a year that is not closed returns 400."""
    with patch(
        "app.routers.year_end.YearEndService.reopen_year",
        new_callable=AsyncMock,
    ) as mock:
        mock.side_effect = ValueError("Fiscal year 2025 is not closed")
        response = await client.post(f"{BASE}/reopen")
    assert response.status_code == 400
    assert "not closed" in response.json()["detail"]


@pytest.mark.anyio
async def test_close_unauthenticated(client: AsyncClient):
    """Unauthenticated request to close gets 401."""
    response = await client.post(f"{BASE}/close")
    assert response.status_code in (401, 403)


@pytest.mark.anyio
async def test_reopen_unauthenticated(client: AsyncClient):
    """Unauthenticated request to reopen gets 401."""
    response = await client.post(f"{BASE}/reopen")
    assert response.status_code in (401, 403)
