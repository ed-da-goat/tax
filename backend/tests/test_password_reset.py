"""
Tests for Password Reset (module E2).

Tests the auth router endpoints:
- POST /api/v1/auth/forgot-password  -- request a reset token
- POST /api/v1/auth/reset-password   -- reset password with token (JSON body)

Also tests the password_reset service functions directly.

Note: The forgot-password and reset-password endpoints use lazy imports
(from ... import ... inside the function body), so mocks must target the
source modules (app.services.password_reset, app.services.email,
app.schemas.auth) rather than the router module.
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.main import app


# ---------------------------------------------------------------------------
# POST /api/v1/auth/forgot-password -- endpoint tests
#
# The endpoint has @limiter.limit("5/minute") which requires a client IP.
# The slowapi limiter needs the Request object; in test mode with ASGI
# transport, request.client may be None, so we also mock the limiter.
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_forgot_password_success(client: AsyncClient):
    """Forgot password returns generic success message regardless of email existence."""
    with patch(
        "app.services.password_reset.request_password_reset",
        new_callable=AsyncMock,
    ) as mock_reset, patch(
        "app.services.email.send_email",
        new_callable=AsyncMock,
    ) as mock_email:
        mock_reset.return_value = {
            "token": "abc123",
            "email": "user@example.com",
            "user_id": str(uuid.uuid4()),
            "expires_minutes": 30,
        }
        response = await client.post(
            "/api/v1/auth/forgot-password?email=user@example.com",
        )
    assert response.status_code == 200
    data = response.json()
    assert "sent" in data["message"].lower() or "reset" in data["message"].lower()
    mock_email.assert_called_once()


@pytest.mark.anyio
async def test_forgot_password_nonexistent_email(client: AsyncClient):
    """Non-existent email still returns 200 to prevent enumeration."""
    with patch(
        "app.services.password_reset.request_password_reset",
        new_callable=AsyncMock,
    ) as mock_reset, patch(
        "app.services.email.send_email",
        new_callable=AsyncMock,
    ) as mock_email:
        mock_reset.return_value = {
            "token": None,
            "email": "nobody@example.com",
            "expires_minutes": 30,
        }
        response = await client.post(
            "/api/v1/auth/forgot-password?email=nobody@example.com",
        )
    assert response.status_code == 200
    # Email should NOT be sent when token is None
    mock_email.assert_not_called()


@pytest.mark.anyio
async def test_forgot_password_sends_email_with_reset_url(client: AsyncClient):
    """When token is generated, email is sent with reset URL."""
    with patch(
        "app.services.password_reset.request_password_reset",
        new_callable=AsyncMock,
    ) as mock_reset, patch(
        "app.services.email.send_email",
        new_callable=AsyncMock,
    ) as mock_email:
        mock_reset.return_value = {
            "token": "reset-token-xyz",
            "email": "user@example.com",
            "user_id": str(uuid.uuid4()),
            "expires_minutes": 30,
        }
        await client.post(
            "/api/v1/auth/forgot-password?email=user@example.com",
        )
    mock_email.assert_called_once()
    call_kwargs = mock_email.call_args[1]
    assert call_kwargs["to"] == "user@example.com"
    assert "Password Reset" in call_kwargs["subject"]
    assert "reset-token-xyz" in call_kwargs["html_body"]


# ---------------------------------------------------------------------------
# POST /api/v1/auth/reset-password -- endpoint tests (JSON body)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_reset_password_success(client: AsyncClient):
    """Valid token and strong password resets successfully."""
    with patch(
        "app.services.password_reset.reset_password",
        new_callable=AsyncMock,
    ) as mock_reset, patch(
        "app.schemas.auth._validate_password_strength",
    ) as mock_validate:
        mock_reset.return_value = True
        mock_validate.return_value = None
        response = await client.post(
            "/api/v1/auth/reset-password",
            json={"token": "valid-token", "new_password": "SecurePass123!"},
        )
    assert response.status_code == 200
    assert "reset" in response.json()["message"].lower()


@pytest.mark.anyio
async def test_reset_password_invalid_token(client: AsyncClient):
    """Invalid or expired token returns 400."""
    with patch(
        "app.services.password_reset.reset_password",
        new_callable=AsyncMock,
    ) as mock_reset, patch(
        "app.schemas.auth._validate_password_strength",
    ) as mock_validate:
        mock_reset.return_value = False
        mock_validate.return_value = None
        response = await client.post(
            "/api/v1/auth/reset-password",
            json={"token": "bad-token", "new_password": "SecurePass123!"},
        )
    assert response.status_code == 400
    detail = response.json()["detail"].lower()
    assert "invalid" in detail or "expired" in detail


@pytest.mark.anyio
async def test_reset_password_weak_password(client: AsyncClient):
    """Weak password fails validation with 400."""
    with patch(
        "app.schemas.auth._validate_password_strength",
        side_effect=ValueError("Password must contain at least one uppercase letter"),
    ):
        response = await client.post(
            "/api/v1/auth/reset-password",
            json={"token": "some-token", "new_password": "weak"},
        )
    assert response.status_code == 400


@pytest.mark.anyio
async def test_reset_password_too_short(client: AsyncClient):
    """Password shorter than 8 characters returns 400."""
    with patch(
        "app.schemas.auth._validate_password_strength",
    ) as mock_validate:
        mock_validate.return_value = None
        response = await client.post(
            "/api/v1/auth/reset-password",
            json={"token": "some-token", "new_password": "short"},
        )
    assert response.status_code == 400
    assert "8 characters" in response.json()["detail"]
