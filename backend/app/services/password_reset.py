"""
Password reset service (E2).

Generates time-limited reset tokens and processes password resets.
Tokens are stored in the database (password_reset_tokens table) so they
survive process restarts.
"""

import hashlib
import secrets
import uuid
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.models.password_reset_token import PasswordResetToken
from app.services.auth import hash_password

TOKEN_EXPIRY_MINUTES = 30


def _hash_token(token: str) -> str:
    """Hash a reset token for safe DB storage (SHA-256)."""
    return hashlib.sha256(token.encode()).hexdigest()


async def _cleanup_expired(db: AsyncSession) -> None:
    """Delete expired tokens."""
    now = datetime.now(timezone.utc)
    await db.execute(
        delete(PasswordResetToken).where(PasswordResetToken.expires_at < now)
    )


async def create_reset_token(db: AsyncSession, user_id: uuid.UUID, email: str) -> str:
    """Generate a time-limited password reset token and store its hash in the DB."""
    await _cleanup_expired(db)

    token = secrets.token_urlsafe(32)
    row = PasswordResetToken(
        user_id=user_id,
        token_hash=_hash_token(token),
        email=email,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXPIRY_MINUTES),
    )
    db.add(row)
    await db.flush()
    return token


async def validate_reset_token(db: AsyncSession, token: str) -> PasswordResetToken | None:
    """Validate a reset token. Returns the DB row or None if invalid/expired/used."""
    token_hash = _hash_token(token)
    result = await db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at >= datetime.now(timezone.utc),
        )
    )
    return result.scalar_one_or_none()


async def consume_reset_token(db: AsyncSession, token: str) -> PasswordResetToken | None:
    """Validate and consume (mark used) a reset token."""
    row = await validate_reset_token(db, token)
    if row:
        row.used_at = datetime.now(timezone.utc)
        await db.flush()
    return row


async def request_password_reset(db: AsyncSession, email: str) -> dict:
    """
    Generate a password reset token for the given email.
    Returns token info (to be sent via email).
    Always returns success to prevent email enumeration.
    """
    result = await db.execute(
        select(User).where(User.email == email, User.is_active.is_(True), User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()

    if user:
        token = await create_reset_token(db, user.id, user.email)
        return {
            "token": token,
            "email": email,
            "user_id": str(user.id),
            "expires_minutes": TOKEN_EXPIRY_MINUTES,
        }

    # Return a dummy response to prevent enumeration
    return {"token": None, "email": email, "expires_minutes": TOKEN_EXPIRY_MINUTES}


async def reset_password(db: AsyncSession, token: str, new_password: str) -> bool:
    """Reset a user's password using a valid token."""
    row = await consume_reset_token(db, token)
    if not row:
        return False

    result = await db.execute(
        select(User).where(User.id == row.user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        return False

    user.password_hash = hash_password(new_password)
    await db.flush()
    return True
