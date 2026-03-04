================================================================
FILE: CLAUDE.md
(Place in project root. Every agent reads this on every /init.)
================================================================

# GEORGIA CPA FIRM — ACCOUNTING SYSTEM MASTER CONTEXT

## FIRM PROFILE
- Type: CPA firm, Georgia USA
- Staff: 2-5 (1 CPA-owner + associates)
- Clients: 26-50 active clients, all migrating from QuickBooks Online
- Client entity types: Sole proprietors, S-Corps, C-Corps, 
  Partnerships/LLCs
- Deployment: Local machine via Claude Code, no cloud dependency
- Version control: Git + GitHub (mandatory for every change)
- Purpose: Replace QuickBooks Online subscription entirely

## TECH STACK
[CHANGED: Stack fields now pre-decided based on firm profile]
- Frontend: React + Vite (fast local dev, no build server needed)
- Backend: Python + FastAPI (readable, strong accounting libraries)
- Database: PostgreSQL (local instance, ACID compliant for financials)
- Auth: JWT with role-based access control (local, no OAuth needed)
- PDF generation: WeasyPrint (Georgia tax form exports)
- File storage: Local filesystem under /data/documents/[client_id]/
- Migration tool: Custom CSV parser (reads QuickBooks Online exports)

## ROLE PERMISSION SCHEMA
[CHANGED: Explicit two-role system based on firm workflow]

ROLE: CPA_OWNER (you)
  - All permissions below PLUS:
  - Approve and post transactions
  - Run and finalize payroll
  - Export tax forms (500, 600, G-7, ST-3)
  - Manage users and staff access
  - Restore from backup
  - Override soft-deleted records (audit trail preserved)

ROLE: ASSOCIATE
  - View all client data and reports
  - Enter draft transactions (status: PENDING_APPROVAL)
  - Upload and tag client documents
  - Generate draft reports (cannot finalize or export)
  - Cannot approve, post, run payroll, or export tax forms

Every API endpoint must check role before executing.
If role check fails: return HTTP 403 with message:
  {"error": "Insufficient permissions", "required_role": "[role]"}

## MEMORY PROTOCOL (CRITICAL — READ EVERY SESSION)
1. Run /init first. Read this entire file before writing any code.
2. Read AGENT_LOG.md — confirm your task is not already complete.
3. Read OPEN_ISSUES.md — check for blockers on your module.
4. Read ARCHITECTURE.md — confirm your module's dependencies 
   are built before you start.
5. Before ending your session, update AGENT_LOG.md with what 
   you completed, and OPEN_ISSUES.md with any new blockers.
6. Update the module checklist below with [x] when complete.

## REQUIRED MODULE LIST (build in this order)
[CHANGED: Fully sequenced with QB migration as Phase 0]

