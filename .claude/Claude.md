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
- Deployment: Mac host + Windows LAN clients (no cloud dependency)
- Version control: Git + GitHub (mandatory for every change)
- Purpose: Replace QuickBooks Online subscription entirely

## TECH STACK
- Frontend: React 19.2 + Vite 6 (fast local dev, no build server needed)
- Backend: Python 3.14.2 + FastAPI (readable, strong accounting libraries)
- Database: PostgreSQL (local instance, ACID compliant for financials)
- Auth: JWT with role-based access control + optional TOTP 2FA
- PDF generation: WeasyPrint (Georgia tax form exports)
- File storage: Local filesystem under /data/documents/[client_id]/
- Migration tool: Custom CSV parser (reads QuickBooks Online exports)
- Encryption: Fernet symmetric encryption for PII at rest (app/crypto.py)
- Email: aiosmtplib with HTML templates (app/services/email.py)
- Reverse proxy: nginx via Homebrew, HTTPS with self-signed cert

## ROLE PERMISSION SCHEMA

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

Phase 0 — Migration (run ONCE before any other phase)
  [x] M1. QuickBooks Online CSV parser and validator
  [x] M2. Client splitter (one QB account -> isolated client ledgers)
  [x] M3. Chart of accounts mapper (QB categories -> Georgia standard)
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
          (ASSOCIATE enters -> CPA_OWNER approves -> posts to GL)

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
  [x] X10. W-2 generation (aggregate payroll -> W-2 boxes, PDF)
  [x] X11. 1099-NEC generation (vendor payments -> 1099-NEC, PDF)

Phase 6 — Reporting
  [x] R1. Profit & Loss (per client, date range selectable)
  [x] R2. Balance Sheet (per client, as-of date selectable)
  [x] R3. Cash Flow Statement (per client)
  [x] R4. PDF export for all reports (CPA_OWNER only)
  [x] R5. Firm-level dashboard (all clients, key metrics)
  [x] R6. AR Aging Report (0-30, 31-60, 61-90, 90+ buckets)
  [x] R7. AP Aging Report (0-30, 31-60, 61-90, 90+ buckets)

Phase 7 — Operations
  [x] O1. Audit trail viewer (immutable log of all changes)
  [x] O2. Automated local backup (daily, to /data/backups/)
  [x] O3. Backup restore tool with verification step
  [x] O4. System health check (DB connection, disk space, last backup)

Phase 8 — Feature Gaps
  [x] FG1. W-2 generation (payroll -> W-2 boxes, single/batch PDF)
  [x] FG2. 1099-NEC generation (vendor payments -> 1099-NEC, PDF)
  [x] FG3. AR/AP Aging Reports (bucket classification, PDF export)
  [x] FG4. Check Printing (auto-increment check numbers, PDF)

Phase 9 — Extended Features (added post-Phase 8)
  [x] E1. Time tracking (per client, per employee, billable hours)
  [x] E2. Workflow / engagement management (Kanban board)
  [x] E3. Client portal (messages, document sharing)
  [x] E4. Year-end close (service + router)
  [x] E5. CSV/Excel export for all reports
  [x] E6. Recurring transactions (templates, auto-generate)
  [x] E7. Email service (aiosmtplib, templates, invoice/statement send)
  [x] E8. Client statements (service, PDF, email)
  [x] E9. 2FA (TOTP setup/verify/disable, login flow)
  [x] E10. Global search (backend + frontend Cmd+K modal)
  [x] E11. Invoice/bill PDF generation
  [x] E12. Forgot password (reset tokens, email, frontend page)
  [x] E13. Bulk import (CSV upload for bills/invoices)
  [x] E14. Soft delete restoration (list archived, restore endpoints)
  [x] E15. Direct deposit + NACHA file generation
  [x] E16. Due dates dashboard
  [x] E17. Service billing (hourly rate management)
  [x] E18. Fixed assets tracking
  [x] E19. Budget management
  [x] E20. Contacts management
  [x] E21. Engagements tracking

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
- Missing dependency -> create a typed stub, log [BLOCKER] in
  OPEN_ISSUES.md, proceed with your module using the stub.
