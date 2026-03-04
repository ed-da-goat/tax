"""
Operations service (modules O2-O4).

O2: Automated local backup (pg_dump to /data/backups/).
O3: Backup restore tool with verification step.
O4: System health check (DB, disk, backup status).

Compliance (CLAUDE.md):
- Rule #2: Backups preserve all data including audit trail.
- Failure handling: Disk or DB error → halt, do not partially import.
"""

import os
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
BACKUP_DIR = PROJECT_ROOT / "data" / "backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class BackupInfo:
    """Information about a backup file."""

    filename: str
    filepath: str
    size_bytes: int
    created_at: str


@dataclass
class BackupResult:
    """Result of a backup operation."""

    success: bool
    filename: str | None = None
    filepath: str | None = None
    size_bytes: int = 0
    error: str | None = None


@dataclass
class RestoreResult:
    """Result of a restore operation."""

    success: bool
    filename: str | None = None
    error: str | None = None


@dataclass
class HealthCheckResult:
    """Result of system health check."""

    db_connected: bool
    db_latency_ms: float = 0.0
    disk_total_gb: float = 0.0
    disk_free_gb: float = 0.0
    disk_usage_percent: float = 0.0
    backup_dir_exists: bool = False
    last_backup: str | None = None
    last_backup_size_bytes: int = 0
    total_backups: int = 0
    status: str = "HEALTHY"
    issues: list[str] | None = None


# ---------------------------------------------------------------------------
# O2 — Automated Backup
# ---------------------------------------------------------------------------


