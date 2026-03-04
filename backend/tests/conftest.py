"""
Pytest fixtures for the Georgia CPA accounting system test suite.

Provides:
- Async test client (no real DB required for unit tests)
- Mock authenticated users (CPA_OWNER and ASSOCIATE)
- JWT token generators for both roles
- Override dependencies for testing without a live database

Usage in tests:
    async def test_something(client: AsyncClient, cpa_owner_headers: dict):
        response = await client.get("/health", headers=cpa_owner_headers)
        assert response.status_code == 200
"""

import uuid
from collections.abc import AsyncGenerator
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from app.auth.dependencies import CurrentUser, get_current_user
from app.auth.jwt import create_access_token
from app.database import get_db
from app.main import app


# ---------------------------------------------------------------------------
# Test user constants
# ---------------------------------------------------------------------------
CPA_OWNER_USER_ID = str(uuid.uuid4())
ASSOCIATE_USER_ID = str(uuid.uuid4())

CPA_OWNER_USER = CurrentUser(user_id=CPA_OWNER_USER_ID, role="CPA_OWNER")
ASSOCIATE_USER = CurrentUser(user_id=ASSOCIATE_USER_ID, role="ASSOCIATE")


# ---------------------------------------------------------------------------
# Mock database session (no real DB needed for skeleton tests)
# ---------------------------------------------------------------------------
class MockAsyncSession:
    """
    Minimal mock of an async SQLAlchemy session.

    Builder agents will replace this with a real test database session
    (e.g., using an in-memory SQLite or a test PostgreSQL instance)
    when database models and queries are implemented.
    """

    async def commit(self) -> None:
        pass

    async def rollback(self) -> None:
        pass

    async def close(self) -> None:
        pass

    async def execute(self, *args: Any, **kwargs: Any) -> None:
        pass

    async def flush(self) -> None:
        pass


async def override_get_db() -> AsyncGenerator[MockAsyncSession, None]:
    """Provide a mock DB session for tests that don't need a real database."""
    session = MockAsyncSession()
    try:
        yield session
    finally:
        await session.close()


# ---------------------------------------------------------------------------
# Apply dependency overrides
# ---------------------------------------------------------------------------
app.dependency_overrides[get_db] = override_get_db


# ---------------------------------------------------------------------------
# Async test client
# ---------------------------------------------------------------------------
@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """
    Provide an async HTTP test client for the FastAPI app.

    No real server is started; requests are handled in-process.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# JWT tokens for test users
# ---------------------------------------------------------------------------
@pytest.fixture
def cpa_owner_token() -> str:
    """Return a valid JWT for the CPA_OWNER test user."""
    return create_access_token(
        user_id=CPA_OWNER_USER_ID,
        role="CPA_OWNER",
    )


@pytest.fixture
def associate_token() -> str:
    """Return a valid JWT for the ASSOCIATE test user."""
    return create_access_token(
        user_id=ASSOCIATE_USER_ID,
        role="ASSOCIATE",
    )


# ---------------------------------------------------------------------------
# Auth headers (convenience fixtures)
# ---------------------------------------------------------------------------
@pytest.fixture
def cpa_owner_headers(cpa_owner_token: str) -> dict[str, str]:
    """Return Authorization headers for a CPA_OWNER user."""
    return {"Authorization": f"Bearer {cpa_owner_token}"}


@pytest.fixture
def associate_headers(associate_token: str) -> dict[str, str]:
    """Return Authorization headers for an ASSOCIATE user."""
    return {"Authorization": f"Bearer {associate_token}"}


# ---------------------------------------------------------------------------
# Dependency override helpers for role-specific tests
# ---------------------------------------------------------------------------
@pytest.fixture
def as_cpa_owner() -> None:
    """
    Override get_current_user to always return a CPA_OWNER user.

    Useful when you want to bypass token parsing entirely in tests.
    """

    async def _override() -> CurrentUser:
        return CPA_OWNER_USER

    app.dependency_overrides[get_current_user] = _override
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def as_associate() -> None:
    """
    Override get_current_user to always return an ASSOCIATE user.

    Useful when you want to bypass token parsing entirely in tests.
    """

    async def _override() -> CurrentUser:
        return ASSOCIATE_USER

    app.dependency_overrides[get_current_user] = _override
    yield
    app.dependency_overrides.pop(get_current_user, None)
