# Work Queue

All 34 modules broken into agent-sized tasks. One task = one agent session = one git commit.

## Status Key
- `TODO` — not started
- `IN PROGRESS` — agent working on it
- `DONE` — complete and committed
- `BLOCKED` — waiting on dependency

---

## Phase 0 — Migration

### TASK-001
- **Module:** M1 — QB Online CSV parser and validator
- **Depends on:** NONE
- **Compliance risk:** HIGH
- **Estimated complexity:** MEDIUM
- **Agent instructions:** Build a Python module that reads QuickBooks Online CSV exports, validates required columns and data types per MIGRATION_SPEC.md, and returns structured data or a validation error report. Must handle Chart of Accounts, Transaction Detail, Customer List, Invoice List, Payroll Summary, and Employee List CSVs.

### TASK-002
- **Module:** M2 — Client splitter
- **Depends on:** TASK-001
- **Compliance risk:** HIGH
- **Estimated complexity:** MEDIUM
- **Agent instructions:** Build logic to split a single QB Online dataset into isolated per-client record sets using the client name/customer field as the primary key. Handle edge cases: unassigned transactions, transactions referencing multiple clients. Output one dataset per client_id.

### TASK-003
- **Module:** M3 — Chart of accounts mapper
- **Depends on:** TASK-001, TASK-008
- **Compliance risk:** MEDIUM
- **Estimated complexity:** MEDIUM
- **Agent instructions:** Map QuickBooks Online account categories to the Georgia-standard chart of accounts pre-seeded in F2. Build a mapping table with manual override capability. Flag unmappable accounts for CPA review.

### TASK-004
- **Module:** M4 — Transaction history importer
- **Depends on:** TASK-002, TASK-003, TASK-009
- **Compliance risk:** HIGH
- **Estimated complexity:** HIGH
- **Agent instructions:** Import full transaction history from QB CSVs into the general ledger. Transactions must be imported oldest-first, maintain double-entry integrity, and be wrapped in a single DB transaction. Verify debits=credits after import.

### TASK-005
- **Module:** M5 — Invoice and AR history importer
- **Depends on:** TASK-002, TASK-003, TASK-013
- **Compliance risk:** MEDIUM
- **Estimated complexity:** MEDIUM
- **Agent instructions:** Import QB Online invoice history into the invoices and invoice_lines tables. Map customer references to client_id. Preserve payment history. Verify invoice count matches source.

### TASK-006
- **Module:** M6 — Payroll history importer
- **Depends on:** TASK-002, TASK-020
- **Compliance risk:** HIGH
- **Estimated complexity:** HIGH
- **Agent instructions:** Import QB payroll history into payroll_runs and payroll_items tables. Import gross pay only if withholding amounts are missing — flag affected records with [COMPLIANCE] label. Do not calculate retroactive withholding.

### TASK-007
- **Module:** M7 — Migration audit report
- **Depends on:** TASK-001 through TASK-006
- **Compliance risk:** HIGH
- **Estimated complexity:** LOW
- **Agent instructions:** Generate a comprehensive migration audit report covering: records imported per table, records that failed to map, GL balance verification (debits=credits per client), row count comparison vs QB source. Save to /docs/migration/.

---

## Phase 1 — Foundation

### TASK-008 ✓ DONE
- **Module:** F1 — Database schema + migrations
- **Depends on:** NONE
- **Compliance risk:** HIGH
- **Estimated complexity:** HIGH
- **Status:** DONE (2026-03-04, CEO Orchestrator Session 1)
- **Agent instructions:** The schema (001_initial_schema.sql) is already created by the Research Agent. This task applies it to the database, verifies all tables/constraints/triggers work, and writes tests confirming double-entry enforcement and audit trail triggers fire correctly.

### TASK-009 ✓ DONE
- **Module:** F2 — Chart of accounts (Georgia standard)
- **Depends on:** TASK-008
- **Compliance risk:** MEDIUM
- **Estimated complexity:** LOW
- **Status:** DONE (2026-03-04, CEO Orchestrator Session 2)
- **Agent instructions:** Build the seed data and API endpoint for Georgia-standard chart of accounts. Pre-seed accounts covering all four entity types (sole prop, S-Corp, C-Corp, partnership/LLC). Build CRUD endpoints with client_id isolation.