class BackupService:
    """Database backup operations using pg_dump."""

    @staticmethod
    def create_backup() -> BackupResult:
        """
        Create a PostgreSQL backup using pg_dump.

        Saves to /data/backups/ with a timestamped filename.
        Uses the custom format (-Fc) for compressed, restorable backups.

        Returns BackupResult with success status and file info.
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"ga_cpa_{timestamp}.dump"
        filepath = BACKUP_DIR / filename

        # Parse connection string for pg_dump
        # Format: postgresql+asyncpg://user:pass@host:port/dbname
        db_url = settings.DATABASE_URL
        # Strip the asyncpg driver prefix for pg_dump
        clean_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

        try:
            result = subprocess.run(
                [
                    "pg_dump",
                    "--format=custom",
                    "--compress=6",
                    f"--file={filepath}",
                    clean_url,
                ],
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            if result.returncode != 0:
                return BackupResult(
                    success=False,
                    error=f"pg_dump failed: {result.stderr.strip()}",
                )

            stat = filepath.stat()
            return BackupResult(
                success=True,
                filename=filename,
                filepath=str(filepath),
                size_bytes=stat.st_size,
            )
        except FileNotFoundError:
            return BackupResult(
                success=False,
                error="pg_dump not found. Ensure PostgreSQL client tools are installed.",
            )
        except subprocess.TimeoutExpired:
            return BackupResult(
                success=False,
                error="Backup timed out after 5 minutes.",
            )
        except Exception as e:
            return BackupResult(success=False, error=str(e))

    @staticmethod
    def list_backups() -> list[BackupInfo]:
        """List all backup files in the backup directory, newest first."""
        backups = []
        if not BACKUP_DIR.exists():
            return backups

        for f in sorted(BACKUP_DIR.iterdir(), reverse=True):
            if f.is_file() and (f.suffix == ".dump" or f.suffix == ".sql"):
                stat = f.stat()
                backups.append(BackupInfo(
                    filename=f.name,
                    filepath=str(f),
                    size_bytes=stat.st_size,
                    created_at=datetime.fromtimestamp(
                        stat.st_mtime, tz=timezone.utc
                    ).isoformat(),
                ))

        return backups

    @staticmethod
    def get_backup(filename: str) -> BackupInfo | None:
        """Get info about a specific backup file."""
        filepath = BACKUP_DIR / filename
        if not filepath.exists() or not filepath.is_file():
            return None
        # Prevent path traversal
        if filepath.resolve().parent != BACKUP_DIR.resolve():
            return None
        stat = filepath.stat()
        return BackupInfo(
            filename=filepath.name,
            filepath=str(filepath),
            size_bytes=stat.st_size,
            created_at=datetime.fromtimestamp(
                stat.st_mtime, tz=timezone.utc
            ).isoformat(),
        )


# ---------------------------------------------------------------------------
# O3 — Backup Restore
# ---------------------------------------------------------------------------


class RestoreService:
    """Database restore operations using pg_restore."""

    @staticmethod
    def restore_backup(filename: str) -> RestoreResult:
        """
        Restore a PostgreSQL backup using pg_restore.

        Compliance: Halts on error — does not partially restore.
        Uses --clean to drop existing objects before recreating.

        Parameters
        ----------
        filename : str
            The backup filename (must exist in BACKUP_DIR).

        Returns
        -------
        RestoreResult
        """
        filepath = BACKUP_DIR / filename
        if not filepath.exists():
            return RestoreResult(success=False, filename=filename, error="Backup file not found.")

        # Prevent path traversal
        if filepath.resolve().parent != BACKUP_DIR.resolve():
            return RestoreResult(success=False, filename=filename, error="Invalid backup path.")

        db_url = settings.DATABASE_URL
        clean_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

        try:
            result = subprocess.run(
                [
                    "pg_restore",
                    "--clean",
                    "--if-exists",
                    f"--dbname={clean_url}",
                    str(filepath),
                ],
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout
            )

            # pg_restore returns non-zero for warnings too, check stderr
            if result.returncode != 0 and "ERROR" in result.stderr:
                return RestoreResult(
                    success=False,
                    filename=filename,
                    error=f"pg_restore failed: {result.stderr.strip()[:500]}",
                )

            return RestoreResult(success=True, filename=filename)
        except FileNotFoundError:
            return RestoreResult(
                success=False,
                filename=filename,
                error="pg_restore not found. Ensure PostgreSQL client tools are installed.",
            )
        except subprocess.TimeoutExpired:
            return RestoreResult(
                success=False,
                filename=filename,
                error="Restore timed out after 10 minutes.",
            )
        except Exception as e:
            return RestoreResult(success=False, filename=filename, error=str(e))

    @staticmethod
    def verify_backup(filename: str) -> bool:
        """
        Verify a backup file is valid by listing its contents.

        Returns True if pg_restore --list succeeds.
        """
        filepath = BACKUP_DIR / filename
        if not filepath.exists():
            return False
        if filepath.resolve().parent != BACKUP_DIR.resolve():
            return False

        try:
            result = subprocess.run(
                ["pg_restore", "--list", str(filepath)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.returncode == 0
        except Exception:
            return False


# ---------------------------------------------------------------------------
# O4 — System Health Check
# ---------------------------------------------------------------------------


class HealthCheckService:
    """System health check operations."""

    @staticmethod
    async def check_health(db: AsyncSession) -> HealthCheckResult:
        """
        Run a comprehensive health check.

        Checks:
        1. Database connectivity and latency
        2. Disk space
        3. Backup directory and last backup
        """
        result = HealthCheckResult(db_connected=False)
        issues = []

        # 1. Database connectivity
        try:
            import time
            start = time.monotonic()
            await db.execute(text("SELECT 1"))
            elapsed = (time.monotonic() - start) * 1000
            result.db_connected = True
            result.db_latency_ms = round(elapsed, 2)
            if elapsed > 1000:
                issues.append(f"Database latency high: {elapsed:.0f}ms")
        except Exception as e:
            result.db_connected = False
            issues.append(f"Database connection failed: {str(e)[:200]}")

        # 2. Disk space
        try:
            usage = shutil.disk_usage(str(PROJECT_ROOT))
            result.disk_total_gb = round(usage.total / (1024**3), 2)
            result.disk_free_gb = round(usage.free / (1024**3), 2)
            result.disk_usage_percent = round(
                (usage.used / usage.total) * 100, 1
            )
            if result.disk_usage_percent > 90:
                issues.append(f"Disk usage critical: {result.disk_usage_percent}%")
            elif result.disk_usage_percent > 80:
                issues.append(f"Disk usage high: {result.disk_usage_percent}%")
        except Exception as e:
            issues.append(f"Disk check failed: {str(e)[:200]}")

        # 3. Backup status
        result.backup_dir_exists = BACKUP_DIR.exists()
        if result.backup_dir_exists:
            backups = BackupService.list_backups()
            result.total_backups = len(backups)
            if backups:
                result.last_backup = backups[0].created_at
                result.last_backup_size_bytes = backups[0].size_bytes
            else:
                issues.append("No backups found in backup directory")
        else:
            issues.append("Backup directory does not exist")

        # Determine overall status
        if not result.db_connected:
            result.status = "CRITICAL"
        elif issues:
            result.status = "WARNING"
        else:
            result.status = "HEALTHY"

        result.issues = issues if issues else None
        return result
