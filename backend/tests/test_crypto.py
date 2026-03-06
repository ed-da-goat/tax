"""
Tests for security hardening: Fernet encryption, token blacklist, and logout.
"""

import time
import uuid
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# Fernet encryption tests
# ---------------------------------------------------------------------------


class TestEncryptPII:
    """Test the encrypt_pii / decrypt_pii round-trip."""

    def test_round_trip(self):
        from app.crypto import decrypt_pii, encrypt_pii

        ssn = "123-45-6789"
        encrypted = encrypt_pii(ssn)
        assert encrypted is not None
        assert encrypted != ssn.encode("utf-8")  # Must differ from plaintext
        assert decrypt_pii(encrypted) == ssn

    def test_none_input(self):
        from app.crypto import decrypt_pii, encrypt_pii

        assert encrypt_pii(None) is None
        assert decrypt_pii(None) is None

    def test_empty_string(self):
        from app.crypto import decrypt_pii, encrypt_pii

        assert encrypt_pii("") is None
        assert decrypt_pii(b"") is None

    def test_encrypted_differs_from_plaintext(self):
        from app.crypto import encrypt_pii

        plaintext = "987654321"
        encrypted = encrypt_pii(plaintext)
        assert encrypted != plaintext.encode("utf-8")

    def test_different_encryptions_differ(self):
        """Fernet tokens include a timestamp, so two encryptions of the same value differ."""
        from app.crypto import encrypt_pii

        a = encrypt_pii("same-value")
        b = encrypt_pii("same-value")
        assert a != b  # Fernet is non-deterministic

    def test_decrypt_invalid_token(self):
        from app.crypto import decrypt_pii

        result = decrypt_pii(b"not-a-valid-fernet-token")
        assert result is None  # Should gracefully return None


# ---------------------------------------------------------------------------
# Token blacklist tests
# ---------------------------------------------------------------------------


class TestTokenBlacklist:
    """Test the in-memory JWT blacklist."""

    def test_revoke_and_check(self):
        from app.auth.blacklist import TokenBlacklist

        bl = TokenBlacklist()
        jti = str(uuid.uuid4())
        assert not bl.is_revoked(jti)
        bl.revoke(jti, time.time() + 3600)
        assert bl.is_revoked(jti)

    def test_unknown_jti_not_revoked(self):
        from app.auth.blacklist import TokenBlacklist

        bl = TokenBlacklist()
        assert not bl.is_revoked("nonexistent-jti")

    def test_cleanup_removes_expired(self):
        from app.auth.blacklist import TokenBlacklist

        bl = TokenBlacklist()
        expired_jti = str(uuid.uuid4())
        active_jti = str(uuid.uuid4())

        bl.revoke(expired_jti, time.time() - 10)  # Already expired
        bl.revoke(active_jti, time.time() + 3600)  # Still active

        removed = bl.cleanup()
        assert removed == 1
        assert not bl.is_revoked(expired_jti)
        assert bl.is_revoked(active_jti)

    def test_len(self):
        from app.auth.blacklist import TokenBlacklist

        bl = TokenBlacklist()
        assert len(bl) == 0
        bl.revoke("a", time.time() + 100)
        bl.revoke("b", time.time() + 100)
        assert len(bl) == 2


# ---------------------------------------------------------------------------
# JWT jti claim tests
# ---------------------------------------------------------------------------


class TestJWTJti:
    """Test that JWT tokens now include a jti claim."""

    def test_token_has_jti(self):
        from app.auth.jwt import create_access_token, verify_token

        token = create_access_token(user_id=str(uuid.uuid4()), role="CPA_OWNER")
        payload = verify_token(token)
        assert "jti" in payload
        # jti should be a valid UUID
        uuid.UUID(payload["jti"])

    def test_different_tokens_have_different_jti(self):
        from app.auth.jwt import create_access_token, verify_token

        uid = str(uuid.uuid4())
        t1 = create_access_token(user_id=uid, role="CPA_OWNER")
        t2 = create_access_token(user_id=uid, role="CPA_OWNER")
        p1 = verify_token(t1)
        p2 = verify_token(t2)
        assert p1["jti"] != p2["jti"]


# ---------------------------------------------------------------------------
# Logout + blacklist integration tests
# ---------------------------------------------------------------------------


class TestLogoutIntegration:
    """Test that a revoked token is rejected by get_current_user."""

    @pytest.mark.anyio
    async def test_revoked_token_rejected(self):
        from unittest.mock import AsyncMock, MagicMock

        from fastapi import HTTPException

        from app.auth.blacklist import TokenBlacklist
        from app.auth.dependencies import get_current_user
        from app.auth.jwt import create_access_token, verify_token

        # Create a fresh blacklist for isolation
        test_bl = TokenBlacklist()

        uid = str(uuid.uuid4())
        token = create_access_token(user_id=uid, role="CPA_OWNER")
        payload = verify_token(token)

        # Revoke the token
        test_bl.revoke(payload["jti"], payload["exp"])

        # Patch the blacklist singleton
        creds = MagicMock()
        creds.credentials = token

        # Mock request with no cookies (forces fallback to credentials)
        mock_request = MagicMock()
        mock_request.cookies = {}

        with patch("app.auth.dependencies.blacklist", test_bl):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(request=mock_request, credentials=creds)
            assert exc_info.value.status_code == 401
            assert "revoked" in exc_info.value.detail.lower()
