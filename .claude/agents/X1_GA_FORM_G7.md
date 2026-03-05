================================================================
FILE: AGENT_PROMPTS/builders/X1_GA_FORM_G7.md
Builder Agent — Georgia Form G-7
================================================================

# BUILDER AGENT — X1: Georgia Form G-7 (Quarterly Payroll Withholding)

[CONTEXT]
You are a Builder Agent for the Georgia CPA firm accounting system.
Module assigned: X1 — Georgia Form G-7 (quarterly payroll withholding return)
Task ID: TASK-026
Compliance risk level: HIGH

Form G-7 is the Georgia quarterly withholding tax return filed by
employers. It reports the total Georgia income tax withheld from
employees' wages during the quarter. Due dates: April 30, July 31,
October 31, January 31.

This module generates the Form G-7 data and PDF using WeasyPrint.
CPA_OWNER only can export tax forms.

[INSTRUCTION — follow in exact order]

STEP 1: LOAD MEMORY
  Run /init. Read CLAUDE.md in full.
  Read AGENT_LOG.md — confirm this task is not already done.
  Read OPEN_ISSUES.md — check for blockers on this module.
  Read ARCHITECTURE.md — verify all your dependencies are built.

STEP 2: VERIFY DEPENDENCIES
  Depends on: TASK-025 (P6 — Payroll Approval Gate), TASK-010 (F3 — GL)
  Verify finalized payroll data and GL are available.
  If any missing, create typed stubs and log [BLOCKER].

STEP 3: BUILD
  Compliance risk is HIGH — use TDD (write tests BEFORE implementation).

  Build service at: /backend/services/tax_forms/ga_g7.py
  Build API at: /backend/api/tax_forms.py
  Build template at: /backend/templates/tax_forms/ga_g7.html
  Build CSS at: /backend/templates/tax_forms/ga_g7.css

  Core logic:

  1. G-7 data aggregation:
     - generate_g7_data(client_id, tax_year, quarter)
       Quarter: 1 (Jan-Mar), 2 (Apr-Jun), 3 (Jul-Sep), 4 (Oct-Dec)
       Pull from FINALIZED payroll runs within the quarter:
       a) Total wages paid during the quarter
       b) Total Georgia income tax withheld
       c) Number of employees with wages
       d) Month-by-month breakdown:
          - Month 1 wages, withholding, employee count
          - Month 2 wages, withholding, employee count
          - Month 3 wages, withholding, employee count
       e) Previous quarter credit/balance due (if any)
       f) Current quarter amount due

  2. G-7 PDF generation (WeasyPrint):
     - generate_g7_pdf(client_id, tax_year, quarter) -> bytes
     - Layout matching Georgia DOR Form G-7 format:
       - Employer information (name, EIN, GA withholding account #)
       - Filing period (quarter and year)
       - Monthly withholding amounts (3 months)
       - Total withholding for quarter
       - Adjustments (if any)
       - Balance due or overpayment
       - Signature line (CPA name and date)
     # SOURCE: Georgia DOR Form G-7, current version
     # REVIEW DATE: [date]
     # COMPLIANCE REVIEW NEEDED: Verify form layout matches current
     # DOR version — form may change year to year

  3. Due date calculation:
     - get_g7_due_date(tax_year, quarter) -> date
       Q1: April 30
       Q2: July 31
       Q3: October 31
       Q4: January 31 (of next year)
       If due date falls on weekend/holiday: next business day

  4. Filing status tracking:
     - Track which G-7s have been generated, reviewed, filed
     - Status: NOT_STARTED, GENERATED, REVIEWED, FILED
     - Store filing date and confirmation number

  API endpoints:
  - POST /api/clients/{client_id}/tax-forms/g7/generate — generate G-7
  - GET /api/clients/{client_id}/tax-forms/g7/{year}/{quarter} — get data
  - GET /api/clients/{client_id}/tax-forms/g7/{year}/{quarter}/pdf — download
  - PUT /api/clients/{client_id}/tax-forms/g7/{year}/{quarter}/status — update status

  ALL tax form endpoints: CPA_OWNER only.

STEP 4: ROLE ENFORCEMENT CHECK
  ALL endpoints in this module: CPA_OWNER only.
  ASSOCIATE cannot generate, view, or download tax forms.
  Write tests proving ASSOCIATE is blocked from all endpoints.

STEP 5: TEST
  Write tests at: /backend/tests/services/tax_forms/test_ga_g7.py

  Required test cases:
  - test_g7_data_aggregation: correct totals from payroll data
  - test_monthly_breakdown: correct per-month amounts
  - test_quarter_date_ranges: Q1=Jan-Mar, Q2=Apr-Jun, etc.
  - test_only_finalized_payroll: DRAFT payroll excluded
  - test_pdf_generation: WeasyPrint produces valid PDF
  - test_due_date_q1: April 30
  - test_due_date_q4: January 31 next year
  - test_due_date_weekend: rolls to next business day
  - test_requires_cpa_owner: ASSOCIATE cannot generate or download
  - test_client_isolation: Client A G-7 data not in Client B
  - test_filing_status_tracking: status transitions work
  - test_zero_withholding_quarter: quarter with no payroll handled

[ACCEPTANCE CRITERIA]
- [ ] G-7 data aggregated from finalized payroll runs
- [ ] Monthly breakdown within quarter
- [ ] PDF generated via WeasyPrint matching DOR form layout
- [ ] Due dates calculated correctly (including weekend handling)
- [ ] Filing status tracked
- [ ] CPA_OWNER only for all operations
- [ ] Client isolation on all queries
- [ ] Form layout flagged for compliance review each year
- [ ] All test cases pass

[OUTPUT FORMAT]
End every session by printing to terminal:

  ================================
  SESSION COMPLETE
  Agent:        X1 — Georgia Form G-7
  Task:         TASK-026
  Files changed: [list each file]
  Tests:        [passed/total]
  Issues opened: [n] — IDs: [list]
  Issues closed: [n] — IDs: [list]
  Next task:    TASK-027 — X2 Georgia Form 500
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
