"""
Tests for JWT token creation/verification and role-based access control.

Compliance tests (CLAUDE.md):
- 403 response format: {"error": "Insufficient permissions", "required_role": "<role>"}
- require_role works at function level, not just route level
- Both CPA_OWNER and ASSOCIATE tokens are correctly validated
"""

import pytest
from jose import JWTError

from app.auth.dependencies import CurrentUser, require_role, verify_role
from app.auth.jwt import create_access_token, verify_token
from fastapi import HTTPException


class TestJWTTokens:
    """Tests for JWT creation and verification."""

    def test_create_and_verify_cpa_owner_token(self) -> None:
        """CPA_OWNER token should round-trip through create/verify."""
        token = create_access_token(user_id="user-123", role="CPA_OWNER")
        payload = verify_token(token)
        assert payload["sub"] == "user-123"
        assert payload["role"] == "CPA_OWNER"

    def test_create_and_verify_associate_token(self) -> None:
        """ASSOCIATE token should round-trip through create/verify."""
        token = create_access_token(user_id="user-456", role="ASSOCIATE")
        payload = verify_token(token)
        assert payload["sub"] == "user-456"
        assert payload["role"] == "ASSOCIATE"

    def test_invalid_token_raises_error(self) -> None:
        """An invalid token string should raise JWTError."""
        with pytest.raises(JWTError):
            verify_token("this.is.not.a.valid.token")

    def test_token_contains_expiration(self) -> None:
        """Every token should have an expiration claim."""
        token = create_access_token(user_id="user-789", role="CPA_OWNER")
        payload = verify_token(token)
        assert "exp" in payload

    def test_token_contains_issued_at(self) -> None:
        """Every token should have an issued-at claim."""
        token = create_access_token(user_id="user-789", role="CPA_OWNER")
        payload = verify_token(token)
        assert "iat" in payload


class TestCurrentUser:
    """Tests for the CurrentUser dataclass."""

    def test_cpa_owner_properties(self) -> None:
        user = CurrentUser(user_id="u1", role="CPA_OWNER")
        assert user.is_cpa_owner is True
        assert user.is_associate is False

    def test_associate_properties(self) -> None:
        user = CurrentUser(user_id="u2", role="ASSOCIATE")
        assert user.is_cpa_owner is False
        assert user.is_associate is True


class TestVerifyRole:
    """Tests for the function-level role check (defense in depth)."""

    def test_verify_role_passes_for_matching_role(self) -> None:
        """verify_role should not raise when the role matches."""
        user = CurrentUser(user_id="u1", role="CPA_OWNER")
        # Should not raise
        verify_role(user, "CPA_OWNER")

    def test_verify_role_raises_403_for_wrong_role(self) -> None:
        """
        verify_role should raise HTTP 403 with the required format
        when the user has the wrong role.

        Compliance: {"error": "Insufficient permissions", "required_role": "<role>"}
        """
        user = CurrentUser(user_id="u2", role="ASSOCIATE")
        with pytest.raises(HTTPException) as exc_info:
            verify_role(user, "CPA_OWNER")

        assert exc_info.value.status_code == 403
        detail = exc_info.value.detail
        assert detail["error"] == "Insufficient permissions"
        assert detail["required_role"] == "CPA_OWNER"

    def test_associate_cannot_access_cpa_owner_function(self) -> None:
        """
        An ASSOCIATE user must be rejected at the function level
        even if they somehow bypass route-level checks.

        This is the defense-in-depth requirement from CLAUDE.md rule #6.
        """
        associate = CurrentUser(user_id="u3", role="ASSOCIATE")
        with pytest.raises(HTTPException) as exc_info:
            verify_role(associate, "CPA_OWNER")
        assert exc_info.value.status_code == 403
