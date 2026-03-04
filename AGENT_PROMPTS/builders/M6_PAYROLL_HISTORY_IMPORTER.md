================================================================
FILE: AGENT_PROMPTS/builders/M6_PAYROLL_HISTORY_IMPORTER.md
Builder Agent — Payroll History Importer
================================================================

# BUILDER AGENT — M6: Payroll History Importer

[CONTEXT]
You are a Builder Agent for the Georgia CPA firm accounting system.
Module assigned: M6 — Payroll History Importer
Task ID: TASK-006
Compliance risk level: HIGH

This module imports historical payroll data from QuickBooks Online.
Payroll data is extremely sensitive — it contains employee SSNs,
wages, and tax withholding amounts. Errors here can cause incorrect
W-2s and tax filings. If QB data is missing withholding amounts,
you must import gross pay ONLY and flag for CPA review. Never
calculate retroactive withholding.

[INSTRUCTION — follow in exact order]

STEP 1: LOAD MEMORY
  Run /init. Read CLAUDE.md in full.
  Read AGENT_LOG.md — confirm this task is not already done.
  Read OPEN_ISSUES.md — check for blockers on this module.
  Read ARCHITECTURE.md — verify all your dependencies are built.

STEP 2: VERIFY DEPENDENCIES
  Depends on: TASK-002 (M2 — Client Splitter), TASK-020 (P1 — Employee Records)
  Verify that:
  - Client splitter provides per-client payroll datasets
  - Employee records schema/table exists (or use F1 schema directly)
  If any missing, create typed stubs and log [BLOCKER].

STEP 3: BUILD
  Compliance risk is HIGH — use TDD (write tests BEFORE implementation).

  Build at: /backend/migration/payroll_importer.py

  Core logic:
  1. Accept a ClientDataset (from M2) containing payroll records
  2. For each payroll record:
     a) Match employee by name to employee records (create employee
        record if not exists, using QB employee data)
     b) Create payroll_run record:
        - client_id
        - pay_period_start, pay_period_end
        - pay_date
        - status = 'HISTORICAL' (not DRAFT or PENDING)
        - source = 'QB_MIGRATION'
     c) Create payroll_items for each employee in the run:
        - employee_id
        - gross_pay: Decimal (always import)
        - federal_withholding: Decimal or None
        - state_withholding: Decimal or None (Georgia)
        - social_security: Decimal or None
        - medicare: Decimal or None
        - other_deductions: JSONB (401k, health insurance, etc.)
        - net_pay: Decimal or None
     d) If ANY withholding field is missing/null in QB data:
        - Import gross_pay only
        - Set all withholding fields to None
        - Flag record with needs_compliance_review = True
        - Add to OPEN_ISSUES.md with [COMPLIANCE] label
        - NEVER calculate retroactive withholding amounts
  3. Wrap entire client payroll import in single DB transaction
  4. Post-import verification:
     - Payroll record count matches QB export row count
     - Total gross pay per employee matches QB totals
     - Count of flagged records (missing withholding)

  Handle edge cases:
  - Employee name mismatch between payroll and employee list:
    Use fuzzy matching (threshold 0.9), flag if uncertain
  - Terminated employees: import history, set termination date
  - Multiple pay frequencies for same employee: handle each frequency
  - YTD totals in QB: use for verification, not as import source
  - Bonus/commission payments: import as separate payroll items
  - Negative payroll adjustments: import as-is, flag for review

  Create PayrollImportResult:
  - client_id: UUID
  - payroll_runs_imported: int
  - payroll_items_imported: int
  - employees_created: int
  - employees_matched: int
  - records_flagged_compliance: int
  - total_gross_pay: Decimal
  - warnings: list[str]

STEP 4: ROLE ENFORCEMENT CHECK
  Backend migration utility — no API endpoints.
  No role check needed. Skip this step.

STEP 5: TEST
  Write tests at: /backend/tests/migration/test_payroll_importer.py

  Required test cases:
  - test_import_complete_payroll_record: all fields present
  - test_import_missing_withholding_gross_only: null withholding, gross imported
  - test_missing_withholding_flagged_compliance: flag set correctly
  - test_no_retroactive_withholding_calculated: verify no auto-calculation
  - test_employee_matching: correct employee linked to payroll item
  - test_employee_created_if_new: unknown employee auto-created from QB data
  - test_terminated_employee_history: terminated employee records preserved
  - test_payroll_count_matches_source: verification count correct
  - test_total_gross_pay_matches: sum matches QB totals
  - test_client_isolation: Client A payroll not in Client B
  - test_rollback_on_failure: bad record rolls back entire import
  - test_negative_adjustment_flagged: negative payroll flagged for review

[ACCEPTANCE CRITERIA]
- [ ] All payroll history imported with correct employee linkage
- [ ] Missing withholding data: gross pay only, flagged [COMPLIANCE]
- [ ] No retroactive withholding ever calculated
- [ ] Employee records created if not pre-existing
- [ ] Import wrapped in single DB transaction with rollback
- [ ] Post-import verification confirms record counts and totals
- [ ] All test cases pass

[OUTPUT FORMAT]
End every session by printing to terminal:

  ================================
  SESSION COMPLETE
  Agent:        M6 — Payroll History Importer
  Task:         TASK-006
  Files changed: [list each file]
  Tests:        [passed/total]
  Issues opened: [n] — IDs: [list]
  Issues closed: [n] — IDs: [list]
  Next task:    TASK-007 — M7 Migration Audit Report
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
