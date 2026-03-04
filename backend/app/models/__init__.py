"""
SQLAlchemy ORM models package.

All models inherit from Base (defined in base.py) which provides:
- UUID primary key
- created_at, updated_at, deleted_at timestamps
- Soft-delete support (records are never hard-deleted per CLAUDE.md compliance rule #2)

Import models here so Alembic and other tools can discover them.
"""

from app.models.base import Base, SoftDeleteMixin, TimestampMixin

__all__ = ["Base", "TimestampMixin", "SoftDeleteMixin"]