- Uncertain Georgia tax rule -> do NOT guess. Write:
  # COMPLIANCE REVIEW NEEDED: [describe uncertainty]
  Add to OPEN_ISSUES.md with label [COMPLIANCE] and assign to CPA_OWNER.
- Failing test -> do not commit. Either fix it or mark as known-failing
  with @pytest.mark.xfail and a comment explaining why, then log it.
- Design conflict with existing code -> stop. Document in OPEN_ISSUES.md
  under [CONFLICT] before touching any existing module.
- Disk or DB error during migration -> halt, do not partially import.
  QB data must be preserved. Log error, print recovery instructions.

## BUILD STATUS (updated 2026-03-06)

  Phase 0 — Migration:      7/7   ████████  COMPLETE
  Phase 1 — Foundation:     5/5   ████████  COMPLETE
  Phase 2 — Transactions:   4/4   ████████  COMPLETE
  Phase 3 — Documents:      3/3   ████████  COMPLETE
  Phase 4 — Payroll:        6/6   ████████  COMPLETE
  Phase 5 — Tax Forms:     11/11  ████████  COMPLETE (+W-2, 1099-NEC)
  Phase 6 — Reporting:      7/7   ████████  COMPLETE (+AR/AP Aging)
  Phase 7 — Operations:     4/4   ████████  COMPLETE
  Phase 8 — Feature Gaps:   4/4   ████████  COMPLETE (W-2, 1099, Aging, Checks)
  Phase 9 — Extended:      21/21  ████████  COMPLETE
  TOTAL: 59/59 modules complete — ALL PHASES COMPLETE

  Frontend:  28 pages, 11+ shared components  COMPLETE
    [x] Shared components (Modal, DataTable, FormField, Toast, Tabs, etc.)
    [x] Utility helpers (format.js — currency, dates, entity types)
    [x] React Query hooks (useApiQuery, useApiMutation)
    [x] Dashboard (firm metrics, revenue chart, due dates, activity feed)
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
    [x] Reports page (CSV/Excel/PDF export)
    [x] Tax Exports page
    [x] Login page (2FA TOTP support)
    [x] Password reset page
    [x] Global search (Cmd+K modal)
    [x] Audit trail viewer page
    [x] System admin page
    [x] Time tracking, Workflows, Client portal, Due dates
    [x] Service billing, Fixed assets, Budgets, Contacts, Engagements
    [x] Unsaved changes warning hook
    [x] Mobile responsive CSS

  Backend:   34 routers, 257+ API endpoints, 50+ ORM models, 58 DB tables
  Tests:     900 passing (pytest), 0 xfailed

## ENVIRONMENT NOTES
- Python: 3.14.2 (venv at backend/.venv)
- PostgreSQL: local, role 'postgres', database 'ga_cpa'
- DB connection: see backend/.env (password changed from default)
- Schema: 59 tables (incl. password_reset_tokens), 25 audit triggers, 38 hard-delete triggers
- DB migrations: 003 (checks), 004 (audit PII), 005 (recurring), 006 (reset tokens), 007 (Phase 9 hard-delete triggers)
- Default user: edward@755mortgage.com / admin123 (CPA_OWNER)

## KEY FILE PATHS
- Backend root: backend/app/
- Router registry: backend/app/routers/__init__.py
- Model registry: backend/app/models/__init__.py
- Config: backend/app/config.py (reads from backend/.env)
- Encryption: backend/app/crypto.py (encrypt_pii/decrypt_pii)
- Migrations: backend/db/migrations/ (001-006)
- Frontend root: frontend/src/
- CSS (single file): frontend/src/styles/index.css
- Deploy scripts: deploy/
- Audit trigger function: fn_audit_log() (PostgreSQL)

## COMMANDS
- Run tests: cd backend && .venv/bin/python -m pytest --tb=short -q
- Build frontend: cd frontend && npm run build
- Start backend dev: cd backend && .venv/bin/python -m uvicorn app.main:app --reload
- Start frontend dev: cd frontend && npm run dev
- Seed test data: cd backend && .venv/bin/python scripts/seed_test_data.py --reset
- DB access: PGPASSWORD=<see .env> psql -U postgres -d ga_cpa

