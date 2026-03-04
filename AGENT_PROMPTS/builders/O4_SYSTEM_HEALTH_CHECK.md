================================================================
FILE: AGENT_PROMPTS/builders/O4_SYSTEM_HEALTH_CHECK.md
Builder Agent — System Health Check
================================================================

# BUILDER AGENT — O4: System Health Check

[CONTEXT]
You are a Builder Agent for the Georgia CPA firm accounting system.
Module assigned: O4 — System health check (DB connection, disk space, last backup)
Task ID: TASK-043
Compliance risk level: LOW

This module provides a system health overview: database connectivity,
disk space availability, last backup status, and overall system
readiness. It includes both an API endpoint for programmatic checks
and a React dashboard widget for visual display.

[INSTRUCTION — follow in exact order]

STEP 1: LOAD MEMORY
  Run /init. Read CLAUDE.md in full.
  Read AGENT_LOG.md — confirm this task is not already done.
  Read OPEN_ISSUES.md — check for blockers on this module.
  Read ARCHITECTURE.md — verify all your dependencies are built.

STEP 2: VERIFY DEPENDENCIES
  Depends on: TASK-008 (F1 — Database Schema), TASK-041 (O2 — Backup)
  Verify database connection and backup status are available.
  If any missing, create stubs and log [BLOCKER].

STEP 3: BUILD
  Compliance risk is LOW — write tests alongside implementation.

  Build service at: /backend/services/health_check.py
  Build API at: /backend/api/health.py
  Build React component at: /frontend/src/components/dashboard/HealthWidget.jsx

  Core logic:

  1. Database health:
     - check_database() -> DatabaseHealth
       a) Attempt connection to PostgreSQL
       b) Run simple query: SELECT 1
       c) Check connection pool status (active, idle, max)
       d) Check database size
       e) Return: status (OK/DEGRADED/DOWN), response_time_ms,
          connection_count, db_size_mb

  2. Disk space:
     - check_disk_space() -> DiskHealth
       a) Check disk usage for:
          - /data/documents/ (document storage)
          - /data/backups/ (backup storage)
          - Overall filesystem
       b) Calculate free space percentage
       c) Return: status (OK if > 20% free, WARNING if 10-20%,
          CRITICAL if < 10%), total_gb, used_gb, free_gb, free_pct

  3. Backup health:
     - check_backup_status() -> BackupHealth
       a) Query last backup from system_backups table
       b) Check: was last backup successful?
       c) Check: how old is the last backup?
       d) Return: status (OK if < 24h, WARNING if 24-48h,
          CRITICAL if > 48h), last_backup_at, last_backup_status,
          hours_since_backup, backup_count

  4. Application health:
     - check_app_health() -> AppHealth
       a) Verify all required services are importable
       b) Check that migrations are up to date
       c) Check that required environment variables are set
       d) Return: status, version, uptime, migration_status

  5. Overall health:
     - get_system_health() -> SystemHealth
       Combine all checks:
       - database: DatabaseHealth
       - disk: DiskHealth
       - backup: BackupHealth
       - application: AppHealth
       - overall_status: OK / DEGRADED / CRITICAL
         (worst status of all checks)
       - timestamp

  6. React widget:
     - Status indicator: green/yellow/red circle
     - Expandable: click to see details of each check
     - Auto-refresh every 60 seconds
     - Include in firm dashboard (R5)

  API endpoints:
  - GET /api/health — overall system health (no auth required)
  - GET /api/health/database — database health
  - GET /api/health/disk — disk space
  - GET /api/health/backup — backup status
  - GET /api/health/detailed — all checks combined (auth required)

  The basic /api/health endpoint should not require authentication
  (useful for monitoring scripts). Detailed health requires auth.

STEP 4: ROLE ENFORCEMENT CHECK
  - GET /api/health: no auth (monitoring)
  - GET /api/health/detailed: both roles
  No CPA_OWNER-only restrictions in this module.

STEP 5: TEST
  Write tests at: /backend/tests/services/test_health_check.py

  Required test cases:
  - test_database_ok: database connection succeeds
  - test_database_down: simulate connection failure, status DOWN
  - test_disk_space_ok: > 20% free = OK
  - test_disk_space_warning: 10-20% free = WARNING
  - test_disk_space_critical: < 10% free = CRITICAL
  - test_backup_ok: backup < 24h = OK
  - test_backup_warning: backup 24-48h = WARNING
  - test_backup_critical: backup > 48h = CRITICAL
  - test_overall_worst_status: overall = worst individual check
  - test_health_no_auth: /api/health works without token
  - test_detailed_requires_auth: /api/health/detailed needs token
  - test_app_health_checks_env: missing env vars detected

[ACCEPTANCE CRITERIA]
- [ ] Database connectivity verified with response time
- [ ] Disk space checked for document and backup directories
- [ ] Backup freshness verified (24h warning, 48h critical)
- [ ] Application health (migrations, env vars)
- [ ] Overall status = worst of all individual checks
- [ ] Basic health endpoint works without auth
- [ ] React widget with color-coded status
- [ ] Auto-refresh on dashboard
- [ ] All test cases pass

[OUTPUT FORMAT]
End every session by printing to terminal:

  ================================
  SESSION COMPLETE
  Agent:        O4 — System Health Check
  Task:         TASK-043
  Files changed: [list each file]
  Tests:        [passed/total]
  Issues opened: [n] — IDs: [list]
  Issues closed: [n] — IDs: [list]
  Next task:    ALL TASKS COMPLETE — System ready for integration testing
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
