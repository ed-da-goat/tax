================================================================
FILE: AGENT_PROMPTS/builders/X7_FEDERAL_FORM_1120.md
Builder Agent — Federal Form 1120
================================================================

# BUILDER AGENT — X7: Federal Form 1120 Data Export

[CONTEXT]
You are a Builder Agent for the Georgia CPA firm accounting system.
Module assigned: X7 — Federal Form 1120 data export (C-Corps)
Task ID: TASK-032
Compliance risk level: HIGH

Federal Form 1120 is the U.S. Corporation Income Tax Return for
C-Corporations. Unlike S-Corps, C-Corps pay tax at the entity
level (flat 21% federal rate as of 2018 TCJA). This module maps
GL data to Form 1120 line items.

CPA_OWNER only can export tax form data.

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

  Build service at: /backend/services/tax_forms/federal_1120.py
  Build template at: /backend/templates/tax_forms/form_1120.html

  Core logic:

  1. Form 1120 data aggregation:
     - generate_1120_data(client_id, tax_year)
       Only for entity_type = 'C_CORP'
       Map GL data to Form 1120 lines:
       # SOURCE: IRS Form 1120 Instructions, Tax Year [YYYY]
       # REVIEW DATE: [date]

       Income:
       - Line 1a: Gross receipts or sales
       - Line 2: Cost of goods sold
       - Line 3: Gross profit
       - Line 4: Dividends (from investments)
       - Line 5: Interest income
       - Lines 6-10: Other income
       - Line 11: Total income

       Deductions:
       - Line 12: Compensation of officers
       - Line 13: Salaries and wages
       - Line 14: Repairs and maintenance
       - Line 15: Bad debts
       - Line 16: Rents
       - Line 17: Taxes and licenses
       - Line 18: Interest expense
       - Line 20: Depreciation
       - Lines 21-26: Other deductions
       - Line 27: Total deductions
       - Line 28: Taxable income before NOL
       - Line 29a: Net operating loss deduction
       - Line 30: Taxable income

       Tax computation:
       - Line 31: Total tax
         Federal corporate rate: 21%
         # SOURCE: IRC Section 11(b), as amended by TCJA 2017
         # REVIEW DATE: [date]
         # Store in payroll_tax_tables, tax_type = 'FEDERAL_CORPORATE'
       - Line 32: Estimated tax payments
       - Line 35: Amount owed (or overpayment)

  2. Schedule L (Balance Sheet):
     - Pull from GL as-of-date balances for beginning and end of year
     - Assets, liabilities, equity per the books

  3. Schedule M-1 (Reconciliation):
     - Book income to tax income reconciliation
     # COMPLIANCE REVIEW NEEDED: M-1 items require CPA judgment.
     # Provide book income, CPA handles adjustments.

  4. Export formats:
     - JSON, PDF (WeasyPrint), CSV

  API endpoints:
  - POST /api/clients/{client_id}/tax-forms/1120/generate — generate
  - GET /api/clients/{client_id}/tax-forms/1120/{year} — get data
  - GET /api/clients/{client_id}/tax-forms/1120/{year}/pdf — PDF
  - GET /api/clients/{client_id}/tax-forms/1120/{year}/csv — CSV

  ALL endpoints: CPA_OWNER only.

STEP 4: ROLE ENFORCEMENT CHECK
  ALL endpoints: CPA_OWNER only.

STEP 5: TEST
  Write tests at: /backend/tests/services/tax_forms/test_federal_1120.py

  Required test cases:
  - test_c_corp_only: non-C_CORP rejected
  - test_income_aggregation: revenue mapped correctly
  - test_deduction_mapping: expenses mapped correctly
  - test_taxable_income_calculation: income - deductions
  - test_federal_tax_rate_21_percent: 21% rate applied
  - test_tax_rate_parameterized: rate from tax tables, not hardcoded
  - test_estimated_payments_credited: payments reduce balance
  - test_schedule_l_balance_sheet: beginning/end balances populated
  - test_pdf_generation: valid PDF produced
  - test_requires_cpa_owner: ASSOCIATE blocked
  - test_client_isolation: correct client data only
  - test_loss_handling: negative taxable income (NOL)

[ACCEPTANCE CRITERIA]
- [ ] C-Corp clients only
- [ ] GL data mapped to Form 1120 line items
- [ ] Federal 21% rate from tax tables (parameterized)
- [ ] Schedule L balance sheet data populated
- [ ] Schedule M-1 flagged for CPA judgment
- [ ] PDF and CSV export
- [ ] CPA_OWNER only
- [ ] All test cases pass

[OUTPUT FORMAT]
End every session by printing to terminal:

  ================================
  SESSION COMPLETE
  Agent:        X7 — Federal Form 1120
  Task:         TASK-032
  Files changed: [list each file]
  Tests:        [passed/total]
  Issues opened: [n] — IDs: [list]
  Issues closed: [n] — IDs: [list]
  Next task:    TASK-033 — X8 Federal Form 1065
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
