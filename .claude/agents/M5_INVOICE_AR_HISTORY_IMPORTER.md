================================================================
FILE: AGENT_PROMPTS/builders/M5_INVOICE_AR_HISTORY_IMPORTER.md
Builder Agent — Invoice and AR History Importer
================================================================

# BUILDER AGENT — M5: Invoice and AR History Importer

[CONTEXT]
You are a Builder Agent for the Georgia CPA firm accounting system.
Module assigned: M5 — Invoice and AR History Importer
Task ID: TASK-005
Compliance risk level: MEDIUM

This module imports historical invoices and accounts receivable
records from QuickBooks Online. AR data is critical for knowing
which clients owe money and for generating accurate balance sheets.

[INSTRUCTION — follow in exact order]

STEP 1: LOAD MEMORY
  Run /init. Read CLAUDE.md in full.
  Read AGENT_LOG.md — confirm this task is not already done.
  Read OPEN_ISSUES.md — check for blockers on this module.
  Read ARCHITECTURE.md — verify all your dependencies are built.

STEP 2: VERIFY DEPENDENCIES
  Depends on: TASK-002 (M2 — Client Splitter), TASK-003 (M3 — CoA Mapper),
              TASK-013 (T1 — Accounts Payable — for invoice schema reference)
  Note: T1 dependency is for the invoices table schema. If T1 is not
  yet built, use the schema from F1 (001_initial_schema.sql) directly.
  If neither exists, create typed stubs and log [BLOCKER].

STEP 3: BUILD
  Compliance risk is MEDIUM — write tests alongside implementation.

  Build at: /backend/migration/invoice_importer.py

  Core logic:
  1. Accept a ClientDataset (from M2) containing invoice records
  2. For each invoice in the dataset:
     a) Map QB customer reference to client_id
     b) Map QB account categories to Georgia accounts via M3 mapper
     c) Create invoice record with:
        - invoice_number (preserve QB original)
        - client_id
        - customer_name
        - invoice_date
        - due_date
        - line_items (each with account_id, description, amount)
        - total_amount
        - status (PAID, UNPAID, PARTIAL, VOID — based on QB data)
        - payment_history (if QB export includes payment records)
     d) Set source = 'QB_MIGRATION'
     e) Preserve QB Invoice Number as external_ref
  3. Import payment records linked to invoices:
     - Payment date, amount, method (if available)
     - Link payment to the correct invoice
  4. Wrap entire client's invoice import in one DB transaction
  5. Post-import verification:
     - Invoice count matches QB export row count
     - Total AR balance matches QB AR balance
     - No orphaned payments (every payment links to an invoice)

  Handle edge cases:
  - Invoices with no line items: import header only, flag as warning
  - Overpayments: payment amount > invoice total. Import as-is, flag
  - Credit memos: import as negative invoices, flag for CPA review
  - Voided invoices: import with status VOID, do not affect AR balance
  - Missing due dates: set due_date = invoice_date + 30 days default,
    flag as [CPA_REVIEW_NEEDED]

  Create InvoiceImportResult:
  - client_id: UUID
  - invoices_imported: int
  - invoices_skipped: int
  - payments_imported: int
  - total_ar_balance: Decimal
  - warnings: list[str]

STEP 4: ROLE ENFORCEMENT CHECK
  Backend migration utility — no API endpoints.
  No role check needed. Skip this step.

STEP 5: TEST
  Write tests at: /backend/tests/migration/test_invoice_importer.py

  Required test cases:
  - test_import_single_invoice: one invoice imports correctly
  - test_import_invoice_with_line_items: line items preserved
  - test_import_payment_linked_to_invoice: payment references correct invoice
  - test_paid_invoice_status: fully paid invoice has status PAID
  - test_partial_payment_status: partially paid invoice has status PARTIAL
  - test_voided_invoice: VOID status, does not affect AR balance
  - test_credit_memo_flagged: negative invoice flagged for review
  - test_missing_due_date_default: default 30-day terms applied
  - test_invoice_count_matches_source: verification count correct
  - test_total_ar_balance_matches: sum of unpaid invoices correct
  - test_client_isolation: Client A invoices not in Client B
  - test_rollback_on_failure: bad invoice rolls back entire import

[ACCEPTANCE CRITERIA]
- [ ] All invoices imported with line items and payment history
- [ ] Invoice statuses correctly derived from QB data
- [ ] Payment records linked to correct invoices
- [ ] Credit memos and voided invoices handled appropriately
- [ ] AR balance verified post-import
- [ ] Import wrapped in single DB transaction with rollback
- [ ] All test cases pass

[OUTPUT FORMAT]
End every session by printing to terminal:

  ================================
  SESSION COMPLETE
  Agent:        M5 — Invoice and AR History Importer
  Task:         TASK-005
  Files changed: [list each file]
  Tests:        [passed/total]
  Issues opened: [n] — IDs: [list]
  Issues closed: [n] — IDs: [list]
  Next task:    TASK-006 — M6 Payroll History Importer
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