Phase 0 — Migration (run ONCE before any other phase)
  [x] M1. QuickBooks Online CSV parser and validator
  [x] M2. Client splitter (one QB account → isolated client ledgers)
  [ ] M3. Chart of accounts mapper (QB categories → Georgia standard)
  [ ] M4. Transaction history importer (full history, not just balances)
  [ ] M5. Invoice and AR history importer
  [ ] M6. Payroll history importer
  [ ] M7. Migration audit report (flags any data that didn't map cleanly)

Phase 1 — Foundation
  [x] F1. Database schema + all migrations
  [x] F2. Chart of accounts (Georgia standard categories, pre-seeded)
  [x] F3. General ledger with double-entry enforcement
  [x] F4. Client management (create, edit, archive, entity type tagging)
  [x] F5. User auth (login, JWT, role assignment)

Phase 2 — Transactions
  [x] T1. Accounts Payable (AP)
  [x] T2. Accounts Receivable (AR) + client invoicing
  [ ] T3. Bank reconciliation engine
  [x] T4. Transaction approval workflow 
          (ASSOCIATE enters → CPA_OWNER approves → posts to GL)

Phase 3 — Document Management
  [ ] D1. Document upload (PDF, images) tagged to client + transaction
  [ ] D2. Document viewer (in-browser, no external app)
  [ ] D3. Document search by client, date, type

Phase 4 — Payroll (Georgia-specific)
  [ ] P1. Employee records (per client)
  [ ] P2. Georgia income tax withholding engine
          Source: Georgia Form G-4 instructions + DOR withholding tables
          Tax year: must be parameterized (tables change annually)
  [ ] P3. Georgia SUTA calculator
          Default new employer rate: 2.7% on first $9,500 wages
          Must support per-client custom rate (experienced employers)
  [ ] P4. Federal withholding + FICA + FUTA calculator
  [ ] P5. Pay stub generator (PDF output)
  [ ] P6. Payroll approval gate (CPA_OWNER only can finalize)

Phase 5 — Tax Form Exports
  [ ] X1. Georgia Form G-7 (quarterly payroll withholding)
          Due: last day of month after quarter end
  [ ] X2. Georgia Form 500 (individual income — Schedule C clients)
  [ ] X3. Georgia Form 600 (corporate income — C-Corp clients)
  [ ] X4. Georgia Form ST-3 (sales tax — applicable clients)
  [ ] X5. Federal Schedule C data export (sole proprietors)
  [ ] X6. Federal Form 1120-S data export (S-Corps)
  [ ] X7. Federal Form 1120 data export (C-Corps)
  [ ] X8. Federal Form 1065 data export (partnerships/LLCs)
  [ ] X9. Tax document checklist generator (per client, per entity type)

Phase 6 — Reporting
  [ ] R1. Profit & Loss (per client, date range selectable)
  [ ] R2. Balance Sheet (per client, as-of date selectable)
  [ ] R3. Cash Flow Statement (per client)
  [ ] R4. PDF export for all reports (CPA_OWNER only)
  [ ] R5. Firm-level dashboard (all clients, key metrics)

Phase 7 — Operations
  [x] O1. Audit trail viewer (immutable log of all changes)
  [ ] O2. Automated local backup (daily, to /data/backups/)
  [ ] O3. Backup restore tool with verification step
  [ ] O4. System health check (DB connection, disk space, last backup)

## GIT COMMIT SCHEMA (MANDATORY)
Format:
  [AGENT-ID] [MODULE-CODE] [ACTION]: short description (max 72 chars)

  Body (required — all four lines):
  BUILT: what was completed
  DECISION: why this approach was chosen
  REMAINING: what is not yet done in this module
  ISSUES: OPEN_ISSUES.md ticket numbers created (or NONE)

ACTION types: INIT | BUILD | FIX | REFACTOR | TEST | MIGRATE | STUB

Examples:
  [MIGRATION] [M2] [BUILD]: Split QB CSV into isolated client ledgers
  BUILT: Parser splits single QB export into per-client_id record sets
  DECISION: Used client name matching + entity type as composite key
  REMAINING: Edge case where two clients share same business name
  ISSUES: #3 (duplicate client name collision)

  [PAYROLL] [P2] [BUILD]: Georgia G-4 withholding calculator 2024
  BUILT: Bracket lookup table for single/married filing statuses
  DECISION: Lookup table over formula — safer for mid-year rate changes
  REMAINING: Annualized vs per-period calculation not yet validated
  ISSUES: #7 (need CPA review of supplemental wage rate handling)

## COMPLIANCE RULES (never violate)
1. DOUBLE-ENTRY: Every transaction must debit and credit equal amounts.
   Enforce at the database level with a CHECK constraint, not just 
   application logic. If you cannot enforce this, do not ship.

2. AUDIT TRAIL: Records are never deleted. Use soft deletes only
   (deleted_at timestamp). Every INSERT, UPDATE, DELETE must write
   a row to the audit_log table with: table_name, record_id, 
   action, old_values (JSON), new_values (JSON), user_id, timestamp.

3. GEORGIA PAYROLL: Never hardcode tax rates without citing source.
   Required comment format above every rate constant:
   # SOURCE: Georgia DOR [document name], Tax Year [YYYY], Page [n]
   # REVIEW DATE: [date this was last verified]

4. CLIENT ISOLATION: Every table that holds client data must have 
   client_id as a non-nullable foreign key. Every query that returns 
   client data must filter by client_id. 
   Write a test that proves Client A queries cannot return Client B data.

5. APPROVAL WORKFLOW: Transactions entered by ASSOCIATE must have 
   status = 'PENDING_APPROVAL' and must not affect GL balances until 
   CPA_OWNER posts them. Never auto-post on entry.

6. PAYROLL GATE: Payroll finalization endpoint must verify 
   current_user.role == 'CPA_OWNER' at the function level,
   not just the route level. Defense in depth.

## FAILURE HANDLING
- Missing dependency → create a typed stub, log [BLOCKER] in
  OPEN_ISSUES.md, proceed with your module using the stub.
- Uncertain Georgia tax rule → do NOT guess. Write:
  # COMPLIANCE REVIEW NEEDED: [describe uncertainty]
  Add to OPEN_ISSUES.md with label [COMPLIANCE] and assign to CPA_OWNER.
- Failing test → do not commit. Either fix it or mark as known-failing
  with @pytest.mark.xfail and a comment explaining why, then log it.
- Design conflict with existing code → stop. Document in OPEN_ISSUES.md
  under [CONFLICT] before touching any existing module.
- Disk or DB error during migration → halt, do not partially import.
  QB data must be preserved. Log error, print recovery instructions.

## BUILD STATUS (updated 2026-03-04, session 4)

  Phase 0 — Migration:     2/7   ██░░░░░░  (M1, M2 done)
  Phase 1 — Foundation:    5/5   ████████  COMPLETE
  Phase 2 — Transactions:  3/4   ██████░░  (T1, T2, T4 done)
  Phase 3 — Documents:     0/3   ░░░░░░░░
  Phase 4 — Payroll:       0/6   ░░░░░░░░
  Phase 5 — Tax Forms:     0/9   ░░░░░░░░
  Phase 6 — Reporting:     0/5   ░░░░░░░░
  Phase 7 — Operations:    1/4   █░░░░░░░  (O1 done)
  TOTAL: 11/34 modules complete

## ENVIRONMENT NOTES
- Python: 3.14.2 (venv at backend/.venv)
- PostgreSQL: local, role 'postgres', database 'ga_cpa'
- DB connection: postgresql+asyncpg://postgres:postgres@localhost:5432/ga_cpa
- Schema: 26 tables, 1 view, 24 audit triggers, 87 seed CoA entries
- Tests: 331 passing (auth:10, auth_endpoints:18, clients:25, coa:28, health:2, journal_entries:40, audit_log:16, qbo_parser:65, vendors:11, bills:28, invoices:33, approvals:21, client_splitter:34)
- Agent prompts: see AGENT_PROMPTS/ (not in this file)

## NEXT TASKS (priority order)
1. TASK-015 — T3 Bank Reconciliation (depends T1+T2, both done)
2. TASK-003 — M3 Chart of Accounts Mapper (depends M1+F1, both done)
3. TASK-017 — D1 Document Upload (depends F4+F5, both done)
4. TASK-020 — P1 Employee Records (depends F4, done)
   Phase 2 nearly complete (3/4). T3, M3, D1, P1 can all run in parallel.

## OPEN COMPLIANCE FLAGS
11 open issues (#1-#11) — all TY2026 rate verification.
See OPEN_ISSUES.md for details.