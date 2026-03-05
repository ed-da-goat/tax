================================================================
FILE: AGENT_PROMPTS/builders/X5_FEDERAL_SCHEDULE_C.md
Builder Agent — Federal Schedule C
================================================================

# BUILDER AGENT — X5: Federal Schedule C Data Export

[CONTEXT]
You are a Builder Agent for the Georgia CPA firm accounting system.
Module assigned: X5 — Federal Schedule C data export (sole proprietors)
Task ID: TASK-030
Compliance risk level: HIGH

Federal Schedule C (Profit or Loss from Business) reports sole
proprietor business income and expenses. This module maps GL account
data to the specific line items on Schedule C. The output is a data
export (not the official IRS form) that the CPA uses to complete
the actual tax filing.

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

  Build service at: /backend/services/tax_forms/federal_schedule_c.py
  Build template at: /backend/templates/tax_forms/schedule_c.html

  Core logic:

  1. Schedule C line-item mapping:
     - generate_schedule_c_data(client_id, tax_year)
       Only for entity_type = 'SOLE_PROP'
       Map GL accounts to Schedule C lines:
       # SOURCE: IRS Schedule C (Form 1040) Instructions, Tax Year [YYYY]
       # REVIEW DATE: [date]

       Part I — Income:
       - Line 1: Gross receipts (Revenue accounts 4000-4100)
       - Line 2: Returns and allowances
       - Line 4: Cost of goods sold (COGS accounts 5000-5200)
       - Line 5: Gross profit (Line 1 - Line 2 - Line 4)
       - Line 6: Other income (4200-4400)
       - Line 7: Gross income (Line 5 + Line 6)

       Part II — Expenses:
       - Line 8: Advertising (6000)
       - Line 9: Car and truck (6100)
       - Line 15: Insurance (6300)
       - Line 17: Legal and professional (6500)
       - Line 18: Office expense (6400)
       - Line 20b: Rent — other business property (6600)
       - Line 22: Supplies (6400 subcategories)
       - Line 24a: Travel (6950)
       - Line 24b: Meals (6900)
       - Line 25: Utilities (6700)
       - Line 27: Other expenses (6800, 6960, 6970, 6980)
       - Line 28: Total expenses
       - Line 31: Net profit or loss

       Unmapped accounts: list separately for CPA to manually assign

  2. Data validation:
     - Verify GL data is complete for the tax year
     - Flag any accounts not mapped to a Schedule C line
     - Flag any unusual amounts (negative revenue, very large expenses)
     - Warn if no revenue recorded (possible data issue)

  3. Export formats:
     - JSON data structure matching Schedule C lines
     - PDF summary via WeasyPrint (data worksheet, not official form)
     - CSV export option for import into tax software

  API endpoints:
  - POST /api/clients/{client_id}/tax-forms/schedule-c/generate — generate
  - GET /api/clients/{client_id}/tax-forms/schedule-c/{year} — get data
  - GET /api/clients/{client_id}/tax-forms/schedule-c/{year}/pdf — PDF
  - GET /api/clients/{client_id}/tax-forms/schedule-c/{year}/csv — CSV

  ALL endpoints: CPA_OWNER only.

STEP 4: ROLE ENFORCEMENT CHECK
  ALL endpoints: CPA_OWNER only.
  Write tests proving ASSOCIATE cannot access.

STEP 5: TEST
  Write tests at: /backend/tests/services/tax_forms/test_schedule_c.py

  Required test cases:
  - test_sole_prop_only: non-SOLE_PROP rejected
  - test_revenue_mapping: revenue accounts -> Line 1
  - test_cogs_mapping: COGS accounts -> Line 4
  - test_expense_line_mapping: each expense category mapped correctly
  - test_net_profit_calculation: revenue - COGS - expenses = net
  - test_unmapped_accounts_flagged: unknown accounts listed separately
  - test_pdf_generation: valid PDF produced
  - test_csv_export: valid CSV produced
  - test_requires_cpa_owner: ASSOCIATE blocked
  - test_client_isolation: Client A data not in Client B export
  - test_loss_result: negative net income handled correctly
  - test_zero_revenue_warning: flagged if no revenue

[ACCEPTANCE CRITERIA]
- [ ] Sole proprietor clients only
- [ ] GL accounts mapped to Schedule C line items
- [ ] Unmapped accounts flagged for CPA review
- [ ] Net profit/loss calculated correctly
- [ ] PDF and CSV export options
- [ ] CPA_OWNER only
- [ ] All test cases pass

[OUTPUT FORMAT]
End every session by printing to terminal:

  ================================
  SESSION COMPLETE
  Agent:        X5 — Federal Schedule C
  Task:         TASK-030
  Files changed: [list each file]
  Tests:        [passed/total]
  Issues opened: [n] — IDs: [list]
  Issues closed: [n] — IDs: [list]
  Next task:    TASK-031 — X6 Federal Form 1120-S
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
