"""
Tests for Global Search (module D1).

Tests the search router endpoint:
- GET /api/v1/search?q=...&limit=...

Uses mock service layer to avoid real DB dependency.
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.main import app


MOCK_RESULTS_FULL = {
    "clients": [
        {
            "id": str(uuid.uuid4()),
            "name": "Acme Corp",
            "entity_type": "C_CORP",
            "email": "acme@example.com",
            "phone": "555-1234",
            "type": "client",
        },
    ],
    "vendors": [
        {
            "id": str(uuid.uuid4()),
            "name": "Acme Supply Co",
            "client_id": str(uuid.uuid4()),
            "client_name": "Test Client",
            "type": "vendor",
        },
    ],
    "employees": [
        {
            "id": str(uuid.uuid4()),
            "name": "John Acme",
            "client_id": str(uuid.uuid4()),
            "client_name": "Test Client",
            "type": "employee",
        },
    ],
    "invoices": [
        {
            "id": str(uuid.uuid4()),
            "name": "#INV-001 \u2014 Acme Widget",
            "amount": 1500.0,
            "status": "SENT",
            "client_id": str(uuid.uuid4()),
            "client_name": "Test Client",
            "type": "invoice",
        },
    ],
    "bills": [
        {
            "id": str(uuid.uuid4()),
            "name": "#BILL-001 \u2014 Acme Supply Co",
            "amount": 750.0,
            "status": "APPROVED",
            "client_id": str(uuid.uuid4()),
            "client_name": "Test Client",
            "type": "bill",
        },
    ],
}

MOCK_RESULTS_EMPTY = {
    "clients": [],
    "vendors": [],
    "employees": [],
    "invoices": [],
    "bills": [],
}


# ---------------------------------------------------------------------------
# Happy path tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_search_returns_results(client: AsyncClient, cpa_owner_headers):
    """Search with matching query returns categorized results."""
    with patch(
        "app.routers.search.SearchService.search",
        new_callable=AsyncMock,
    ) as mock:
        mock.return_value = MOCK_RESULTS_FULL
        response = await client.get(
            "/api/v1/search?q=acme",
            headers=cpa_owner_headers,
        )
    assert response.status_code == 200
    data = response.json()
    assert len(data["clients"]) == 1
    assert data["clients"][0]["name"] == "Acme Corp"
    assert len(data["vendors"]) == 1
    assert len(data["employees"]) == 1
    assert len(data["invoices"]) == 1
    assert len(data["bills"]) == 1


@pytest.mark.anyio
async def test_search_empty_results(client: AsyncClient, cpa_owner_headers):
    """Search with no matches returns empty categories."""
    with patch(
        "app.routers.search.SearchService.search",
        new_callable=AsyncMock,
    ) as mock:
        mock.return_value = MOCK_RESULTS_EMPTY
        response = await client.get(
            "/api/v1/search?q=zzzznonexistent",
            headers=cpa_owner_headers,
        )
    assert response.status_code == 200
    data = response.json()
    for key in ("clients", "vendors", "employees", "invoices", "bills"):
        assert data[key] == []


@pytest.mark.anyio
async def test_search_with_custom_limit(client: AsyncClient, cpa_owner_headers):
    """Custom limit parameter is passed through to service."""
    with patch(
        "app.routers.search.SearchService.search",
        new_callable=AsyncMock,
    ) as mock:
        mock.return_value = MOCK_RESULTS_EMPTY
        response = await client.get(
            "/api/v1/search?q=test&limit=5",
            headers=cpa_owner_headers,
        )
    assert response.status_code == 200
    mock.assert_called_once()
    # Verify the limit argument was passed
    call_args = mock.call_args
    assert call_args[0][1] == "test"  # query
    assert call_args[0][2] == 5       # limit


@pytest.mark.anyio
async def test_search_as_associate(client: AsyncClient, associate_headers):
    """ASSOCIATE can use global search."""
    with patch(
        "app.routers.search.SearchService.search",
        new_callable=AsyncMock,
    ) as mock:
        mock.return_value = MOCK_RESULTS_EMPTY
        response = await client.get(
            "/api/v1/search?q=test",
            headers=associate_headers,
        )
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Validation tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_search_missing_query_param(client: AsyncClient, cpa_owner_headers):
    """Missing q parameter returns 422."""
    response = await client.get("/api/v1/search", headers=cpa_owner_headers)
    assert response.status_code == 422


@pytest.mark.anyio
async def test_search_query_too_short(client: AsyncClient, cpa_owner_headers):
    """Query shorter than min_length=2 returns 422."""
    response = await client.get("/api/v1/search?q=a", headers=cpa_owner_headers)
    assert response.status_code == 422


@pytest.mark.anyio
async def test_search_limit_exceeds_max(client: AsyncClient, cpa_owner_headers):
    """Limit exceeding max (50) returns 422."""
    response = await client.get(
        "/api/v1/search?q=test&limit=100",
        headers=cpa_owner_headers,
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Auth tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_search_unauthenticated(client: AsyncClient):
    """Unauthenticated request gets 401."""
    response = await client.get("/api/v1/search?q=test")
    assert response.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Service layer pass-through test
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_search_passes_correct_args(client: AsyncClient, cpa_owner_headers):
    """Verify that the router passes the correct query and limit to the service."""
    with patch(
        "app.routers.search.SearchService.search",
        new_callable=AsyncMock,
    ) as mock:
        mock.return_value = MOCK_RESULTS_EMPTY
        await client.get(
            "/api/v1/search?q=hello+world&limit=25",
            headers=cpa_owner_headers,
        )
    mock.assert_called_once()
    args = mock.call_args[0]
    assert args[1] == "hello world"
    assert args[2] == 25


@pytest.mark.anyio
async def test_search_returns_all_five_categories(client: AsyncClient, cpa_owner_headers):
    """Response always contains all five category keys."""
    with patch(
        "app.routers.search.SearchService.search",
        new_callable=AsyncMock,
    ) as mock:
        mock.return_value = MOCK_RESULTS_FULL
        response = await client.get(
            "/api/v1/search?q=test",
            headers=cpa_owner_headers,
        )
    data = response.json()
    expected_keys = {"clients", "vendors", "employees", "invoices", "bills"}
    assert set(data.keys()) == expected_keys
