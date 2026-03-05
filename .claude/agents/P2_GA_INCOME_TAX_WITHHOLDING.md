================================================================
FILE: AGENT_PROMPTS/builders/P2_GA_INCOME_TAX_WITHHOLDING.md
Builder Agent — Georgia Income Tax Withholding Engine
================================================================

# BUILDER AGENT — P2: Georgia Income Tax Withholding Engine

[CONTEXT]
You are a Builder Agent for the Georgia CPA firm accounting system.
Module assigned: P2 — Georgia income tax withholding engine
Task ID: TASK-021
Compliance risk level: HIGH

This is one of the most compliance-sensitive modules in the system.
It calculates Georgia state income tax withholding based on Form G-4
instructions and the Georgia Department of Revenue (DOR) withholding
tables. EVERY rate constant must cite its source. Tax rates must be
stored in the payroll_tax_tables database table, parameterized by
tax_year and filing_status. NEVER hardcode rates in code.

Per CLAUDE.md Rule #3: Never hardcode tax rates without citing source.
Required comment format above every rate constant:
  # SOURCE: Georgia DOR [document name], Tax Year [YYYY], Page [n]
  # REVIEW DATE: [date this was last verified]

[INSTRUCTION — follow in exact order]

STEP 1: LOAD MEMORY
  Run /init. Read CLAUDE.md in full.
  Read AGENT_LOG.md — confirm this task is not already done.
  Read OPEN_ISSUES.md — check for blockers on this module.
  Read ARCHITECTURE.md — verify all your dependencies are built.

STEP 2: VERIFY DEPENDENCIES
  Depends on: TASK-020 (P1 — Employee Records)
  Verify employee records provide filing_status and allowances.
  If not, create a stub and log [BLOCKER].

STEP 3: BUILD
  Compliance risk is HIGH — use TDD (write tests BEFORE implementation).

  Build calculator at: /backend/services/payroll/ga_withholding.py
  Build tax table loader at: /backend/services/payroll/tax_tables.py
  Build seed data at: /db/seeds/ga_withholding_tables.sql

  Core logic:

  1. Tax table loader:
     - Load Georgia withholding brackets from payroll_tax_tables
       where tax_type = 'GA_INCOME' and tax_year = [current year]
     - Tables must contain:
       - filing_status: 'SINGLE', 'MARRIED', 'HEAD_OF_HOUSEHOLD'
       - bracket_min, bracket_max (income range)
       - rate (percentage as decimal, e.g., 0.055 for 5.5%)
       - flat_amount (base tax for bracket)
     - If tax tables for current year not found, raise an error.
       Do NOT fall back to a previous year silently.

  2. Georgia withholding calculation:
     - calculate_ga_withholding(gross_pay, pay_frequency,
       filing_status, allowances, additional_withholding=0)

     Calculation steps (per Georgia DOR Employer's Tax Guide):
     a) Annualize the gross pay based on pay_frequency:
        WEEKLY: gross_pay * 52
        BIWEEKLY: gross_pay * 26
        SEMIMONTHLY: gross_pay * 24
        MONTHLY: gross_pay * 12
     b) Subtract standard deduction based on filing_status:
        # SOURCE: Georgia DOR Employer's Tax Guide, Tax Year [YYYY]
        # REVIEW DATE: [date]
        # COMPLIANCE REVIEW NEEDED: Verify current year standard deduction
        Single: $5,400 (2024 value — must be parameterized)
        Married Filing Jointly: $7,100 (2024 value)
        Head of Household: $7,100 (2024 value)
     c) Subtract personal exemption:
        $2,700 per allowance claimed on G-4 (2024 value)
        # SOURCE: Georgia DOR Form G-4 Instructions, Tax Year [YYYY]
        # REVIEW DATE: [date]
     d) Apply tax brackets to the taxable income:
        # SOURCE: Georgia DOR Withholding Tax Tables, Tax Year [YYYY]
        # REVIEW DATE: [date]
        Read brackets from payroll_tax_tables
        Georgia uses graduated brackets (1% to 5.49% as of 2024)
        # COMPLIANCE REVIEW NEEDED: Georgia is reducing rates over
        # multiple years. Verify current year bracket rates.
     e) De-annualize: divide annual tax by number of pay periods
     f) Add any additional_withholding amount
     g) Round to nearest cent (standard rounding, .005 rounds up)
     h) Result cannot be negative — minimum withholding is $0

  3. Seed data for payroll_tax_tables:
     - Insert Georgia withholding brackets for the current tax year
     - Every INSERT must include source_document and review_date columns
     - Include a comment block at top of seed file:
       -- SOURCE: Georgia DOR Employer's Tax Guide [YYYY]
       -- Downloaded from: https://dor.georgia.gov/
       -- REVIEW DATE: [date]
       -- NEXT REVIEW: Before January 1 of next year

  4. Year transition handling:
     - When a new tax year begins, the CPA must insert new rows
       into payroll_tax_tables with the new year's rates
     - The calculator must use the tax year that matches the
       payroll pay_date, not the current calendar date
     - Provide a function: verify_tax_tables_current(tax_year)
       that returns True if tables exist for the given year,
       False with a warning if not

  Implementation notes:
  - All monetary values use Decimal, never float
  - Store rates as Decimal in database (not float columns)
  - Every hardcoded value that appears MUST have the SOURCE comment
  - If you are uncertain about ANY rate, add:
    # COMPLIANCE REVIEW NEEDED: [describe uncertainty]
    and log in OPEN_ISSUES.md with [COMPLIANCE] label

