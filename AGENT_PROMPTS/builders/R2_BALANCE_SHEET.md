================================================================
FILE: AGENT_PROMPTS/builders/R2_BALANCE_SHEET.md
Builder Agent — Balance Sheet
================================================================

# BUILDER AGENT — R2: Balance Sheet

[CONTEXT]
You are a Builder Agent for the Georgia CPA firm accounting system.
Module assigned: R2 — Balance Sheet (per client, as-of date selectable)
Task ID: TASK-036
Compliance risk level: LOW

The Balance Sheet shows a snapshot of a client's financial position
at a point in time: Assets = Liabilities + Equity. It pulls
cumulative balances from POSTED journal entries up to the as-of date.

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

  Build service at: /backend/services/reports/balance_sheet.py
  Build API at: /backend/api/reports.py (extend existing)
  Build React component at: /frontend/src/components/reports/BalanceSheet.jsx

  Core logic:

  1. Balance Sheet generation:
     - generate_balance_sheet(client_id, as_of_date)
       Pull cumulative POSTED journal entry balances up to as_of_date:

       Assets (account type: ASSET, 1000-1999):
       - Current Assets:
         - Cash and Cash Equivalents
         - Accounts Receivable
         - Inventory
         - Prepaid Expenses
       - Fixed Assets:
         - Property/Equipment
         - Accumulated Depreciation (contra)
       - Other Assets
       - Total Assets

       Liabilities (account type: LIABILITY, 2000-2999):
       - Current Liabilities:
         - Accounts Payable
         - Accrued Expenses
         - Payroll Liabilities
         - Sales Tax Payable
         - Short-term Notes
       - Long-term Liabilities:
         - Long-term Debt
       - Total Liabilities

       Equity (account type: EQUITY, 3000-3999):
       - Owner's Equity / Capital Stock
       - Retained Earnings
         NOTE: Retained earnings = prior year's net income
         carried forward. Calculate as: all revenue minus all
         expenses from beginning of time to start of current
         fiscal year.
       - Current Year Net Income
         (Revenue - Expenses from start of fiscal year to as_of_date)
       - Owner's Draw / Distributions
       - Total Equity

       Verification: Total Assets == Total Liabilities + Total Equity
       If this does not balance, flag as error — something is wrong
       with the GL data.

  2. Balance direction:
     - Assets: normal debit balance (debits - credits)
     - Liabilities: normal credit balance (credits - debits)
     - Equity: normal credit balance (credits - debits)
     - Contra accounts (like accumulated depreciation): opposite

  3. Comparison:
     - generate_balance_sheet_comparison(client_id, date1, date2)
       Show two dates side by side with change ($ and %)

  4. React component:
     - As-of date picker
     - Formatted balance sheet with sections
     - Balance verification indicator (shows if balanced)
     - Comparison toggle
     - Print-friendly layout

  API endpoints:
  - GET /api/clients/{client_id}/reports/balance-sheet
    Query params: as_of_date
  - GET /api/clients/{client_id}/reports/balance-sheet/comparison
    Query params: date1, date2

STEP 4: ROLE ENFORCEMENT CHECK
  Both roles can view. PDF export in R4 (CPA_OWNER only).

STEP 5: TEST
  Write tests at: /backend/tests/services/reports/test_balance_sheet.py

  Required test cases:
  - test_assets_total: asset accounts summed correctly
  - test_liabilities_total: liability accounts summed correctly
  - test_equity_total: equity accounts summed correctly
  - test_balance_equation: assets == liabilities + equity
  - test_retained_earnings_calculated: prior year net income
  - test_current_year_net_income: YTD revenue - expenses
  - test_as_of_date_filtering: only entries up to date included
  - test_only_posted_entries: DRAFT/PENDING excluded
  - test_normal_balance_direction: debit vs credit accounts
  - test_contra_account_handling: accumulated depreciation correct
  - test_comparison_report: two dates with change calculated
  - test_client_isolation: Client A data not in Client B report
  - test_imbalance_flagged: if A != L+E, error flagged

[ACCEPTANCE CRITERIA]
- [ ] Assets, liabilities, equity sections correct
- [ ] Balance equation verified (A = L + E)
- [ ] Retained earnings calculated from prior periods
- [ ] Current year net income included in equity
- [ ] As-of date filtering works
- [ ] Only POSTED entries included
- [ ] Normal balance direction correct for each account type
- [ ] Comparison report with change
- [ ] Client isolation
- [ ] All test cases pass

[OUTPUT FORMAT]
End every session by printing to terminal:

  ================================
  SESSION COMPLETE
  Agent:        R2 — Balance Sheet
  Task:         TASK-036
  Files changed: [list each file]
  Tests:        [passed/total]
  Issues opened: [n] — IDs: [list]
  Issues closed: [n] — IDs: [list]
  Next task:    TASK-037 — R3 Cash Flow Statement
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
