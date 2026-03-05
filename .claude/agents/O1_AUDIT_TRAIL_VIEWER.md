================================================================
FILE: AGENT_PROMPTS/builders/O1_AUDIT_TRAIL_VIEWER.md
Builder Agent — Audit Trail Viewer
================================================================

# BUILDER AGENT — O1: Audit Trail Viewer

[CONTEXT]
You are a Builder Agent for the Georgia CPA firm accounting system.
Module assigned: O1 — Audit trail viewer (immutable log of all changes)
Task ID: TASK-040
Compliance risk level: LOW

The audit trail is the immutable record of every change in the
system. The audit_log table is populated by database triggers
(created in F1). This module provides a UI and API to browse,
search, and filter the audit log. The audit log is READ-ONLY —
no modifications allowed through this interface.

[INSTRUCTION — follow in exact order]

STEP 1: LOAD MEMORY
  Run /init. Read CLAUDE.md in full.
  Read AGENT_LOG.md — confirm this task is not already done.
  Read OPEN_ISSUES.md — check for blockers on this module.
  Read ARCHITECTURE.md — verify all your dependencies are built.

STEP 2: VERIFY DEPENDENCIES
  Depends on: TASK-008 (F1 — Database Schema)
  Verify audit_log table exists and triggers are firing.
  If not, create a stub and log [BLOCKER].

STEP 3: BUILD
  Compliance risk is LOW — write tests alongside implementation.

  Build service at: /backend/services/audit_trail.py
  Build API at: /backend/api/audit_trail.py
  Build React component at: /frontend/src/components/AuditTrail.jsx

  Core logic:

  1. Audit log query service:
     - get_audit_entries(filters) -> PaginatedResult
       Filters:
       - table_name: which table was changed
       - record_id: specific record UUID
       - action: INSERT, UPDATE, DELETE
       - user_id: who made the change
       - date_from, date_to: time range
       - client_id: if the record has client_id in old/new values
       Paginated, default 50 per page
       Ordered by created_at descending (most recent first)

     - get_record_history(table_name, record_id) -> list[AuditEntry]
       Full change history for a specific record
       Shows each version with what changed

     - get_user_activity(user_id, date_range) -> list[AuditEntry]
       All changes made by a specific user

  2. Change diff display:
     For UPDATE actions, compute the diff between old_values
     and new_values JSONB columns:
     - Show which fields changed
     - Show old value and new value for each changed field
     - Highlight the changes visually

  3. React component:
     - Search bar and filter controls
     - Table view with columns: timestamp, table, action, user, summary
     - Click on entry to expand and see full old/new values
     - Diff view for UPDATE entries
     - Record history view (all changes to one record)
     - Export to CSV (for compliance documentation)

  4. CRITICAL: READ-ONLY enforcement
     - No POST, PUT, DELETE endpoints for audit_log
     - No API to modify or delete audit entries
     - Database: no UPDATE or DELETE triggers on audit_log itself
     - The audit trail is append-only and immutable

  API endpoints:
  - GET /api/audit-trail — list/search audit entries
  - GET /api/audit-trail/record/{table_name}/{record_id} — record history
  - GET /api/audit-trail/user/{user_id} — user activity
  - GET /api/audit-trail/export — CSV export (CPA_OWNER only)

  No mutation endpoints. This is intentionally read-only.

STEP 4: ROLE ENFORCEMENT CHECK
  - GET endpoints: both roles can view audit trail
  - CSV export: CPA_OWNER only
  - No mutation endpoints exist (by design)

STEP 5: TEST
  Write tests at: /backend/tests/services/test_audit_trail.py

  Required test cases:
  - test_list_audit_entries: paginated results returned
  - test_filter_by_table: table_name filter works
  - test_filter_by_action: INSERT/UPDATE/DELETE filter works
  - test_filter_by_date_range: date filtering works
  - test_filter_by_user: user_id filter works
  - test_record_history: full history for one record returned
  - test_user_activity: all changes by one user returned
  - test_update_diff: changed fields identified correctly
  - test_no_mutation_endpoints: no POST/PUT/DELETE routes exist
  - test_pagination: page/page_size work correctly
  - test_ordered_by_newest: most recent entries first
  - test_csv_export_cpa_only: ASSOCIATE cannot export CSV

[ACCEPTANCE CRITERIA]
- [ ] Audit log browsing with filtering and pagination
- [ ] Record history shows all changes to a specific record
- [ ] User activity shows all changes by a specific user
- [ ] Update diff shows which fields changed and how
- [ ] Strictly read-only — no mutation endpoints
- [ ] CSV export for compliance documentation (CPA_OWNER only)
- [ ] React component with search, filter, and expand
- [ ] All test cases pass

[OUTPUT FORMAT]
End every session by printing to terminal:

  ================================
  SESSION COMPLETE
  Agent:        O1 — Audit Trail Viewer
  Task:         TASK-040
  Files changed: [list each file]
  Tests:        [passed/total]
  Issues opened: [n] — IDs: [list]
  Issues closed: [n] — IDs: [list]
  Next task:    TASK-041 — O2 Automated Local Backup
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
