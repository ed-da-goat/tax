================================================================
FILE: AGENT_PROMPTS/builders/P5_PAY_STUB_GENERATOR.md
Builder Agent — Pay Stub Generator
================================================================

# BUILDER AGENT — P5: Pay Stub Generator

[CONTEXT]
You are a Builder Agent for the Georgia CPA firm accounting system.
Module assigned: P5 — Pay stub generator (PDF output)
Task ID: TASK-024
Compliance risk level: MEDIUM

This module generates professional pay stub PDFs using WeasyPrint.
Each pay stub shows gross pay, all deductions (federal withholding,
Georgia state withholding, Social Security, Medicare, SUTA, other),
net pay, and year-to-date totals. One stub per employee per payroll
run.

[INSTRUCTION — follow in exact order]

STEP 1: LOAD MEMORY
  Run /init. Read CLAUDE.md in full.
  Read AGENT_LOG.md — confirm this task is not already done.
  Read OPEN_ISSUES.md — check for blockers on this module.
  Read ARCHITECTURE.md — verify all your dependencies are built.

STEP 2: VERIFY DEPENDENCIES
  Depends on: TASK-020 (P1 — Employee Records), TASK-021 (P2 — GA Withholding),
              TASK-022 (P3 — GA SUTA), TASK-023 (P4 — Federal Taxes)
  Verify all four payroll calculators are available.
  If any missing, create typed stubs and log [BLOCKER].

STEP 3: BUILD
  Compliance risk is MEDIUM — write tests alongside implementation.

  Build service at: /backend/services/payroll/pay_stub_generator.py
  Build payroll processor at: /backend/services/payroll/processor.py
  Build API at: /backend/api/payroll.py
  Build templates at:
  - /backend/templates/pay_stub.html
  - /backend/templates/pay_stub.css

  Core components:

  1. Payroll processor (runs all calculators):
     - process_payroll(client_id, pay_period_start, pay_period_end,
       pay_date, employee_hours: dict[employee_id, hours_or_salary])
     - For each employee:
       a) Calculate gross pay (hours * rate or salary / periods)
       b) Get YTD wages from existing payroll records
       c) Run GA withholding calculator (P2)
       d) Run GA SUTA calculator (P3)
       e) Run federal withholding calculator (P4)
       f) Run Social Security calculator (P4)
       g) Run Medicare calculator (P4)
       h) Run FUTA calculator (P4)
       i) Apply other deductions (401k, health insurance, etc.)
       j) Calculate net pay: gross - all deductions
     - Create payroll_run record (status = DRAFT)
     - Create payroll_items for each employee
     - Return payroll run with all items for review

  2. Pay stub PDF generation (WeasyPrint):
     - generate_pay_stub(payroll_item_id) -> bytes (PDF)
     - HTML template with professional layout:
       Header:
       - Company/client name and address
       - Employee name and ID
       - Pay period and pay date
       Current period section:
       - Gross pay
       - Federal income tax withholding
       - Georgia state income tax withholding
       - Social Security (OASDI)
       - Medicare
       - Georgia SUTA (employer portion — shown for info)
       - Other deductions (itemized)
       - Net pay
       YTD section (same breakdown, cumulative):
       - YTD gross
       - YTD federal withholding
       - YTD state withholding
       - YTD Social Security
       - YTD Medicare
       - YTD other deductions
       - YTD net pay
     - CSS styling for clean print layout (fits on one page)
     - Save generated PDF to:
       /data/documents/{client_id}/payroll/{year}/{pay_date}_{employee_id}.pdf

  3. Bulk pay stub generation:
     - generate_all_stubs(payroll_run_id) -> list of PDF paths
       Generate one stub per employee in the payroll run

  API endpoints:
  - POST /api/clients/{client_id}/payroll/process — process payroll (DRAFT)
  - GET /api/clients/{client_id}/payroll/runs — list payroll runs
  - GET /api/clients/{client_id}/payroll/runs/{id} — get run details
  - GET /api/clients/{client_id}/payroll/runs/{id}/stubs — list stubs
  - GET /api/clients/{client_id}/payroll/items/{id}/stub — download stub PDF
  - POST /api/clients/{client_id}/payroll/runs/{id}/generate-stubs — generate all

STEP 4: ROLE ENFORCEMENT CHECK
  - POST process payroll: both roles (creates as DRAFT)
  - GET endpoints: both roles
  - POST generate stubs: both roles (stubs are informational)
  - Finalization is NOT in this module — it is in P6
  Write test confirming both roles can process and view.

STEP 5: TEST
  Write tests at: /backend/tests/services/payroll/test_pay_stub_generator.py

  Required test cases:
  - test_process_payroll_creates_run: payroll run created with items
  - test_all_taxes_calculated: all tax types present in payroll item
  - test_net_pay_correct: gross - all deductions = net
  - test_ytd_totals_accumulate: second run includes first run's amounts
  - test_generate_stub_pdf: WeasyPrint produces valid PDF bytes
  - test_stub_contains_all_fields: PDF includes gross, deductions, net, YTD
  - test_stub_saved_to_disk: PDF file created at expected path
  - test_bulk_stubs_generated: all employees get stubs
  - test_salary_employee_calculation: salary / periods = correct gross
  - test_hourly_employee_calculation: hours * rate = correct gross
  - test_client_isolation: Client A payroll not visible to Client B
  - test_payroll_run_status_draft: new run starts as DRAFT

[ACCEPTANCE CRITERIA]
- [ ] Payroll processor runs all tax calculators per employee
- [ ] Net pay correctly calculated (gross minus all deductions)
- [ ] YTD totals accumulated from previous payroll runs
- [ ] Pay stub PDF generated via WeasyPrint
- [ ] Professional layout with current period and YTD sections
- [ ] Both hourly and salary employees supported
- [ ] PDFs saved to /data/documents/{client_id}/payroll/
- [ ] Bulk generation for entire payroll run
- [ ] Client isolation on all queries
- [ ] All test cases pass

[OUTPUT FORMAT]
End every session by printing to terminal:

  ================================
  SESSION COMPLETE
  Agent:        P5 — Pay Stub Generator
  Task:         TASK-024
  Files changed: [list each file]
  Tests:        [passed/total]
  Issues opened: [n] — IDs: [list]
  Issues closed: [n] — IDs: [list]
  Next task:    TASK-025 — P6 Payroll Approval Gate
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
