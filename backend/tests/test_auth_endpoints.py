"""
Tests for authentication and user management endpoints (module F5).

Tests cover:
- Login with valid/invalid credentials
- User creation by CPA_OWNER succeeds
- User creation by ASSOCIATE returns 403
- GET /me returns current user info
- ASSOCIATE cannot list/update/deactivate users
- permission_log gets written on 403
- Deactivated user cannot login

All tests use mock DB and patched service functions to avoid
requiring a live PostgreSQL instance.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.auth.dependencies import CurrentUser, get_current_user
from app.auth.jwt import create_access_token
from app.main import app


# ---------------------------------------------------------------------------
# Helpers — fake User objects that look like SQLAlchemy model instances
# ---------------------------------------------------------------------------

def _make_fake_user(
    user_id: uuid.UUID | None = None,
    email: str = "owner@firm.com",
    full_name: str = "Test Owner",
    role: str = "CPA_OWNER",
    is_active: bool = True,
    last_login_at: datetime | None = None,
) -> MagicMock:
    """Create a mock User ORM object for testing."""
    user = MagicMock()
    user.id = user_id or uuid.uuid4()
    user.email = email
    user.full_name = full_name
    user.role = role
    user.is_active = is_active
    user.last_login_at = last_login_at
    user.created_at = datetime.now(timezone.utc)
    user.updated_at = datetime.now(timezone.utc)
    user.deleted_at = None
    user.password_hash = "fakehash"
    return user


CPA_OWNER_ID = uuid.uuid4()
ASSOCIATE_ID = uuid.uuid4()

FAKE_CPA_OWNER = _make_fake_user(
    user_id=CPA_OWNER_ID, email="owner@firm.com", role="CPA_OWNER"
)
FAKE_ASSOCIATE = _make_fake_user(
    user_id=ASSOCIATE_ID, email="associate@firm.com",
    full_name="Test Associate", role="ASSOCIATE",
)


# ---------------------------------------------------------------------------
# Dependency overrides for role-based tests
# ---------------------------------------------------------------------------

def _override_as_cpa_owner():
    async def _dep():
        return CurrentUser(user_id=str(CPA_OWNER_ID), role="CPA_OWNER")
    return _dep


def _override_as_associate():
    async def _dep():
        return CurrentUser(user_id=str(ASSOCIATE_ID), role="ASSOCIATE")
    return _dep


# ---------------------------------------------------------------------------
# Test: POST /api/v1/auth/login
# ---------------------------------------------------------------------------


class TestLogin:
    """Tests for the login endpoint."""

    @patch("app.routers.auth.auth_service")
    async def test_login_valid_credentials(
        self, mock_svc: MagicMock, client: AsyncClient
    ) -> None:
        """Successful login returns a JWT and user data."""
        mock_svc.authenticate = AsyncMock(return_value=FAKE_CPA_OWNER)

        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "owner@firm.com", "password": "securepass1"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "owner@firm.com"
        assert data["user"]["role"] == "CPA_OWNER"

    @patch("app.routers.auth.auth_service")
    async def test_login_invalid_credentials(
        self, mock_svc: MagicMock, client: AsyncClient
    ) -> None:
        """Invalid credentials return 401."""
        mock_svc.authenticate = AsyncMock(return_value=None)

        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "bad@firm.com", "password": "wrongpass1"},
        )
        assert response.status_code == 401
        assert "Invalid email or password" in response.json()["detail"]

    @patch("app.routers.auth.auth_service")
    async def test_login_deactivated_user(
        self, mock_svc: MagicMock, client: AsyncClient
    ) -> None:
        """Deactivated user cannot login (authenticate returns None)."""
        mock_svc.authenticate = AsyncMock(return_value=None)

        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "deactivated@firm.com", "password": "securepass1"},
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Test: POST /api/v1/auth/users (CPA_OWNER only)
# ---------------------------------------------------------------------------


class TestCreateUser:
    """Tests for user creation endpoint."""

    @patch("app.routers.auth.auth_service")
    async def test_cpa_owner_can_create_user(
        self, mock_svc: MagicMock, client: AsyncClient
    ) -> None:
        """CPA_OWNER can create a new user."""
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            new_user = _make_fake_user(
                email="newuser@firm.com",
                full_name="New User",
                role="ASSOCIATE",
            )
            mock_svc.create_user = AsyncMock(return_value=new_user)

            response = await client.post(
                "/api/v1/auth/users",
                json={
                    "email": "newuser@firm.com",
                    "password": "Secure1!pass",
                    "full_name": "New User",
                    "role": "ASSOCIATE",
                },
            )
            assert response.status_code == 201
            data = response.json()
            assert data["email"] == "newuser@firm.com"
            assert data["role"] == "ASSOCIATE"
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    @patch("app.routers.auth.auth_service")
    async def test_associate_cannot_create_user(
        self, mock_svc: MagicMock, client: AsyncClient
    ) -> None:
        """ASSOCIATE gets 403 when trying to create a user."""
        app.dependency_overrides[get_current_user] = _override_as_associate()
        try:
            mock_svc.log_permission_denial = AsyncMock()

            response = await client.post(
                "/api/v1/auth/users",
                json={
                    "email": "shouldfail@firm.com",
                    "password": "Secure1!pass",
                    "full_name": "Should Fail",
                    "role": "ASSOCIATE",
                },
            )
            assert response.status_code == 403
            detail = response.json()["detail"]
            assert detail["error"] == "Insufficient permissions"
            assert detail["required_role"] == "CPA_OWNER"
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    @patch("app.routers.auth.auth_service")
    async def test_permission_log_written_on_403(
        self, mock_svc: MagicMock, client: AsyncClient
    ) -> None:
        """403 rejection writes to permission_log via log_permission_denial."""
        app.dependency_overrides[get_current_user] = _override_as_associate()
        try:
            mock_svc.log_permission_denial = AsyncMock()

            await client.post(
                "/api/v1/auth/users",
                json={
                    "email": "shouldfail@firm.com",
                    "password": "Secure1!pass",
                    "full_name": "Should Fail",
                    "role": "ASSOCIATE",
                },
            )

            # Verify log_permission_denial was called
            mock_svc.log_permission_denial.assert_called_once()
            call_kwargs = mock_svc.log_permission_denial.call_args
            # Check key arguments
            assert call_kwargs.kwargs["role_required"] == "CPA_OWNER"
            assert call_kwargs.kwargs["role_provided"] == "ASSOCIATE"
            assert call_kwargs.kwargs["user_id"] == str(ASSOCIATE_ID)
            assert call_kwargs.kwargs["endpoint"] == "/api/v1/auth/users"
            assert call_kwargs.kwargs["method"] == "POST"
        finally:
            app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------------------------
# Test: GET /api/v1/auth/me
# ---------------------------------------------------------------------------


class TestGetMe:
    """Tests for the /me endpoint."""

    @patch("app.routers.auth.auth_service")
    async def test_me_returns_current_user(
        self, mock_svc: MagicMock, client: AsyncClient
    ) -> None:
        """GET /me returns the authenticated user's profile."""
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            mock_svc.get_user = AsyncMock(return_value=FAKE_CPA_OWNER)

            response = await client.get("/api/v1/auth/me")
            assert response.status_code == 200
            data = response.json()
            assert data["email"] == "owner@firm.com"
            assert data["role"] == "CPA_OWNER"
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    @patch("app.routers.auth.auth_service")
    async def test_me_associate(
        self, mock_svc: MagicMock, client: AsyncClient
    ) -> None:
        """GET /me works for ASSOCIATE users too (no role restriction)."""
        app.dependency_overrides[get_current_user] = _override_as_associate()
        try:
            mock_svc.get_user = AsyncMock(return_value=FAKE_ASSOCIATE)

            response = await client.get("/api/v1/auth/me")
            assert response.status_code == 200
            data = response.json()
            assert data["email"] == "associate@firm.com"
            assert data["role"] == "ASSOCIATE"
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    async def test_me_unauthenticated(self, client: AsyncClient) -> None:
        """GET /me without a token returns 401 or 403."""
        # Remove any overrides to test unauthenticated access
        app.dependency_overrides.pop(get_current_user, None)
        response = await client.get("/api/v1/auth/me")
        assert response.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Test: GET /api/v1/auth/users (CPA_OWNER only)
