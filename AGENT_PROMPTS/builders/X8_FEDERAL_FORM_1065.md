================================================================
FILE: AGENT_PROMPTS/builders/X8_FEDERAL_FORM_1065.md
Builder Agent — Federal Form 1065
================================================================

# BUILDER AGENT — X8: Federal Form 1065 Data Export

[CONTEXT]
You are a Builder Agent for the Georgia CPA firm accounting system.
Module assigned: X8 — Federal Form 1065 data export (partnerships/LLCs)
Task ID: TASK-033
Compliance risk level: HIGH

Federal Form 1065 is the U.S. Return of Partnership Income.
Partnerships and multi-member LLCs are pass-through entities —
income passes through to partners on Schedule K-1. This module
maps GL data to Form 1065 line items and generates K-1 data for
each partner.

CPA_OWNER only can export tax form data.

NOTE: WORK_QUEUE.md lists this task as depending on itself (TASK-033).
This is a typo — the actual dependency is TASK-010 (F3 — GL) and
TASK-035 (R1 — P&L). Correct the dependency reference.

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

  Build service at: /backend/services/tax_forms/federal_1065.py
  Build template at: /backend/templates/tax_forms/form_1065.html

  Core logic:

  1. Form 1065 data aggregation:
     - generate_1065_data(client_id, tax_year)
       Only for entity_type = 'PARTNERSHIP_LLC'
       Map GL data to Form 1065 lines:
       # SOURCE: IRS Form 1065 Instructions, Tax Year [YYYY]
       # REVIEW DATE: [date]

       Income:
       - Line 1a: Gross receipts or sales
       - Line 2: Cost of goods sold
       - Line 3: Gross profit
       - Lines 4-7: Other income
       - Line 8: Total income

       Deductions:
       - Line 9: Salaries and wages (not partner draws)
       - Line 10: Guaranteed payments to partners
       - Line 11: Repairs and maintenance
       - Line 12: Bad debts
       - Line 13: Rent
       - Line 14: Taxes and licenses
       - Line 15: Interest expense
       - Line 16: Depreciation
       - Lines 17-20: Other deductions
       - Line 21: Total deductions
       - Line 22: Ordinary business income (loss)

  2. Schedule K data (partnership items):
     - Ordinary business income/loss
     - Net rental real estate income
     - Other net rental income
     - Guaranteed payments
     - Interest income
     - Dividend income
     - Royalties
     - Net short/long-term capital gain/loss
     - Section 179 deduction
     - Charitable contributions
     - Self-employment earnings
     - Partner's health insurance premiums
     # COMPLIANCE REVIEW NEEDED: Full Schedule K has many items.
     # CPA must review for completeness per client.

  3. Schedule K-1 per partner:
     - generate_k1_data(client_id, tax_year, partner_id)
     - Allocate items based on:
       a) Partnership agreement percentages (profit/loss/capital)
       b) Default: equal sharing if no agreement specified
     - Each partner's share of income, deductions, credits
     - Self-employment income for general partners
     - Guaranteed payments allocated to specific partners
     # NOTE: Partner records need to exist in the system.
     # If partners table does not exist, create it or use the
     # existing equity/capital account structure.

  4. Partner capital account tracking:
     - Beginning capital balance
     - Capital contributions during year
     - Share of income/loss
     - Distributions
     - Ending capital balance
     # Use GL account 3400 (Partner Capital Accounts)

  5. Export formats: JSON, PDF (WeasyPrint), CSV

  API endpoints:
  - POST /api/clients/{client_id}/tax-forms/1065/generate — generate
  - GET /api/clients/{client_id}/tax-forms/1065/{year} — get data
  - GET /api/clients/{client_id}/tax-forms/1065/{year}/pdf — PDF
  - GET /api/clients/{client_id}/tax-forms/1065/{year}/k1/{partner_id} — K-1

  ALL endpoints: CPA_OWNER only.

STEP 4: ROLE ENFORCEMENT CHECK
  ALL endpoints: CPA_OWNER only.

STEP 5: TEST
  Write tests at: /backend/tests/services/tax_forms/test_federal_1065.py

  Required test cases:
  - test_partnership_llc_only: non-PARTNERSHIP_LLC rejected
  - test_income_aggregation: revenue mapped correctly
  - test_deduction_mapping: expenses mapped correctly
  - test_guaranteed_payments_on_line_10: partner guaranteed payments
  - test_ordinary_income: income - deductions
  - test_schedule_k_items: pass-through items calculated
  - test_k1_allocation_by_percentage: pro-rata per agreement
  - test_k1_equal_allocation_default: equal split without agreement
  - test_capital_account_reconciliation: beginning + contributions +
    income - distributions = ending
  - test_self_employment_income: general partners' SE income
  - test_pdf_generation: valid PDF produced
  - test_requires_cpa_owner: ASSOCIATE blocked
  - test_client_isolation: correct client data only

[ACCEPTANCE CRITERIA]
- [ ] Partnership/LLC clients only
- [ ] GL data mapped to Form 1065 line items
- [ ] Schedule K items calculated
- [ ] K-1 per partner with pro-rata allocation
- [ ] Guaranteed payments properly allocated
- [ ] Partner capital accounts reconciled
- [ ] Self-employment income for general partners
- [ ] PDF and CSV export
- [ ] CPA_OWNER only
- [ ] All test cases pass

[OUTPUT FORMAT]
End every session by printing to terminal:

  ================================
  SESSION COMPLETE
  Agent:        X8 — Federal Form 1065
  Task:         TASK-033
  Files changed: [list each file]
  Tests:        [passed/total]
  Issues opened: [n] — IDs: [list]
  Issues closed: [n] — IDs: [list]
  Next task:    TASK-034 — X9 Tax Document Checklist
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
