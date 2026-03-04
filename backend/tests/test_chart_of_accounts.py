"""
Tests for Chart of Accounts API (module F2).

Compliance tests:
- Client isolation: Client A's accounts never returned when querying Client B (rule #4)
- Role enforcement: ASSOCIATE cannot create/update/delete accounts (CLAUDE.md)
- Soft deletes: deactivated accounts excluded from list queries (rule #2)
- Unique constraint: duplicate account_number within same client rejected

Uses a real PostgreSQL session (rolled back after each test) via the
db_session and db_client fixtures from conftest.py.
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chart_of_accounts import ChartOfAccounts
from app.services.chart_of_accounts import ChartOfAccountsService, TEMPLATE_CLIENT_ID


# ---------------------------------------------------------------------------
# Helper: create a test client record in the DB
# ---------------------------------------------------------------------------
async def _create_test_client(db: AsyncSession, client_id: uuid.UUID | None = None) -> uuid.UUID:
    """Insert a minimal client row and return its UUID."""
    cid = client_id or uuid.uuid4()
    await db.execute(
        text(
            "INSERT INTO clients (id, name, entity_type, is_active) "
            "VALUES (:id, :name, 'SOLE_PROP', true)"
        ),
        {"id": str(cid), "name": f"Test Client {cid}"},
    )
    await db.flush()
    return cid


# ---------------------------------------------------------------------------
# Service-layer tests (direct DB, no HTTP)
# ---------------------------------------------------------------------------
class TestChartOfAccountsService:
    """Tests for ChartOfAccountsService business logic."""

    async def test_create_account(self, db_session: AsyncSession) -> None:
        """Creating an account persists it with correct fields."""
        from app.schemas.chart_of_accounts import AccountCreate

        client_id = await _create_test_client(db_session)
        data = AccountCreate(
            account_number="9999",
            account_name="Test Account",
            account_type="ASSET",
            sub_type="Current Asset",
            is_active=True,
        )
        account = await ChartOfAccountsService.create_account(db_session, client_id, data)

        assert account.client_id == client_id
        assert account.account_number == "9999"
        assert account.account_name == "Test Account"
        assert account.account_type == "ASSET"
        assert account.sub_type == "Current Asset"
        assert account.is_active is True
        assert account.deleted_at is None

    async def test_get_account_filters_by_client_id(self, db_session: AsyncSession) -> None:
        """get_account returns None if queried with wrong client_id."""
        from app.schemas.chart_of_accounts import AccountCreate

        client_a = await _create_test_client(db_session)
        client_b = await _create_test_client(db_session)

        data = AccountCreate(
            account_number="1000",
            account_name="Cash",
            account_type="ASSET",
        )
        account = await ChartOfAccountsService.create_account(db_session, client_a, data)

        # Same client retrieves it
        found = await ChartOfAccountsService.get_account(db_session, client_a, account.id)
        assert found is not None
        assert found.id == account.id

        # Different client cannot see it
        not_found = await ChartOfAccountsService.get_account(db_session, client_b, account.id)
        assert not_found is None

    async def test_list_accounts_scoped_to_client(self, db_session: AsyncSession) -> None:
        """list_accounts only returns accounts belonging to the queried client."""
        from app.schemas.chart_of_accounts import AccountCreate

        client_a = await _create_test_client(db_session)
        client_b = await _create_test_client(db_session)

        # Create accounts for both clients
        await ChartOfAccountsService.create_account(
            db_session, client_a,
            AccountCreate(account_number="1000", account_name="Cash A", account_type="ASSET"),
        )
        await ChartOfAccountsService.create_account(
            db_session, client_b,
            AccountCreate(account_number="1000", account_name="Cash B", account_type="ASSET"),
        )

        accounts_a = await ChartOfAccountsService.list_accounts(db_session, client_a)
        accounts_b = await ChartOfAccountsService.list_accounts(db_session, client_b)

        assert len(accounts_a) == 1
        assert accounts_a[0].account_name == "Cash A"
        assert len(accounts_b) == 1
        assert accounts_b[0].account_name == "Cash B"

    async def test_list_accounts_filter_by_type(self, db_session: AsyncSession) -> None:
        """list_accounts can filter by account_type."""
        from app.schemas.chart_of_accounts import AccountCreate

        client_id = await _create_test_client(db_session)

        await ChartOfAccountsService.create_account(
            db_session, client_id,
            AccountCreate(account_number="1000", account_name="Cash", account_type="ASSET"),
        )
        await ChartOfAccountsService.create_account(
            db_session, client_id,
            AccountCreate(account_number="4000", account_name="Revenue", account_type="REVENUE"),
        )

        assets = await ChartOfAccountsService.list_accounts(db_session, client_id, account_type="ASSET")
        assert len(assets) == 1
        assert assets[0].account_type == "ASSET"

    async def test_list_accounts_filter_by_active(self, db_session: AsyncSession) -> None:
        """list_accounts can filter by is_active flag."""
        from app.schemas.chart_of_accounts import AccountCreate

        client_id = await _create_test_client(db_session)

        await ChartOfAccountsService.create_account(
            db_session, client_id,
            AccountCreate(account_number="1000", account_name="Active", account_type="ASSET", is_active=True),
        )
        await ChartOfAccountsService.create_account(
            db_session, client_id,
            AccountCreate(account_number="1001", account_name="Inactive", account_type="ASSET", is_active=False),
        )

        active = await ChartOfAccountsService.list_accounts(db_session, client_id, is_active=True)
        assert len(active) == 1
        assert active[0].account_name == "Active"

    async def test_update_account(self, db_session: AsyncSession) -> None:
        """update_account modifies only the specified fields."""
        from app.schemas.chart_of_accounts import AccountCreate, AccountUpdate

        client_id = await _create_test_client(db_session)
        data = AccountCreate(
            account_number="1000",
            account_name="Old Name",
            account_type="ASSET",
        )
        account = await ChartOfAccountsService.create_account(db_session, client_id, data)

        updated = await ChartOfAccountsService.update_account(
            db_session, client_id, account.id,
            AccountUpdate(account_name="New Name"),
        )
        assert updated is not None
        assert updated.account_name == "New Name"
        assert updated.account_number == "1000"  # unchanged

    async def test_update_account_wrong_client_returns_none(self, db_session: AsyncSession) -> None:
        """update_account returns None when client_id doesn't match."""
        from app.schemas.chart_of_accounts import AccountCreate, AccountUpdate

        client_a = await _create_test_client(db_session)
        client_b = await _create_test_client(db_session)

        data = AccountCreate(account_number="1000", account_name="Cash", account_type="ASSET")
        account = await ChartOfAccountsService.create_account(db_session, client_a, data)

        result = await ChartOfAccountsService.update_account(
            db_session, client_b, account.id,
            AccountUpdate(account_name="Hacked"),
        )
        assert result is None

    async def test_deactivate_account_sets_deleted_at(self, db_session: AsyncSession) -> None:
        """deactivate_account sets deleted_at and is_active=False."""
        from app.schemas.chart_of_accounts import AccountCreate

        client_id = await _create_test_client(db_session)
        data = AccountCreate(account_number="1000", account_name="Cash", account_type="ASSET")
        account = await ChartOfAccountsService.create_account(db_session, client_id, data)

        deactivated = await ChartOfAccountsService.deactivate_account(db_session, client_id, account.id)
        assert deactivated is not None
        assert deactivated.deleted_at is not None
        assert deactivated.is_active is False

    async def test_deactivated_account_excluded_from_list(self, db_session: AsyncSession) -> None:
        """Soft-deleted accounts do not appear in list_accounts."""
        from app.schemas.chart_of_accounts import AccountCreate

        client_id = await _create_test_client(db_session)
        data = AccountCreate(account_number="1000", account_name="Cash", account_type="ASSET")
        account = await ChartOfAccountsService.create_account(db_session, client_id, data)

        await ChartOfAccountsService.deactivate_account(db_session, client_id, account.id)
        accounts = await ChartOfAccountsService.list_accounts(db_session, client_id)
        assert len(accounts) == 0

    async def test_deactivated_account_excluded_from_get(self, db_session: AsyncSession) -> None:
        """Soft-deleted accounts return None from get_account."""
        from app.schemas.chart_of_accounts import AccountCreate

        client_id = await _create_test_client(db_session)
        data = AccountCreate(account_number="1000", account_name="Cash", account_type="ASSET")
        account = await ChartOfAccountsService.create_account(db_session, client_id, data)

        await ChartOfAccountsService.deactivate_account(db_session, client_id, account.id)
        result = await ChartOfAccountsService.get_account(db_session, client_id, account.id)
        assert result is None

    async def test_clone_template_accounts(self, db_session: AsyncSession) -> None:
        """clone_template_accounts copies all template accounts to a new client."""
        client_id = await _create_test_client(db_session)

        # Count template accounts first
        template_accounts = await ChartOfAccountsService.list_accounts(
            db_session, TEMPLATE_CLIENT_ID
        )
        template_count = len(template_accounts)
        assert template_count > 0, "Template client should have seed accounts"

        cloned = await ChartOfAccountsService.clone_template_accounts(db_session, client_id)
        assert len(cloned) == template_count

        # Verify all cloned accounts belong to the new client
        for account in cloned:
            assert account.client_id == client_id

    async def test_duplicate_account_number_raises(self, db_session: AsyncSession) -> None:
        """Creating two accounts with the same number for the same client fails."""
        from sqlalchemy.exc import IntegrityError
        from app.schemas.chart_of_accounts import AccountCreate

        client_id = await _create_test_client(db_session)
        data = AccountCreate(account_number="1000", account_name="Cash", account_type="ASSET")

        await ChartOfAccountsService.create_account(db_session, client_id, data)
        with pytest.raises(IntegrityError):
            await ChartOfAccountsService.create_account(db_session, client_id, data)

    async def test_same_account_number_different_clients_ok(self, db_session: AsyncSession) -> None:
        """Two different clients can have the same account number."""
        from app.schemas.chart_of_accounts import AccountCreate

        client_a = await _create_test_client(db_session)
        client_b = await _create_test_client(db_session)

        data = AccountCreate(account_number="1000", account_name="Cash", account_type="ASSET")
        acct_a = await ChartOfAccountsService.create_account(db_session, client_a, data)
        acct_b = await ChartOfAccountsService.create_account(db_session, client_b, data)

        assert acct_a.id != acct_b.id
        assert acct_a.client_id != acct_b.client_id


