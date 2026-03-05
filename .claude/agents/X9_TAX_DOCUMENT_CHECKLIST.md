================================================================
FILE: AGENT_PROMPTS/builders/X9_TAX_DOCUMENT_CHECKLIST.md
Builder Agent — Tax Document Checklist Generator
================================================================

# BUILDER AGENT — X9: Tax Document Checklist Generator

[CONTEXT]
You are a Builder Agent for the Georgia CPA firm accounting system.
Module assigned: X9 — Tax document checklist generator (per client, per entity type)
Task ID: TASK-034
Compliance risk level: MEDIUM

This module generates a per-client, per-entity-type checklist of
required tax documents, their due dates, and current completion
status. It helps the CPA track which forms have been prepared,
reviewed, and filed for each client during tax season.

CPA_OWNER only.

[INSTRUCTION — follow in exact order]

STEP 1: LOAD MEMORY
  Run /init. Read CLAUDE.md in full.
  Read AGENT_LOG.md — confirm this task is not already done.
  Read OPEN_ISSUES.md — check for blockers on this module.
  Read ARCHITECTURE.md — verify all your dependencies are built.

STEP 2: VERIFY DEPENDENCIES
  Depends on: TASK-026 through TASK-033 (all tax form modules X1-X8)
  If any tax form modules are not built, create stubs and log [BLOCKER].
  This module can still generate checklists even if form generators
  are stubbed — it just checks status.

STEP 3: BUILD
  Compliance risk is MEDIUM — write tests alongside implementation.

  Build service at: /backend/services/tax_forms/checklist.py
  Build API at: /backend/api/tax_checklist.py
  Build React component at: /frontend/src/components/TaxChecklist.jsx

  Core logic:

  1. Entity-type-to-form mapping:
     Define which forms are required for each entity type:

     SOLE_PROP:
     - Federal Schedule C (X5)
     - Georgia Form 500 (X2) — if Georgia resident
     - Georgia Form G-7 (X1) — if has employees (quarterly)
     - Georgia Form ST-3 (X4) — if collects sales tax (monthly/quarterly)
     - Federal estimated tax payments (quarterly)

     S_CORP:
     - Federal Form 1120-S (X6)
     - Schedule K-1 per shareholder (X6)
     - Georgia Form 600-S (companion to Form 600 for S-Corps)
       # COMPLIANCE REVIEW NEEDED: Georgia S-Corp filing — verify
       # whether Form 600 or 600-S is required and add to X3 if needed.
     - Georgia Form G-7 (X1) — if has employees (quarterly)
     - Georgia Form ST-3 (X4) — if collects sales tax

     C_CORP:
     - Federal Form 1120 (X7)
     - Georgia Form 600 (X3)
     - Georgia Form G-7 (X1) — if has employees (quarterly)
     - Georgia Form ST-3 (X4) — if collects sales tax

     PARTNERSHIP_LLC:
     - Federal Form 1065 (X8)
     - Schedule K-1 per partner (X8)
     - Georgia Form 700 (partnership return)
       # COMPLIANCE REVIEW NEEDED: Georgia partnership filing
       # requirements — verify form number and add module if needed.
     - Georgia Form G-7 (X1) — if has employees (quarterly)
     - Georgia Form ST-3 (X4) — if collects sales tax

  2. Due date calculations:
     For each form, calculate the due date for the given tax year:
     - Schedule C / Form 500: April 15 (individual)
     - Form 1120-S: March 15
     - Form 1120: April 15
     - Form 1065: March 15
     - Form G-7: quarterly (Apr 30, Jul 31, Oct 31, Jan 31)
     - Form ST-3: per client filing frequency
     - Georgia Form 600: April 15 (or 15th of 4th month after fiscal year)
     If date falls on weekend/holiday: next business day
     Extension dates also tracked if extension filed

  3. Completion status tracking:
     For each form in the checklist:
     - status: NOT_STARTED, IN_PROGRESS, GENERATED, REVIEWED, FILED, EXTENDED
     - generated_date, reviewed_date, filed_date
     - extension_filed: bool
     - extension_date: date (if extended)
     - notes: freeform text for CPA notes
     - assigned_to: user_id (who is working on it)

  4. Checklist generation:
     - generate_checklist(client_id, tax_year) -> TaxChecklist
       Based on entity_type, create checklist entries for all
       required forms with due dates
     - get_checklist(client_id, tax_year) -> TaxChecklist
     - update_checklist_item(item_id, status, notes)
     - get_firm_overview(tax_year) -> list of all clients with
       their checklist completion percentage

  5. React component:
     - Per-client checklist view with status indicators
     - Color coding: red (overdue), yellow (upcoming), green (filed)
     - Firm overview: all clients in a table with completion bars
     - Quick-update: click to change status

  API endpoints:
  - POST /api/clients/{client_id}/tax-checklist/{year}/generate — generate
  - GET /api/clients/{client_id}/tax-checklist/{year} — get checklist
  - PUT /api/tax-checklist/items/{id} — update item status
  - GET /api/tax-checklist/overview/{year} — firm-wide overview

  ALL endpoints: CPA_OWNER only.

STEP 4: ROLE ENFORCEMENT CHECK
  ALL endpoints: CPA_OWNER only.
  Write tests proving ASSOCIATE cannot access.

STEP 5: TEST
  Write tests at: /backend/tests/services/tax_forms/test_checklist.py

  Required test cases:
  - test_sole_prop_checklist: correct forms for sole proprietor
  - test_s_corp_checklist: correct forms for S-Corp (includes K-1s)
  - test_c_corp_checklist: correct forms for C-Corp
  - test_partnership_checklist: correct forms for partnership/LLC
  - test_due_dates_calculated: correct due dates per form type
  - test_weekend_due_date_rollover: weekend -> next business day
  - test_status_update: status transitions work
  - test_extension_tracking: extension date recorded
  - test_firm_overview: all clients with completion percentages
  - test_requires_cpa_owner: ASSOCIATE cannot access
  - test_client_isolation: Client A checklist separate from Client B
  - test_g7_quarterly_entries: 4 G-7 entries for client with employees

[ACCEPTANCE CRITERIA]
- [ ] Correct forms identified per entity type
- [ ] Due dates calculated including weekend/holiday handling
- [ ] Completion status tracked per form per client
- [ ] Extension tracking supported
- [ ] Firm-wide overview shows all clients and completion %
- [ ] React component with color-coded status indicators
- [ ] CPA_OWNER only
- [ ] All test cases pass

[OUTPUT FORMAT]
End every session by printing to terminal:

  ================================
  SESSION COMPLETE
  Agent:        X9 — Tax Document Checklist
  Task:         TASK-034
  Files changed: [list each file]
  Tests:        [passed/total]
  Issues opened: [n] — IDs: [list]
  Issues closed: [n] — IDs: [list]
  Next task:    TASK-035 — R1 Profit & Loss
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
