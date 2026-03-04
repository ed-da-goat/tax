"""
SQLAlchemy declarative base with common mixins.

Compliance note (CLAUDE.md rule #2 — AUDIT TRAIL):
    Records are NEVER deleted. All models that inherit SoftDeleteMixin
    use a `deleted_at` timestamp for soft deletes. Hard deletes are
    prohibited at the application level.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    declared_attr,
    mapped_column,
)


class Base(DeclarativeBase):
    """
    Declarative base for all ORM models.

    Every model gets a UUID primary key by default via `id`.
    """

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    @declared_attr.directive
    def __tablename__(cls) -> str:  # noqa: N805
        """Auto-generate table name from class name (snake_case)."""
        # Convert CamelCase to snake_case
        name = cls.__name__
        result: list[str] = []
        for i, char in enumerate(name):
            if char.isupper() and i > 0:
                result.append("_")
            result.append(char.lower())
        return "".join(result)


class TimestampMixin:
    """
    Mixin that adds created_at and updated_at columns.

    All tables in this system must include these fields
    per CLAUDE.md schema requirements.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class SoftDeleteMixin:
    """
    Mixin that adds soft-delete support via deleted_at.

    Compliance (CLAUDE.md rule #2):
        Records are NEVER hard-deleted. Setting deleted_at marks
        a record as logically removed. All queries against
        soft-deletable tables should filter `WHERE deleted_at IS NULL`
        unless explicitly requesting archived records.
    """

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
        nullable=True,
    )

    @property
    def is_deleted(self) -> bool:
        """Return True if this record has been soft-deleted."""
        return self.deleted_at is not None
