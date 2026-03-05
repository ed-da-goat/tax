================================================================
FILE: AGENT_PROMPTS/builders/F2_CHART_OF_ACCOUNTS.md
Builder Agent — Chart of Accounts (Georgia Standard)
================================================================

# BUILDER AGENT — F2: Chart of Accounts (Georgia Standard Categories, Pre-seeded)

[CONTEXT]
You are a Builder Agent for the Georgia CPA firm accounting system.
Module assigned: F2 — Chart of Accounts (Georgia standard categories, pre-seeded)
Task ID: TASK-009
Compliance risk level: MEDIUM

This module pre-seeds the chart of accounts with Georgia-standard
accounting categories covering all four entity types: sole
proprietors, S-Corps, C-Corps, and partnerships/LLCs. The CoA is
the backbone of every financial report and tax form — incorrect
categories mean incorrect filings.

[INSTRUCTION — follow in exact order]

STEP 1: LOAD MEMORY
  Run /init. Read CLAUDE.md in full.
  Read AGENT_LOG.md — confirm this task is not already done.
  Read OPEN_ISSUES.md — check for blockers on this module.
  Read ARCHITECTURE.md — verify all your dependencies are built.

STEP 2: VERIFY DEPENDENCIES
  Depends on: TASK-008 (F1 — Database Schema)
  Verify that the chart_of_accounts table exists in the schema.
  If not, create a stub and log [BLOCKER].

STEP 3: BUILD
  Compliance risk is MEDIUM — write tests alongside implementation.

  Build seed data at: /db/seeds/chart_of_accounts.sql
  Build API at: /backend/api/chart_of_accounts.py
  Build service at: /backend/services/chart_of_accounts.py

  Seed data — Georgia-standard chart of accounts:
  Use standard account numbering convention:
  - 1000-1999: Assets
    - 1000 Cash and Cash Equivalents
    - 1010 Savings
    - 1100 Accounts Receivable
    - 1200 Inventory
    - 1300 Prepaid Expenses
    - 1400 Fixed Assets
    - 1410 Accumulated Depreciation
    - 1500 Other Assets
  - 2000-2999: Liabilities
    - 2000 Accounts Payable
    - 2100 Accrued Expenses
    - 2200 Payroll Liabilities
    - 2210 Federal Withholding Payable
    - 2220 State Withholding Payable (Georgia)
    - 2230 FICA Payable
    - 2240 FUTA Payable
    - 2250 SUTA Payable (Georgia)
    - 2300 Sales Tax Payable (Georgia ST-3)
    - 2400 Short-term Notes Payable
    - 2500 Long-term Debt
    - 2600 Other Liabilities
  - 3000-3999: Equity
    - 3000 Owner's Equity / Capital Stock
    - 3100 Retained Earnings
    - 3200 Owner's Draw / Distributions
    - 3300 Additional Paid-in Capital (C-Corp/S-Corp)
    - 3400 Partner Capital Accounts (Partnership/LLC)
  - 4000-4999: Revenue
    - 4000 Service Revenue
    - 4100 Product Revenue / Sales
    - 4200 Other Income
    - 4300 Interest Income
    - 4400 Gain on Sale of Assets
  - 5000-5999: Cost of Goods Sold
    - 5000 Cost of Goods Sold
    - 5100 Direct Labor
    - 5200 Materials and Supplies
  - 6000-6999: Operating Expenses
    - 6000 Advertising and Marketing
    - 6100 Auto and Vehicle Expense
    - 6200 Payroll Expenses
    - 6210 Employer FICA
    - 6220 Employer FUTA
    - 6230 Employer SUTA (Georgia)
    - 6300 Insurance
    - 6400 Office Supplies
    - 6500 Professional Fees
    - 6600 Rent Expense
    - 6700 Utilities
    - 6800 Depreciation Expense
    - 6900 Meals and Entertainment
    - 6950 Travel Expense
    - 6960 Dues and Subscriptions
    - 6970 Bank Charges
    - 6980 Miscellaneous Expense
  - 7000-7999: Other Expense
    - 7000 Interest Expense
    - 7100 Loss on Sale of Assets
    - 7200 Charitable Contributions

  Entity-type-specific accounts:
  - S-Corp: 3300 Additional Paid-in Capital, Officer Compensation
  - C-Corp: 3300 Additional Paid-in Capital, Income Tax Expense (7300)
  - Partnership/LLC: 3400 Partner Capital, Guaranteed Payments (6250)
  - Sole Prop: 3000 Owner's Equity, 3200 Owner's Draw

  Each account in seed data must specify:
  - account_number, account_name, account_type, applicable_entity_types

  When a new client is created, copy the standard CoA into that
  client's chart of accounts (filtered by entity type). Each client
  gets their own copy so they can customize.

  API endpoints (FastAPI):
  - GET /api/clients/{client_id}/accounts — list all accounts for client
  - POST /api/clients/{client_id}/accounts — create custom account
  - PUT /api/clients/{client_id}/accounts/{id} — update account
  - DELETE /api/clients/{client_id}/accounts/{id} — soft delete
  - POST /api/clients/{client_id}/accounts/seed — seed standard CoA
    (CPA_OWNER only)

  All endpoints must filter by client_id. No cross-client access.

STEP 4: ROLE ENFORCEMENT CHECK
  - POST /seed endpoint: CPA_OWNER only
  - POST create, PUT update: both roles (ASSOCIATE can suggest)
  - DELETE: CPA_OWNER only
  - GET list: both roles
  Write tests proving ASSOCIATE cannot seed or delete accounts.

STEP 5: TEST
  Write tests at: /backend/tests/services/test_chart_of_accounts.py

  Required test cases:
  - test_seed_sole_prop_accounts: correct accounts for sole proprietor
  - test_seed_scorp_accounts: includes officer compensation, paid-in capital
  - test_seed_ccorp_accounts: includes income tax expense
  - test_seed_partnership_accounts: includes partner capital, guaranteed payments
  - test_client_isolation: Client A cannot see Client B accounts
  - test_create_custom_account: new account added to client's CoA
  - test_soft_delete_account: deleted_at set, not removed from DB
  - test_list_excludes_deleted: soft-deleted accounts not in list results
  - test_seed_requires_cpa_owner: ASSOCIATE cannot seed
  - test_delete_requires_cpa_owner: ASSOCIATE cannot delete

[ACCEPTANCE CRITERIA]
- [ ] Standard Georgia CoA seed data covers all 4 entity types
- [ ] Account numbering follows 1000-7999 convention
- [ ] New client gets entity-type-filtered copy of standard CoA
- [ ] CRUD API endpoints work with client_id isolation
- [ ] CPA_OWNER-only operations enforced
- [ ] Georgia-specific accounts included (state withholding, SUTA, sales tax)
- [ ] All test cases pass

[OUTPUT FORMAT]
End every session by printing to terminal:

  ================================
  SESSION COMPLETE
  Agent:        F2 — Chart of Accounts (Georgia Standard)
  Task:         TASK-009
  Files changed: [list each file]
  Tests:        [passed/total]
  Issues opened: [n] — IDs: [list]
  Issues closed: [n] — IDs: [list]
  Next task:    TASK-010 — F3 General Ledger
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
