"""
Tests for Contacts / CRM API endpoints (PM4).

Tests cover:
- Create contact
- List contacts with client_id and search filters
- Get single contact
- Update contact
- Delete contact (soft-delete)
- Unauthenticated request returns 401

Uses mock DB and patched service layer.
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

def _make_contact(**overrides):
    contact_id = overrides.get("id", uuid.uuid4())
    return MagicMock(
        id=contact_id,
        client_id=overrides.get("client_id", uuid.uuid4()),
        first_name=overrides.get("first_name", "Jane"),
        last_name=overrides.get("last_name", "Doe"),
        email=overrides.get("email", "jane.doe@example.com"),
        phone=overrides.get("phone", "770-555-1234"),
        mobile=overrides.get("mobile", None),
        title=overrides.get("title", "CFO"),
        is_primary=overrides.get("is_primary", False),
        address=overrides.get("address", "123 Main St"),
        city=overrides.get("city", "Atlanta"),
        state=overrides.get("state", "GA"),
        zip=overrides.get("zip", "30301"),
        notes=overrides.get("notes", None),
        tags=overrides.get("tags", []),
        custom_fields=overrides.get("custom_fields", {}),
        deleted_at=None,
        created_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
    )


# ---------------------------------------------------------------------------
# Create Contact
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_create_contact(client: AsyncClient, cpa_owner_headers):
    """POST /api/v1/contacts creates a contact."""
    mock_contact = _make_contact()
    with patch(
        "app.routers.contacts.ContactService.create",
        new_callable=AsyncMock,
    ) as mock_create:
        mock_create.return_value = mock_contact
        response = await client.post(
            "/api/v1/contacts",
            headers=cpa_owner_headers,
            json={
                "client_id": str(uuid.uuid4()),
                "first_name": "Jane",
                "last_name": "Doe",
                "email": "jane.doe@example.com",
                "phone": "770-555-1234",
                "title": "CFO",
            },
        )
    assert response.status_code == 201
    data = response.json()
    assert data["first_name"] == "Jane"
    assert data["last_name"] == "Doe"
    assert data["email"] == "jane.doe@example.com"


@pytest.mark.anyio
async def test_create_contact_associate(client: AsyncClient, associate_headers):
    """POST /api/v1/contacts is accessible to ASSOCIATE."""
    mock_contact = _make_contact()
    with patch(
        "app.routers.contacts.ContactService.create",
        new_callable=AsyncMock,
    ) as mock_create:
        mock_create.return_value = mock_contact
        response = await client.post(
            "/api/v1/contacts",
            headers=associate_headers,
            json={
                "client_id": str(uuid.uuid4()),
                "first_name": "John",
                "last_name": "Smith",
            },
        )
    assert response.status_code == 201


@pytest.mark.anyio
async def test_create_contact_with_tags(client: AsyncClient, cpa_owner_headers):
    """POST /api/v1/contacts supports tags and custom fields."""
    mock_contact = _make_contact(
        tags=["VIP", "referral"],
        custom_fields={"source": "website"},
    )
    with patch(
        "app.routers.contacts.ContactService.create",
        new_callable=AsyncMock,
    ) as mock_create:
        mock_create.return_value = mock_contact
        response = await client.post(
            "/api/v1/contacts",
            headers=cpa_owner_headers,
            json={
                "client_id": str(uuid.uuid4()),
                "first_name": "Jane",
                "last_name": "Doe",
                "tags": ["VIP", "referral"],
                "custom_fields": {"source": "website"},
            },
        )
    assert response.status_code == 201
    data = response.json()
    assert data["tags"] == ["VIP", "referral"]
    assert data["custom_fields"] == {"source": "website"}


# ---------------------------------------------------------------------------
# List Contacts
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_list_contacts(client: AsyncClient, cpa_owner_headers):
    """GET /api/v1/contacts lists contacts."""
    contacts = [_make_contact() for _ in range(3)]
    with patch(
        "app.routers.contacts.ContactService.list_contacts",
        new_callable=AsyncMock,
    ) as mock_list:
        mock_list.return_value = (contacts, 3)
        response = await client.get("/api/v1/contacts", headers=cpa_owner_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3


@pytest.mark.anyio
async def test_list_contacts_with_client_filter(client: AsyncClient, cpa_owner_headers):
    """GET /api/v1/contacts supports client_id filter."""
    client_id = uuid.uuid4()
    contacts = [_make_contact(client_id=client_id)]
    with patch(
        "app.routers.contacts.ContactService.list_contacts",
        new_callable=AsyncMock,
    ) as mock_list:
        mock_list.return_value = (contacts, 1)
        response = await client.get(
            "/api/v1/contacts",
            headers=cpa_owner_headers,
            params={"client_id": str(client_id)},
        )
    assert response.status_code == 200
    assert response.json()["total"] == 1
    mock_list.assert_called_once()
    call_args = mock_list.call_args
    assert call_args[0][1] == client_id  # client_id arg


@pytest.mark.anyio
async def test_list_contacts_with_search(client: AsyncClient, cpa_owner_headers):
    """GET /api/v1/contacts supports search parameter."""
    contacts = [_make_contact(first_name="Jane", last_name="Doe")]
    with patch(
        "app.routers.contacts.ContactService.list_contacts",
        new_callable=AsyncMock,
    ) as mock_list:
        mock_list.return_value = (contacts, 1)
        response = await client.get(
            "/api/v1/contacts",
            headers=cpa_owner_headers,
            params={"search": "Jane"},
        )
    assert response.status_code == 200
    assert response.json()["total"] == 1
    call_args = mock_list.call_args
    assert call_args[0][2] == "Jane"  # search arg


# ---------------------------------------------------------------------------
# Get Contact
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_get_contact(client: AsyncClient, cpa_owner_headers):
    """GET /api/v1/contacts/{id} returns a single contact."""
    contact_id = uuid.uuid4()
    mock_contact = _make_contact(id=contact_id)
    with patch(
        "app.routers.contacts.ContactService.get",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.return_value = mock_contact
        response = await client.get(
            f"/api/v1/contacts/{contact_id}", headers=cpa_owner_headers
        )
    assert response.status_code == 200
    assert response.json()["id"] == str(contact_id)


# ---------------------------------------------------------------------------
# Update Contact
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_update_contact(client: AsyncClient, cpa_owner_headers):
    """PUT /api/v1/contacts/{id} updates a contact."""
    contact_id = uuid.uuid4()
    mock_contact = _make_contact(id=contact_id, first_name="Janet", title="CEO")
    with patch(
        "app.routers.contacts.ContactService.update",
        new_callable=AsyncMock,
    ) as mock_update:
        mock_update.return_value = mock_contact
        response = await client.put(
            f"/api/v1/contacts/{contact_id}",
            headers=cpa_owner_headers,
            json={"first_name": "Janet", "title": "CEO"},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "Janet"
    assert data["title"] == "CEO"


# ---------------------------------------------------------------------------
# Delete Contact
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_delete_contact(client: AsyncClient, cpa_owner_headers):
    """DELETE /api/v1/contacts/{id} soft-deletes a contact."""
    contact_id = uuid.uuid4()
    with patch(
        "app.routers.contacts.ContactService.delete",
        new_callable=AsyncMock,
    ) as mock_delete:
        mock_delete.return_value = None
        response = await client.delete(
            f"/api/v1/contacts/{contact_id}", headers=cpa_owner_headers
        )
    assert response.status_code == 204


# ---------------------------------------------------------------------------
# Auth check
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_list_contacts_unauthenticated(client: AsyncClient):
    """GET /api/v1/contacts without auth returns 401."""
    response = await client.get("/api/v1/contacts")
    assert response.status_code == 401
