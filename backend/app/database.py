"""
SQLAlchemy async engine and session factory.

Provides the `get_db` dependency for FastAPI route injection.
All database access in the application flows through this module.
"""

from collections.abc import AsyncGenerator

from fastapi import Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings

# ---------------------------------------------------------------------------
# Async engine — used by the running application
# ---------------------------------------------------------------------------
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
)

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------
async def get_db(request: Request = None) -> AsyncGenerator[AsyncSession, None]:
    """
    Yield an async database session for a single request.

    Sets PostgreSQL session variables `app.current_user_id` and
    `app.current_ip` so the fn_audit_log() trigger can record
    who made the change.

    The session is automatically closed when the request completes.
    Callers should use `async with session.begin():` for transactions
    that need explicit commit/rollback control.
    """
    async with async_session_factory() as session:
        try:
            # Propagate audit context from middleware to PostgreSQL session.
            # SET commands don't support bind parameters in asyncpg, so we
            # use set_config() which is a regular SQL function.
            if request is not None:
                user_id = getattr(request.state, "audit_user_id", None)
                client_ip = getattr(request.state, "audit_client_ip", None)
                if user_id:
                    await session.execute(
                        text("SELECT set_config('app.current_user_id', :uid, true)"),
                        {"uid": str(user_id)},
                    )
                if client_ip and client_ip != "unknown":
                    await session.execute(
                        text("SELECT set_config('app.current_ip', :ip, true)"),
                        {"ip": str(client_ip)},
                    )
            yield session
        finally:
            await session.close()
