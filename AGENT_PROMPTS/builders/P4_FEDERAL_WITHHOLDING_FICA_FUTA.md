================================================================
FILE: AGENT_PROMPTS/builders/P4_FEDERAL_WITHHOLDING_FICA_FUTA.md
Builder Agent — Federal Withholding + FICA + FUTA
================================================================

# BUILDER AGENT — P4: Federal Withholding + FICA + FUTA Calculator

[CONTEXT]
You are a Builder Agent for the Georgia CPA firm accounting system.
Module assigned: P4 — Federal withholding + FICA + FUTA calculator
Task ID: TASK-023
Compliance risk level: HIGH

This module calculates federal payroll taxes: income tax withholding
(per IRS Publication 15-T), Social Security tax (6.2%), Medicare tax
(1.45% + 0.9% additional above threshold), and FUTA (6.0% minus
5.4% Georgia credit = 0.6% effective). All rates from payroll_tax_tables.

Per CLAUDE.md Rule #3: Every rate constant must cite its source.

[INSTRUCTION — follow in exact order]

STEP 1: LOAD MEMORY
  Run /init. Read CLAUDE.md in full.
  Read AGENT_LOG.md — confirm this task is not already done.
  Read OPEN_ISSUES.md — check for blockers on this module.
  Read ARCHITECTURE.md — verify all your dependencies are built.

STEP 2: VERIFY DEPENDENCIES
  Depends on: TASK-020 (P1 — Employee Records)
  Verify employee records provide filing_status and W-4 data.
  If not, create a stub and log [BLOCKER].

STEP 3: BUILD
  Compliance risk is HIGH — use TDD (write tests BEFORE implementation).

  Build calculators at:
  - /backend/services/payroll/federal_withholding.py
  - /backend/services/payroll/fica.py
  - /backend/services/payroll/futa.py
  Build seed data at: /db/seeds/federal_tax_tables.sql

  Core calculators:

  1. Federal income tax withholding:
     - calculate_federal_withholding(gross_pay, pay_frequency,
       filing_status, w4_step2, w4_step3, w4_step4a, w4_step4b,
       w4_step4c)
     - Use IRS Publication 15-T percentage method:
       # SOURCE: IRS Publication 15-T, Tax Year [YYYY]
       # REVIEW DATE: [date]
       a) Annualize gross pay
       b) Subtract Step 4(b) deductions (if any)
       c) Apply standard deduction based on filing status
       d) Look up tax brackets from payroll_tax_tables
          (tax_type = 'FEDERAL_INCOME', filing_status, tax_year)
       e) Calculate annual tax
       f) Subtract Step 3 credits (if any)
       g) Add Step 4(a) extra income tax (if any)
       h) Add Step 4(c) extra withholding (if any)
       i) De-annualize by pay periods
     - Support both 2020+ W-4 format and pre-2020 format
       (allowances-based for legacy employees)

  2. Social Security (OASDI):
     - calculate_social_security(gross_pay, ytd_wages, tax_year)
     - Rate: 6.2% (employee share)
       # SOURCE: IRS Publication 15, Tax Year [YYYY]
       # REVIEW DATE: [date]
     - Wage base: $168,600 (2024 — must be parameterized by year)
     - If ytd_wages >= wage_base: tax = $0
     - Taxable = min(gross_pay, wage_base - ytd_wages)
     - Tax = taxable * 0.062

  3. Medicare:
     - calculate_medicare(gross_pay, ytd_wages, filing_status, tax_year)
     - Regular rate: 1.45% on all wages (no cap)
       # SOURCE: IRS Publication 15, Tax Year [YYYY]
       # REVIEW DATE: [date]
     - Additional Medicare: 0.9% on wages above threshold
       Thresholds:
       - Single / Head of Household: $200,000
       - Married Filing Jointly: $250,000
       - Married Filing Separately: $125,000
       # SOURCE: IRS Form 8959 Instructions, Tax Year [YYYY]
       # REVIEW DATE: [date]
     - Tax = (gross_pay * 0.0145) +
             max(0, (ytd_wages + gross_pay - threshold) * 0.009 -
                    max(0, (ytd_wages - threshold) * 0.009))

  4. FUTA:
     - calculate_futa(gross_pay, ytd_wages, tax_year)
     - Gross rate: 6.0%
     - Georgia credit: 5.4% (Georgia is a credit state)
     - Effective rate: 0.6%
       # SOURCE: IRS Publication 15, FUTA section, Tax Year [YYYY]
       # REVIEW DATE: [date]
       # NOTE: Georgia credit assumes state UI taxes paid timely.
       # COMPLIANCE REVIEW NEEDED: Verify Georgia credit eligibility
       # each year — credit can be reduced if state borrows from
       # federal UI trust fund.
     - Wage base: $7,000 per employee per year
     - If ytd_wages >= $7,000: FUTA = $0
     - Taxable = min(gross_pay, 7000 - ytd_wages)
     - FUTA = taxable * 0.006

  5. Seed data for federal tax tables:
     - Insert all federal income tax brackets by filing status
     - Insert Social Security wage base and rate
     - Insert Medicare rate and thresholds
     - Insert FUTA rate and wage base
     - All with source_document and review_date

