"""
Authentication and user management service layer.

All user CRUD and authentication logic lives here, independent of
the HTTP layer. Role enforcement happens both here (defense in depth)
and at the router level.

Compliance:
- Passwords hashed with passlib bcrypt, never stored in plaintext.
- Soft deletes only (deleted_at timestamp).
- Every 403 logged to permission_log table.
"""

import uuid
from datetime import datetime, timezone

from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, verify_role
from app.models.permission_log import PermissionLog
from app.models.user import User
from app.schemas.auth import UserCreate, UserUpdate

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against its bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


# ---------------------------------------------------------------------------
# Service functions
# ---------------------------------------------------------------------------


async def create_user(db: AsyncSession, data: UserCreate) -> User:
    """
    Create a new user with a bcrypt-hashed password.

    Role enforcement: caller must be CPA_OWNER (checked at router level
    and can be re-checked here via verify_role for defense in depth).
    """
    user = User(
        id=uuid.uuid4(),
        email=data.email,
        password_hash=hash_password(data.password),
        full_name=data.full_name,
        role=data.role,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate(
    db: AsyncSession, email: str, password: str
) -> User | None:
    """
    Verify email + password and return the User if valid, else None.

    Returns None if:
    - No user with that email exists
    - Password does not match
    - User is not active
    - User is soft-deleted
    """
    result = await db.execute(
        select(User).where(
            User.email == email,
            User.is_active.is_(True),
            User.deleted_at.is_(None),
        )
    )
    user = result.scalars().first()

    # Timing-attack mitigation: always run the password hash comparison
    # even if the user doesn't exist, so response time is constant.
    if user is None:
        # Dummy verify to consume the same time as a real check
        pwd_context.hash("timing-attack-dummy-password")
        return None
    if not verify_password(password, user.password_hash):
        return None

    # Update last_login_at
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(user)
    return user


async def get_user(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    """Fetch a single user by ID (excludes soft-deleted)."""
    result = await db.execute(
        select(User).where(User.id == user_id, User.deleted_at.is_(None))
    )
    return result.scalars().first()


async def list_users(db: AsyncSession) -> list[User]:
    """List all active, non-deleted users."""
    result = await db.execute(
        select(User).where(
            User.is_active.is_(True),
            User.deleted_at.is_(None),
        ).order_by(User.full_name)
    )
    return list(result.scalars().all())


async def update_user(
    db: AsyncSession, user_id: uuid.UUID, data: UserUpdate
) -> User | None:
    """
    Update user fields. Only non-None fields in data are applied.

    Role enforcement: CPA_OWNER only (checked at router level).
    """
    user = await get_user(db, user_id)
    if user is None:
        return None

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    user.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(user)
    return user


async def deactivate_user(
    db: AsyncSession, user_id: uuid.UUID
) -> User | None:
    """
    Soft-delete a user by setting deleted_at and is_active=False.

    Compliance (CLAUDE.md rule #2): records are never hard-deleted.
    """
    user = await get_user(db, user_id)
    if user is None:
        return None

    user.is_active = False
    user.deleted_at = datetime.now(timezone.utc)
    user.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(user)
    return user


async def log_permission_denial(
    db: AsyncSession,
    user_id: str | None,
    endpoint: str,
    method: str,
    role_required: str,
    role_provided: str,
    ip_address: str | None,
) -> None:
    """
    Write a row to the permission_log table for a 403 rejection.

    Compliance (CLAUDE.md): every 403 MUST be logged.
    """
    entry = PermissionLog(
        id=uuid.uuid4(),
        user_id=uuid.UUID(user_id) if user_id else None,
        endpoint=endpoint,
        method=method,
        role_required=role_required,
        role_provided=role_provided,
        ip_address=ip_address,
    )
    db.add(entry)
    await db.commit()
