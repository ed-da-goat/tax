"""
Tests for Recurring Transactions (module C3).

Tests the recurring router endpoints:
- GET    /api/v1/clients/{id}/recurring          -- list templates
- POST   /api/v1/clients/{id}/recurring          -- create template
- GET    /api/v1/clients/{id}/recurring/{tid}     -- get template detail
- PATCH  /api/v1/clients/{id}/recurring/{tid}     -- update template
- DELETE /api/v1/clients/{id}/recurring/{tid}     -- soft-delete template
- POST   /api/v1/recurring/generate              -- generate due transactions

Uses mock service layer to avoid real DB dependency.

Note: The recurring router accesses user.id (not user.user_id) in the
create and generate endpoints. Tests that hit those endpoints override
get_current_user to return a mock user with both attributes.
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
TEMPLATE_ID = str(uuid.uuid4())
ACCOUNT_ID = str(uuid.uuid4())
USER_ID = str(uuid.uuid4())
BASE = f"/api/v1/clients/{CLIENT_ID}/recurring"

MOCK_TEMPLATE = {
    "id": TEMPLATE_ID,
    "client_id": CLIENT_ID,
    "source_type": "JOURNAL_ENTRY",
    "description": "Monthly rent",
    "frequency": "MONTHLY",
    "next_date": "2025-04-01",
    "end_date": None,
    "total_amount": 2000.0,
    "status": "ACTIVE",
    "vendor_id": None,
    "occurrences_generated": 0,
    "max_occurrences": 12,
    "last_generated_date": None,
    "created_by": USER_ID,
    "lines": [
        {
            "id": str(uuid.uuid4()),
            "account_id": ACCOUNT_ID,
            "description": "Rent payment",
            "debit": 2000.0,
            "credit": 0,
        },
        {
            "id": str(uuid.uuid4()),
            "account_id": str(uuid.uuid4()),
            "description": "Cash",
            "debit": 0,
            "credit": 2000.0,
        },
    ],
}

CREATE_BODY = {
    "source_type": "JOURNAL_ENTRY",
    "description": "Monthly rent",
    "frequency": "MONTHLY",
    "next_date": "2025-04-01",
    "lines": [
        {"account_id": ACCOUNT_ID, "description": "Rent", "debit": 2000.0, "credit": 0},
        {"account_id": str(uuid.uuid4()), "description": "Cash", "debit": 0, "credit": 2000.0},
    ],
}


# ---------------------------------------------------------------------------
# GET /clients/{id}/recurring -- list templates
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_list_templates(client: AsyncClient, cpa_owner_headers):
    """List recurring templates for a client."""
    with patch(
        "app.routers.recurring.RecurringService.list_templates",
        new_callable=AsyncMock,
    ) as mock:
        mock.return_value = [MOCK_TEMPLATE]
        response = await client.get(BASE, headers=cpa_owner_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["description"] == "Monthly rent"


@pytest.mark.anyio
async def test_list_templates_empty(client: AsyncClient, cpa_owner_headers):
    """List returns empty array when no templates exist."""
    with patch(
        "app.routers.recurring.RecurringService.list_templates",
        new_callable=AsyncMock,
    ) as mock:
        mock.return_value = []
        response = await client.get(BASE, headers=cpa_owner_headers)
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.anyio
async def test_list_templates_as_associate(client: AsyncClient, associate_headers):
    """ASSOCIATE can list recurring templates."""
    with patch(
        "app.routers.recurring.RecurringService.list_templates",
        new_callable=AsyncMock,
    ) as mock:
        mock.return_value = []
        response = await client.get(BASE, headers=associate_headers)
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# POST /clients/{id}/recurring -- create template
# Uses _override_cpa_owner because the router accesses user.id
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_create_template(client: AsyncClient, _override_cpa_owner):
    """Create a recurring template successfully."""
    with patch(
        "app.routers.recurring.RecurringService.create_template",
        new_callable=AsyncMock,
    ) as mock:
        mock.return_value = MOCK_TEMPLATE
        response = await client.post(BASE, json=CREATE_BODY)
    assert response.status_code == 200
    data = response.json()
    assert data["description"] == "Monthly rent"
    assert data["frequency"] == "MONTHLY"


@pytest.mark.anyio
async def test_create_template_invalid_source_type(client: AsyncClient, _override_cpa_owner):
    """Invalid source_type should fail validation (422)."""
    bad_body = {**CREATE_BODY, "source_type": "INVALID"}
    response = await client.post(BASE, json=bad_body)
    assert response.status_code == 422


@pytest.mark.anyio
async def test_create_template_invalid_frequency(client: AsyncClient, _override_cpa_owner):
    """Invalid frequency should fail validation (422)."""
    bad_body = {**CREATE_BODY, "frequency": "DAILY"}
    response = await client.post(BASE, json=bad_body)
    assert response.status_code == 422


@pytest.mark.anyio
async def test_create_template_no_lines_returns_400(client: AsyncClient, _override_cpa_owner):
    """Service raises ValueError when no lines provided; router returns 400."""
    body_no_lines = {**CREATE_BODY, "lines": []}
    with patch(
        "app.routers.recurring.RecurringService.create_template",
        new_callable=AsyncMock,
    ) as mock:
        mock.side_effect = ValueError("At least one line is required")
        response = await client.post(BASE, json=body_no_lines)
    assert response.status_code == 400
    assert "line" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# GET /clients/{id}/recurring/{tid} -- get template detail
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_get_template(client: AsyncClient, cpa_owner_headers):
    """Get a recurring template by ID."""
    with patch(
        "app.routers.recurring.RecurringService.get_template",
        new_callable=AsyncMock,
    ) as mock:
        mock.return_value = MOCK_TEMPLATE
        response = await client.get(f"{BASE}/{TEMPLATE_ID}", headers=cpa_owner_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == TEMPLATE_ID


@pytest.mark.anyio
async def test_get_template_not_found(client: AsyncClient, cpa_owner_headers):
    """Non-existent template returns 404."""
    fake_id = str(uuid.uuid4())
    with patch(
        "app.routers.recurring.RecurringService.get_template",
        new_callable=AsyncMock,
    ) as mock:
        mock.side_effect = ValueError("Recurring template not found")
        response = await client.get(f"{BASE}/{fake_id}", headers=cpa_owner_headers)
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /clients/{id}/recurring/{tid} -- update template
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_update_template(client: AsyncClient, cpa_owner_headers):
    """Update a recurring template."""
    updated = {**MOCK_TEMPLATE, "description": "Updated rent"}
    with patch(
        "app.routers.recurring.RecurringService.update_template",
        new_callable=AsyncMock,
    ) as mock:
        mock.return_value = updated
        response = await client.patch(
            f"{BASE}/{TEMPLATE_ID}",
            json={"description": "Updated rent"},
            headers=cpa_owner_headers,
        )
    assert response.status_code == 200
    assert response.json()["description"] == "Updated rent"


@pytest.mark.anyio
async def test_update_template_not_found(client: AsyncClient, cpa_owner_headers):
    """Updating a non-existent template returns 400."""
    with patch(
        "app.routers.recurring.RecurringService.update_template",
        new_callable=AsyncMock,
    ) as mock:
        mock.side_effect = ValueError("Recurring template not found")
        response = await client.patch(
            f"{BASE}/{TEMPLATE_ID}",
            json={"description": "nope"},
            headers=cpa_owner_headers,
        )
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# DELETE /clients/{id}/recurring/{tid} -- soft-delete template
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_delete_template(client: AsyncClient, cpa_owner_headers):
    """Soft-delete a recurring template."""
    with patch(
        "app.routers.recurring.RecurringService.delete_template",
        new_callable=AsyncMock,
    ) as mock:
        mock.return_value = {"deleted": True, "id": TEMPLATE_ID}
        response = await client.delete(f"{BASE}/{TEMPLATE_ID}", headers=cpa_owner_headers)
    assert response.status_code == 200
    assert response.json()["deleted"] is True


@pytest.mark.anyio
async def test_delete_template_not_found(client: AsyncClient, cpa_owner_headers):
    """Deleting a non-existent template returns 404."""
    with patch(
        "app.routers.recurring.RecurringService.delete_template",
        new_callable=AsyncMock,
    ) as mock:
        mock.side_effect = ValueError("Recurring template not found")
        response = await client.delete(f"{BASE}/{TEMPLATE_ID}", headers=cpa_owner_headers)
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /recurring/generate -- generate due transactions (CPA_OWNER only)
# Uses _override_cpa_owner because the router accesses user.id
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_generate_due(client: AsyncClient, _override_cpa_owner):
    """CPA_OWNER can generate due recurring transactions."""
    mock_result = {
        "generated": [
            {"template_id": TEMPLATE_ID, "type": "JOURNAL_ENTRY", "entry_id": str(uuid.uuid4())}
        ],
        "count": 1,
        "as_of": "2025-04-01",
    }
    with patch(
        "app.routers.recurring.RecurringService.generate_due",
        new_callable=AsyncMock,
    ) as mock:
        mock.return_value = mock_result
        response = await client.post(
            "/api/v1/recurring/generate?as_of=2025-04-01",
        )
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert len(data["generated"]) == 1


@pytest.mark.anyio
async def test_generate_due_no_date(client: AsyncClient, _override_cpa_owner):
    """Generate uses today when no as_of date provided."""
    mock_result = {"generated": [], "count": 0, "as_of": "2025-03-05"}
    with patch(
        "app.routers.recurring.RecurringService.generate_due",
        new_callable=AsyncMock,
    ) as mock:
        mock.return_value = mock_result
        response = await client.post("/api/v1/recurring/generate")
    assert response.status_code == 200
    assert response.json()["count"] == 0


@pytest.mark.anyio
async def test_generate_due_as_associate_forbidden(client: AsyncClient, _override_associate):
    """ASSOCIATE gets 403 when attempting to generate recurring transactions."""
    response = await client.post("/api/v1/recurring/generate")
    assert response.status_code == 403


@pytest.mark.anyio
async def test_generate_unauthenticated(client: AsyncClient):
    """Unauthenticated request to generate gets 401."""
    response = await client.post("/api/v1/recurring/generate")
    assert response.status_code in (401, 403)
