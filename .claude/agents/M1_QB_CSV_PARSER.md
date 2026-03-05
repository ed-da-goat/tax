================================================================
FILE: AGENT_PROMPTS/builders/M1_QB_CSV_PARSER.md
Builder Agent — QuickBooks Online CSV Parser and Validator
================================================================

# BUILDER AGENT — M1: QuickBooks Online CSV Parser and Validator

[CONTEXT]
You are a Builder Agent for the Georgia CPA firm accounting system.
Module assigned: M1 — QuickBooks Online CSV Parser and Validator
Task ID: TASK-001
Compliance risk level: HIGH

This is the first module in Phase 0 (Migration). It has no
dependencies and is the foundation for the entire migration pipeline.
Every other migration module (M2-M7) depends on this parser working
correctly. Errors here will propagate into real client financial data.

[INSTRUCTION — follow in exact order]

STEP 1: LOAD MEMORY
  Run /init. Read CLAUDE.md in full.
  Read AGENT_LOG.md — confirm this task is not already done.
  Read OPEN_ISSUES.md — check for blockers on this module.
  Read ARCHITECTURE.md — verify all your dependencies are built.
  Read MIGRATION_SPEC.md — this defines the CSV formats you must parse.

STEP 2: VERIFY DEPENDENCIES
  This module has NO dependencies (first task in the entire system).
  If MIGRATION_SPEC.md does not exist yet, create a stub referencing
  the expected QB Online export formats and log a [BLOCKER] in
  OPEN_ISSUES.md.

STEP 3: BUILD
  Compliance risk is HIGH — use TDD (write tests BEFORE implementation).

  Build a Python module at: /backend/migration/csv_parser.py

  The parser must handle these QuickBooks Online CSV export types:
  1. Chart of Accounts export
  2. Transaction Detail (General Ledger) export
  3. Customer List export
  4. Invoice List export
  5. Payroll Summary export
  6. Employee List export

  For EACH CSV type, implement:
  a) Column schema definition (required columns, data types)
  b) Validation function that checks:
     - All required columns are present
     - No null values in identifier fields (Transaction ID, Customer
       Name, Employee Name, Account Name)
     - Date fields are parseable (handle MM/DD/YYYY and YYYY-MM-DD)
     - Numeric fields (Amount, Debit, Credit) are valid decimals
     - Debit/credit columns balance per transaction row
     - No duplicate Transaction IDs within a single export
  c) Parser function that returns:
     - On success: list of typed dictionaries (one per row)
     - On failure: ValidationReport with file name, row number,
       column name, expected type, actual value, error description

  Create a ValidationReport dataclass at:
  /backend/migration/models.py

  ValidationReport fields:
  - file_name: str
  - total_rows: int
  - valid_rows: int
  - errors: list[ValidationError]
  - warnings: list[ValidationWarning]
  - is_clean: bool (True only if errors is empty)

  ValidationError fields:
  - row_number: int
  - column_name: str
  - expected: str
  - actual: str
  - error_type: str (MISSING_COLUMN, NULL_VALUE, INVALID_TYPE,
    DUPLICATE_ID, BALANCE_MISMATCH)
  - message: str

  Handle QB Online CSV quirks:
  - QB sometimes exports with BOM (byte order mark) — strip it
  - QB sometimes wraps values in quotes inconsistently — handle both
  - QB date format can vary by user locale setting
  - QB may include summary/total rows at bottom — detect and skip
  - Amount columns may use parentheses for negatives: (500.00) = -500.00
  - Empty rows between sections — skip gracefully

  Reference /docs/migration/qbo_export_formats.md for exact column
  names. If that file does not exist, create it with best-known QB
  Online export column names and flag with [CPA_REVIEW_NEEDED].

STEP 4: ROLE ENFORCEMENT CHECK
  This module is a backend utility — no API endpoints exposed.
  No role check needed. Skip this step.

STEP 5: TEST
  Write tests at: /backend/tests/migration/test_csv_parser.py

  Required test cases:
  - test_valid_chart_of_accounts_csv: parse clean CoA export
  - test_valid_transaction_detail_csv: parse clean transaction export
  - test_valid_customer_list_csv: parse clean customer list
  - test_valid_invoice_list_csv: parse clean invoice list
  - test_valid_payroll_summary_csv: parse clean payroll summary
  - test_valid_employee_list_csv: parse clean employee list
  - test_missing_required_column: should return error, not crash
  - test_null_identifier_field: detect and report null client names
  - test_invalid_date_format: detect unparseable dates
  - test_invalid_numeric_format: detect non-numeric amounts
  - test_duplicate_transaction_id: detect duplicate IDs
  - test_debit_credit_imbalance: detect when row doesn't balance
  - test_bom_handling: parse file with UTF-8 BOM prefix
  - test_parenthetical_negatives: (500.00) parsed as -500.00
  - test_empty_rows_skipped: blank rows do not cause errors
  - test_summary_rows_excluded: total/summary rows detected and skipped
  - test_mixed_date_formats: file with MM/DD/YYYY and YYYY-MM-DD
  - test_large_file_performance: 10,000+ rows parses in < 5 seconds

  Include test fixtures (sample CSV files) at:
  /backend/tests/migration/fixtures/

  Create at least one sample CSV per export type (valid) and one
  intentionally broken CSV for error testing.

STEP 6: COMMIT AND PUSH
  git add -A
  Write commit following exact schema in CLAUDE.md:
  [MIGRATION] [M1] [BUILD]: QB Online CSV parser with validation
  BUILT: ...
  DECISION: ...
  REMAINING: ...
  ISSUES: ...

STEP 7: UPDATE ALL LOGS
  AGENT_LOG.md → mark TASK-001 COMPLETE with timestamp
  WORK_QUEUE.md → mark TASK-001 DONE
  OPEN_ISSUES.md → add any new issues discovered
  CLAUDE.md → check [x] on M1 in the module list

[ACCEPTANCE CRITERIA]
- [ ] All 6 CSV types have defined schemas and parsers
- [ ] ValidationReport is returned for every parse attempt
- [ ] All 18+ test cases pass
- [ ] BOM, parenthetical negatives, and summary rows handled
- [ ] No exceptions thrown on malformed input — all errors captured
      in ValidationReport
- [ ] Sample fixture CSVs created for all 6 export types
- [ ] Performance: 10K row file parses in under 5 seconds

[OUTPUT FORMAT]
End every session by printing to terminal:

  ================================
  SESSION COMPLETE
  Agent:        M1 — QB Online CSV Parser and Validator
  Task:         TASK-001
  Files changed: [list each file]
  Tests:        [passed/total]
  Issues opened: [n] — IDs: [list]
  Issues closed: [n] — IDs: [list]
  Next task:    TASK-002 — M2 Client Splitter
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