### TASK-010
- **Module:** F3 — General ledger with double-entry
- **Depends on:** TASK-008, TASK-009
- **Compliance risk:** HIGH
- **Estimated complexity:** HIGH
- **Agent instructions:** Build the general ledger service: create journal entries with lines, enforce debits=credits via trigger, post entries to GL. Build API endpoints for journal entry CRUD. Status flow: DRAFT → PENDING_APPROVAL → POSTED. Only CPA_OWNER can post.

### TASK-011 ✓ DONE
- **Module:** F4 — Client management
- **Depends on:** TASK-008
- **Compliance risk:** LOW
- **Estimated complexity:** LOW
- **Status:** DONE (2026-03-04, CEO Orchestrator Session 2)
- **Agent instructions:** Build client CRUD API: create, edit, archive (soft delete), list. Include entity_type tagging. Every query must filter by client_id. Write a test proving Client A queries cannot return Client B data.

### TASK-012 ✓ DONE
- **Module:** F5 — User auth (JWT + roles)
- **Depends on:** TASK-008
- **Compliance risk:** MEDIUM
- **Estimated complexity:** MEDIUM
- **Status:** DONE (2026-03-04, CEO Orchestrator Session 2)
- **Agent instructions:** Build JWT authentication: login endpoint, token generation/validation, role-based middleware (CPA_OWNER vs ASSOCIATE). Log all 403s to permission_log table. Write tests proving ASSOCIATE cannot access CPA_OWNER endpoints.

---

## Phase 2 — Transactions

### TASK-013
- **Module:** T1 — Accounts Payable
- **Depends on:** TASK-010, TASK-011
- **Compliance risk:** MEDIUM
- **Estimated complexity:** MEDIUM
- **Agent instructions:** Build AP module: vendor management, bill entry (DRAFT → PENDING_APPROVAL → APPROVED → PAID), bill payment recording. Each bill posts to GL via journal entry. Client_id isolation on all queries.

### TASK-014
- **Module:** T2 — Accounts Receivable + invoicing
- **Depends on:** TASK-010, TASK-011
- **Compliance risk:** MEDIUM
- **Estimated complexity:** MEDIUM
- **Agent instructions:** Build AR module: invoice creation (DRAFT → PENDING_APPROVAL → SENT → PAID), payment recording, overdue detection. Each invoice posts to GL. PDF invoice generation via WeasyPrint. Client_id isolation.

### TASK-015
- **Module:** T3 — Bank reconciliation
- **Depends on:** TASK-010, TASK-013, TASK-014
- **Compliance risk:** MEDIUM
- **Estimated complexity:** HIGH
- **Agent instructions:** Build bank reconciliation engine: import bank transactions, match against GL entries (auto-match + manual match), calculate reconciled vs statement balance, mark reconciliation complete. Client_id isolation.

### TASK-016
- **Module:** T4 — Transaction approval workflow
- **Depends on:** TASK-010, TASK-012
- **Compliance risk:** HIGH
- **Estimated complexity:** MEDIUM
- **Agent instructions:** Build approval workflow: ASSOCIATE enters transaction (status: PENDING_APPROVAL), CPA_OWNER reviews and approves (status: POSTED) or rejects. Transactions do not affect GL until POSTED. Role check at function level, not just route.

---

## Phase 3 — Documents

### TASK-017
- **Module:** D1 — Document upload
- **Depends on:** TASK-011, TASK-012
- **Compliance risk:** LOW
- **Estimated complexity:** LOW
- **Agent instructions:** Build document upload endpoint: accept PDF/images, store to /data/documents/[client_id]/, save metadata to documents table. Tag documents to client + optionally to a transaction. Client_id isolation.

### TASK-018
- **Module:** D2 — Document viewer
- **Depends on:** TASK-017
- **Compliance risk:** LOW
- **Estimated complexity:** LOW
- **Agent instructions:** Build in-browser document viewer: serve documents via API endpoint with proper MIME types. React component to display PDFs and images inline. No external app dependency.

### TASK-019
- **Module:** D3 — Document search
- **Depends on:** TASK-017
- **Compliance risk:** LOW
- **Estimated complexity:** LOW
- **Agent instructions:** Build document search: filter by client_id, date range, document type, tags. Return paginated results. Client_id isolation.

---

## Phase 4 — Payroll

### TASK-020
- **Module:** P1 — Employee records
- **Depends on:** TASK-011
- **Compliance risk:** LOW
- **Estimated complexity:** LOW
- **Agent instructions:** Build employee CRUD per client: name, SSN (encrypted), filing status, allowances, pay rate, pay type, hire/termination dates. Client_id isolation. SSN must be encrypted at rest.

