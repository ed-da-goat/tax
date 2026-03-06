"""
Tests for 2FA (TOTP) endpoints (C6).

Covers:
- POST /api/v1/auth/2fa/setup    — generate TOTP secret + QR code
- POST /api/v1/auth/2fa/verify   — verify code and activate 2FA
- POST /api/v1/auth/2fa/disable  — disable 2FA with valid code
- GET  /api/v1/auth/2fa/status   — check 2FA enabled status
- Error cases: already enabled, not set up, invalid code

Note: pyotp, qrcode, encrypt_value, decrypt_value are lazy-imported inside
the endpoint functions, so we patch them at their source modules rather than
at app.routers.auth.
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
CPA_OWNER_ID = uuid.uuid4()


def _override_as_cpa_owner():
    async def _dep():
        return CurrentUser(user_id=str(CPA_OWNER_ID), role="CPA_OWNER")
    return _dep


def _make_fake_user(
    user_id=None,
    totp_secret_encrypted=None,
    **overrides,
):
    user = MagicMock()
    user.id = user_id or CPA_OWNER_ID
    user.email = overrides.get("email", "owner@firm.com")
    user.full_name = overrides.get("full_name", "Test Owner")
    user.role = overrides.get("role", "CPA_OWNER")
    user.is_active = overrides.get("is_active", True)
    user.totp_secret_encrypted = totp_secret_encrypted
    user.password_hash = overrides.get("password_hash", "fakehash")
    user.last_login_at = None
    user.created_at = datetime.now(timezone.utc)
    user.updated_at = datetime.now(timezone.utc)
    user.deleted_at = None
    return user


# ---------------------------------------------------------------------------
# Tests: 2FA Setup
# ---------------------------------------------------------------------------


class TestSetup2FA:

    @patch("app.routers.auth.auth_service")
    async def test_setup_2fa_success(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            user = _make_fake_user(totp_secret_encrypted=None)
            mock_svc.get_user = AsyncMock(return_value=user)

            with patch("pyotp.random_base32", return_value="JBSWY3DPEHPK3PXP"), \
                 patch("pyotp.TOTP") as mock_totp_cls, \
                 patch("qrcode.make") as mock_qr_make, \
                 patch("app.crypto.encrypt_value", return_value="encrypted_secret"):

                mock_totp = MagicMock()
                mock_totp.provisioning_uri.return_value = "otpauth://totp/test"
                mock_totp_cls.return_value = mock_totp

                mock_qr_img = MagicMock()
                mock_qr_img.save = MagicMock(
                    side_effect=lambda buf, **kw: buf.write(b"PNG_DATA")
                )
                mock_qr_make.return_value = mock_qr_img

                response = await client.post("/api/v1/auth/2fa/setup")
                assert response.status_code == 200
                data = response.json()
                assert data["secret"] == "JBSWY3DPEHPK3PXP"
                assert data["qr_code"].startswith("data:image/png;base64,")
                assert "provisioning_uri" in data
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    @patch("app.routers.auth.auth_service")
    async def test_setup_2fa_already_enabled(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            user = _make_fake_user(totp_secret_encrypted="encrypted_secret_value")
            mock_svc.get_user = AsyncMock(return_value=user)

            response = await client.post("/api/v1/auth/2fa/setup")
            assert response.status_code == 400
            assert "already enabled" in response.json()["detail"]
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    @patch("app.routers.auth.auth_service")
    async def test_setup_2fa_user_not_found(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            mock_svc.get_user = AsyncMock(return_value=None)

            response = await client.post("/api/v1/auth/2fa/setup")
            assert response.status_code == 404
        finally:
            app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------------------------
# Tests: 2FA Verify (Activate)
# ---------------------------------------------------------------------------


class TestVerify2FA:

    @patch("app.routers.auth.auth_service")
    async def test_verify_2fa_success(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            user = _make_fake_user(totp_secret_encrypted="PENDING:encrypted_secret")
            mock_svc.get_user = AsyncMock(return_value=user)

            with patch("app.crypto.decrypt_value", return_value="JBSWY3DPEHPK3PXP"), \
                 patch("app.crypto.encrypt_value", return_value="final_encrypted"), \
                 patch("pyotp.TOTP") as mock_totp_cls:

                mock_totp = MagicMock()
                mock_totp.verify.return_value = True
                mock_totp_cls.return_value = mock_totp

                response = await client.post("/api/v1/auth/2fa/verify?code=123456")
                assert response.status_code == 200
                data = response.json()
                assert data["enabled"] is True
                assert "activated" in data["message"]
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    @patch("app.routers.auth.auth_service")
    async def test_verify_2fa_invalid_code(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            user = _make_fake_user(totp_secret_encrypted="PENDING:encrypted_secret")
            mock_svc.get_user = AsyncMock(return_value=user)

            with patch("app.crypto.decrypt_value", return_value="JBSWY3DPEHPK3PXP"), \
                 patch("pyotp.TOTP") as mock_totp_cls:

                mock_totp = MagicMock()
                mock_totp.verify.return_value = False
                mock_totp_cls.return_value = mock_totp

                response = await client.post("/api/v1/auth/2fa/verify?code=000000")
                assert response.status_code == 400
                assert "Invalid TOTP code" in response.json()["detail"]
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    @patch("app.routers.auth.auth_service")
    async def test_verify_2fa_no_pending_setup(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            user = _make_fake_user(totp_secret_encrypted=None)
            mock_svc.get_user = AsyncMock(return_value=user)

            response = await client.post("/api/v1/auth/2fa/verify?code=123456")
            assert response.status_code == 400
            assert "No pending 2FA setup" in response.json()["detail"]
        finally:
            app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------------------------
# Tests: 2FA Disable
# ---------------------------------------------------------------------------


class TestDisable2FA:

    @patch("app.routers.auth.auth_service")
    async def test_disable_2fa_success(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            user = _make_fake_user(totp_secret_encrypted="encrypted_secret")
            mock_svc.get_user = AsyncMock(return_value=user)

            with patch("app.crypto.decrypt_value", return_value="JBSWY3DPEHPK3PXP"), \
                 patch("pyotp.TOTP") as mock_totp_cls:

                mock_totp = MagicMock()
                mock_totp.verify.return_value = True
                mock_totp_cls.return_value = mock_totp

                response = await client.post("/api/v1/auth/2fa/disable?code=123456")
                assert response.status_code == 200
                data = response.json()
                assert data["enabled"] is False
                assert "disabled" in data["message"]
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    @patch("app.routers.auth.auth_service")
    async def test_disable_2fa_not_enabled(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            user = _make_fake_user(totp_secret_encrypted=None)
            mock_svc.get_user = AsyncMock(return_value=user)

            response = await client.post("/api/v1/auth/2fa/disable?code=123456")
            assert response.status_code == 400
            assert "not enabled" in response.json()["detail"]
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    @patch("app.routers.auth.auth_service")
    async def test_disable_2fa_invalid_code(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            user = _make_fake_user(totp_secret_encrypted="encrypted_secret")
            mock_svc.get_user = AsyncMock(return_value=user)

            with patch("app.crypto.decrypt_value", return_value="JBSWY3DPEHPK3PXP"), \
                 patch("pyotp.TOTP") as mock_totp_cls:

                mock_totp = MagicMock()
                mock_totp.verify.return_value = False
                mock_totp_cls.return_value = mock_totp

                response = await client.post("/api/v1/auth/2fa/disable?code=000000")
                assert response.status_code == 400
                assert "Invalid TOTP code" in response.json()["detail"]
        finally:
            app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------------------------
# Tests: 2FA Status
# ---------------------------------------------------------------------------


class TestGet2FAStatus:

    @patch("app.routers.auth.auth_service")
    async def test_2fa_status_enabled(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            user = _make_fake_user(totp_secret_encrypted="encrypted_secret")
            mock_svc.get_user = AsyncMock(return_value=user)

            response = await client.get("/api/v1/auth/2fa/status")
            assert response.status_code == 200
            assert response.json()["enabled"] is True
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    @patch("app.routers.auth.auth_service")
    async def test_2fa_status_disabled(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            user = _make_fake_user(totp_secret_encrypted=None)
            mock_svc.get_user = AsyncMock(return_value=user)

            response = await client.get("/api/v1/auth/2fa/status")
            assert response.status_code == 200
            assert response.json()["enabled"] is False
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    @patch("app.routers.auth.auth_service")
    async def test_2fa_status_pending_not_counted(self, mock_svc, client: AsyncClient):
        """PENDING setup should not count as enabled."""
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            user = _make_fake_user(totp_secret_encrypted="PENDING:encrypted")
            mock_svc.get_user = AsyncMock(return_value=user)

            response = await client.get("/api/v1/auth/2fa/status")
            assert response.status_code == 200
            assert response.json()["enabled"] is False
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    @patch("app.routers.auth.auth_service")
    async def test_2fa_status_user_not_found(self, mock_svc, client: AsyncClient):
        app.dependency_overrides[get_current_user] = _override_as_cpa_owner()
        try:
            mock_svc.get_user = AsyncMock(return_value=None)

            response = await client.get("/api/v1/auth/2fa/status")
            assert response.status_code == 404
        finally:
            app.dependency_overrides.pop(get_current_user, None)
