"""
Tests for operations modules (O2-O4).

O2: Backup creation and listing
O3: Backup verification
O4: Health check

Note: Actual pg_dump/pg_restore operations are tested with mocks
to avoid modifying the real database. Health check uses real DB session.
"""

import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.operations import (
    BACKUP_DIR,
    BackupService,
    HealthCheckService,
    RestoreService,
)


# ---------------------------------------------------------------------------
# O2 — Backup Tests
# ---------------------------------------------------------------------------


class TestBackupService:

    def test_list_backups_empty_dir(self, tmp_path: Path):
        with patch("app.services.operations.BACKUP_DIR", tmp_path):
            backups = BackupService.list_backups()
            assert backups == []

    def test_list_backups_with_files(self, tmp_path: Path):
        # Create fake backup files
        (tmp_path / "ga_cpa_20240601_120000.dump").write_bytes(b"fake_dump_1")
        (tmp_path / "ga_cpa_20240602_120000.dump").write_bytes(b"fake_dump_2")
        (tmp_path / "readme.txt").write_text("not a backup")

        with patch("app.services.operations.BACKUP_DIR", tmp_path):
            backups = BackupService.list_backups()
            assert len(backups) == 2
            # Should be sorted newest first
            assert "20240602" in backups[0].filename

    def test_get_backup_exists(self, tmp_path: Path):
        (tmp_path / "test.dump").write_bytes(b"data")
        with patch("app.services.operations.BACKUP_DIR", tmp_path):
            info = BackupService.get_backup("test.dump")
            assert info is not None
            assert info.filename == "test.dump"
            assert info.size_bytes == 4

    def test_get_backup_not_found(self, tmp_path: Path):
        with patch("app.services.operations.BACKUP_DIR", tmp_path):
            info = BackupService.get_backup("nonexistent.dump")
            assert info is None

    def test_get_backup_path_traversal(self, tmp_path: Path):
        """Path traversal attempts should return None."""
        with patch("app.services.operations.BACKUP_DIR", tmp_path):
            info = BackupService.get_backup("../../../etc/passwd")
            assert info is None

    @patch("app.services.operations.subprocess.run")
    def test_create_backup_success(self, mock_run, tmp_path: Path):
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        with patch("app.services.operations.BACKUP_DIR", tmp_path):
            # Pre-create the file that pg_dump would create
            # We need to patch the filepath calculation
            result = BackupService.create_backup()
            # pg_dump was called
            mock_run.assert_called_once()
            call_args = mock_run.call_args[0][0]
            assert call_args[0] == "pg_dump"

    @patch("app.services.operations.subprocess.run")
    def test_create_backup_failure(self, mock_run, tmp_path: Path):
        mock_run.return_value = MagicMock(returncode=1, stderr="connection refused")

        with patch("app.services.operations.BACKUP_DIR", tmp_path):
            result = BackupService.create_backup()
            assert not result.success
            assert "connection refused" in result.error


# ---------------------------------------------------------------------------
# O3 — Restore Tests
# ---------------------------------------------------------------------------


class TestRestoreService:

    def test_verify_backup_not_found(self, tmp_path: Path):
        with patch("app.services.operations.BACKUP_DIR", tmp_path):
            assert RestoreService.verify_backup("nonexistent.dump") is False

    @patch("app.services.operations.subprocess.run")
    def test_verify_backup_valid(self, mock_run, tmp_path: Path):
        (tmp_path / "valid.dump").write_bytes(b"data")
        mock_run.return_value = MagicMock(returncode=0)

        with patch("app.services.operations.BACKUP_DIR", tmp_path):
            assert RestoreService.verify_backup("valid.dump") is True
            mock_run.assert_called_once()

    @patch("app.services.operations.subprocess.run")
    def test_verify_backup_invalid(self, mock_run, tmp_path: Path):
        (tmp_path / "invalid.dump").write_bytes(b"corrupted")
        mock_run.return_value = MagicMock(returncode=1)

        with patch("app.services.operations.BACKUP_DIR", tmp_path):
            assert RestoreService.verify_backup("invalid.dump") is False

    def test_restore_not_found(self, tmp_path: Path):
        with patch("app.services.operations.BACKUP_DIR", tmp_path):
            result = RestoreService.restore_backup("nonexistent.dump")
            assert not result.success
            assert "not found" in result.error

    def test_restore_path_traversal(self, tmp_path: Path):
        with patch("app.services.operations.BACKUP_DIR", tmp_path):
            result = RestoreService.restore_backup("../../../etc/passwd")
            assert not result.success

    @patch("app.services.operations.subprocess.run")
    def test_restore_success(self, mock_run, tmp_path: Path):
        (tmp_path / "good.dump").write_bytes(b"data")
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        with patch("app.services.operations.BACKUP_DIR", tmp_path):
            result = RestoreService.restore_backup("good.dump")
            assert result.success
            assert result.filename == "good.dump"


# ---------------------------------------------------------------------------
# O4 — Health Check Tests
# ---------------------------------------------------------------------------


class TestHealthCheck:

    @pytest.mark.asyncio
    async def test_health_check_db_connected(self, db_session: AsyncSession):
        result = await HealthCheckService.check_health(db_session)
        assert result.db_connected is True
        assert result.db_latency_ms > 0

    @pytest.mark.asyncio
    async def test_health_check_disk_info(self, db_session: AsyncSession):
        result = await HealthCheckService.check_health(db_session)
        assert result.disk_total_gb > 0
        assert result.disk_free_gb > 0
        assert 0 <= result.disk_usage_percent <= 100

    @pytest.mark.asyncio
    async def test_health_check_backup_dir(self, db_session: AsyncSession):
        result = await HealthCheckService.check_health(db_session)
        assert result.backup_dir_exists is True

    @pytest.mark.asyncio
    async def test_health_check_status(self, db_session: AsyncSession):
        result = await HealthCheckService.check_health(db_session)
        assert result.status in ("HEALTHY", "WARNING", "CRITICAL")
