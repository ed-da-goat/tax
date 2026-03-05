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
  [x] M3. Chart of accounts mapper (QB categories → Georgia standard)
  [x] M4. Transaction history importer (full history, not just balances)
  [x] M5. Invoice and AR history importer
  [x] M6. Payroll history importer
  [x] M7. Migration audit report (flags any data that didn't map cleanly)

Phase 1 — Foundation
  [x] F1. Database schema + all migrations
  [x] F2. Chart of accounts (Georgia standard categories, pre-seeded)
  [x] F3. General ledger with double-entry enforcement
  [x] F4. Client management (create, edit, archive, entity type tagging)
  [x] F5. User auth (login, JWT, role assignment)

Phase 2 — Transactions
  [x] T1. Accounts Payable (AP)
  [x] T2. Accounts Receivable (AR) + client invoicing
  [x] T3. Bank reconciliation engine
  [x] T4. Transaction approval workflow 
          (ASSOCIATE enters → CPA_OWNER approves → posts to GL)

Phase 3 — Document Management
  [x] D1. Document upload (PDF, images) tagged to client + transaction
  [x] D2. Document viewer (in-browser, no external app)
  [x] D3. Document search by client, date, type

Phase 4 — Payroll (Georgia-specific)
  [x] P1. Employee records (per client)
  [x] P2. Georgia income tax withholding engine
          Source: Georgia Form G-4 instructions + DOR withholding tables
          Tax year: must be parameterized (tables change annually)
  [x] P3. Georgia SUTA calculator
          Default new employer rate: 2.7% on first $9,500 wages
          Must support per-client custom rate (experienced employers)
  [x] P4. Federal withholding + FICA + FUTA calculator
  [x] P5. Pay stub generator (PDF output)
  [x] P6. Payroll approval gate (CPA_OWNER only can finalize)

Phase 5 — Tax Form Exports
  [x] X1. Georgia Form G-7 (quarterly payroll withholding)
          Due: last day of month after quarter end
  [x] X2. Georgia Form 500 (individual income — Schedule C clients)
  [x] X3. Georgia Form 600 (corporate income — C-Corp clients)
  [x] X4. Georgia Form ST-3 (sales tax — applicable clients)
  [x] X5. Federal Schedule C data export (sole proprietors)
  [x] X6. Federal Form 1120-S data export (S-Corps)
  [x] X7. Federal Form 1120 data export (C-Corps)
  [x] X8. Federal Form 1065 data export (partnerships/LLCs)
  [x] X9. Tax document checklist generator (per client, per entity type)

Phase 6 — Reporting
  [x] R1. Profit & Loss (per client, date range selectable)
  [x] R2. Balance Sheet (per client, as-of date selectable)
  [x] R3. Cash Flow Statement (per client)
  [x] R4. PDF export for all reports (CPA_OWNER only)
  [x] R5. Firm-level dashboard (all clients, key metrics)

Phase 7 — Operations
  [x] O1. Audit trail viewer (immutable log of all changes)
  [x] O2. Automated local backup (daily, to /data/backups/)
  [x] O3. Backup restore tool with verification step
  [x] O4. System health check (DB connection, disk space, last backup)

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

## BUILD STATUS (updated 2026-03-04, session 7)

  Phase 0 — Migration:     7/7   ████████  COMPLETE
  Phase 1 — Foundation:    5/5   ████████  COMPLETE
  Phase 2 — Transactions:  4/4   ████████  COMPLETE
  Phase 3 — Documents:     3/3   ████████  COMPLETE
  Phase 4 — Payroll:       6/6   ████████  COMPLETE
  Phase 5 — Tax Forms:     9/9   ████████  COMPLETE
  Phase 6 — Reporting:     5/5   ████████  COMPLETE
  Phase 7 — Operations:    4/4   ████████  COMPLETE
  TOTAL: 34/34 backend modules complete — ALL PHASES COMPLETE

  Frontend Phase 1 — Priority Workflows:  IN PROGRESS
    [x] Shared components (Modal, DataTable, FormField, Toast, Tabs, etc.)
    [x] Utility helpers (format.js — currency, dates, entity types)
    [x] React Query hooks (useApiQuery, useApiMutation)
    [x] Dashboard (firm metrics, client table, API-connected)
    [x] Clients list (CRUD, filters, pagination, add/edit/archive)
    [x] Client Detail (tabs: overview/CoA/JE, quick actions, account modal)
    [x] Journal Entry Form (dynamic line items, balance validation)
    [x] Approval Queue (batch approve/reject, rejection notes)
    [x] Accounts Payable (vendors + bills CRUD, payment recording)
    [x] Accounts Receivable (invoices, approve/pay workflow)
    [x] Bank Reconciliation page
    [x] Documents page
    [x] Employees page
    [x] Payroll page
    [x] Reports page
    [x] Tax Exports page
    [x] Auth fix (synchronous user set on login)

## ENVIRONMENT NOTES
- Python: 3.14.2 (venv at backend/.venv)
- PostgreSQL: local, role 'postgres', database 'ga_cpa'
- DB connection: postgresql+asyncpg://postgres:postgres@localhost:5432/ga_cpa
- Schema: 26 tables, 1 view, 24 audit triggers, 87 seed CoA entries
- Backend tests: 588 passing, 0 xfailed
- Frontend: React 18.3 + Vite 6 + React Router 6 + React Query 5
- Frontend build: 158 modules, 0 errors, vanilla CSS
- Default user: edward@755mortgage.com / admin123 (CPA_OWNER)
- Agent prompts: see AGENT_PROMPTS/ (not in this file)

## NEXT TASKS
ALL 34 BACKEND MODULES COMPLETE. Frontend Phase 1 complete.

Remaining work:
1. CPA_OWNER review of all 11 open compliance flags (OPEN_ISSUES.md)
2. End-to-end integration testing with real QBO export data
3. Frontend Phase 2: remaining pages (Bank Recon, Documents, Employees,
   Payroll, Reports, Tax Exports) — pages exist but need API integration
4. Production deployment preparation

## OPEN COMPLIANCE FLAGS
11 open issues (#1-#11) — all TY2026 rate verification.
See OPEN_ISSUES.md for details.