## DEPLOYMENT (updated 2026-03-06)
- Platform: macOS (Darwin 24.6.0, Apple Silicon)
- Reverse proxy: nginx via Homebrew, HTTPS with self-signed cert
- Backend service: launchd (com.gacpa.backend) — auto-start, auto-restart
- Nightly backup: launchd (com.gacpa.backup) — 2:00 AM, 30-day retention
- DB maintenance: launchd (com.gacpa.dbmaint) — weekly VACUUM/REINDEX
- Log rotation: launchd (com.gacpa.logrotate) — daily rotation
- Access: https://localhost (local), https://<LAN-IP> (LAN clients)
- LAN: Windows clients connect via browser to Mac host IP over HTTPS
- Firewall: setup.sh auto-adds nginx to macOS Application Firewall
- Cert: auto-regenerates if LAN IP changes (SAN mismatch detection)
- CORS: auto-updates in .env when IP changes during setup
- Deploy scripts: deploy/setup.sh (install), deploy/teardown.sh (uninstall)
- Logs: deploy/logs/ (permissions 600, dir 700)
- Certs: deploy/certs/ (self-signed, 10-year validity)
- Windows cert trust: see deploy/windows-trust.md
- Test data seed: backend/scripts/seed_test_data.py (--reset to wipe+reseed)
- DEBUG=false in .env (docs/redoc/openapi disabled, Secure cookies, SameSite=Strict)

## SECURITY HARDENING (completed 2026-03-06)
Full security audit performed. 11 issues found and fixed:
  [x] Password reset moved from URL query string to JSON POST body
  [x] Reset tokens stored in DB (migration 006), not in-memory
  [x] Default secrets removed from config.py — app crashes if .env missing
  [x] Log file permissions restricted to 600 (dir 700)
  [x] SameSite=Strict enforced always (not just non-DEBUG)
  [x] JWT expiry reduced from 60 to 30 minutes
  [x] 2FA endpoints rate-limited (5/minute)
  [x] TOTP valid_window=0 (current window only, ~30 seconds)
  [x] GPG passphrase passed via --passphrase-fd 0 (not visible in ps)
  [x] Bulk import capped at 5,000 rows per CSV
  [x] DEBUG=false set in .env (disables /docs, /redoc, /openapi.json)

What's already solid (no changes needed):
  - bcrypt password hashing with timing-attack mitigation
  - httpOnly + Secure + SameSite=Strict cookies
  - Full security header suite (HSTS, X-Frame-Options, CSP)
  - SQLAlchemy parameterized queries (no SQL injection)
  - Defense-in-depth role checks (route + function level)
  - Login rate limiting (per-IP and per-email)
  - Fernet encryption for PII at rest (SSN, tax ID)
  - Encrypted backups (GPG AES-256)
  - Request body size limits
  - No XSS vectors (React auto-escapes, no dangerouslySetInnerHTML)

## AGENT SYSTEM

All agent prompts live in AGENT_PROMPTS/. Agents are designed to be
run as independent Claude Code sessions, each with a specific role.

### Agent Index

| # | Agent | File | Purpose | When to Run |
|---|-------|------|---------|-------------|
| CEO | CEO Orchestrator | `CEO_ORCHESTRATOR.md` | Coordinates all agents, assigns tasks, detects conflicts | START of every work session |
| 00 | Research Agent | `00_RESEARCH_AGENT.md` | Project blueprint, schema, folder structure, work queue | ONCE at project start |
| 01 | Migration Agent | `01_MIGRATION_AGENT.md` | QuickBooks Online CSV import (validate, dry-run, import) | ONCE per QB export batch |
| 02 | Builder Agent | `02_BUILDER_AGENT_TEMPLATE.md` | Template for all module implementations | Copy per module |
| 03 | Review Agent | `03_REVIEW_AGENT.md` | QA review of Research Agent output | PARALLEL with Agent 00 |
| 04 | GA Tax Research | `04_GEORGIA_TAX_RESEARCH_AGENT.md` | Georgia DOR rates, withholding tables, form specs | ONCE before payroll modules |
| 05 | QB Format Research | `05_QB_FORMAT_RESEARCH_AGENT.md` | QuickBooks Online CSV export format analysis | ONCE before Migration Agent |
| -- | Test Data Generator | `generate_test_data.md` | Generate fake QBO CSV files for end-to-end testing | As needed for testing |

