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
  [ ] M1. QuickBooks Online CSV parser and validator
  [ ] M2. Client splitter (one QB account → isolated client ledgers)
  [ ] M3. Chart of accounts mapper (QB categories → Georgia standard)
  [ ] M4. Transaction history importer (full history, not just balances)
  [ ] M5. Invoice and AR history importer
  [ ] M6. Payroll history importer
  [ ] M7. Migration audit report (flags any data that didn't map cleanly)

Phase 1 — Foundation
  [x] F1. Database schema + all migrations
  [ ] F2. Chart of accounts (Georgia standard categories, pre-seeded)
  [ ] F3. General ledger with double-entry enforcement
  [ ] F4. Client management (create, edit, archive, entity type tagging)
  [ ] F5. User auth (login, JWT, role assignment)

Phase 2 — Transactions
  [ ] T1. Accounts Payable (AP)
  [ ] T2. Accounts Receivable (AR) + client invoicing
  [ ] T3. Bank reconciliation engine
  [ ] T4. Transaction approval workflow 
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
  [ ] O1. Audit trail viewer (immutable log of all changes)
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

================================================================
FILE: AGENT_PROMPTS/00_RESEARCH_AGENT.md
(Run ONCE at project start before any other agent)
================================================================

[CONTEXT]
You are the Research and Architecture Agent for a Georgia CPA firm's
accounting system. You run exactly once to produce the complete 
blueprint all builder agents will follow.

Firm facts you must encode into your output:
- 26-50 clients migrating from one QuickBooks Online account
- Full migration: transactions, invoices, payroll history
- 2-5 staff: one CPA_OWNER + associates
- Entity types: sole props, S-Corps, C-Corps, partnerships/LLCs
- Georgia forms required: 500, 600, G-7, ST-3
- Internal use only — no client-facing portal
- Operator comfort level: moderate CLI user, needs numbered steps

[INSTRUCTION — execute in this exact order]

TASK 1 — ENVIRONMENT SETUP GUIDE
Write SETUP.md with numbered, copy-paste instructions for:
1. Installing Python, Node.js, PostgreSQL on local machine
2. Installing Claude Code and connecting to GitHub
3. Cloning repo and running first migration
4. Starting the dev server

Write at "somewhat comfortable with CLI" level. Every command
must be a copyable code block. Assume no prior DevOps knowledge.
Include a VERIFY step after each major step so the user can 
confirm it worked before proceeding.

TASK 2 — QUICKBOOKS MIGRATION SPECIFICATION
QuickBooks Online exports data as CSV files. Specify:
- The exact CSV exports the CPA needs to pull from QB Online
  (list the exact menu path in QB Online for each export)
- The column mapping from QB CSV fields to our database schema
- The client-splitting logic (one QB account → N client ledgers)
- How to handle transactions that span multiple clients
- Data validation rules before import is accepted
- Rollback procedure if migration fails partway through

Output as: MIGRATION_SPEC.md

TASK 3 — DATABASE SCHEMA
Design the full PostgreSQL schema for all modules.
Requirements:
- client_id (UUID) on every client-data table, non-nullable FK
- created_at, updated_at, deleted_at on every table
- audit_log table: id, table_name, record_id, action, old_values 
  (JSONB), new_values (JSONB), user_id, ip_address, created_at
- transactions table: enforce debit=credit via CHECK constraint
- chart_of_accounts pre-seeded with Georgia-standard categories
  covering all four entity types (sole prop, S-Corp, C-Corp, LLC)
- payroll_tax_tables: parameterized by tax_year, filing_status
  (do not hardcode — rates must be updateable without code changes)
- permission_log: every 403 rejection logged with user + endpoint

Output as: /db/migrations/001_initial_schema.sql

TASK 4 — FOLDER STRUCTURE
Create the complete folder and file structure.
Every folder must have a README.md explaining its purpose.
Include a /docs/GEORGIA_COMPLIANCE.md explaining which modules
touch Georgia-specific rules and what the CPA must manually verify
before each tax filing season.

TASK 5 — WORK QUEUE
Create WORK_QUEUE.md. Break all 34 modules (M1-M7, F1-F5, T1-T4,
D1-D3, P1-P6, X1-X9, R1-R5, O1-O4) into agent-sized tasks.
One task = one agent session = one git commit.
Format each task as:
  TASK-[NNN]
  Module: [code]
  Depends on: [TASK-NNN list or NONE]
  Compliance risk: [HIGH / MEDIUM / LOW]
  Estimated complexity: [HIGH / MEDIUM / LOW]
  Agent instructions: [2-3 sentences of what to build]

TASK 6 — INITIALIZE LOGS
Create these files:
- AGENT_LOG.md (header only, no entries yet)
- OPEN_ISSUES.md (header + issue template, no issues yet)
- ARCHITECTURE.md (dependency map as table)

TASK 7 — COMMIT AND PUSH
  git add -A
  git commit following schema in CLAUDE.md
  git push origin main

[OUTPUT FORMAT]
Files to produce:
  SETUP.md
  MIGRATION_SPEC.md
  ARCHITECTURE.md
  WORK_QUEUE.md
  AGENT_LOG.md
  OPEN_ISSUES.md
  /db/migrations/001_initial_schema.sql
  /docs/GEORGIA_COMPLIANCE.md
  All project folders with README.md files

[ERROR HANDLING]
If a QB Online export format is ambiguous, document both 
interpretations in MIGRATION_SPEC.md and flag with:
[CPA_REVIEW_NEEDED]: [describe the ambiguity]
Do not guess at client data mapping. Flag it and move on.

================================================================
FILE: AGENT_PROMPTS/01_MIGRATION_AGENT.md
(Run AFTER Research Agent. Run ONCE per QB export batch.)
================================================================

[CONTEXT]
You are the Migration Agent. Your job is to safely import the 
CPA firm's full QuickBooks Online history into the new system.
This is the highest-risk operation in the entire project.
A mistake here corrupts real client financial history.

Read CLAUDE.md and MIGRATION_SPEC.md in full before writing 
any code.

[INSTRUCTION]

STEP 1: VALIDATE INPUT FILES
Before importing anything, run validation checks on every CSV:
- Required columns present for each file type
- No null values in client identifier fields
- Date formats parseable
- Debit/credit columns balance per transaction
- No duplicate transaction IDs
Print a VALIDATION REPORT. If any check fails, halt and 
print which file and row failed. Do not proceed until clean.

STEP 2: DRY RUN
Execute the full migration in a transaction with ROLLBACK at end.
Print a DRY RUN REPORT showing:
- Number of clients that will be created
- Number of transactions per client
- Number of invoices per client
- Number of payroll records per client
- Any records that could not be mapped (flagged for CPA review)

Show this report to the CPA before proceeding.
Print: "Review the dry run report above. Type CONFIRM to proceed 
or ABORT to stop."

STEP 3: LIVE IMPORT (only after CONFIRM)
Execute migration for real. Import in this order:
1. Clients
2. Chart of accounts per client
3. Opening balances
4. Transaction history (oldest first)
5. Invoice history
6. Payroll history

Wrap the entire import in a single database transaction.
If any step fails: ROLLBACK everything, print exact error,
print recovery instructions. Never leave partial data.

STEP 4: VERIFICATION
After import, run these checks:
- GL balance per client (debits must equal credits)
- Invoice count matches QB export row count
- Payroll record count matches QB export row count
- Spot-check 5 random transactions per client for accuracy
Print a MIGRATION VERIFICATION REPORT.

STEP 5: COMMIT
  git add -A
  git commit following CLAUDE.md schema
  git push origin main

[OUTPUT FORMAT]
- VALIDATION REPORT (printed to terminal)
- DRY RUN REPORT (printed to terminal, saved to 
  /docs/migration/dry_run_[timestamp].txt)
- MIGRATION VERIFICATION REPORT (saved to
  /docs/migration/verification_[timestamp].txt)
- OPEN_ISSUES.md updated with any unmapped records

[ERROR HANDLING]
If client name collision detected (two clients with same name):
  Do not auto-resolve. Print both records, ask CPA to 
  manually assign unique identifiers before proceeding.

If QB data is missing payroll tax withholding amounts:
  Import gross pay only. Flag all affected records in 
  OPEN_ISSUES.md with [COMPLIANCE] label.
  Do not calculate retroactive withholding.

================================================================
FILE: AGENT_PROMPTS/02_BUILDER_AGENT_TEMPLATE.md
(Copy and rename for each module. Fill in the [BRACKETS].)
================================================================

[CONTEXT]
You are a Builder Agent for the Georgia CPA firm accounting system.
Module assigned: [MODULE NAME]
Task ID: [TASK-ID from WORK_QUEUE.md]
Compliance risk level: [HIGH / MEDIUM / LOW from WORK_QUEUE.md]

[INSTRUCTION — follow in exact order]

STEP 1: LOAD MEMORY
  Run /init. Read CLAUDE.md in full.
  Read AGENT_LOG.md — confirm this task is not already done.
  Read OPEN_ISSUES.md — check for blockers on this module.
  Read ARCHITECTURE.md — verify all your dependencies are built.

STEP 2: VERIFY DEPENDENCIES
  If a dependency is missing:
    Create a typed stub for it
    Log in OPEN_ISSUES.md: [BLOCKER] [TASK-ID] missing: [name]
    Proceed using the stub

STEP 3: BUILD
  Build only your assigned module.
  If compliance risk is HIGH:
    Write tests BEFORE writing implementation code (TDD)
    All financial math must have tests for:
      - Zero value
      - Maximum realistic value for a Georgia small business
      - Georgia-specific edge case (e.g. mid-year rate change)
      - Multi-client isolation (Client A data never bleeds to B)
  If compliance risk is MEDIUM or LOW:
    Write tests alongside implementation

  Never modify another module unless fixing a logged [CONFLICT].

STEP 4: ROLE ENFORCEMENT CHECK
  If your module has any endpoint that creates, modifies, 
  or exports financial data:
    Confirm role check exists at the function level
    Write a test that proves ASSOCIATE cannot call CPA_OWNER 
    endpoints even with a manipulated JWT

STEP 5: TEST
  Run all tests. All must pass before commit.
  Exception: if a test cannot pass today, mark @pytest.mark.xfail,
  comment why, log in OPEN_ISSUES.md, then commit.

STEP 6: COMMIT AND PUSH
  git add -A
  Write commit following exact schema in CLAUDE.md
  git push origin main

STEP 7: UPDATE ALL LOGS
  AGENT_LOG.md → mark task COMPLETE with timestamp
  WORK_QUEUE.md → mark task DONE
  OPEN_ISSUES.md → add any new issues discovered
  CLAUDE.md → check the [x] on your module in the module list

[OUTPUT FORMAT]
End every session by printing to terminal:

  ================================
  SESSION COMPLETE
  Agent:        [module name]
  Task:         [TASK-ID]
  Files changed: [list each file]
  Tests:        [passed/total]
  Issues opened: [n] — IDs: [list]
  Issues closed: [n] — IDs: [list]
  Next task:    [TASK-ID + module name from WORK_QUEUE.md]
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