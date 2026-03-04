================================================================
FILE: AGENT_PROMPTS/builders/T3_BANK_RECONCILIATION.md
Builder Agent — Bank Reconciliation Engine
================================================================

# BUILDER AGENT — T3: Bank Reconciliation Engine

[CONTEXT]
You are a Builder Agent for the Georgia CPA firm accounting system.
Module assigned: T3 — Bank Reconciliation Engine
Task ID: TASK-015
Compliance risk level: MEDIUM

Bank reconciliation ensures the GL matches bank statements. This is
a critical month-end process for every client. The engine must
support importing bank transactions, auto-matching against GL
entries, manual matching for unmatched items, and finalizing
the reconciliation.

[INSTRUCTION — follow in exact order]

STEP 1: LOAD MEMORY
  Run /init. Read CLAUDE.md in full.
  Read AGENT_LOG.md — confirm this task is not already done.
  Read OPEN_ISSUES.md — check for blockers on this module.
  Read ARCHITECTURE.md — verify all your dependencies are built.

STEP 2: VERIFY DEPENDENCIES
  Depends on: TASK-010 (F3 — GL), TASK-013 (T1 — AP), TASK-014 (T2 — AR)
  Verify GL service, AP, and AR are available (bank rec needs
  to match against entries from all sources).
  If any missing, create typed stubs and log [BLOCKER].

STEP 3: BUILD
  Compliance risk is MEDIUM — write tests alongside implementation.

  Build service at: /backend/services/bank_reconciliation.py
  Build API at: /backend/api/bank_reconciliation.py
  Build models at: /backend/models/bank.py

  Core components:

  1. Bank account management:
     - create_bank_account(client_id, account_name, bank_name,
       account_number_last4)
     - list_bank_accounts(client_id)

  2. Bank transaction import:
     - import_bank_transactions(bank_account_id, csv_file)
       Parse bank statement CSV (common formats: OFX, QFX, CSV)
       Create bank_transaction records
     - Required fields: date, description, amount (positive=deposit,
       negative=withdrawal)

  3. Auto-matching engine:
     - auto_match(bank_account_id, date_range)
       Match bank transactions to GL journal entries by:
       a) Exact amount match within +/- 2 day window
       b) Check number match (if available)
       c) Description similarity (fuzzy match)
       Return: list of proposed matches with confidence scores
     - Matching rules (in priority order):
       1. Exact amount + exact date = 100% confidence
       2. Exact amount + +/-1 day = 95% confidence
       3. Exact amount + +/-2 days = 85% confidence
       4. Amount match + description similarity > 0.8 = 80%
       5. Below 80% = flag for manual review

  4. Manual matching:
     - manual_match(bank_transaction_id, journal_entry_id)
       Link a bank transaction to a specific GL entry
     - unmatch(bank_transaction_id) — remove a match
     - create_adjustment(bank_account_id, bank_transaction_id,
       account_id, description)
       For bank transactions with no GL entry — create a new
       journal entry to record the transaction

  5. Reconciliation finalization:
     - start_reconciliation(bank_account_id, statement_date,
       statement_balance)
     - get_reconciliation_status(reconciliation_id)
       Show: statement balance, GL balance, difference,
       unmatched bank items, unmatched GL items
     - finalize_reconciliation(reconciliation_id, finalized_by)
       CPA_OWNER only
       Only if difference == 0 (or within tolerance, configurable)
       Mark all matched transactions as is_reconciled = True

  API endpoints:
  - POST /api/clients/{client_id}/bank-accounts — create account
  - GET /api/clients/{client_id}/bank-accounts — list accounts
  - POST /api/clients/{client_id}/bank-accounts/{id}/import — import CSV
  - POST /api/clients/{client_id}/bank-accounts/{id}/auto-match — auto-match
  - POST /api/clients/{client_id}/bank-transactions/{id}/match — manual match
  - POST /api/clients/{client_id}/bank-transactions/{id}/unmatch — unmatch
  - POST /api/clients/{client_id}/bank-accounts/{id}/reconciliation — start
  - GET /api/clients/{client_id}/reconciliations/{id} — status
  - POST /api/clients/{client_id}/reconciliations/{id}/finalize — finalize

STEP 4: ROLE ENFORCEMENT CHECK
  - finalize_reconciliation: CPA_OWNER only
  - All other operations: both roles
  Write test proving ASSOCIATE cannot finalize.

STEP 5: TEST
  Write tests at: /backend/tests/services/test_bank_reconciliation.py

  Required test cases:
  - test_import_bank_transactions: CSV import creates records
  - test_auto_match_exact: exact amount + date produces 100% match
  - test_auto_match_date_tolerance: +/-2 day window works
  - test_auto_match_no_match: unmatched items flagged
  - test_manual_match: link bank txn to GL entry
  - test_unmatch: remove a match
  - test_create_adjustment_entry: new GL entry for unmatched bank txn
  - test_reconciliation_balanced: statement matches GL, can finalize
  - test_reconciliation_unbalanced: difference != 0, cannot finalize
  - test_finalize_requires_cpa_owner: ASSOCIATE cannot finalize
  - test_client_isolation: Client A bank data not in Client B
  - test_reconciled_flag_set: finalized txns marked is_reconciled

[ACCEPTANCE CRITERIA]
- [ ] Bank transaction CSV import working
- [ ] Auto-matching with confidence scoring
- [ ] Manual match and unmatch supported
- [ ] Adjustment entries create GL journal entries
- [ ] Reconciliation shows statement vs GL difference
- [ ] Finalization only when balanced (CPA_OWNER only)
- [ ] Client isolation on all queries
- [ ] All test cases pass

[OUTPUT FORMAT]
End every session by printing to terminal:

  ================================
  SESSION COMPLETE
  Agent:        T3 — Bank Reconciliation
  Task:         TASK-015
  Files changed: [list each file]
  Tests:        [passed/total]
  Issues opened: [n] — IDs: [list]
  Issues closed: [n] — IDs: [list]
  Next task:    TASK-016 — T4 Transaction Approval Workflow
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
