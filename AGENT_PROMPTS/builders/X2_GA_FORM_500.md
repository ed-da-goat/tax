================================================================
FILE: AGENT_PROMPTS/builders/X2_GA_FORM_500.md
Builder Agent — Georgia Form 500
================================================================

# BUILDER AGENT — X2: Georgia Form 500 (Individual Income Tax)

[CONTEXT]
You are a Builder Agent for the Georgia CPA firm accounting system.
Module assigned: X2 — Georgia Form 500 (individual income — Schedule C clients)
Task ID: TASK-027
Compliance risk level: HIGH

Georgia Form 500 is the individual income tax return. For the CPA
firm's purposes, this applies to sole proprietor clients who report
business income on Schedule C. This module pulls Schedule C data
from the GL, calculates Georgia taxable income, and generates
the form data and PDF using WeasyPrint.

CPA_OWNER only can export tax forms.

[INSTRUCTION — follow in exact order]

STEP 1: LOAD MEMORY
  Run /init. Read CLAUDE.md in full.
  Read AGENT_LOG.md — confirm this task is not already done.
  Read OPEN_ISSUES.md — check for blockers on this module.
  Read ARCHITECTURE.md — verify all your dependencies are built.

STEP 2: VERIFY DEPENDENCIES
  Depends on: TASK-010 (F3 — GL), TASK-035 (R1 — P&L)
  The P&L report provides the income/expense data that feeds into
  Schedule C and Form 500. If not built, use GL queries directly.
  If any missing, create typed stubs and log [BLOCKER].

STEP 3: BUILD
  Compliance risk is HIGH — use TDD (write tests BEFORE implementation).

  Build service at: /backend/services/tax_forms/ga_form_500.py
  Build template at: /backend/templates/tax_forms/ga_form_500.html

  Core logic:

  1. Form 500 data aggregation:
     - generate_form_500_data(client_id, tax_year)
       Only for clients with entity_type = 'SOLE_PROP'
       Pull from GL for the tax year:
       a) Gross receipts/revenue (account type: REVENUE)
       b) Cost of goods sold (account type: COGS)
       c) Business expenses by category (account type: EXPENSE)
       d) Net business income (revenue - COGS - expenses)
       e) Map GL categories to Schedule C lines
       f) Calculate Georgia taxable income:
          - Start with federal taxable income (from Schedule C)
          - Apply Georgia modifications (additions and subtractions)
          # COMPLIANCE REVIEW NEEDED: Georgia modifications vary by year.
          # CPA must review before filing.
       g) Apply Georgia tax brackets
          # SOURCE: Georgia DOR Form 500 Instructions, Tax Year [YYYY]
          # REVIEW DATE: [date]
          Read from payroll_tax_tables where tax_type = 'GA_INDIVIDUAL'
       h) Calculate tax due
       i) Apply estimated payments and withholding credits

  2. Schedule C mapping:
     Map GL account categories to Schedule C lines:
     - Line 1: Gross receipts (Revenue accounts)
     - Line 4: Cost of goods sold (COGS accounts)
     - Line 7: Gross income (Line 1 - Line 4)
     - Lines 8-27: Expense categories:
       - Advertising (6000)
       - Car/truck (6100)
       - Insurance (6300)
       - Office expense (6400)
       - Rent (6600)
       - Utilities (6700)
       - Other expenses (itemized)
     - Line 28: Total expenses
     - Line 31: Net profit/loss

  3. PDF generation (WeasyPrint):
     - generate_form_500_pdf(client_id, tax_year) -> bytes
     - Layout approximating Georgia Form 500
     # COMPLIANCE REVIEW NEEDED: This is a data worksheet, not an
     # official filing copy. CPA must transfer data to official
     # form or e-file software for actual filing.

  API endpoints:
  - POST /api/clients/{client_id}/tax-forms/500/generate — generate
  - GET /api/clients/{client_id}/tax-forms/500/{year} — get data
  - GET /api/clients/{client_id}/tax-forms/500/{year}/pdf — download PDF

  ALL endpoints: CPA_OWNER only.

STEP 4: ROLE ENFORCEMENT CHECK
  ALL endpoints: CPA_OWNER only.
  Write tests proving ASSOCIATE cannot access any Form 500 endpoint.

STEP 5: TEST
  Write tests at: /backend/tests/services/tax_forms/test_ga_form_500.py

  Required test cases:
  - test_sole_prop_only: non-SOLE_PROP client rejected
  - test_revenue_aggregation: gross receipts from revenue accounts
  - test_expense_categorization: expenses mapped to Schedule C lines
  - test_net_income_calculation: revenue - COGS - expenses = net
  - test_ga_tax_bracket_application: correct tax from brackets
  - test_pdf_generation: WeasyPrint produces valid PDF
  - test_requires_cpa_owner: ASSOCIATE cannot access
  - test_client_isolation: Client A data not in Client B form
  - test_zero_income: $0 income produces $0 tax
  - test_loss_handling: negative net income handled correctly

[ACCEPTANCE CRITERIA]
- [ ] Sole proprietor clients only (entity_type validation)
- [ ] GL data mapped to Schedule C line items
- [ ] Georgia taxable income calculated with bracket application
- [ ] PDF generated via WeasyPrint
- [ ] Georgia modifications flagged for CPA review
- [ ] CPA_OWNER only for all operations
- [ ] Client isolation on all queries
- [ ] All test cases pass

[OUTPUT FORMAT]
End every session by printing to terminal:

  ================================
  SESSION COMPLETE
  Agent:        X2 — Georgia Form 500
  Task:         TASK-027
  Files changed: [list each file]
  Tests:        [passed/total]
  Issues opened: [n] — IDs: [list]
  Issues closed: [n] — IDs: [list]
  Next task:    TASK-028 — X3 Georgia Form 600
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
