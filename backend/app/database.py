"""
SQLAlchemy async engine and session factory.

Provides the `get_db` dependency for FastAPI route injection.
All database access in the application flows through this module.
"""

from collections.abc import AsyncGenerator

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
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Yield an async database session for a single request.

    The session is automatically closed when the request completes.
    Callers should use `async with session.begin():` for transactions
    that need explicit commit/rollback control.
    """
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()