### TASK-021
- **Module:** P2 — Georgia income tax withholding
- **Depends on:** TASK-020
- **Compliance risk:** HIGH
- **Estimated complexity:** HIGH
- **Agent instructions:** Build Georgia withholding calculator using Form G-4 instructions and DOR withholding tables. Read rates from payroll_tax_tables (parameterized by tax_year and filing_status). Every rate constant must cite source. TDD required.

### TASK-022
- **Module:** P3 — Georgia SUTA calculator
- **Depends on:** TASK-020
- **Compliance risk:** HIGH
- **Estimated complexity:** MEDIUM
- **Agent instructions:** Build SUTA calculator: default 2.7% on first $9,500 wages for new employers. Support per-client custom rates for experienced employers. Read from payroll_tax_tables. Cite source for every rate. TDD required.

### TASK-023
- **Module:** P4 — Federal withholding + FICA + FUTA
- **Depends on:** TASK-020
- **Compliance risk:** HIGH
- **Estimated complexity:** HIGH
- **Agent instructions:** Build federal payroll tax calculators: income tax withholding (IRS Pub 15-T), Social Security (6.2%), Medicare (1.45% + 0.9% additional), FUTA (6.0% - 5.4% credit). All rates from payroll_tax_tables. Cite sources. TDD required.

### TASK-024
- **Module:** P5 — Pay stub generator
- **Depends on:** TASK-020, TASK-021, TASK-022, TASK-023
- **Compliance risk:** MEDIUM
- **Estimated complexity:** MEDIUM
- **Agent instructions:** Build pay stub PDF generator using WeasyPrint. Show gross pay, all deductions (federal, state, FICA, SUTA), net pay, YTD totals. One stub per employee per payroll run.

### TASK-025
- **Module:** P6 — Payroll approval gate
- **Depends on:** TASK-024, TASK-012
- **Compliance risk:** HIGH
- **Estimated complexity:** LOW
- **Agent instructions:** Build payroll finalization gate: only CPA_OWNER can finalize payroll. Verify role at function level AND route level (defense in depth). Write test proving ASSOCIATE cannot finalize even with manipulated JWT.

---

## Phase 5 — Tax Forms

### TASK-026
- **Module:** X1 — Georgia Form G-7
- **Depends on:** TASK-025, TASK-010
- **Compliance risk:** HIGH
- **Estimated complexity:** HIGH
- **Agent instructions:** Build G-7 quarterly withholding return generator. Pull payroll data for quarter, calculate totals, generate PDF matching DOR form layout. Due dates: Apr 30, Jul 31, Oct 31, Jan 31. CPA_OWNER only.

### TASK-027
- **Module:** X2 — Georgia Form 500
- **Depends on:** TASK-010, TASK-033
- **Compliance risk:** HIGH
- **Estimated complexity:** HIGH
- **Agent instructions:** Build Form 500 (individual income tax) data export for sole proprietor clients. Pull Schedule C data from GL, calculate Georgia taxable income. PDF generation. CPA_OWNER only.

### TASK-028
- **Module:** X3 — Georgia Form 600
- **Depends on:** TASK-010, TASK-033
- **Compliance risk:** HIGH
- **Estimated complexity:** HIGH
- **Agent instructions:** Build Form 600 (corporate income tax) data export for C-Corp clients. Pull income/expense data from GL, apply 5.75% rate (parameterized). PDF generation. CPA_OWNER only.

### TASK-029
- **Module:** X4 — Georgia Form ST-3
- **Depends on:** TASK-010, TASK-014
- **Compliance risk:** HIGH
- **Estimated complexity:** MEDIUM
- **Agent instructions:** Build ST-3 (sales tax return) generator for applicable clients. Pull sales data from AR, apply jurisdiction-specific rates. PDF generation. CPA_OWNER only.

### TASK-030
- **Module:** X5 — Federal Schedule C
- **Depends on:** TASK-010, TASK-033
- **Compliance risk:** HIGH
- **Estimated complexity:** MEDIUM
- **Agent instructions:** Build Schedule C data export for sole proprietors. Pull revenue and expense categories from GL, map to Schedule C lines. CPA_OWNER only.

