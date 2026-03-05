================================================================
FILE: AGENT_PROMPTS/builders/X4_GA_FORM_ST3.md
Builder Agent — Georgia Form ST-3
================================================================

# BUILDER AGENT — X4: Georgia Form ST-3 (Sales Tax)

[CONTEXT]
You are a Builder Agent for the Georgia CPA firm accounting system.
Module assigned: X4 — Georgia Form ST-3 (sales tax — applicable clients)
Task ID: TASK-029
Compliance risk level: HIGH

Georgia Form ST-3 is the sales and use tax return. Not all clients
collect sales tax — only those selling taxable goods/services.
Georgia has a 4% state rate plus local options that vary by
jurisdiction (county/city). This module pulls sales data from
AR, applies jurisdiction-specific rates, and generates the form
data and PDF using WeasyPrint.

CPA_OWNER only can export tax forms.

[INSTRUCTION — follow in exact order]

STEP 1: LOAD MEMORY
  Run /init. Read CLAUDE.md in full.
  Read AGENT_LOG.md — confirm this task is not already done.
  Read OPEN_ISSUES.md — check for blockers on this module.
  Read ARCHITECTURE.md — verify all your dependencies are built.

STEP 2: VERIFY DEPENDENCIES
  Depends on: TASK-010 (F3 — GL), TASK-014 (T2 — AR)
  Verify GL and AR services are available.
  If any missing, create typed stubs and log [BLOCKER].

STEP 3: BUILD
  Compliance risk is HIGH — use TDD (write tests BEFORE implementation).

  Build service at: /backend/services/tax_forms/ga_st3.py
  Build template at: /backend/templates/tax_forms/ga_st3.html
  Build rate table at: /db/seeds/ga_sales_tax_rates.sql

  Core logic:

  1. Sales tax rate management:
     - Georgia state rate: 4%
       # SOURCE: Georgia Code O.C.G.A. 48-8-30
       # REVIEW DATE: [date]
     - Local options tax (LOST): varies by county/city
       # SOURCE: Georgia DOR Sales Tax Rate Chart
       # REVIEW DATE: [date]
       # COMPLIANCE REVIEW NEEDED: Local rates change frequently.
       # CPA must verify rates for each client's jurisdiction(s)
       # before filing.
     - Store rates in a sales_tax_jurisdictions table or
       payroll_tax_tables with tax_type = 'GA_SALES_TAX'
     - Fields: jurisdiction_name, jurisdiction_type (STATE, COUNTY,
       CITY, SPECIAL), rate, effective_date, end_date

  2. ST-3 data aggregation:
     - generate_st3_data(client_id, tax_period)
       tax_period: monthly or quarterly (based on client's filing freq)
       Pull from AR/GL:
       a) Gross sales (from revenue/sales accounts)
       b) Exempt sales (if tracked)
       c) Taxable sales (gross - exempt)
       d) Tax collected (from Sales Tax Payable account 2300)
       e) Tax due by jurisdiction:
          - State tax (4% of taxable sales)
          - County tax (varies)
          - City/special district tax (varies)
       f) Total tax due
       g) Credits/payments
       h) Balance due or overpayment

  3. Filing frequency:
     - Monthly: clients with > $200/month in sales tax
     - Quarterly: clients with < $200/month in sales tax
     # COMPLIANCE REVIEW NEEDED: Filing frequency thresholds.
     # Store as client setting, CPA configures per client.

  4. PDF generation (WeasyPrint):
     - generate_st3_pdf(client_id, tax_period) -> bytes
     # COMPLIANCE REVIEW NEEDED: Data worksheet only.

  API endpoints:
  - POST /api/clients/{client_id}/tax-forms/st3/generate — generate
  - GET /api/clients/{client_id}/tax-forms/st3/{period} — get data
  - GET /api/clients/{client_id}/tax-forms/st3/{period}/pdf — download PDF

  ALL endpoints: CPA_OWNER only.

STEP 4: ROLE ENFORCEMENT CHECK
  ALL endpoints: CPA_OWNER only.
  Write tests proving ASSOCIATE cannot access.

STEP 5: TEST
  Write tests at: /backend/tests/services/tax_forms/test_ga_st3.py

  Required test cases:
  - test_state_tax_rate: 4% applied to taxable sales
  - test_local_tax_applied: county/city rate added
  - test_combined_rate_correct: state + local = total rate
  - test_exempt_sales_excluded: exempt sales not taxed
  - test_tax_collected_vs_due: compare collected to calculated
  - test_pdf_generation: WeasyPrint produces valid PDF
  - test_monthly_period: monthly filing period data correct
  - test_quarterly_period: quarterly filing period data correct
  - test_requires_cpa_owner: ASSOCIATE cannot access
  - test_client_isolation: Client A sales data not in Client B form
  - test_zero_sales_period: period with no sales handled
  - test_jurisdiction_rate_lookup: correct rate for jurisdiction

[ACCEPTANCE CRITERIA]
- [ ] Sales data aggregated from AR/GL
- [ ] State 4% rate applied correctly
- [ ] Local jurisdiction rates supported (parameterized)
- [ ] Exempt sales excluded from tax calculation
- [ ] Monthly and quarterly filing periods supported
- [ ] PDF generated via WeasyPrint
- [ ] CPA_OWNER only for all operations
- [ ] Local rates flagged for frequent CPA review
- [ ] All test cases pass

[OUTPUT FORMAT]
End every session by printing to terminal:

  ================================
  SESSION COMPLETE
  Agent:        X4 — Georgia Form ST-3
  Task:         TASK-029
  Files changed: [list each file]
  Tests:        [passed/total]
  Issues opened: [n] — IDs: [list]
  Issues closed: [n] — IDs: [list]
  Next task:    TASK-030 — X5 Federal Schedule C
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
