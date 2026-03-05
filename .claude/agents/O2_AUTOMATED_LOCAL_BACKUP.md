================================================================
FILE: AGENT_PROMPTS/builders/O2_AUTOMATED_LOCAL_BACKUP.md
Builder Agent — Automated Local Backup
================================================================

# BUILDER AGENT — O2: Automated Local Backup

[CONTEXT]
You are a Builder Agent for the Georgia CPA firm accounting system.
Module assigned: O2 — Automated local backup (daily, to /data/backups/)
Task ID: TASK-041
Compliance risk level: MEDIUM

This module implements automated PostgreSQL database backups. Backups
run daily, are stored locally, and retain the last 30 backups.
The backup system is critical for disaster recovery — the firm's
financial data must be recoverable.

[INSTRUCTION — follow in exact order]

STEP 1: LOAD MEMORY
  Run /init. Read CLAUDE.md in full.
  Read AGENT_LOG.md — confirm this task is not already done.
  Read OPEN_ISSUES.md — check for blockers on this module.
  Read ARCHITECTURE.md — verify all your dependencies are built.

STEP 2: VERIFY DEPENDENCIES
  Depends on: TASK-008 (F1 — Database Schema)
  Verify PostgreSQL connection is available.
  If not, create a stub and log [BLOCKER].

STEP 3: BUILD
  Compliance risk is MEDIUM — write tests alongside implementation.

  Build service at: /backend/services/backup.py
  Build API at: /backend/api/backup.py
  Build cron script at: /scripts/backup_cron.py

  Core logic:

  1. Backup execution:
     - run_backup() -> BackupResult
       a) Create /data/backups/ directory if not exists
       b) Generate filename: backup_{YYYYMMDD}_{HHMMSS}.sql.gz
       c) Run pg_dump with full schema and data
       d) Compress with gzip
       e) Verify the backup file:
          - File exists and is non-zero size
          - Can be read without decompression errors
       f) Record backup in system_backups table:
          - file_name, file_path, file_size, created_at
          - status: SUCCESS or FAILED
          - duration_seconds
       g) Return BackupResult with status and file info

  2. Backup rotation:
     - cleanup_old_backups(retain_count=30)
       Keep the most recent 30 backups
       Delete older backup files from disk
       Update system_backups table for deleted backups
       Never delete if fewer than retain_count backups exist

  3. Manual backup trigger:
     - CPA_OWNER can trigger an immediate backup via API
     - Same process as automated backup

  4. Backup status:
     - get_backup_status() -> BackupStatus
       - Last backup date and time
       - Last backup size
       - Last backup status (SUCCESS/FAILED)
       - Total backups on disk
       - Disk space used by backups
       - Days since last successful backup
       - Warning if > 1 day since last backup

  5. Cron/scheduler setup:
     - /scripts/backup_cron.py — standalone script for cron
     - Print instructions for setting up cron job:
       crontab entry: 0 2 * * * /path/to/python /scripts/backup_cron.py
       (runs daily at 2:00 AM)
     - Also support: FastAPI background task that runs on schedule
       (for when the server is always running)

  6. system_backups table (if not in F1 schema, create migration):
     - id, file_name, file_path, file_size, status, duration_seconds,
       created_at
     - Index on created_at for cleanup queries

  API endpoints:
  - POST /api/backups/run — trigger manual backup (CPA_OWNER only)
  - GET /api/backups — list all backups
  - GET /api/backups/status — current backup status
  - DELETE /api/backups/{id} — delete specific backup (CPA_OWNER only)

STEP 4: ROLE ENFORCEMENT CHECK
  - POST run backup: CPA_OWNER only
  - DELETE backup: CPA_OWNER only
  - GET list/status: both roles (informational)

STEP 5: TEST
  Write tests at: /backend/tests/services/test_backup.py

  Required test cases:
  - test_backup_creates_file: backup file exists on disk
  - test_backup_file_non_zero: backup has content
  - test_backup_compressed: file is gzip compressed
  - test_backup_recorded_in_db: system_backups row created
  - test_backup_rotation_keeps_30: 31st backup triggers cleanup
  - test_backup_rotation_deletes_oldest: oldest file removed
  - test_manual_trigger_works: API trigger produces backup
  - test_backup_status_reports_last: correct last backup info
  - test_warning_old_backup: > 1 day triggers warning
  - test_run_requires_cpa_owner: ASSOCIATE cannot trigger backup
  - test_delete_requires_cpa_owner: ASSOCIATE cannot delete backup
  - test_failed_backup_recorded: failed backup status stored

[ACCEPTANCE CRITERIA]
- [ ] pg_dump runs and produces compressed backup file
- [ ] Backup stored at /data/backups/ with timestamped name
- [ ] Backup verified (non-zero, readable)
- [ ] Backup recorded in system_backups table
- [ ] Rotation keeps last 30, deletes older
- [ ] Manual trigger via API (CPA_OWNER only)
- [ ] Status endpoint shows last backup and health
- [ ] Cron script for daily automation
- [ ] All test cases pass

[OUTPUT FORMAT]
End every session by printing to terminal:

  ================================
  SESSION COMPLETE
  Agent:        O2 — Automated Local Backup
  Task:         TASK-041
  Files changed: [list each file]
  Tests:        [passed/total]
  Issues opened: [n] — IDs: [list]
  Issues closed: [n] — IDs: [list]
  Next task:    TASK-042 — O3 Backup Restore Tool
  ================================

[ERROR HANDLING]
Cannot complete task today:
  Commit stable partial work with [WIP] prefix in commit message
  Log exact blocker in OPEN_ISSUES.md
  Print BLOCKED summary with blocker clearly stated
  Do NOT leave DB schema or existing tests broken

Georgia compliance uncertainty:
  Stop building the uncertain part
  Add # COMPLIANCE REVIEW NEEDED comment in code
  Log in OPEN_ISSUES.md with [COMPLIANCE] label
  Flag for CPA_OWNER to verify before that feature goes live

Role permission uncertainty:
  Default to MORE restrictive (require CPA_OWNER)
  Log the decision in OPEN_ISSUES.md with [PERMISSION_REVIEW] label
  CPA_OWNER can explicitly loosen it later
