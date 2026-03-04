"""
SQLAlchemy ORM models package.

All models inherit from Base (defined in base.py) which provides:
- UUID primary key
- created_at, updated_at, deleted_at timestamps
- Soft-delete support (records are never hard-deleted per CLAUDE.md compliance rule #2)

Import models here so Alembic and other tools can discover them.
"""

from app.models.base import Base, SoftDeleteMixin, TimestampMixin
from app.models.client import Client, EntityType
from app.models.user import User
from app.models.permission_log import PermissionLog
from app.models.chart_of_accounts import ChartOfAccounts

__all__ = [
    "Base", "TimestampMixin", "SoftDeleteMixin",
    "Client", "EntityType",
    "User", "PermissionLog",
    "ChartOfAccounts",
]
