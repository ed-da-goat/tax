"""
API router for operations (modules O2-O4).

O2: Backup management (create, list, get)
O3: Backup restore (CPA_OWNER only)
O4: System health check

Compliance (CLAUDE.md):
- Backup restore: CPA_OWNER only (per CLAUDE.md role permissions).
- Defense in depth: verify_role at function level for destructive ops.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, get_current_user, require_role, verify_role
from app.database import get_db
from app.schemas import MessageResponse
from app.services.operations import (
    BackupService,
    HealthCheckService,
    RestoreService,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# O2 — Backup
# ---------------------------------------------------------------------------


@router.post(
    "/backup",
    summary="Create a database backup",
    status_code=status.HTTP_201_CREATED,
)
async def create_backup(
    user: CurrentUser = Depends(require_role("CPA_OWNER")),
):
    """Create a new database backup. CPA_OWNER only."""
    verify_role(user, "CPA_OWNER")
    result = BackupService.create_backup()
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Backup failed: {result.error}",
        )
    return {
        "message": "Backup created successfully",
        "filename": result.filename,
        "filepath": result.filepath,
        "size_bytes": result.size_bytes,
    }


@router.get(
    "/backups",
    summary="List all backups",
)
async def list_backups(
    user: CurrentUser = Depends(get_current_user),
):
    """List all available database backups. Both roles allowed."""
    backups = BackupService.list_backups()
    return {
        "total": len(backups),
        "backups": [
            {
                "filename": b.filename,
                "size_bytes": b.size_bytes,
                "created_at": b.created_at,
            }
            for b in backups
        ],
    }


@router.get(
    "/backups/{filename}",
    summary="Get backup details",
)
async def get_backup(
    filename: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Get details about a specific backup. Both roles allowed."""
    backup = BackupService.get_backup(filename)
    if backup is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backup not found",
        )
    return {
        "filename": backup.filename,
        "filepath": backup.filepath,
        "size_bytes": backup.size_bytes,
        "created_at": backup.created_at,
    }


# ---------------------------------------------------------------------------
# O3 — Restore
# ---------------------------------------------------------------------------


@router.post(
    "/backups/{filename}/verify",
    summary="Verify a backup file is valid",
)
async def verify_backup(
    filename: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Verify a backup file's integrity. Both roles allowed."""
    is_valid = RestoreService.verify_backup(filename)
    return {"filename": filename, "valid": is_valid}


@router.post(
    "/backups/{filename}/restore",
    summary="Restore from a backup",
)
async def restore_backup(
    filename: str,
    user: CurrentUser = Depends(require_role("CPA_OWNER")),
):
    """
    Restore database from a backup file. CPA_OWNER only.

    WARNING: This will replace the current database contents.
    The backup is verified before restore begins.

    Compliance: Halts on error — does not partially restore.
    """
    verify_role(user, "CPA_OWNER")

    # Verify backup first
    if not RestoreService.verify_backup(filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Backup file is invalid or corrupted.",
        )

    result = RestoreService.restore_backup(filename)
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Restore failed: {result.error}",
        )
    return {"message": "Database restored successfully", "filename": result.filename}


# ---------------------------------------------------------------------------
# O4 — Health Check
# ---------------------------------------------------------------------------


@router.get(
    "/health",
    summary="System health check",
)
async def health_check(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """
    Run a comprehensive system health check.

    Checks: database connectivity, disk space, backup status.
    Both roles allowed.
    """
    result = await HealthCheckService.check_health(db)
    return {
        "status": result.status,
        "database": {
            "connected": result.db_connected,
            "latency_ms": result.db_latency_ms,
        },
        "disk": {
            "total_gb": result.disk_total_gb,
            "free_gb": result.disk_free_gb,
            "usage_percent": result.disk_usage_percent,
        },
        "backups": {
            "directory_exists": result.backup_dir_exists,
            "total_backups": result.total_backups,
            "last_backup": result.last_backup,
            "last_backup_size_bytes": result.last_backup_size_bytes,
        },
        "issues": result.issues,
    }
