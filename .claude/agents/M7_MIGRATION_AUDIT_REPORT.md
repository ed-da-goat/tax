================================================================
FILE: AGENT_PROMPTS/builders/M7_MIGRATION_AUDIT_REPORT.md
Builder Agent — Migration Audit Report
================================================================

# BUILDER AGENT — M7: Migration Audit Report

[CONTEXT]
You are a Builder Agent for the Georgia CPA firm accounting system.
Module assigned: M7 — Migration Audit Report (flags any data that didn't map cleanly)
Task ID: TASK-007
Compliance risk level: HIGH

This module generates the final migration audit report. The CPA
owner must review this report before the system goes live. It must
clearly show what was imported, what was skipped, what was flagged,
and whether the data is trustworthy enough to use for financial
reporting and tax filings.

[INSTRUCTION — follow in exact order]

STEP 1: LOAD MEMORY
  Run /init. Read CLAUDE.md in full.
  Read AGENT_LOG.md — confirm this task is not already done.
  Read OPEN_ISSUES.md — check for blockers on this module.
  Read ARCHITECTURE.md — verify all your dependencies are built.

STEP 2: VERIFY DEPENDENCIES
  Depends on: TASK-001 through TASK-006 (all other migration modules)
  This is the final migration module. All M1-M6 must be complete.
  If any are missing, create stubs that return sample ImportResult
  data and log [BLOCKER].

STEP 3: BUILD
  Compliance risk is HIGH — use TDD (write tests BEFORE implementation).

  Build at: /backend/migration/audit_report.py

  Core logic:
  1. Collect results from all importers (M4, M5, M6):
     - ImportResult from transaction importer
     - InvoiceImportResult from invoice importer
     - PayrollImportResult from payroll importer
  2. Query the database to verify imported data integrity:
     a) GL balance check: for EACH client, sum(debits) == sum(credits)
     b) Transaction count per client matches expected from M4 result
     c) Invoice count per client matches expected from M5 result
     d) Payroll record count per client matches expected from M6 result
     e) No orphaned records (transactions without valid client_id)
  3. Generate a comprehensive MigrationAuditReport:
     - report_timestamp: datetime
     - overall_status: CLEAN | HAS_WARNINGS | HAS_ERRORS
     - per_client_summary: list[ClientMigrationSummary]
       - client_id, client_name
       - transactions: imported / skipped / total
       - invoices: imported / skipped / total
       - payroll_runs: imported / skipped / total
       - gl_balanced: bool
       - compliance_flags: int (records needing CPA review)
     - unmapped_accounts: list (from M3 mapping report)
     - skipped_transactions: list (from M4 with reasons)
     - compliance_flagged_records: list (payroll missing withholding, etc.)
     - data_quality_score: float (0.0 - 1.0, based on % clean records)
  4. Save report to: /docs/migration/audit_report_[timestamp].txt
  5. Also generate a machine-readable JSON version at:
     /docs/migration/audit_report_[timestamp].json

  Report sections (human-readable text version):
  ```
  ============================================
  MIGRATION AUDIT REPORT
  Generated: [timestamp]
  ============================================

  EXECUTIVE SUMMARY
  - Total clients migrated: [n]
  - Overall status: [CLEAN / HAS_WARNINGS / HAS_ERRORS]
  - Data quality score: [n]%

  PER-CLIENT BREAKDOWN
  [table with columns: Client | Transactions | Invoices | Payroll | GL Balanced | Flags]

  UNMAPPED ACCOUNTS (requires CPA action)
  [list of QB accounts that could not be mapped]

  SKIPPED TRANSACTIONS (requires CPA review)
  [list with reason for each skip]

  COMPLIANCE FLAGS
  [list of records that need CPA review before going live]

  RECOMMENDED ACTIONS
  [numbered list of what the CPA should review/fix]
  ============================================
  ```

STEP 4: ROLE ENFORCEMENT CHECK
  Backend migration utility — no API endpoints.
  No role check needed. Skip this step.

STEP 5: TEST
  Write tests at: /backend/tests/migration/test_audit_report.py

  Required test cases:
  - test_clean_migration_report: all data imports cleanly, status CLEAN
  - test_warnings_report: some skipped records, status HAS_WARNINGS
  - test_errors_report: GL imbalance detected, status HAS_ERRORS
  - test_gl_balance_verification: debits == credits confirmed per client
  - test_transaction_count_verification: counts match expected
  - test_invoice_count_verification: counts match expected
  - test_payroll_count_verification: counts match expected
  - test_unmapped_accounts_listed: all unmapped accounts in report
  - test_compliance_flags_counted: correct count of flagged records
  - test_data_quality_score: score calculation correct
  - test_report_saved_to_file: text and JSON files created
  - test_per_client_isolation: report shows per-client, not global

[ACCEPTANCE CRITERIA]
- [ ] Report aggregates results from all migration modules
- [ ] GL balance verified per client (debits == credits)
- [ ] Record counts verified against source data
- [ ] All unmapped/skipped/flagged items clearly listed
- [ ] Human-readable text report saved to /docs/migration/
- [ ] Machine-readable JSON report saved alongside
- [ ] Data quality score calculated
- [ ] Recommended actions section helps CPA know what to review
- [ ] All test cases pass

[OUTPUT FORMAT]
End every session by printing to terminal:

  ================================
  SESSION COMPLETE
  Agent:        M7 — Migration Audit Report
  Task:         TASK-007
  Files changed: [list each file]
  Tests:        [passed/total]
  Issues opened: [n] — IDs: [list]
  Issues closed: [n] — IDs: [list]
  Next task:    TASK-008 — F1 Database Schema
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