### Builder Agent Instances (AGENT_PROMPTS/builders/)

Each file is a copy of the Builder Template (Agent 02) filled in for
a specific module. All 43 builder instances exist:

  Phase 0 — Migration (M1-M7):
    M1_QB_CSV_PARSER, M2_CLIENT_SPLITTER, M3_CHART_OF_ACCOUNTS_MAPPER,
    M4_TRANSACTION_HISTORY_IMPORTER, M5_INVOICE_AR_HISTORY_IMPORTER,
    M6_PAYROLL_HISTORY_IMPORTER, M7_MIGRATION_AUDIT_REPORT

  Phase 1 — Foundation (F1-F5):
    F1_DATABASE_SCHEMA, F2_CHART_OF_ACCOUNTS, F3_GENERAL_LEDGER,
    F4_CLIENT_MANAGEMENT, F5_USER_AUTH

  Phase 2 — Transactions (T1-T4):
    T1_ACCOUNTS_PAYABLE, T2_ACCOUNTS_RECEIVABLE,
    T3_BANK_RECONCILIATION, T4_TRANSACTION_APPROVAL_WORKFLOW

  Phase 3 — Documents (D1-D3):
    D1_DOCUMENT_UPLOAD, D2_DOCUMENT_VIEWER, D3_DOCUMENT_SEARCH

  Phase 4 — Payroll (P1-P6):
    P1_EMPLOYEE_RECORDS, P2_GA_INCOME_TAX_WITHHOLDING,
    P3_GA_SUTA_CALCULATOR, P4_FEDERAL_WITHHOLDING_FICA_FUTA,
    P5_PAY_STUB_GENERATOR, P6_PAYROLL_APPROVAL_GATE

  Phase 5 — Tax Exports (X1-X9):
    X1_GA_FORM_G7, X2_GA_FORM_500, X3_GA_FORM_600, X4_GA_FORM_ST3,
    X5_FEDERAL_SCHEDULE_C, X6_FEDERAL_FORM_1120S,
    X7_FEDERAL_FORM_1120, X8_FEDERAL_FORM_1065,
    X9_TAX_DOCUMENT_CHECKLIST

  Phase 6 — Reporting (R1-R5):
    R1_PROFIT_AND_LOSS, R2_BALANCE_SHEET, R3_CASH_FLOW_STATEMENT,
    R4_PDF_EXPORT_REPORTS, R5_FIRM_LEVEL_DASHBOARD

  Phase 7 — Operations (O1-O4):
    O1_AUDIT_TRAIL_VIEWER, O2_AUTOMATED_LOCAL_BACKUP,
    O3_BACKUP_RESTORE_TOOL, O4_SYSTEM_HEALTH_CHECK

### How to Use Agents

1. Open a new Claude Code session
2. Run /init to load this CLAUDE.md
3. Copy the relevant agent prompt into the conversation
4. The agent follows its instructions autonomously
5. After completion, check AGENT_LOG.md for the session summary

For multi-terminal parallel builds:
1. Run the CEO Orchestrator first — it tells you which agents to run
2. Open one terminal per assigned agent
3. Never run two agents that write to the same files
4. Run CEO Orchestrator again when all terminals finish

### Agent Descriptions

**CEO Orchestrator** — Team coordinator. Does not write code.
Reads all status files (CLAUDE.md, AGENT_LOG.md, OPEN_ISSUES.md,
WORK_QUEUE.md, ARCHITECTURE.md). Prints a build dashboard showing
completion percentages per phase. Identifies all available work by
analyzing the dependency graph. Assigns tasks to terminals, avoiding
file conflicts. Detects stale blockers, compliance gaps, dependency
violations, and uncommitted changes. Updates AGENT_LOG.md with
session report. Tells the CPA exactly what to do next.
Decision rules: parallelize tasks that touch different files; serialize
Migration (Phase 0) tasks; recommend stopping if >3 compliance flags
are unresolved or tests are failing.

