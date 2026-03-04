"""
Business logic for the Audit Trail Viewer (Module O1).

Compliance (CLAUDE.md rule #2 — AUDIT TRAIL):
    This service is STRICTLY READ-ONLY. There are no create, update,
    or delete methods. The audit_log table is immutable and written
    exclusively by PostgreSQL triggers.
"""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.schemas.audit_log import AuditLogFilters


class AuditLogService:
    """Read-only service for querying the audit trail."""

    @staticmethod
    async def list_entries(
        db: AsyncSession,
        filters: AuditLogFilters,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[AuditLog], int]:
        """
        List audit log entries with optional filters and pagination.

        Returns (entries, total_count).
        """
        base = select(AuditLog)

        if filters.table_name is not None:
            base = base.where(AuditLog.table_name == filters.table_name)
        if filters.record_id is not None:
            base = base.where(AuditLog.record_id == filters.record_id)
        if filters.user_id is not None:
            base = base.where(AuditLog.user_id == filters.user_id)
        if filters.action is not None:
            base = base.where(AuditLog.action == filters.action.value)
        if filters.date_from is not None:
            base = base.where(AuditLog.created_at >= filters.date_from)
        if filters.date_to is not None:
            base = base.where(AuditLog.created_at <= filters.date_to)

        # Total count
        count_stmt = select(func.count()).select_from(base.subquery())
        total_result = await db.execute(count_stmt)
        total = total_result.scalar_one()

        # Paginated results, newest first
        stmt = base.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(stmt)
        entries = list(result.scalars().all())

        return entries, total

    @staticmethod
    async def get_entry(
        db: AsyncSession,
        entry_id: UUID,
    ) -> AuditLog | None:
        """
        Retrieve a single audit log entry by ID.

        Returns None if not found.
        """
        stmt = select(AuditLog).where(AuditLog.id == entry_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_record_history(
        db: AsyncSession,
        table_name: str,
        record_id: UUID,
    ) -> list[AuditLog]:
        """
        Get the full audit history for a specific record.

        Returns all changes ordered by created_at ascending (oldest first),
        so the caller sees the chronological timeline of changes.
        """
        stmt = (
            select(AuditLog)
            .where(
                AuditLog.table_name == table_name,
                AuditLog.record_id == record_id,
            )
            .order_by(AuditLog.created_at.asc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())