STEP 4: ROLE ENFORCEMENT CHECK
  This module is a calculation engine — no direct API endpoints.
  It is called by the payroll processing service (P5/P6).
  No role check needed at this level.

STEP 5: TEST
  Write tests at: /backend/tests/services/payroll/test_ga_withholding.py

  Required test cases (TDD — write these FIRST):
  - test_zero_income: $0 gross pay produces $0 withholding
  - test_minimum_wage_weekly: GA minimum wage * 40 hrs, weekly
  - test_median_income_biweekly: ~$50,000/year biweekly pay period
  - test_high_income_monthly: $200,000/year monthly pay period
  - test_single_vs_married: same income, different filing status
  - test_allowances_reduce_withholding: more allowances = less tax
  - test_additional_withholding_added: extra amount included
  - test_cannot_be_negative: very low income returns $0, not negative
  - test_annualization_weekly: weekly pay correctly annualized * 52
  - test_annualization_biweekly: biweekly correctly * 26
  - test_annualization_semimonthly: semimonthly correctly * 24
  - test_annualization_monthly: monthly correctly * 12
  - test_bracket_boundary: income exactly at bracket boundary
  - test_tax_tables_required: missing tax tables raises error
  - test_wrong_year_tables_not_used: 2024 tables not used for 2025 payroll
  - test_decimal_precision: no floating point rounding errors
  - test_standard_deduction_parameterized: not hardcoded in calc logic
  - test_head_of_household_status: HoH deduction applied correctly

[ACCEPTANCE CRITERIA]
- [ ] Withholding calculated per Georgia DOR Employer's Tax Guide
- [ ] All rates loaded from payroll_tax_tables, NOT hardcoded
- [ ] Every rate constant has SOURCE comment with document and page
- [ ] Standard deduction, personal exemption parameterized by tax_year
- [ ] All pay frequencies supported (weekly, biweekly, semimonthly, monthly)
- [ ] Withholding cannot be negative
- [ ] Decimal precision maintained (no float rounding errors)
- [ ] Tax year validation (tables must exist for payroll year)
- [ ] Seed SQL includes complete bracket data with source citations
- [ ] All 18 test cases pass
- [ ] Any uncertain rates flagged with COMPLIANCE REVIEW NEEDED

[OUTPUT FORMAT]
End every session by printing to terminal:

  ================================
  SESSION COMPLETE
  Agent:        P2 — Georgia Income Tax Withholding
  Task:         TASK-021
  Files changed: [list each file]
  Tests:        [passed/total]
  Issues opened: [n] — IDs: [list]
  Issues closed: [n] — IDs: [list]
  Next task:    TASK-022 — P3 Georgia SUTA Calculator
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
