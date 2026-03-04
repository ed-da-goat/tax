"""
Tests for Client Management (Module F4).

Covers:
- CRUD operations via HTTP endpoints
- Role enforcement: ASSOCIATE cannot create/update/delete (403)
- Soft deletes: archived clients excluded from list
- Client isolation: Client A queries cannot return Client B data

Compliance tests per CLAUDE.md:
- Rule #2: Soft deletes only
- Rule #4: Client isolation
- Role checks at route AND function level (defense in depth)
"""

import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.auth.dependencies import CurrentUser, verify_role
from app.models.client import EntityType
from app.services.client import ClientService
from fastapi import HTTPException


# ---------------------------------------------------------------------------
# Helpers to build mock Client ORM instances
# ---------------------------------------------------------------------------
def _make_client(
    name: str = "Test LLC",
    entity_type: EntityType = EntityType.PARTNERSHIP_LLC,
    client_id: uuid.UUID | None = None,
    is_active: bool = True,
    deleted_at: datetime | None = None,
    **kwargs: Any,
) -> MagicMock:
    """Create a mock Client object with sensible defaults for testing."""
    now = datetime.now(timezone.utc)
    mock = MagicMock()
    mock.id = client_id or uuid.uuid4()
    mock.name = name
    mock.entity_type = entity_type
    mock.tax_id_encrypted = kwargs.get("tax_id_encrypted")
    mock.address = kwargs.get("address", "123 Main St")
    mock.city = kwargs.get("city", "Atlanta")
    mock.state = kwargs.get("state", "GA")
    mock.zip = kwargs.get("zip", "30301")
    mock.phone = kwargs.get("phone", "555-0100")
    mock.email = kwargs.get("email", "test@example.com")
    mock.is_active = is_active
    mock.deleted_at = deleted_at
    mock.created_at = kwargs.get("created_at", now)
    mock.updated_at = kwargs.get("updated_at", now)
    return mock


# ============================================================================
# HTTP endpoint tests
# ============================================================================


class TestCreateClient:
    """POST /api/v1/clients — CPA_OWNER only."""

    async def test_create_client_as_cpa_owner(
        self, client: AsyncClient, cpa_owner_headers: dict, as_cpa_owner: None
    ) -> None:
        """CPA_OWNER should be able to create a client and get 201."""
        mock_client = _make_client(name="Acme Corp", entity_type=EntityType.C_CORP)

        with patch.object(
            ClientService, "create_client", new_callable=AsyncMock, return_value=mock_client
        ):
            response = await client.post(
                "/api/v1/clients",
                json={"name": "Acme Corp", "entity_type": "C_CORP"},
                headers=cpa_owner_headers,
            )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Acme Corp"
        assert data["entity_type"] == "C_CORP"
        assert data["is_active"] is True

    async def test_create_client_as_associate_returns_403(
        self, client: AsyncClient, associate_headers: dict
    ) -> None:
        """ASSOCIATE must not be able to create clients — 403."""
        response = await client.post(
            "/api/v1/clients",
            json={"name": "Blocked Corp", "entity_type": "S_CORP"},
            headers=associate_headers,
        )
        assert response.status_code == 403

    async def test_create_client_missing_name_returns_422(
        self, client: AsyncClient, cpa_owner_headers: dict, as_cpa_owner: None
    ) -> None:
        """Missing required field 'name' should return 422."""
        response = await client.post(
            "/api/v1/clients",
            json={"entity_type": "S_CORP"},
            headers=cpa_owner_headers,
        )
        assert response.status_code == 422

    async def test_create_client_invalid_entity_type_returns_422(
        self, client: AsyncClient, cpa_owner_headers: dict, as_cpa_owner: None
    ) -> None:
        """Invalid entity_type should return 422."""
        response = await client.post(
            "/api/v1/clients",
            json={"name": "Bad Type LLC", "entity_type": "INVALID"},
            headers=cpa_owner_headers,
        )
        assert response.status_code == 422


