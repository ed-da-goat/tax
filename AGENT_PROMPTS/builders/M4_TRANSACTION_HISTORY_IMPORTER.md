================================================================
FILE: AGENT_PROMPTS/builders/M4_TRANSACTION_HISTORY_IMPORTER.md
Builder Agent — Transaction History Importer
================================================================

# BUILDER AGENT — M4: Transaction History Importer

[CONTEXT]
You are a Builder Agent for the Georgia CPA firm accounting system.
Module assigned: M4 — Transaction History Importer (full history, not just balances)
Task ID: TASK-004
Compliance risk level: HIGH

This module imports the full transaction history from QuickBooks
Online into the general ledger. This is the highest-volume, highest-
risk import operation. Transactions must maintain double-entry
integrity, be imported oldest-first, and be wrapped in a single
database transaction so partial imports never occur.

[INSTRUCTION — follow in exact order]

STEP 1: LOAD MEMORY
  Run /init. Read CLAUDE.md in full.
  Read AGENT_LOG.md — confirm this task is not already done.
  Read OPEN_ISSUES.md — check for blockers on this module.
  Read ARCHITECTURE.md — verify all your dependencies are built.
  Read MIGRATION_SPEC.md — understand the import order and rules.

STEP 2: VERIFY DEPENDENCIES
  Depends on: TASK-002 (M2 — Client Splitter), TASK-003 (M3 — CoA Mapper),
              TASK-009 (F2 — Chart of Accounts seed), TASK-010 (F3 — General Ledger)
  Verify that:
  - Client splitter produces per-client datasets
  - CoA mapper provides QB-to-Georgia account mappings
  - GL service accepts journal entry creation
  If any missing, create typed stubs and log [BLOCKER].

STEP 3: BUILD
  Compliance risk is HIGH — use TDD (write tests BEFORE implementation).

  Build at: /backend/migration/transaction_importer.py

  Core logic:
  1. Accept a ClientDataset (from M2) and a CoA mapping (from M3)
  2. Sort all transactions by date (oldest first — chronological order)
  3. For each transaction:
     a) Map QB account names to Georgia account IDs via CoA mapping
     b) Create a journal entry with debit and credit lines
     c) Verify debit total == credit total for the entry
     d) Set status to POSTED (these are historical, already finalized)
     e) Set source = 'QB_MIGRATION' to distinguish from manual entries
     f) Preserve the original QB transaction ID as external_ref
  4. Wrap the ENTIRE import for a single client in one DB transaction
     - If ANY transaction fails: ROLLBACK everything for that client
     - Print exact error: which transaction, which row, what failed
     - Print recovery instructions
     - Never leave partial data in the database
  5. After successful import, run verification:
     - Sum of all debits == sum of all credits per client
     - Transaction count matches source CSV row count
     - Date range of imported transactions matches source

  Handle edge cases:
  - Transactions with unmapped accounts (from M3 flagged items):
    Skip these transactions, add to a skipped_transactions list,
    flag in migration report. Do NOT halt the entire import.
  - Zero-amount transactions: import but flag as warning
  - Transactions with memo/description exceeding DB column length:
    Truncate to column max, preserve full text in a notes field
  - Duplicate external_ref (QB transaction ID): skip duplicate,
    log warning, continue

  Create an ImportResult dataclass:
  - client_id: UUID
  - transactions_imported: int
  - transactions_skipped: int
  - skipped_reasons: list[SkippedTransaction]
  - total_debits: Decimal
  - total_credits: Decimal
  - balance_verified: bool (debits == credits)
  - date_range: tuple[date, date]

STEP 4: ROLE ENFORCEMENT CHECK
  This module is a backend utility used during migration only.
  No API endpoints exposed during normal operation.
  No role check needed. Skip this step.

STEP 5: TEST
  Write tests at: /backend/tests/migration/test_transaction_importer.py

  Required test cases:
  - test_import_single_transaction: one journal entry imports correctly
  - test_import_chronological_order: oldest transaction imported first
  - test_debit_credit_balance: imported entries have balanced debits/credits
  - test_rollback_on_failure: bad transaction rolls back entire client import
  - test_unmapped_account_skipped: txn with unknown account is skipped
  - test_skipped_transactions_reported: skip reasons in ImportResult
  - test_duplicate_external_ref_skipped: duplicate QB IDs handled
  - test_zero_amount_transaction_warning: zero txns imported with flag
  - test_source_marked_qb_migration: all imported txns have correct source
  - test_client_isolation: Client A import does not touch Client B
  - test_verification_passes: post-import debits == credits
  - test_transaction_count_matches: imported count matches source count
  - test_large_import_performance: 5000+ transactions in < 30 seconds
  - test_memo_truncation: long memos truncated without data loss

[ACCEPTANCE CRITERIA]
- [ ] Full transaction history imported in chronological order
- [ ] Double-entry integrity enforced (debits == credits per entry)
- [ ] Entire client import wrapped in single DB transaction
- [ ] Rollback on any failure — no partial data ever
- [ ] Unmapped accounts cause skip, not halt
- [ ] ImportResult provides complete audit of what was imported/skipped
- [ ] Post-import verification confirms data integrity
- [ ] All test cases pass

[OUTPUT FORMAT]
End every session by printing to terminal:

  ================================
  SESSION COMPLETE
  Agent:        M4 — Transaction History Importer
  Task:         TASK-004
  Files changed: [list each file]
  Tests:        [passed/total]
  Issues opened: [n] — IDs: [list]
  Issues closed: [n] — IDs: [list]
  Next task:    TASK-005 — M5 Invoice and AR History Importer
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