**Research Agent (00)** — Run ONCE at project start.
Produces the full project blueprint: SETUP.md (numbered CLI
instructions), MIGRATION_SPEC.md (QB CSV column mappings, client
splitting logic, rollback procedure), database schema
(001_initial_schema.sql with all constraints), folder structure
with README.md files, WORK_QUEUE.md (all 34+ tasks as a DAG with
dependencies and compliance risk ratings), ARCHITECTURE.md
(dependency map), AGENT_LOG.md, OPEN_ISSUES.md, and
docs/GEORGIA_COMPLIANCE.md. Commits and pushes when done.
Status: COMPLETE (committed in ac3090c).

**Migration Agent (01)** — Run ONCE per QB export batch.
Highest-risk operation — imports real client financial history.
Step 1: Validates every CSV (required columns, balanced debits/credits,
no duplicate IDs). Step 2: Dry run in a ROLLBACK transaction, prints
report of client/transaction/invoice/payroll counts for CPA review.
Step 3: Live import only after explicit CONFIRM — wraps everything
in a single transaction (clients -> CoA -> balances -> transactions ->
invoices -> payroll). Rolls back completely on any failure. Step 4:
Verification (GL balance check, count matching, spot-checks).
Handles client name collisions by asking CPA to resolve manually.
Flags missing payroll withholding as [COMPLIANCE] — never calculates
retroactive withholding.

**Builder Agent Template (02)** — Copy per module.
Generic template for all module implementations. Fill in [BRACKETS]
with specific module info from WORK_QUEUE.md. Follows strict order:
1) Load memory (read all coordination files). 2) Verify dependencies
(stub if missing, log blocker). 3) Build (TDD for HIGH compliance
risk modules — test zero, max, GA edge case, multi-client isolation).
4) Role enforcement check (prove ASSOCIATE can't call CPA_OWNER
endpoints). 5) Run all tests — must pass before commit. 6) Commit
and push. 7) Update AGENT_LOG.md, WORK_QUEUE.md, OPEN_ISSUES.md,
CLAUDE.md checklist. Prints session summary at end.
Error handling: partial work gets [WIP] prefix commit; compliance
uncertainty stops the build and flags [COMPLIANCE]; permission
uncertainty defaults to MORE restrictive.

**Review Agent (03)** — Run parallel with Research Agent.
QA reviewer — does not write code. Monitors Research Agent output
files and checks each against detailed criteria:
- SETUP.md: commands copy-pasteable, verify steps exist
- MIGRATION_SPEC.md: QB menu paths accurate, edge cases covered,
  rollback is real SQL ROLLBACK
- 001_initial_schema.sql: client_id UUID on every table, audit_log
  complete, CHECK constraint on transactions, parameterized tax tables,
  ON DELETE RESTRICT (not CASCADE), proper indexes
- WORK_QUEUE.md: all modules present, valid DAG, sensible compliance
  risk ratings (HIGH for GL/payroll/tax, MEDIUM for AP/AR/approval,
  LOW for docs/dashboard/health)
- ARCHITECTURE.md: matches WORK_QUEUE dependencies
Outputs PASS/ISSUES FOUND per file. Flags CRITICAL issues as blockers.
Saves combined report to docs/reviews/research_agent_review.md.

**Georgia Tax Research Agent (04)** — Run ONCE before payroll modules.
Gathers exact tax rates, withholding tables, form specs, and filing
deadlines from Georgia DOR. Every number includes source citation
(authority, document, tax year, URL, verification date).
Produces: georgia_withholding_tables.md (G-4 brackets, filing statuses,
exemptions, supplemental rate), georgia_suta_rates.md (new employer
2.7%, $9,500 base, experienced employer range), federal_payroll_rates.md
(SS/Medicare/FUTA rates and bases), georgia_form_specs.md (G-7, 500,
600, ST-3 — fields, due dates, e-file thresholds),
rate_change_protocol.md (when GA announces changes, update procedure),
QUICK_REFERENCE.md (single-page summary for builders).
Unverifiable rates get [UNVERIFIED] flag and OPEN_ISSUES.md entry.