# ---------------------------------------------------------------------------


class TestListUsers:
    """Tests for user listing endpoint."""

    @patch("app.routers.auth.auth_service")
    async def test_cpa_owner_can_list_users(
        self, mock_svc: MagicMock, client: AsyncClient
    ) -> None:
        """CPA_OWNER can list all users."""
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            mock_svc.list_users = AsyncMock(
                return_value=[FAKE_CPA_OWNER, FAKE_ASSOCIATE]
            )

            response = await client.get("/api/v1/auth/users")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    @patch("app.routers.auth.auth_service")
    async def test_associate_cannot_list_users(
        self, mock_svc: MagicMock, client: AsyncClient
    ) -> None:
        """ASSOCIATE gets 403 when trying to list users."""
        app.dependency_overrides[get_current_user] = _override_as_associate()
        try:
            mock_svc.log_permission_denial = AsyncMock()

            response = await client.get("/api/v1/auth/users")
            assert response.status_code == 403
            detail = response.json()["detail"]
            assert detail["error"] == "Insufficient permissions"
            assert detail["required_role"] == "CPA_OWNER"
        finally:
            app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------------------------
# Test: PUT /api/v1/auth/users/{id} (CPA_OWNER only)
# ---------------------------------------------------------------------------


class TestUpdateUser:
    """Tests for user update endpoint."""

    @patch("app.routers.auth.auth_service")
    async def test_cpa_owner_can_update_user(
        self, mock_svc: MagicMock, client: AsyncClient
    ) -> None:
        """CPA_OWNER can update a user."""
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            updated_user = _make_fake_user(
                user_id=ASSOCIATE_ID,
                email="updated@firm.com",
                full_name="Updated Name",
                role="ASSOCIATE",
            )
            mock_svc.update_user = AsyncMock(return_value=updated_user)

            response = await client.put(
                f"/api/v1/auth/users/{ASSOCIATE_ID}",
                json={"full_name": "Updated Name"},
            )
            assert response.status_code == 200
            assert response.json()["full_name"] == "Updated Name"
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    @patch("app.routers.auth.auth_service")
    async def test_associate_cannot_update_user(
        self, mock_svc: MagicMock, client: AsyncClient
    ) -> None:
        """ASSOCIATE gets 403 when trying to update a user."""
        app.dependency_overrides[get_current_user] = _override_as_associate()
        try:
            mock_svc.log_permission_denial = AsyncMock()

            response = await client.put(
                f"/api/v1/auth/users/{CPA_OWNER_ID}",
                json={"full_name": "Hacked Name"},
            )
            assert response.status_code == 403
        finally:
            app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------------------------
