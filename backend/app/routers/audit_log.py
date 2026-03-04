"""
Audit Trail Viewer API endpoints (Module O1).

Endpoints (ALL READ-ONLY):
    GET /api/v1/audit-log                              — List with filters (both roles)
    GET /api/v1/audit-log/{id}                         — Single entry (both roles)
    GET /api/v1/audit-log/record/{table_name}/{record_id} — Record history (both roles)

Compliance (CLAUDE.md rule #2 — AUDIT TRAIL):
    The audit log is IMMUTABLE. There are NO POST, PUT, or DELETE endpoints.
    Both CPA_OWNER and ASSOCIATE roles may read the audit trail.
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, get_current_user
from app.database import get_db
from app.schemas.audit_log import (
    AuditAction,
    AuditLogEntry,
    AuditLogFilters,
    AuditLogList,
)
from app.services.audit_log import AuditLogService

router = APIRouter()


@router.get("", response_model=AuditLogList)
async def list_audit_log(
    table_name: str | None = Query(None),
    record_id: UUID | None = Query(None),
    user_id: UUID | None = Query(None),
    action: AuditAction | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> AuditLogList:
    """List audit log entries with optional filters. Both roles."""
    filters = AuditLogFilters(
        table_name=table_name,
        record_id=record_id,
        user_id=user_id,
        action=action,
        date_from=date_from,
        date_to=date_to,
    )
    entries, total = await AuditLogService.list_entries(
        db, filters=filters, skip=skip, limit=limit
    )
    return AuditLogList(
        items=[AuditLogEntry.model_validate(e) for e in entries],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/record/{table_name}/{record_id}", response_model=list[AuditLogEntry])
async def get_record_history(
    table_name: str,
    record_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> list[AuditLogEntry]:
    """
    Get the full audit history for a specific record.

    Returns all changes ordered chronologically (oldest first).
    Both roles may call this.
    """
    entries = await AuditLogService.get_record_history(db, table_name, record_id)
    return [AuditLogEntry.model_validate(e) for e in entries]


@router.get("/{entry_id}", response_model=AuditLogEntry)
async def get_audit_log_entry(
    entry_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> AuditLogEntry:
    """Get a single audit log entry by ID. Both roles."""
    entry = await AuditLogService.get_entry(db, entry_id)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit log entry not found",
        )
    return AuditLogEntry.model_validate(entry)
