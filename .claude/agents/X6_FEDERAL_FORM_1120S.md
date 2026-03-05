================================================================
FILE: AGENT_PROMPTS/builders/X6_FEDERAL_FORM_1120S.md
Builder Agent — Federal Form 1120-S
================================================================

# BUILDER AGENT — X6: Federal Form 1120-S Data Export

[CONTEXT]
You are a Builder Agent for the Georgia CPA firm accounting system.
Module assigned: X6 — Federal Form 1120-S data export (S-Corps)
Task ID: TASK-031
Compliance risk level: HIGH

Federal Form 1120-S is the income tax return for S-Corporations.
S-Corps are pass-through entities — income passes through to
shareholders on Schedule K-1. This module maps GL data to Form
1120-S line items and generates K-1 data for each shareholder.

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

  Build service at: /backend/services/tax_forms/federal_1120s.py
  Build template at: /backend/templates/tax_forms/form_1120s.html

  Core logic:

  1. Form 1120-S data aggregation:
     - generate_1120s_data(client_id, tax_year)
       Only for entity_type = 'S_CORP'
       Map GL data to Form 1120-S lines:
       # SOURCE: IRS Form 1120-S Instructions, Tax Year [YYYY]
       # REVIEW DATE: [date]

       Page 1 — Income:
       - Line 1a: Gross receipts or sales
       - Line 2: Cost of goods sold
       - Line 3: Gross profit
       - Lines 4-5: Other income
       - Line 6: Total income

       Deductions:
       - Line 7: Compensation of officers
       - Line 8: Salaries and wages (non-officer)
       - Line 9: Repairs and maintenance
       - Line 10: Bad debts
       - Line 11: Rents
       - Line 12: Taxes and licenses
       - Line 13: Interest
       - Line 14: Depreciation
       - Lines 15-19: Other deductions
       - Line 20: Total deductions
       - Line 21: Ordinary business income (loss)

  2. Schedule K data (S-Corp items):
     - Ordinary business income/loss (from Page 1)
     - Net rental real estate income
     - Other net rental income
     - Interest income
     - Dividend income
     - Royalties
     - Net short/long-term capital gain/loss
     - Section 179 deduction
     - Charitable contributions
     - Tax-exempt interest income
     # COMPLIANCE REVIEW NEEDED: Schedule K items are numerous.
     # Provide common items, CPA must review for completeness.

  3. Schedule K-1 data per shareholder:
     - generate_k1_data(client_id, tax_year, shareholder_id)
     - Pro-rata share based on ownership percentage
     - Each shareholder's share of income, deductions, credits
     # NOTE: Shareholder records may need to be added to the schema.
     # If shareholders table does not exist, create it or flag as
     # [BLOCKER] and use a simple shareholder list.

  4. Export formats:
     - JSON data structure matching form lines
     - PDF summary via WeasyPrint (data worksheet)
     - CSV for import into tax software

  API endpoints:
  - POST /api/clients/{client_id}/tax-forms/1120s/generate — generate
  - GET /api/clients/{client_id}/tax-forms/1120s/{year} — get data
  - GET /api/clients/{client_id}/tax-forms/1120s/{year}/pdf — PDF
  - GET /api/clients/{client_id}/tax-forms/1120s/{year}/k1/{shareholder_id} — K-1

  ALL endpoints: CPA_OWNER only.

STEP 4: ROLE ENFORCEMENT CHECK
  ALL endpoints: CPA_OWNER only.
  Write tests proving ASSOCIATE cannot access.

STEP 5: TEST
  Write tests at: /backend/tests/services/tax_forms/test_federal_1120s.py

  Required test cases:
  - test_s_corp_only: non-S_CORP rejected
  - test_income_aggregation: revenue mapped to correct lines
  - test_deduction_mapping: expenses mapped to correct lines
  - test_ordinary_income_calculation: income - deductions
  - test_officer_compensation_separate: officer pay on Line 7
  - test_schedule_k_items: pass-through items calculated
  - test_k1_pro_rata: shareholder gets ownership % of items
  - test_pdf_generation: valid PDF produced
  - test_requires_cpa_owner: ASSOCIATE blocked
  - test_client_isolation: Client A data not in Client B

[ACCEPTANCE CRITERIA]
- [ ] S-Corp clients only (entity_type validation)
- [ ] GL data mapped to Form 1120-S line items
- [ ] Schedule K items calculated
- [ ] K-1 data per shareholder with pro-rata allocation
- [ ] Officer compensation separated from regular wages
- [ ] PDF and CSV export options
- [ ] CPA_OWNER only
- [ ] All test cases pass

[OUTPUT FORMAT]
End every session by printing to terminal:

  ================================
  SESSION COMPLETE
  Agent:        X6 — Federal Form 1120-S
  Task:         TASK-031
  Files changed: [list each file]
  Tests:        [passed/total]
  Issues opened: [n] — IDs: [list]
  Issues closed: [n] — IDs: [list]
  Next task:    TASK-032 — X7 Federal Form 1120
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