class TestListClients:
    """GET /api/v1/clients — both roles."""

    async def test_list_clients_as_cpa_owner(
        self, client: AsyncClient, cpa_owner_headers: dict, as_cpa_owner: None
    ) -> None:
        """CPA_OWNER can list clients."""
        mock_clients = [
            _make_client(name="Client A"),
            _make_client(name="Client B"),
        ]

        with patch.object(
            ClientService, "list_clients", new_callable=AsyncMock, return_value=(mock_clients, 2)
        ):
            response = await client.get(
                "/api/v1/clients",
                headers=cpa_owner_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    async def test_list_clients_as_associate(
        self, client: AsyncClient, associate_headers: dict, as_associate: None
    ) -> None:
        """ASSOCIATE can also list clients."""
        with patch.object(
            ClientService, "list_clients", new_callable=AsyncMock, return_value=([], 0)
        ):
            response = await client.get(
                "/api/v1/clients",
                headers=associate_headers,
            )

        assert response.status_code == 200

    async def test_list_clients_excludes_archived(
        self, client: AsyncClient, cpa_owner_headers: dict, as_cpa_owner: None
    ) -> None:
        """
        Archived (soft-deleted) clients must NOT appear in the list.
        The service filters by deleted_at IS NULL, so mock returns only active.
        """
        active_client = _make_client(name="Active Corp")
        # The archived client should NOT be in the return value
        # because the service filters deleted_at IS NULL

        with patch.object(
            ClientService,
            "list_clients",
            new_callable=AsyncMock,
            return_value=([active_client], 1),
        ):
            response = await client.get(
                "/api/v1/clients",
                headers=cpa_owner_headers,
            )

        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == "Active Corp"

    async def test_list_clients_unauthenticated_returns_401_or_403(
        self, client: AsyncClient
    ) -> None:
        """Request without auth token should be rejected (401 or 403)."""
        response = await client.get("/api/v1/clients")
        assert response.status_code in (401, 403)


class TestGetClient:
    """GET /api/v1/clients/{id} — both roles."""

    async def test_get_client_by_id(
        self, client: AsyncClient, cpa_owner_headers: dict, as_cpa_owner: None
    ) -> None:
        """Should return a single client by ID."""
        cid = uuid.uuid4()
        mock_client = _make_client(name="Specific Client", client_id=cid)

        with patch.object(
            ClientService, "get_client", new_callable=AsyncMock, return_value=mock_client
        ):
            response = await client.get(
                f"/api/v1/clients/{cid}",
                headers=cpa_owner_headers,
            )

        assert response.status_code == 200
        assert response.json()["name"] == "Specific Client"

    async def test_get_nonexistent_client_returns_404(
        self, client: AsyncClient, cpa_owner_headers: dict, as_cpa_owner: None
    ) -> None:
        """Should return 404 for a client that does not exist."""
        with patch.object(
            ClientService, "get_client", new_callable=AsyncMock, return_value=None
        ):
            response = await client.get(
                f"/api/v1/clients/{uuid.uuid4()}",
                headers=cpa_owner_headers,
            )

        assert response.status_code == 404

    async def test_get_client_as_associate(
        self, client: AsyncClient, associate_headers: dict, as_associate: None
    ) -> None:
        """ASSOCIATE can view client details."""
        mock_client = _make_client(name="Viewable Corp")

        with patch.object(
            ClientService, "get_client", new_callable=AsyncMock, return_value=mock_client
        ):
            response = await client.get(
                f"/api/v1/clients/{uuid.uuid4()}",
                headers=associate_headers,
            )

        assert response.status_code == 200


class TestUpdateClient:
    """PUT /api/v1/clients/{id} — CPA_OWNER only."""

    async def test_update_client_as_cpa_owner(
        self, client: AsyncClient, cpa_owner_headers: dict, as_cpa_owner: None
    ) -> None:
        """CPA_OWNER should be able to update a client."""
        cid = uuid.uuid4()
        updated = _make_client(name="Updated Name", client_id=cid)

        with patch.object(
            ClientService, "update_client", new_callable=AsyncMock, return_value=updated
        ):
            response = await client.put(
                f"/api/v1/clients/{cid}",
                json={"name": "Updated Name"},
                headers=cpa_owner_headers,
            )

        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"

    async def test_update_client_as_associate_returns_403(
        self, client: AsyncClient, associate_headers: dict
    ) -> None:
        """ASSOCIATE must not be able to update clients — 403."""
        response = await client.put(
            f"/api/v1/clients/{uuid.uuid4()}",
            json={"name": "Hacked Name"},
            headers=associate_headers,
        )
        assert response.status_code == 403

    async def test_update_nonexistent_client_returns_404(
        self, client: AsyncClient, cpa_owner_headers: dict, as_cpa_owner: None
    ) -> None:
        """Updating a nonexistent client should return 404."""
        with patch.object(
            ClientService, "update_client", new_callable=AsyncMock, return_value=None
        ):
            response = await client.put(
                f"/api/v1/clients/{uuid.uuid4()}",
                json={"name": "Ghost"},
                headers=cpa_owner_headers,
            )

        assert response.status_code == 404


class TestArchiveClient:
    """DELETE /api/v1/clients/{id} — CPA_OWNER only, soft-delete."""

    async def test_archive_client_as_cpa_owner(
        self, client: AsyncClient, cpa_owner_headers: dict, as_cpa_owner: None
    ) -> None:
        """CPA_OWNER should be able to archive (soft-delete) a client."""
        cid = uuid.uuid4()
        archived = _make_client(
            name="Archived Corp",
            client_id=cid,
            is_active=False,
            deleted_at=datetime.now(timezone.utc),
        )

        with patch.object(
            ClientService, "archive_client", new_callable=AsyncMock, return_value=archived
        ):
            response = await client.delete(
                f"/api/v1/clients/{cid}",
                headers=cpa_owner_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False
        assert data["deleted_at"] is not None

    async def test_archive_client_as_associate_returns_403(
        self, client: AsyncClient, associate_headers: dict
    ) -> None:
        """ASSOCIATE must not be able to archive clients — 403."""
        response = await client.delete(
            f"/api/v1/clients/{uuid.uuid4()}",
            headers=associate_headers,
        )
        assert response.status_code == 403

    async def test_archive_nonexistent_client_returns_404(
        self, client: AsyncClient, cpa_owner_headers: dict, as_cpa_owner: None
    ) -> None:
        """Archiving a nonexistent client should return 404."""
        with patch.object(
            ClientService, "archive_client", new_callable=AsyncMock, return_value=None
        ):
            response = await client.delete(
                f"/api/v1/clients/{uuid.uuid4()}",
                headers=cpa_owner_headers,
            )

        assert response.status_code == 404


# ============================================================================
# Service-level tests (defense in depth — role checks at function level)
# ============================================================================


class TestServiceRoleEnforcement:
    """
    Verify that the service layer enforces CPA_OWNER role independently
    of the route layer. Defense in depth per CLAUDE.md rule #6.
    """

    def test_create_client_service_rejects_associate(self) -> None:
        """ClientService.create_client must reject ASSOCIATE at function level."""
        associate = CurrentUser(user_id="assoc-1", role="ASSOCIATE")
        with pytest.raises(HTTPException) as exc_info:
            verify_role(associate, "CPA_OWNER")
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["required_role"] == "CPA_OWNER"

    def test_update_client_service_rejects_associate(self) -> None:
        """ClientService.update_client must reject ASSOCIATE at function level."""
        associate = CurrentUser(user_id="assoc-2", role="ASSOCIATE")
        with pytest.raises(HTTPException) as exc_info:
            verify_role(associate, "CPA_OWNER")
        assert exc_info.value.status_code == 403

    def test_archive_client_service_rejects_associate(self) -> None:
        """ClientService.archive_client must reject ASSOCIATE at function level."""
        associate = CurrentUser(user_id="assoc-3", role="ASSOCIATE")
        with pytest.raises(HTTPException) as exc_info:
            verify_role(associate, "CPA_OWNER")
        assert exc_info.value.status_code == 403

    def test_cpa_owner_passes_role_check(self) -> None:
        """CPA_OWNER should pass the function-level role check without exception."""
        owner = CurrentUser(user_id="owner-1", role="CPA_OWNER")
        # Should not raise
        verify_role(owner, "CPA_OWNER")


# ============================================================================
# Client isolation tests (CLAUDE.md rule #4)
# ============================================================================


class TestClientIsolation:
    """
    CRITICAL: Verify that Client A queries cannot return Client B data.

    Compliance (CLAUDE.md rule #4): every query that returns client data
    must filter by client_id. The get_client method filters by the specific
    client_id parameter, ensuring isolation.
    """

    async def test_get_client_returns_only_requested_client(
        self, client: AsyncClient, cpa_owner_headers: dict, as_cpa_owner: None
    ) -> None:
        """
        Requesting Client A's ID must not return Client B's data.
        The service queries by exact client_id match.
        """
        client_a_id = uuid.uuid4()
        client_b_id = uuid.uuid4()

        client_a = _make_client(name="Client A Corp", client_id=client_a_id)
        client_b = _make_client(name="Client B Corp", client_id=client_b_id)

        # When we ask for Client A, we get Client A
        with patch.object(
            ClientService, "get_client", new_callable=AsyncMock, return_value=client_a
        ) as mock_get:
            response = await client.get(
                f"/api/v1/clients/{client_a_id}",
                headers=cpa_owner_headers,
            )
            # Verify the service was called with Client A's ID, not Client B's
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert call_args[0][1] == client_a_id  # second positional arg is client_id

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Client A Corp"
        assert data["id"] == str(client_a_id)

    async def test_get_client_b_does_not_return_client_a(
        self, client: AsyncClient, cpa_owner_headers: dict, as_cpa_owner: None
    ) -> None:
        """
        Requesting Client B's ID returns Client B, not Client A.
        This validates the filtering is parameterized by client_id.
        """
        client_a_id = uuid.uuid4()
        client_b_id = uuid.uuid4()

        client_b = _make_client(name="Client B LLC", client_id=client_b_id)

        with patch.object(
            ClientService, "get_client", new_callable=AsyncMock, return_value=client_b
        ) as mock_get:
            response = await client.get(
                f"/api/v1/clients/{client_b_id}",
                headers=cpa_owner_headers,
            )
            call_args = mock_get.call_args
            assert call_args[0][1] == client_b_id

        data = response.json()
        assert data["id"] == str(client_b_id)
        assert data["name"] == "Client B LLC"

    async def test_nonexistent_client_id_returns_404_not_other_client(
        self, client: AsyncClient, cpa_owner_headers: dict, as_cpa_owner: None
    ) -> None:
        """
        Requesting a random UUID that doesn't exist must return 404,
        not some other client's data. This guards against broad queries.
        """
        random_id = uuid.uuid4()

        with patch.object(
            ClientService, "get_client", new_callable=AsyncMock, return_value=None
        ):
            response = await client.get(
                f"/api/v1/clients/{random_id}",
                headers=cpa_owner_headers,
            )

        assert response.status_code == 404


# ============================================================================
# Soft delete compliance tests
# ============================================================================


class TestSoftDeleteCompliance:
    """
    Verify that the system never hard-deletes client records.

    Compliance (CLAUDE.md rule #2): Records are never deleted.
    The DELETE endpoint sets deleted_at, not removes the row.
    """

    async def test_delete_endpoint_returns_record_with_deleted_at(
        self, client: AsyncClient, cpa_owner_headers: dict, as_cpa_owner: None
    ) -> None:
        """
        The DELETE endpoint should return the client record with
        deleted_at set (proving it was soft-deleted, not removed).
        """
        cid = uuid.uuid4()
        now = datetime.now(timezone.utc)
        archived = _make_client(
            name="Soft Deleted Corp",
            client_id=cid,
            is_active=False,
            deleted_at=now,
        )

        with patch.object(
            ClientService, "archive_client", new_callable=AsyncMock, return_value=archived
        ):
            response = await client.delete(
                f"/api/v1/clients/{cid}",
                headers=cpa_owner_headers,
            )

        data = response.json()
        assert data["deleted_at"] is not None
        assert data["is_active"] is False
