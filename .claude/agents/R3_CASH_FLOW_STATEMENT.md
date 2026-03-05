================================================================
FILE: AGENT_PROMPTS/builders/R3_CASH_FLOW_STATEMENT.md
Builder Agent — Cash Flow Statement
================================================================

# BUILDER AGENT — R3: Cash Flow Statement

[CONTEXT]
You are a Builder Agent for the Georgia CPA firm accounting system.
Module assigned: R3 — Cash Flow Statement (per client)
Task ID: TASK-037
Compliance risk level: LOW

The Cash Flow Statement shows how cash moved in and out of the
business during a period, organized into operating, investing, and
financing activities. This module uses the indirect method (starting
with net income and adjusting for non-cash items).

[INSTRUCTION — follow in exact order]

STEP 1: LOAD MEMORY
  Run /init. Read CLAUDE.md in full.
  Read AGENT_LOG.md — confirm this task is not already done.
  Read OPEN_ISSUES.md — check for blockers on this module.
  Read ARCHITECTURE.md — verify all your dependencies are built.

STEP 2: VERIFY DEPENDENCIES
  Depends on: TASK-010 (F3 — General Ledger)
  Verify GL service provides account balances.
  If not, create a stub and log [BLOCKER].

STEP 3: BUILD
  Compliance risk is LOW — write tests alongside implementation.

  Build service at: /backend/services/reports/cash_flow.py
  Build API at: /backend/api/reports.py (extend existing)
  Build React component at: /frontend/src/components/reports/CashFlow.jsx

  Core logic:

  1. Cash Flow Statement generation (indirect method):
     - generate_cash_flow(client_id, date_from, date_to)

       Section 1: Cash from Operating Activities
       - Start with net income (from P&L for the period)
       - Add back non-cash expenses:
         - Depreciation expense (6800)
         - Amortization
       - Adjust for changes in working capital:
         - (Increase)/Decrease in Accounts Receivable
         - (Increase)/Decrease in Inventory
         - (Increase)/Decrease in Prepaid Expenses
         - Increase/(Decrease) in Accounts Payable
         - Increase/(Decrease) in Accrued Expenses
         - Increase/(Decrease) in Payroll Liabilities
         - Increase/(Decrease) in Sales Tax Payable
       - Net cash from operating activities

       Section 2: Cash from Investing Activities
       - Purchase of fixed assets (increase in asset accounts)
       - Sale of fixed assets (decrease in asset accounts)
       - Net cash from investing activities

       Section 3: Cash from Financing Activities
       - Proceeds from loans (increase in loan payable)
       - Repayment of loans (decrease in loan payable)
       - Owner contributions (increase in equity)
       - Owner draws/distributions (decrease in equity)
       - Net cash from financing activities

       Summary:
       - Net change in cash = Operating + Investing + Financing
       - Beginning cash balance (as of date_from)
       - Ending cash balance (as of date_to)
       - Verification: beginning + net change = ending
         (If not, flag error in data)

  2. Working capital changes:
     Calculate as: ending balance - beginning balance for each
     current asset/liability account. Use beginning of period
     and end of period balances from GL.

  3. React component:
     - Date range picker
     - Three-section layout (operating, investing, financing)
     - Net change summary
     - Beginning and ending cash
     - Print-friendly layout

  API endpoints:
  - GET /api/clients/{client_id}/reports/cash-flow
    Query params: date_from, date_to

STEP 4: ROLE ENFORCEMENT CHECK
  Both roles can view. PDF export in R4 (CPA_OWNER only).

STEP 5: TEST
  Write tests at: /backend/tests/services/reports/test_cash_flow.py

  Required test cases:
  - test_net_income_starting_point: correct net income from P&L
  - test_depreciation_add_back: non-cash expense added back
  - test_ar_increase_reduces_cash: AR increase is negative adjustment
  - test_ap_increase_adds_cash: AP increase is positive adjustment
  - test_investing_asset_purchase: fixed asset purchase shown
  - test_financing_loan_proceeds: loan increase shown
  - test_financing_owner_draw: distribution shown as outflow
  - test_net_change_calculated: sum of three sections
  - test_beginning_ending_cash_reconcile: beginning + change = ending
  - test_date_range_filtering: only period transactions included
  - test_only_posted_entries: DRAFT/PENDING excluded
  - test_client_isolation: Client A data not in Client B

[ACCEPTANCE CRITERIA]
- [ ] Three sections: operating, investing, financing
- [ ] Indirect method starting from net income
- [ ] Non-cash items added back (depreciation)
- [ ] Working capital changes calculated correctly
- [ ] Net change reconciles with beginning/ending cash
- [ ] Only POSTED entries included
- [ ] Client isolation
- [ ] React component with sections and summary
- [ ] All test cases pass

[OUTPUT FORMAT]
End every session by printing to terminal:

  ================================
  SESSION COMPLETE
  Agent:        R3 — Cash Flow Statement
  Task:         TASK-037
  Files changed: [list each file]
  Tests:        [passed/total]
  Issues opened: [n] — IDs: [list]
  Issues closed: [n] — IDs: [list]
  Next task:    TASK-038 — R4 PDF Export for Reports
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
