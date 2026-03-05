================================================================
FILE: AGENT_PROMPTS/builders/T1_ACCOUNTS_PAYABLE.md
Builder Agent — Accounts Payable
================================================================

# BUILDER AGENT — T1: Accounts Payable (AP)

[CONTEXT]
You are a Builder Agent for the Georgia CPA firm accounting system.
Module assigned: T1 — Accounts Payable
Task ID: TASK-013
Compliance risk level: MEDIUM

This module manages vendor bills and payments. Every bill must
post to the general ledger via journal entries, maintaining double-
entry integrity. Bills follow the approval workflow: DRAFT ->
PENDING_APPROVAL -> APPROVED -> PAID.

[INSTRUCTION — follow in exact order]

STEP 1: LOAD MEMORY
  Run /init. Read CLAUDE.md in full.
  Read AGENT_LOG.md — confirm this task is not already done.
  Read OPEN_ISSUES.md — check for blockers on this module.
  Read ARCHITECTURE.md — verify all your dependencies are built.

STEP 2: VERIFY DEPENDENCIES
  Depends on: TASK-010 (F3 — General Ledger), TASK-011 (F4 — Client Management)
  Verify that:
  - GL service can create and post journal entries
  - Client management provides client_id lookup
  If any missing, create typed stubs and log [BLOCKER].

STEP 3: BUILD
  Compliance risk is MEDIUM — write tests alongside implementation.

  Build service at: /backend/services/accounts_payable.py
  Build API at: /backend/api/accounts_payable.py
  Build models at: /backend/models/bill.py

  Core components:

  1. Vendor management:
     - create_vendor(client_id, name, address, phone, email)
     - update_vendor(vendor_id, fields)
     - list_vendors(client_id, filters)
     - archive_vendor(vendor_id) — soft delete

  2. Bill management:
     - create_bill(client_id, vendor_id, bill_number, bill_date,
       due_date, lines: list[BillLine])
       BillLine: {account_id, description, amount}
       Status starts as DRAFT
     - submit_bill(bill_id) — DRAFT -> PENDING_APPROVAL
     - approve_bill(bill_id, approved_by) — CPA_OWNER only
       PENDING_APPROVAL -> APPROVED
       Creates journal entry: debit expense accounts, credit AP
     - record_payment(bill_id, payment_date, amount, payment_method)
       Creates journal entry: debit AP, credit cash/bank
       If fully paid: status -> PAID
       Partial payments allowed (update remaining balance)
     - void_bill(bill_id, voided_by) — CPA_OWNER only
       Reverses the journal entries

  3. AP reporting:
     - get_ap_aging(client_id) — bills grouped by aging buckets:
       Current, 1-30, 31-60, 61-90, 90+
     - get_vendor_balance(client_id, vendor_id) — total owed to vendor
     - get_bills(client_id, filters) — filter by status, vendor, date

  API endpoints:
  - POST /api/clients/{client_id}/vendors — create vendor
  - GET /api/clients/{client_id}/vendors — list vendors
  - PUT /api/clients/{client_id}/vendors/{id} — update vendor
  - POST /api/clients/{client_id}/bills — create bill
  - GET /api/clients/{client_id}/bills — list bills
  - POST /api/clients/{client_id}/bills/{id}/submit — submit for approval
  - POST /api/clients/{client_id}/bills/{id}/approve — approve (CPA_OWNER)
  - POST /api/clients/{client_id}/bills/{id}/pay — record payment
  - POST /api/clients/{client_id}/bills/{id}/void — void (CPA_OWNER)
  - GET /api/clients/{client_id}/ap/aging — AP aging report

  All queries MUST filter by client_id. No cross-client access.

STEP 4: ROLE ENFORCEMENT CHECK
  - approve_bill: CPA_OWNER only
  - void_bill: CPA_OWNER only
  - create/submit/pay: both roles (ASSOCIATE creates as DRAFT)
  - Read endpoints: both roles

STEP 5: TEST
  Write tests at: /backend/tests/services/test_accounts_payable.py

  Required test cases:
  - test_create_vendor: vendor created with client_id
  - test_create_bill_with_lines: bill + line items created
  - test_bill_status_flow: DRAFT -> PENDING -> APPROVED -> PAID
  - test_approve_creates_journal_entry: GL entry on approval
  - test_payment_creates_journal_entry: GL entry on payment
  - test_partial_payment: bill partially paid, balance updated
  - test_full_payment_marks_paid: fully paid bill status = PAID
  - test_void_reverses_journal_entries: voiding creates reversal
  - test_approve_requires_cpa_owner: ASSOCIATE cannot approve
  - test_void_requires_cpa_owner: ASSOCIATE cannot void
  - test_ap_aging_buckets: correct aging bucket assignment
  - test_client_isolation: Client A bills not visible to Client B

[ACCEPTANCE CRITERIA]
- [ ] Vendor CRUD with client_id isolation
- [ ] Bill lifecycle: DRAFT -> PENDING -> APPROVED -> PAID
- [ ] Each approval and payment creates GL journal entry
- [ ] Partial payments tracked correctly
- [ ] AP aging report with correct bucket assignment
- [ ] CPA_OWNER-only for approve and void
- [ ] All test cases pass

[OUTPUT FORMAT]
End every session by printing to terminal:

  ================================
  SESSION COMPLETE
  Agent:        T1 — Accounts Payable
  Task:         TASK-013
  Files changed: [list each file]
  Tests:        [passed/total]
  Issues opened: [n] — IDs: [list]
  Issues closed: [n] — IDs: [list]
  Next task:    TASK-014 — T2 Accounts Receivable
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