**QB Format Research Agent (05)** — Run ONCE before Migration Agent.
Documents exact CSV export formats from QuickBooks Online for all
data types: Chart of Accounts, Transactions (General Journal),
Customer/Client List, Invoices, Payroll, Vendors, Bills/AP.
For each: QBO menu path, exact CSV column headers, data types,
mapping to our schema, sample rows. Produces column_mapping.md
(comprehensive QBO-to-DB mapping table with [UNMAPPED] and
[NO_SOURCE] flags), client_splitting_logic.md (algorithm for
one-QBO-account-to-N-client-ledgers, edge cases), qbo_known_issues.md
(encoding, row limits, date ranges, deleted records, truncation).
Also creates scripts/generate_sample_qbo_data.py for testing
without real client data.

**Test Data Generator** — Run as needed.
Generates 32 fake QBO CSV files (4 clients x 8 file types) for
end-to-end testing of the full migration + accounting pipeline.
Clients: Peachtree Landscaping LLC (sole prop), Atlanta Tech
Solutions Inc (S-Corp), Southern Manufacturing Corp (C-Corp),
Buckhead Partners Group (partnership/LLC). Each has CoA, transactions,
customers, invoices, vendors, employees, payroll summary, and
general journal. Data is Georgia-specific (real city names, ZIP codes),
financially consistent (trial balance roughly balanced), and
entity-type appropriate (owner draws for sole prop, shareholder
distributions for S-Corp, etc.). No real PII.

## NEXT TASKS
ALL 59 MODULES COMPLETE. Frontend complete (28 pages).
Deployment complete (macOS launchd + nginx HTTPS + nightly backup).
Security hardening complete (11/11 audit findings fixed).
LAN cross-compatibility complete (firewall, IP-aware cert, Windows trust docs).
Test data seeded (4 clients, all entity types, all workflow statuses).

Remaining work:
1. CPA_OWNER review of all 11 open compliance flags (OPEN_ISSUES.md)
2. End-to-end integration testing with real QBO export data
3. Team onboarding: create ASSOCIATE accounts, migrate first real client
4. Trust self-signed cert on Windows machines (see deploy/windows-trust.md)
5. Frontend pages: recurring templates manager, year-end close UI
6. Deferred features: Plaid bank feeds (paid API), document OCR (Tesseract)

## OPEN COMPLIANCE FLAGS
11 open compliance issues (#1-#11) — all TY2026 rate verification.
6 resolved bug issues (#18-#23) — backend audit fixes.
See OPEN_ISSUES.md for details.

## PHASE 8 — FEATURE GAP DETAILS

### W-2 Generation (X10/FG1)
- Endpoints: GET /api/v1/tax/clients/{id}/w2, w2/{emp}/pdf, w2/pdf
- Service: app/services/payroll/w2_generator.py
- Pay date method, SS wage base capped, substitute form label
- COMPLIANCE REVIEW NEEDED: Verify 2026 SS wage base ($168,600)

### 1099-NEC Generation (X11/FG2)
- Endpoints: GET /api/v1/tax/clients/{id}/1099-nec, 1099-nec/{v}/pdf, 1099-nec/pdf
- Service: app/services/tax_exports_1099.py
- $600 IRS threshold, only 1099-eligible vendors, substitute form label

### AR/AP Aging Reports (R6-R7/FG3)
- Endpoints: GET /api/v1/reports/clients/{id}/ar-aging, ar-aging/pdf, ap-aging, ap-aging/pdf
- Service: app/services/aging.py
- Buckets: Current, 1-30, 31-60, 61-90, 90+
- AR: SENT/OVERDUE invoices; AP: APPROVED bills

### Check Printing (FG4)
- Endpoints: POST .../bills/{id}/payments/{pid}/print-check
- Sequence: GET/PUT /api/v1/clients/{id}/check-sequence
- Service: app/services/check_printing.py, app/services/check_sequence.py
- Auto-increment from 1001, atomic via INSERT ON CONFLICT
- Reprint uses same check_number (no double-allocation)
- Migration: db/migrations/003_w2_1099_aging_checks.sql
