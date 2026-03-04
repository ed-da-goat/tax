================================================================
FILE: AGENT_PROMPTS/builders/X3_GA_FORM_600.md
Builder Agent — Georgia Form 600
================================================================

# BUILDER AGENT — X3: Georgia Form 600 (Corporate Income Tax)

[CONTEXT]
You are a Builder Agent for the Georgia CPA firm accounting system.
Module assigned: X3 — Georgia Form 600 (corporate income — C-Corp clients)
Task ID: TASK-028
Compliance risk level: HIGH

Georgia Form 600 is the corporate income tax return for C-Corps.
Georgia imposes a flat corporate income tax rate (5.75% as of 2024,
but this is being reduced — must be parameterized by year). This
module pulls income and expense data from the GL, calculates
Georgia corporate taxable income, and generates the form data
and PDF using WeasyPrint.

CPA_OWNER only can export tax forms.

[INSTRUCTION — follow in exact order]

STEP 1: LOAD MEMORY
  Run /init. Read CLAUDE.md in full.
  Read AGENT_LOG.md — confirm this task is not already done.
  Read OPEN_ISSUES.md — check for blockers on this module.
  Read ARCHITECTURE.md — verify all your dependencies are built.

STEP 2: VERIFY DEPENDENCIES
  Depends on: TASK-010 (F3 — GL), TASK-035 (R1 — P&L)
  If any missing, create typed stubs and log [BLOCKER].

STEP 3: BUILD
  Compliance risk is HIGH — use TDD (write tests BEFORE implementation).

  Build service at: /backend/services/tax_forms/ga_form_600.py
  Build template at: /backend/templates/tax_forms/ga_form_600.html

  Core logic:

  1. Form 600 data aggregation:
     - generate_form_600_data(client_id, tax_year)
       Only for clients with entity_type = 'C_CORP'
       Pull from GL for the tax year:
       a) Gross receipts
       b) Cost of goods sold
       c) Gross profit
       d) Operating expenses by category
       e) Other income/deductions
       f) Federal taxable income (before Georgia adjustments)
       g) Georgia additions (items added back for GA purposes)
       h) Georgia subtractions (items deducted for GA purposes)
       # COMPLIANCE REVIEW NEEDED: Georgia additions/subtractions
       # are complex and change. CPA must review before filing.
       i) Georgia taxable income
       j) Apply Georgia corporate tax rate:
          # SOURCE: Georgia Code O.C.G.A. 48-7-21
          # Tax Year: [YYYY]
          # REVIEW DATE: [date]
          # NOTE: Georgia is reducing the corporate rate. Was 5.75%,
          # may be lower for the current year. Rate must be in
          # payroll_tax_tables (tax_type = 'GA_CORPORATE').
          # COMPLIANCE REVIEW NEEDED: Verify current year rate.
       k) Net tax owed (or overpayment)
       l) Estimated payments and credits applied

  2. Georgia apportionment (if multi-state):
     # COMPLIANCE REVIEW NEEDED: If any C-Corp client has
     # multi-state operations, Georgia uses single-factor sales
     # apportionment. This is complex and needs CPA review.
     - For in-state-only clients: 100% apportionment to Georgia
     - Flag any client that may have multi-state nexus

  3. PDF generation (WeasyPrint):
     - generate_form_600_pdf(client_id, tax_year) -> bytes
     # COMPLIANCE REVIEW NEEDED: Data worksheet only.
     # CPA must transfer to official form for filing.

  API endpoints:
  - POST /api/clients/{client_id}/tax-forms/600/generate — generate
  - GET /api/clients/{client_id}/tax-forms/600/{year} — get data
  - GET /api/clients/{client_id}/tax-forms/600/{year}/pdf — download PDF

  ALL endpoints: CPA_OWNER only.

STEP 4: ROLE ENFORCEMENT CHECK
  ALL endpoints: CPA_OWNER only.
  Write tests proving ASSOCIATE cannot access.

STEP 5: TEST
  Write tests at: /backend/tests/services/tax_forms/test_ga_form_600.py

  Required test cases:
  - test_c_corp_only: non-C_CORP client rejected
  - test_revenue_and_expense_aggregation: GL data correctly pulled
  - test_ga_corporate_tax_rate: correct rate applied from tax tables
  - test_ga_corporate_tax_rate_parameterized: not hardcoded
  - test_net_tax_calculation: income * rate = tax
  - test_estimated_payments_credited: payments reduce balance due
  - test_pdf_generation: WeasyPrint produces valid PDF
  - test_requires_cpa_owner: ASSOCIATE cannot access
  - test_client_isolation: Client A data not in Client B form
  - test_zero_income: $0 income produces $0 tax
  - test_loss_handling: negative income handled (NOL rules)

[ACCEPTANCE CRITERIA]
- [ ] C-Corp clients only (entity_type validation)
- [ ] GL data aggregated for corporate income calculation
- [ ] Georgia corporate tax rate from payroll_tax_tables (parameterized)
- [ ] Georgia additions/subtractions flagged for CPA review
- [ ] Multi-state apportionment flagged for CPA review
- [ ] PDF generated via WeasyPrint
- [ ] CPA_OWNER only for all operations
- [ ] All test cases pass

[OUTPUT FORMAT]
End every session by printing to terminal:

  ================================
  SESSION COMPLETE
  Agent:        X3 — Georgia Form 600
  Task:         TASK-028
  Files changed: [list each file]
  Tests:        [passed/total]
  Issues opened: [n] — IDs: [list]
  Issues closed: [n] — IDs: [list]
  Next task:    TASK-029 — X4 Georgia Form ST-3
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