# ---------------------------------------------------------------------------
# API endpoint tests (HTTP layer with real DB)
# ---------------------------------------------------------------------------
class TestChartOfAccountsAPI:
    """Tests for the /api/v1/clients/{client_id}/accounts endpoints."""

    async def _setup_client(self, db_session: AsyncSession) -> uuid.UUID:
        """Create a test client and return its ID."""
        return await _create_test_client(db_session)

    async def test_create_account_cpa_owner(
        self, db_session: AsyncSession, db_client: AsyncClient, cpa_owner_headers: dict
    ) -> None:
        """CPA_OWNER can create an account via POST."""
        client_id = await self._setup_client(db_session)
        response = await db_client.post(
            f"/api/v1/clients/{client_id}/accounts",
            json={
                "account_number": "9999",
                "account_name": "Test Revenue",
                "account_type": "REVENUE",
                "sub_type": "Operating Revenue",
            },
            headers=cpa_owner_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["account_number"] == "9999"
        assert data["account_name"] == "Test Revenue"
        assert data["account_type"] == "REVENUE"
        assert data["sub_type"] == "Operating Revenue"
        assert data["is_active"] is True
        assert str(client_id) == data["client_id"]

    async def test_create_account_associate_forbidden(
        self, db_session: AsyncSession, db_client: AsyncClient, associate_headers: dict
    ) -> None:
        """ASSOCIATE cannot create accounts (403)."""
        client_id = await self._setup_client(db_session)
        response = await db_client.post(
            f"/api/v1/clients/{client_id}/accounts",
            json={
                "account_number": "9999",
                "account_name": "Forbidden",
                "account_type": "ASSET",
            },
            headers=associate_headers,
        )
        assert response.status_code == 403

    async def test_list_accounts_both_roles(
        self, db_session: AsyncSession, db_client: AsyncClient,
        cpa_owner_headers: dict, associate_headers: dict,
    ) -> None:
        """Both CPA_OWNER and ASSOCIATE can list accounts."""
        client_id = await self._setup_client(db_session)

        # Create an account first (as CPA_OWNER)
        await db_client.post(
            f"/api/v1/clients/{client_id}/accounts",
            json={"account_number": "1000", "account_name": "Cash", "account_type": "ASSET"},
            headers=cpa_owner_headers,
        )

        # CPA_OWNER can list
        resp_owner = await db_client.get(
            f"/api/v1/clients/{client_id}/accounts",
            headers=cpa_owner_headers,
        )
        assert resp_owner.status_code == 200
        assert resp_owner.json()["total"] == 1

        # ASSOCIATE can list too
        resp_assoc = await db_client.get(
            f"/api/v1/clients/{client_id}/accounts",
            headers=associate_headers,
        )
        assert resp_assoc.status_code == 200
        assert resp_assoc.json()["total"] == 1

    async def test_get_account_both_roles(
        self, db_session: AsyncSession, db_client: AsyncClient,
        cpa_owner_headers: dict, associate_headers: dict,
    ) -> None:
        """Both roles can get a single account by ID."""
        client_id = await self._setup_client(db_session)
        create_resp = await db_client.post(
            f"/api/v1/clients/{client_id}/accounts",
            json={"account_number": "1000", "account_name": "Cash", "account_type": "ASSET"},
            headers=cpa_owner_headers,
        )
        account_id = create_resp.json()["id"]

        for headers in [cpa_owner_headers, associate_headers]:
            resp = await db_client.get(
                f"/api/v1/clients/{client_id}/accounts/{account_id}",
                headers=headers,
            )
            assert resp.status_code == 200
            assert resp.json()["account_number"] == "1000"

    async def test_update_account_cpa_owner(
        self, db_session: AsyncSession, db_client: AsyncClient, cpa_owner_headers: dict
    ) -> None:
        """CPA_OWNER can update an account."""
        client_id = await self._setup_client(db_session)
        create_resp = await db_client.post(
            f"/api/v1/clients/{client_id}/accounts",
            json={"account_number": "1000", "account_name": "Old Name", "account_type": "ASSET"},
            headers=cpa_owner_headers,
        )
        account_id = create_resp.json()["id"]

        update_resp = await db_client.put(
            f"/api/v1/clients/{client_id}/accounts/{account_id}",
            json={"account_name": "New Name"},
            headers=cpa_owner_headers,
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["account_name"] == "New Name"

    async def test_update_account_associate_forbidden(
        self, db_session: AsyncSession, db_client: AsyncClient,
        cpa_owner_headers: dict, associate_headers: dict,
    ) -> None:
        """ASSOCIATE cannot update accounts (403)."""
        client_id = await self._setup_client(db_session)
        create_resp = await db_client.post(
            f"/api/v1/clients/{client_id}/accounts",
            json={"account_number": "1000", "account_name": "Cash", "account_type": "ASSET"},
            headers=cpa_owner_headers,
        )
        account_id = create_resp.json()["id"]

        update_resp = await db_client.put(
            f"/api/v1/clients/{client_id}/accounts/{account_id}",
            json={"account_name": "Hacked"},
            headers=associate_headers,
        )
        assert update_resp.status_code == 403

    async def test_delete_account_cpa_owner(
        self, db_session: AsyncSession, db_client: AsyncClient, cpa_owner_headers: dict
    ) -> None:
        """CPA_OWNER can soft-delete an account."""
        client_id = await self._setup_client(db_session)
        create_resp = await db_client.post(
            f"/api/v1/clients/{client_id}/accounts",
            json={"account_number": "1000", "account_name": "Cash", "account_type": "ASSET"},
            headers=cpa_owner_headers,
        )
        account_id = create_resp.json()["id"]

        delete_resp = await db_client.delete(
            f"/api/v1/clients/{client_id}/accounts/{account_id}",
            headers=cpa_owner_headers,
        )
        assert delete_resp.status_code == 200
        assert delete_resp.json()["is_active"] is False

        # Should no longer appear in list
        list_resp = await db_client.get(
            f"/api/v1/clients/{client_id}/accounts",
            headers=cpa_owner_headers,
        )
        assert list_resp.json()["total"] == 0

    async def test_delete_account_associate_forbidden(
        self, db_session: AsyncSession, db_client: AsyncClient,
        cpa_owner_headers: dict, associate_headers: dict,
    ) -> None:
        """ASSOCIATE cannot delete accounts (403)."""
        client_id = await self._setup_client(db_session)
        create_resp = await db_client.post(
            f"/api/v1/clients/{client_id}/accounts",
            json={"account_number": "1000", "account_name": "Cash", "account_type": "ASSET"},
            headers=cpa_owner_headers,
        )
        account_id = create_resp.json()["id"]

        delete_resp = await db_client.delete(
            f"/api/v1/clients/{client_id}/accounts/{account_id}",
            headers=associate_headers,
        )
        assert delete_resp.status_code == 403

    async def test_client_isolation_via_api(
        self, db_session: AsyncSession, db_client: AsyncClient, cpa_owner_headers: dict
    ) -> None:
        """
        CRITICAL COMPLIANCE TEST (rule #4):
        Client A's accounts must NEVER be returned when querying Client B.
        """
        client_a = await self._setup_client(db_session)
        client_b = await self._setup_client(db_session)

        # Create account for Client A
        create_resp = await db_client.post(
            f"/api/v1/clients/{client_a}/accounts",
            json={"account_number": "1000", "account_name": "Client A Cash", "account_type": "ASSET"},
            headers=cpa_owner_headers,
        )
        account_a_id = create_resp.json()["id"]

        # List Client B's accounts -- should be empty
        list_resp = await db_client.get(
            f"/api/v1/clients/{client_b}/accounts",
            headers=cpa_owner_headers,
        )
        assert list_resp.json()["total"] == 0

        # Try to get Client A's account using Client B's URL
        get_resp = await db_client.get(
            f"/api/v1/clients/{client_b}/accounts/{account_a_id}",
            headers=cpa_owner_headers,
        )
        assert get_resp.status_code == 404

        # Try to update Client A's account using Client B's URL
        update_resp = await db_client.put(
            f"/api/v1/clients/{client_b}/accounts/{account_a_id}",
            json={"account_name": "Stolen"},
            headers=cpa_owner_headers,
        )
        assert update_resp.status_code == 404

        # Try to delete Client A's account using Client B's URL
        delete_resp = await db_client.delete(
            f"/api/v1/clients/{client_b}/accounts/{account_a_id}",
            headers=cpa_owner_headers,
        )
        assert delete_resp.status_code == 404

    async def test_duplicate_account_number_rejected(
        self, db_session: AsyncSession, db_client: AsyncClient, cpa_owner_headers: dict
    ) -> None:
        """Creating a duplicate account_number for the same client returns 409."""
        client_id = await self._setup_client(db_session)
        payload = {"account_number": "1000", "account_name": "Cash", "account_type": "ASSET"}

        resp1 = await db_client.post(
            f"/api/v1/clients/{client_id}/accounts",
            json=payload,
            headers=cpa_owner_headers,
        )
        assert resp1.status_code == 201

        resp2 = await db_client.post(
            f"/api/v1/clients/{client_id}/accounts",
            json=payload,
            headers=cpa_owner_headers,
        )
        assert resp2.status_code == 409

    async def test_clone_template_accounts_via_api(
        self, db_session: AsyncSession, db_client: AsyncClient, cpa_owner_headers: dict
    ) -> None:
        """POST clone-template copies all template accounts to a new client."""
        client_id = await self._setup_client(db_session)

        # Count template accounts
        template_resp = await db_client.get(
            f"/api/v1/clients/{TEMPLATE_CLIENT_ID}/accounts",
            headers=cpa_owner_headers,
        )
        template_count = template_resp.json()["total"]
        assert template_count > 0

        clone_resp = await db_client.post(
            f"/api/v1/clients/{client_id}/accounts/clone-template",
            headers=cpa_owner_headers,
        )
        assert clone_resp.status_code == 201
        assert clone_resp.json()["total"] == template_count

    async def test_clone_template_associate_forbidden(
        self, db_session: AsyncSession, db_client: AsyncClient, associate_headers: dict
    ) -> None:
        """ASSOCIATE cannot clone template accounts (403)."""
        client_id = await _create_test_client(db_session)
        resp = await db_client.post(
            f"/api/v1/clients/{client_id}/accounts/clone-template",
            headers=associate_headers,
        )
        assert resp.status_code == 403

    async def test_get_nonexistent_account_returns_404(
        self, db_session: AsyncSession, db_client: AsyncClient, cpa_owner_headers: dict
    ) -> None:
        """Getting a non-existent account returns 404."""
        client_id = await self._setup_client(db_session)
        fake_id = uuid.uuid4()
        resp = await db_client.get(
            f"/api/v1/clients/{client_id}/accounts/{fake_id}",
            headers=cpa_owner_headers,
        )
        assert resp.status_code == 404

    async def test_list_accounts_type_filter_via_api(
        self, db_session: AsyncSession, db_client: AsyncClient, cpa_owner_headers: dict
    ) -> None:
        """List endpoint supports account_type query filter."""
        client_id = await self._setup_client(db_session)
        await db_client.post(
            f"/api/v1/clients/{client_id}/accounts",
            json={"account_number": "1000", "account_name": "Cash", "account_type": "ASSET"},
            headers=cpa_owner_headers,
        )
        await db_client.post(
            f"/api/v1/clients/{client_id}/accounts",
            json={"account_number": "4000", "account_name": "Revenue", "account_type": "REVENUE"},
            headers=cpa_owner_headers,
        )

        resp = await db_client.get(
            f"/api/v1/clients/{client_id}/accounts?account_type=ASSET",
            headers=cpa_owner_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["account_type"] == "ASSET"

    async def test_unauthenticated_request_rejected(
        self, db_session: AsyncSession, db_client: AsyncClient
    ) -> None:
        """Requests without auth token are rejected (401 or 403)."""
        client_id = await self._setup_client(db_session)
        resp = await db_client.get(f"/api/v1/clients/{client_id}/accounts")
        assert resp.status_code in (401, 403)