### TASK-031
- **Module:** X6 — Federal Form 1120-S
- **Depends on:** TASK-010, TASK-033
- **Compliance risk:** HIGH
- **Estimated complexity:** HIGH
- **Agent instructions:** Build Form 1120-S data export for S-Corp clients. Map GL data to form lines. CPA_OWNER only.

### TASK-032
- **Module:** X7 — Federal Form 1120
- **Depends on:** TASK-010, TASK-033
- **Compliance risk:** HIGH
- **Estimated complexity:** HIGH
- **Agent instructions:** Build Form 1120 data export for C-Corp clients. Map GL data to form lines. CPA_OWNER only.

### TASK-033
- **Module:** X8 — Federal Form 1065
- **Depends on:** TASK-010
- **Compliance risk:** HIGH
- **Estimated complexity:** HIGH
- **Agent instructions:** Build Form 1065 data export for partnership/LLC clients. Map GL data to form lines including K-1 schedule data. CPA_OWNER only.

### TASK-034
- **Module:** X9 — Tax document checklist generator
- **Depends on:** TASK-026 through TASK-033
- **Compliance risk:** MEDIUM
- **Estimated complexity:** LOW
- **Agent instructions:** Build a per-client, per-entity-type checklist of required tax documents. Based on entity type, list which forms are needed, their due dates, and current completion status. CPA_OWNER only.

---

## Phase 6 — Reporting

### TASK-035
- **Module:** R1 — Profit & Loss
- **Depends on:** TASK-010
- **Compliance risk:** LOW
- **Estimated complexity:** MEDIUM
- **Agent instructions:** Build P&L report: pull revenue and expense accounts from GL for a client within a date range. Display formatted report. Client_id isolation.

### TASK-036
- **Module:** R2 — Balance Sheet
- **Depends on:** TASK-010
- **Compliance risk:** LOW
- **Estimated complexity:** MEDIUM
- **Agent instructions:** Build balance sheet: pull asset, liability, and equity accounts from GL as of a given date. Display formatted report. Client_id isolation.

### TASK-037
- **Module:** R3 — Cash Flow Statement
- **Depends on:** TASK-010
- **Compliance risk:** LOW
- **Estimated complexity:** MEDIUM
- **Agent instructions:** Build cash flow statement: operating, investing, financing activities derived from GL transactions. Client_id isolation.

### TASK-038
- **Module:** R4 — PDF export for reports
- **Depends on:** TASK-035, TASK-036, TASK-037
- **Compliance risk:** LOW
- **Estimated complexity:** LOW
- **Agent instructions:** Add PDF export to all three report types using WeasyPrint. CPA_OWNER only can export. Professional formatting suitable for client delivery.

### TASK-039
- **Module:** R5 — Firm-level dashboard
- **Depends on:** TASK-035, TASK-036, TASK-011
- **Compliance risk:** LOW
- **Estimated complexity:** MEDIUM
- **Agent instructions:** Build firm-level dashboard showing all clients with key metrics: total revenue, total expenses, outstanding AR, upcoming tax deadlines. React frontend component.

---

## Phase 7 — Operations

### TASK-040
- **Module:** O1 — Audit trail viewer
- **Depends on:** TASK-008
- **Compliance risk:** LOW
- **Estimated complexity:** LOW
- **Agent instructions:** Build UI and API to browse the audit_log table. Filter by table, record, user, date range. Read-only — no modifications allowed. Paginated results.

### TASK-041
- **Module:** O2 — Automated local backup
- **Depends on:** TASK-008
- **Compliance risk:** MEDIUM
- **Estimated complexity:** MEDIUM
- **Agent instructions:** Build daily automated pg_dump to /data/backups/ with timestamp naming. Retain last 30 backups, delete older. Log backup status to system_backups table. Can be triggered manually or via cron.

### TASK-042
- **Module:** O3 — Backup restore tool
- **Depends on:** TASK-041
- **Compliance risk:** HIGH
- **Estimated complexity:** MEDIUM
- **Agent instructions:** Build restore tool: list available backups, select one, verify integrity, restore with confirmation prompt. CPA_OWNER only. Must verify backup before restoring. Print recovery steps.

### TASK-043
- **Module:** O4 — System health check
- **Depends on:** TASK-008, TASK-041
- **Compliance risk:** LOW
- **Estimated complexity:** LOW
- **Agent instructions:** Build health check endpoint: verify DB connection, check disk space, check last backup age, report system status. Dashboard widget on frontend.
