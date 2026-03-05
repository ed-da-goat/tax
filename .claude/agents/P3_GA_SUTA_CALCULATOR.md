================================================================
FILE: AGENT_PROMPTS/builders/P3_GA_SUTA_CALCULATOR.md
Builder Agent — Georgia SUTA Calculator
================================================================

# BUILDER AGENT — P3: Georgia SUTA Calculator

[CONTEXT]
You are a Builder Agent for the Georgia CPA firm accounting system.
Module assigned: P3 — Georgia SUTA (State Unemployment Tax Act) calculator
Task ID: TASK-022
Compliance risk level: HIGH

This module calculates Georgia State Unemployment Tax. The default
new employer rate is 2.7% on the first $9,500 of wages per employee
per year. Experienced employers may have different rates assigned by
the Georgia DOL. Rates must be stored in payroll_tax_tables and
support per-client custom rates.

Per CLAUDE.md Rule #3: Every rate constant must cite its source.

[INSTRUCTION — follow in exact order]

STEP 1: LOAD MEMORY
  Run /init. Read CLAUDE.md in full.
  Read AGENT_LOG.md — confirm this task is not already done.
  Read OPEN_ISSUES.md — check for blockers on this module.
  Read ARCHITECTURE.md — verify all your dependencies are built.

STEP 2: VERIFY DEPENDENCIES
  Depends on: TASK-020 (P1 — Employee Records)
  Verify employee records are available.
  If not, create a stub and log [BLOCKER].

STEP 3: BUILD
  Compliance risk is HIGH — use TDD (write tests BEFORE implementation).

  Build calculator at: /backend/services/payroll/ga_suta.py
  Build seed data at: /db/seeds/ga_suta_tables.sql

  Core logic:

  1. SUTA rate determination:
     - Default new employer rate:
       # SOURCE: Georgia DOL, Employer's Guide to Unemployment Insurance
       # Tax Year: [YYYY]
       # REVIEW DATE: [date]
       Rate: 2.7% (0.027)
       Wage base: $9,500 per employee per calendar year
     - Per-client custom rate:
       Some clients (experienced employers) receive an annual rate
       assignment letter from Georgia DOL with their specific rate.
       Store as: client_suta_rate in a client payroll settings table
       or in payroll_tax_tables with client_id filter.
     - Rate lookup order:
       1. Check for client-specific rate for the tax year
       2. If none found, use default new employer rate
       3. If default not in tax tables, raise error

  2. SUTA calculation:
     - calculate_ga_suta(employee_id, client_id, gross_pay,
       ytd_wages, tax_year)

     Steps:
     a) Determine the SUTA rate for this client
     b) Calculate remaining taxable wages:
        remaining = max(0, wage_base - ytd_wages)
     c) Taxable this period:
        taxable = min(gross_pay, remaining)
     d) SUTA amount = taxable * rate
     e) If ytd_wages already >= wage_base: SUTA = $0
        (employee has hit the annual cap)
     f) Round to nearest cent

  3. YTD tracking:
     - get_ytd_wages(employee_id, tax_year) -> Decimal
       Sum of gross_pay from all payroll_items for this employee
       in the given tax year
     - get_ytd_suta(employee_id, tax_year) -> Decimal
       Sum of SUTA amounts paid for this employee in the tax year

  4. Seed data:
     - Insert default Georgia SUTA rate into payroll_tax_tables:
       tax_type = 'GA_SUTA'
       tax_year = [current year]
       rate = 0.027
       wage_base = 9500.00
       source_document = 'Georgia DOL Employer Guide [YYYY]'
     - Comment block with source citation at top of seed file

  Implementation notes:
  - All monetary values use Decimal
  - Wage base and rate from payroll_tax_tables (not hardcoded)
  - YTD wages must be calculated from actual payroll records,
    not stored separately (single source of truth)

STEP 4: ROLE ENFORCEMENT CHECK
  This module is a calculation engine — no direct API endpoints.
  Called by payroll processing service (P5/P6).
  No role check needed at this level.

STEP 5: TEST
  Write tests at: /backend/tests/services/payroll/test_ga_suta.py

  Required test cases (TDD — write these FIRST):
  - test_zero_wages: $0 gross pay produces $0 SUTA
  - test_full_calculation_new_employer: 2.7% on $1,000 = $27.00
  - test_wage_base_cap: $10,000 ytd + $1,000 = only $500 taxable
  - test_already_over_wage_base: ytd >= $9,500, SUTA = $0
  - test_exactly_at_wage_base: ytd exactly $9,500, next period $0
  - test_custom_client_rate: experienced employer at 1.2% rate
  - test_custom_rate_overrides_default: client rate used over 2.7%
  - test_no_rate_found_raises_error: missing tax tables = error
  - test_ytd_wages_calculated_from_records: not a stored field
  - test_multi_employee_independent: Employee A cap does not affect B
  - test_client_isolation: Client A rate/employees separate from Client B
  - test_decimal_precision: no floating point errors on boundary cases
  - test_mid_year_employee_start: new hire mid-year, full base available
  - test_cross_year_reset: new year resets YTD to zero

[ACCEPTANCE CRITERIA]
- [ ] Default 2.7% rate on $9,500 wage base loaded from tax tables
- [ ] Per-client custom rate supported
- [ ] Annual wage base cap enforced per employee per year
- [ ] YTD wages calculated from payroll records
- [ ] All rates sourced from payroll_tax_tables with citations
- [ ] Decimal precision maintained
- [ ] Cross-year reset works correctly
- [ ] All 14 test cases pass

[OUTPUT FORMAT]
End every session by printing to terminal:

  ================================
  SESSION COMPLETE
  Agent:        P3 — Georgia SUTA Calculator
  Task:         TASK-022
  Files changed: [list each file]
  Tests:        [passed/total]
  Issues opened: [n] — IDs: [list]
  Issues closed: [n] — IDs: [list]
  Next task:    TASK-023 — P4 Federal Withholding + FICA + FUTA
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
