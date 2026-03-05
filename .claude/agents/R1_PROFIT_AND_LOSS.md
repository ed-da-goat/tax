================================================================
FILE: AGENT_PROMPTS/builders/R1_PROFIT_AND_LOSS.md
Builder Agent — Profit & Loss Report
================================================================

# BUILDER AGENT — R1: Profit & Loss Report

[CONTEXT]
You are a Builder Agent for the Georgia CPA firm accounting system.
Module assigned: R1 — Profit & Loss (per client, date range selectable)
Task ID: TASK-035
Compliance risk level: LOW

The Profit & Loss (Income Statement) report shows revenue, cost of
goods sold, expenses, and net income for a client over a date range.
It pulls data from POSTED journal entries in the GL. This is one of
the most frequently used reports in the system.

[INSTRUCTION — follow in exact order]

STEP 1: LOAD MEMORY
  Run /init. Read CLAUDE.md in full.
  Read AGENT_LOG.md — confirm this task is not already done.
  Read OPEN_ISSUES.md — check for blockers on this module.
  Read ARCHITECTURE.md — verify all your dependencies are built.

STEP 2: VERIFY DEPENDENCIES
  Depends on: TASK-010 (F3 — General Ledger)
  Verify GL service provides account balances and trial balance.
  If not, create a stub and log [BLOCKER].

STEP 3: BUILD
  Compliance risk is LOW — write tests alongside implementation.

  Build service at: /backend/services/reports/profit_loss.py
  Build API at: /backend/api/reports.py
  Build React component at: /frontend/src/components/reports/ProfitLoss.jsx

  Core logic:

  1. P&L data generation:
     - generate_profit_loss(client_id, date_from, date_to)
       Pull POSTED journal entry lines for the date range:
       a) Revenue section:
          - Revenue accounts (type: REVENUE, 4000-4999)
          - Subtotal: Total Revenue
       b) Cost of Goods Sold section:
          - COGS accounts (5000-5999)
          - Subtotal: Total COGS
       c) Gross Profit = Total Revenue - Total COGS
       d) Operating Expenses section:
          - Expense accounts (type: EXPENSE, 6000-6999)
          - Group by account with individual amounts
          - Subtotal: Total Operating Expenses
       e) Other Income/Expenses section:
          - Other income/expense accounts (7000-7999)
          - Subtotal: Total Other
       f) Net Income = Gross Profit - Operating Expenses + Other

     - Each line item shows:
       account_number, account_name, amount
     - Accounts with zero balance for the period may be hidden
       (configurable: show_zero_accounts parameter)

  2. Comparison report:
     - generate_profit_loss_comparison(client_id, period1, period2)
       Show two periods side by side with variance ($ and %)
       Useful for month-over-month or year-over-year analysis

  3. React component:
     - Date range picker (from/to)
     - Formatted P&L report with sections and subtotals
     - Comparison toggle (add second period)
     - Print-friendly layout
     - Export button (triggers R4 PDF export)

  API endpoints:
  - GET /api/clients/{client_id}/reports/profit-loss — generate P&L
    Query params: date_from, date_to, show_zero_accounts
  - GET /api/clients/{client_id}/reports/profit-loss/comparison
    Query params: period1_from, period1_to, period2_from, period2_to

  Both roles can view reports. PDF export is handled by R4 (CPA_OWNER only).

STEP 4: ROLE ENFORCEMENT CHECK
  - GET reports: both roles (viewing is open)
  - PDF export will be in R4, not here
  No special role enforcement needed for viewing.

STEP 5: TEST
  Write tests at: /backend/tests/services/reports/test_profit_loss.py

  Required test cases:
  - test_revenue_totals: revenue accounts summed correctly
  - test_cogs_totals: COGS accounts summed correctly
  - test_gross_profit: revenue - COGS = gross profit
  - test_expense_totals: expense accounts summed correctly
  - test_net_income: gross profit - expenses + other = net
  - test_date_range_filtering: only transactions in range included
  - test_only_posted_entries: DRAFT and PENDING excluded
  - test_comparison_report: two periods with variance calculated
  - test_zero_balance_hidden: zero accounts excluded when flag set
  - test_client_isolation: Client A data not in Client B report
  - test_empty_period: no transactions produces $0 report, not error
  - test_account_grouping: accounts grouped by type correctly

[ACCEPTANCE CRITERIA]
- [ ] Revenue, COGS, expenses, and other sections correct
- [ ] Gross profit and net income calculated correctly
- [ ] Only POSTED entries included (DRAFT/PENDING excluded)
- [ ] Date range filtering works
- [ ] Comparison report with variance
- [ ] Client isolation on all queries
- [ ] React component with date picker and formatting
- [ ] All test cases pass

[OUTPUT FORMAT]
End every session by printing to terminal:

  ================================
  SESSION COMPLETE
  Agent:        R1 — Profit & Loss
  Task:         TASK-035
  Files changed: [list each file]
  Tests:        [passed/total]
  Issues opened: [n] — IDs: [list]
  Issues closed: [n] — IDs: [list]
  Next task:    TASK-036 — R2 Balance Sheet
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