STEP 4: ROLE ENFORCEMENT CHECK
  Calculation engine — no direct API endpoints.
  Called by payroll processing service (P5/P6).
  No role check needed.

STEP 5: TEST
  Write tests at: /backend/tests/services/payroll/test_federal_taxes.py

  Required test cases (TDD — write these FIRST):

  Federal withholding:
  - test_zero_income_federal: $0 produces $0
  - test_single_standard_deduction: correct deduction applied
  - test_married_vs_single: different results by filing status
  - test_w4_step3_credits_reduce_tax: child tax credit etc.
  - test_w4_step4c_extra_withholding: additional withholding added

  Social Security:
  - test_ss_below_wage_base: full 6.2% applied
  - test_ss_at_wage_base: cap respected
  - test_ss_over_wage_base: $0 when already over
  - test_ss_partial_cap: partially over wage base

  Medicare:
  - test_medicare_regular_rate: 1.45% on all wages
  - test_medicare_additional_threshold_single: 0.9% above $200K
  - test_medicare_additional_threshold_married: 0.9% above $250K
  - test_medicare_no_cap: no wage base cap for Medicare

  FUTA:
  - test_futa_below_wage_base: 0.6% applied
  - test_futa_at_wage_base: $7,000 cap respected
  - test_futa_over_wage_base: $0 when already over
  - test_futa_georgia_credit: 5.4% credit applied

  General:
  - test_all_taxes_combined: all four calculated together correctly
  - test_decimal_precision: no floating point errors
  - test_tax_tables_required: missing tables raises error

[ACCEPTANCE CRITERIA]
- [ ] Federal withholding per IRS Pub 15-T percentage method
- [ ] Both 2020+ W-4 and pre-2020 format supported
- [ ] Social Security 6.2% with annual wage base cap
- [ ] Medicare 1.45% + 0.9% additional above threshold
- [ ] FUTA 0.6% effective (with Georgia credit) and $7K wage base
- [ ] All rates from payroll_tax_tables, parameterized by tax_year
- [ ] Every rate has SOURCE comment
- [ ] Decimal precision maintained
- [ ] All 20 test cases pass

[OUTPUT FORMAT]
End every session by printing to terminal:

  ================================
  SESSION COMPLETE
  Agent:        P4 — Federal Withholding + FICA + FUTA
  Task:         TASK-023
  Files changed: [list each file]
  Tests:        [passed/total]
  Issues opened: [n] — IDs: [list]
  Issues closed: [n] — IDs: [list]
  Next task:    TASK-024 — P5 Pay Stub Generator
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
