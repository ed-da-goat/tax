================================================================
FILE: AGENT_PROMPTS/builders/F3_GENERAL_LEDGER.md
Builder Agent — General Ledger with Double-Entry Enforcement
================================================================

# BUILDER AGENT — F3: General Ledger with Double-Entry Enforcement

[CONTEXT]
You are a Builder Agent for the Georgia CPA firm accounting system.
Module assigned: F3 — General Ledger with double-entry enforcement
Task ID: TASK-010
Compliance risk level: HIGH

The general ledger is the single source of truth for all financial
data. Every transaction in the system ultimately posts here. The GL
MUST enforce double-entry at the database level — not just in
application code. If debits do not equal credits, the entry must be
rejected at the database level. This is a non-negotiable compliance
requirement per CLAUDE.md Rule #1.

[INSTRUCTION — follow in exact order]

STEP 1: LOAD MEMORY
  Run /init. Read CLAUDE.md in full.
  Read AGENT_LOG.md — confirm this task is not already done.
  Read OPEN_ISSUES.md — check for blockers on this module.
  Read ARCHITECTURE.md — verify all your dependencies are built.

STEP 2: VERIFY DEPENDENCIES
  Depends on: TASK-008 (F1 — Database Schema), TASK-009 (F2 — Chart of Accounts)
  Verify that:
  - journal_entries and journal_entry_lines tables exist
  - Double-entry trigger exists in schema
  - chart_of_accounts seeded and queryable
  If any missing, create typed stubs and log [BLOCKER].

STEP 3: BUILD
  Compliance risk is HIGH — use TDD (write tests BEFORE implementation).

  Build service at: /backend/services/general_ledger.py
  Build API at: /backend/api/general_ledger.py
  Build models at: /backend/models/journal_entry.py

  Core service functions:
  1. create_journal_entry(client_id, entry_date, description, lines, created_by)
     - Validate: at least 2 lines (one debit, one credit)
     - Validate: sum(debits) == sum(credits) in application code
       (defense in depth — DB trigger is the real enforcement)
     - Validate: all account_ids belong to the same client_id
     - Set status = 'DRAFT' if created by ASSOCIATE
     - Set status = 'PENDING_APPROVAL' when submitted
     - Return the created journal entry with all lines

  2. submit_for_approval(entry_id, user_id)
     - Change status from DRAFT to PENDING_APPROVAL
     - Only the creator or CPA_OWNER can submit

  3. approve_and_post(entry_id, approved_by)
     - CPA_OWNER only (check at function level, not just route)
     - Change status from PENDING_APPROVAL to POSTED
     - Set approved_by and posted_at timestamp
     - POSTED entries affect GL balances
     - DRAFT and PENDING_APPROVAL entries do NOT affect balances

  4. void_entry(entry_id, voided_by, reason)
     - CPA_OWNER only
     - Change status to VOIDED
     - Create a reversing entry (opposite debits/credits)
     - Never delete — audit trail must be preserved

  5. get_account_balance(client_id, account_id, as_of_date=None)
     - Sum all POSTED journal entry lines for the account
     - If as_of_date provided, only include entries on or before date
     - Return: {debit_total, credit_total, balance}
     - For Asset/Expense accounts: balance = debits - credits
     - For Liability/Equity/Revenue accounts: balance = credits - debits

  6. get_trial_balance(client_id, as_of_date=None)
     - Return balances for all active accounts
     - Total debits must equal total credits (verification)

  7. get_journal_entries(client_id, filters)
     - Filter by: date range, status, account, created_by
     - Paginated results
     - Client_id isolation enforced

  API endpoints (FastAPI):
  - POST /api/clients/{client_id}/journal-entries — create entry
  - GET /api/clients/{client_id}/journal-entries — list entries
  - GET /api/clients/{client_id}/journal-entries/{id} — get single entry
  - POST /api/clients/{client_id}/journal-entries/{id}/submit — submit for approval
  - POST /api/clients/{client_id}/journal-entries/{id}/approve — approve and post
  - POST /api/clients/{client_id}/journal-entries/{id}/void — void entry
  - GET /api/clients/{client_id}/accounts/{id}/balance — account balance
  - GET /api/clients/{client_id}/trial-balance — trial balance

  CRITICAL IMPLEMENTATION NOTES:
  - The double-entry CHECK constraint / trigger in the database
    (created by F1) is the REAL enforcement. Application-level
    validation is defense-in-depth only.
  - PENDING_APPROVAL entries MUST NOT appear in balance calculations.
    Only POSTED entries count.
  - Voiding creates a NEW reversing entry. The original stays as-is.
  - All monetary values use Decimal, never float.
  - All queries MUST include client_id in WHERE clause.

STEP 4: ROLE ENFORCEMENT CHECK
  - approve_and_post: CPA_OWNER only — check at function level
  - void_entry: CPA_OWNER only — check at function level
  - create_journal_entry: both roles (ASSOCIATE creates as DRAFT)
  - submit_for_approval: both roles
  - Read endpoints: both roles

  Write tests proving:
  - ASSOCIATE cannot approve entries (even with manipulated JWT)
  - ASSOCIATE cannot void entries
  - ASSOCIATE-created entries start as DRAFT, not POSTED

STEP 5: TEST
  Write tests at: /backend/tests/services/test_general_ledger.py

  Required test cases:
  - test_create_balanced_entry: entry with equal debits/credits succeeds
  - test_reject_unbalanced_entry: unequal debits/credits rejected by DB
  - test_draft_does_not_affect_balance: DRAFT entry not in balance calc
  - test_pending_does_not_affect_balance: PENDING entry not in balance calc
  - test_posted_affects_balance: POSTED entry included in balance calc
  - test_approve_changes_status_to_posted: status transition correct
  - test_approve_requires_cpa_owner: ASSOCIATE cannot approve
  - test_void_creates_reversing_entry: void produces opposite entry
  - test_void_requires_cpa_owner: ASSOCIATE cannot void
  - test_account_balance_calculation: asset vs liability normal balances
  - test_trial_balance_balances: total debits == total credits
  - test_client_isolation: Client A entries invisible to Client B queries
  - test_as_of_date_filtering: balance excludes future entries
  - test_all_accounts_same_client: entry with cross-client accounts rejected
  - test_associate_entry_starts_as_draft: ASSOCIATE cannot auto-post
  - test_decimal_precision: no floating point errors on currency

[ACCEPTANCE CRITERIA]
- [ ] Double-entry enforced at BOTH database and application level
- [ ] Status flow: DRAFT -> PENDING_APPROVAL -> POSTED (or VOIDED)
- [ ] Only POSTED entries affect GL balances
- [ ] CPA_OWNER-only for approve and void (function-level check)
- [ ] Void creates reversing entry, never deletes
- [ ] Account balance correctly calculates normal balance direction
- [ ] Trial balance always balances (debits == credits)
- [ ] Client isolation on every query
- [ ] All monetary values use Decimal
- [ ] All test cases pass (16+)

[OUTPUT FORMAT]
End every session by printing to terminal:

  ================================
  SESSION COMPLETE
  Agent:        F3 — General Ledger
  Task:         TASK-010
  Files changed: [list each file]
  Tests:        [passed/total]
  Issues opened: [n] — IDs: [list]
  Issues closed: [n] — IDs: [list]
  Next task:    TASK-011 — F4 Client Management
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
