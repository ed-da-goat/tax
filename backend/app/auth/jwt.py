"""
JWT token creation and verification utilities.

Tokens encode: user_id, role, and expiration.
Algorithm and secret are configured in app.config.settings.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from app.config import settings


def create_access_token(
    user_id: str,
    role: str,
    extra_claims: dict[str, Any] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a signed JWT access token.

    Args:
        user_id: The UUID of the authenticated user (stored as 'sub').
        role: Either 'CPA_OWNER' or 'ASSOCIATE'.
        extra_claims: Optional additional claims to embed.
        expires_delta: Custom expiration. Defaults to
            settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES.

    Returns:
        Encoded JWT string.
    """
    now = datetime.now(timezone.utc)
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "iat": now,
        "exp": now + expires_delta,
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(
        payload,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )


def verify_token(token: str) -> dict[str, Any]:
    """
    Decode and verify a JWT token.

    Args:
        token: The raw JWT string from the Authorization header.

    Returns:
        The decoded payload dictionary containing at least
        'sub' (user_id) and 'role'.

    Raises:
        JWTError: If the token is expired, malformed, or has
            an invalid signature.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except JWTError:
        raise

    # Validate required claims are present
    if "sub" not in payload or "role" not in payload:
        raise JWTError("Token missing required claims: 'sub' and 'role'")

    return payload
