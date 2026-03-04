================================================================
FILE: AGENT_PROMPTS/builders/O3_BACKUP_RESTORE_TOOL.md
Builder Agent — Backup Restore Tool
================================================================

# BUILDER AGENT — O3: Backup Restore Tool

[CONTEXT]
You are a Builder Agent for the Georgia CPA firm accounting system.
Module assigned: O3 — Backup restore tool with verification step
Task ID: TASK-042
Compliance risk level: HIGH

Restoring a backup overwrites the current database with a previous
state. This is an irreversible, destructive operation. It must
require CPA_OWNER authentication, verification of the backup
integrity, and explicit confirmation before proceeding. A pre-restore
backup of the current state must be taken automatically.

[INSTRUCTION — follow in exact order]

STEP 1: LOAD MEMORY
  Run /init. Read CLAUDE.md in full.
  Read AGENT_LOG.md — confirm this task is not already done.
  Read OPEN_ISSUES.md — check for blockers on this module.
  Read ARCHITECTURE.md — verify all your dependencies are built.

STEP 2: VERIFY DEPENDENCIES
  Depends on: TASK-041 (O2 — Automated Backup)
  Verify backup service is available and backups exist.
  If not, create a stub and log [BLOCKER].

STEP 3: BUILD
  Compliance risk is HIGH — use TDD (write tests BEFORE implementation).

  Build service at: /backend/services/restore.py
  Build API at: /backend/api/restore.py

  Core logic:

  1. List available backups:
     - list_available_backups() -> list[BackupInfo]
       Show: file name, date, size, status (verified/unverified)

  2. Verify backup integrity:
     - verify_backup(backup_id) -> VerificationResult
       a) Decompress the gzip file to temp location
       b) Run pg_restore --list to verify it is a valid pg_dump
       c) Check for SQL syntax errors
       d) Report: tables found, estimated row counts
       e) Return: is_valid, table_count, estimated_rows, warnings

  3. Restore process (multi-step safety):
     - initiate_restore(backup_id, current_user) -> RestoreSession
       CPA_OWNER only — function-level check
       a) Verify backup integrity (step 2)
       b) If invalid: halt, return error
       c) Take a pre-restore backup of current database
          (automatic safety net — label as "pre_restore_*")
       d) Return RestoreSession with:
          - session_id
          - backup_info (what will be restored)
          - current_db_info (what will be overwritten)
          - pre_restore_backup_id (the safety backup)
          - confirmation_required: True
          - expires_at: 15 minutes from now

     - confirm_restore(session_id, current_user, confirmation_code)
       CPA_OWNER only — function-level check
       a) Verify session is valid and not expired
       b) Verify confirmation_code matches (prevent accidental clicks)
       c) Disconnect all other database sessions
       d) Drop current database contents
       e) Restore from backup file using pg_restore
       f) Verify restored data:
          - Table count matches backup
          - Record counts are reasonable
          - Can run a basic query
       g) Record restore event in system log
       h) Return: RestoreResult with success/failure and details

  4. Recovery instructions:
     If restore fails partway:
     - Print step-by-step recovery instructions
     - Reference the pre-restore backup taken in step 3c
     - Provide the exact pg_restore command to run manually

  API endpoints:
  - GET /api/restore/backups — list available backups
  - POST /api/restore/verify/{backup_id} — verify integrity
  - POST /api/restore/initiate/{backup_id} — start restore process
  - POST /api/restore/confirm/{session_id} — confirm and execute

  ALL endpoints: CPA_OWNER only.

STEP 4: ROLE ENFORCEMENT CHECK
  ALL endpoints: CPA_OWNER only.
  Function-level role check on initiate and confirm.
  Write tests proving ASSOCIATE cannot initiate or confirm restore.

STEP 5: TEST
  Write tests at: /backend/tests/services/test_restore.py

  Required test cases:
  - test_list_available_backups: backups listed correctly
  - test_verify_valid_backup: valid backup passes verification
  - test_verify_invalid_backup: corrupt backup fails verification
  - test_initiate_creates_pre_restore_backup: safety backup taken
  - test_initiate_returns_session: restore session created
  - test_session_expires: expired session cannot be confirmed
  - test_confirm_requires_code: wrong confirmation code rejected
  - test_restore_requires_cpa_owner: ASSOCIATE cannot initiate
  - test_confirm_requires_cpa_owner: ASSOCIATE cannot confirm
  - test_successful_restore: database restored to backup state
  - test_failed_restore_recovery: pre-restore backup available
  - test_restore_recorded_in_log: restore event in system log

[ACCEPTANCE CRITERIA]
- [ ] Backup integrity verification before restore
- [ ] Pre-restore safety backup taken automatically
- [ ] Two-step process: initiate then confirm with code
- [ ] Session expiration (15-minute window)
- [ ] CPA_OWNER only at function level
- [ ] Database fully restored from backup
- [ ] Post-restore verification
- [ ] Recovery instructions on failure
- [ ] All test cases pass

[OUTPUT FORMAT]
End every session by printing to terminal:

  ================================
  SESSION COMPLETE
  Agent:        O3 — Backup Restore Tool
  Task:         TASK-042
  Files changed: [list each file]
  Tests:        [passed/total]
  Issues opened: [n] — IDs: [list]
  Issues closed: [n] — IDs: [list]
  Next task:    TASK-043 — O4 System Health Check
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