# Test: DELETE /api/v1/auth/users/{id} (CPA_OWNER only)
# ---------------------------------------------------------------------------


class TestDeactivateUser:
    """Tests for user deactivation (soft-delete) endpoint."""

    @patch("app.routers.auth.auth_service")
    async def test_cpa_owner_can_deactivate_user(
        self, mock_svc: MagicMock, client: AsyncClient
    ) -> None:
        """CPA_OWNER can deactivate a user (soft-delete)."""
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            deactivated = _make_fake_user(
                user_id=ASSOCIATE_ID,
                email="associate@firm.com",
                full_name="Test Associate",
                role="ASSOCIATE",
                is_active=False,
            )
            deactivated.deleted_at = datetime.now(timezone.utc)
            mock_svc.deactivate_user = AsyncMock(return_value=deactivated)

            response = await client.delete(
                f"/api/v1/auth/users/{ASSOCIATE_ID}"
            )
            assert response.status_code == 200
            data = response.json()
            assert data["is_active"] is False
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    @patch("app.routers.auth.auth_service")
    async def test_associate_cannot_deactivate_user(
        self, mock_svc: MagicMock, client: AsyncClient
    ) -> None:
        """ASSOCIATE gets 403 when trying to deactivate a user."""
        app.dependency_overrides[get_current_user] = _override_as_associate()
        try:
            mock_svc.log_permission_denial = AsyncMock()

            response = await client.delete(
                f"/api/v1/auth/users/{CPA_OWNER_ID}"
            )
            assert response.status_code == 403
        finally:
            app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------------------------
# Test: Permission log is written on all 403 endpoints
# ---------------------------------------------------------------------------


class TestPermissionLogOnAllEndpoints:
    """Verify that 403 rejections log to permission_log for every protected endpoint."""

    @patch("app.routers.auth.auth_service")
    async def test_403_on_list_users_logs_denial(
        self, mock_svc: MagicMock, client: AsyncClient
    ) -> None:
        """GET /users by ASSOCIATE logs the denial."""
        app.dependency_overrides[get_current_user] = _override_as_associate()
        try:
            mock_svc.log_permission_denial = AsyncMock()

            await client.get("/api/v1/auth/users")

            mock_svc.log_permission_denial.assert_called_once()
            call_kwargs = mock_svc.log_permission_denial.call_args
            assert call_kwargs.kwargs["method"] == "GET"
            assert call_kwargs.kwargs["endpoint"] == "/api/v1/auth/users"
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    @patch("app.routers.auth.auth_service")
    async def test_403_on_update_user_logs_denial(
        self, mock_svc: MagicMock, client: AsyncClient
    ) -> None:
        """PUT /users/{id} by ASSOCIATE logs the denial."""
        app.dependency_overrides[get_current_user] = _override_as_associate()
        try:
            mock_svc.log_permission_denial = AsyncMock()

            await client.put(
                f"/api/v1/auth/users/{CPA_OWNER_ID}",
                json={"full_name": "Hacked"},
            )

            mock_svc.log_permission_denial.assert_called_once()
            call_kwargs = mock_svc.log_permission_denial.call_args
            assert call_kwargs.kwargs["method"] == "PUT"
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    @patch("app.routers.auth.auth_service")
    async def test_403_on_delete_user_logs_denial(
        self, mock_svc: MagicMock, client: AsyncClient
    ) -> None:
        """DELETE /users/{id} by ASSOCIATE logs the denial."""
        app.dependency_overrides[get_current_user] = _override_as_associate()
        try:
            mock_svc.log_permission_denial = AsyncMock()

            await client.delete(f"/api/v1/auth/users/{CPA_OWNER_ID}")

            mock_svc.log_permission_denial.assert_called_once()
            call_kwargs = mock_svc.log_permission_denial.call_args
            assert call_kwargs.kwargs["method"] == "DELETE"
        finally:
            app.dependency_overrides.pop(get_current_user, None)
