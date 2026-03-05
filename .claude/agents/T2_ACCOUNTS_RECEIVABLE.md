================================================================
FILE: AGENT_PROMPTS/builders/T2_ACCOUNTS_RECEIVABLE.md
Builder Agent — Accounts Receivable + Client Invoicing
================================================================

# BUILDER AGENT — T2: Accounts Receivable + Client Invoicing

[CONTEXT]
You are a Builder Agent for the Georgia CPA firm accounting system.
Module assigned: T2 — Accounts Receivable (AR) + client invoicing
Task ID: TASK-014
Compliance risk level: MEDIUM

This module manages client invoicing, payment tracking, and overdue
detection. Invoices post to the general ledger. PDF invoices are
generated using WeasyPrint for client delivery.

[INSTRUCTION — follow in exact order]

STEP 1: LOAD MEMORY
  Run /init. Read CLAUDE.md in full.
  Read AGENT_LOG.md — confirm this task is not already done.
  Read OPEN_ISSUES.md — check for blockers on this module.
  Read ARCHITECTURE.md — verify all your dependencies are built.

STEP 2: VERIFY DEPENDENCIES
  Depends on: TASK-010 (F3 — General Ledger), TASK-011 (F4 — Client Management)
  Verify GL service and client management are available.
  If any missing, create typed stubs and log [BLOCKER].

STEP 3: BUILD
  Compliance risk is MEDIUM — write tests alongside implementation.

  Build service at: /backend/services/accounts_receivable.py
  Build API at: /backend/api/accounts_receivable.py
  Build models at: /backend/models/invoice.py
  Build PDF template at: /backend/templates/invoice.html

  Core components:

  1. Invoice management:
     - create_invoice(client_id, customer_name, invoice_date,
       due_date, lines: list[InvoiceLine])
       InvoiceLine: {account_id, description, quantity, unit_price}
       Status starts as DRAFT
     - submit_invoice(invoice_id) — DRAFT -> PENDING_APPROVAL
     - approve_invoice(invoice_id, approved_by) — CPA_OWNER only
       PENDING_APPROVAL -> SENT
       Creates journal entry: debit AR, credit revenue accounts
     - record_payment(invoice_id, payment_date, amount, method)
       Creates journal entry: debit cash, credit AR
       If fully paid: status -> PAID
       Partial payments allowed
     - void_invoice(invoice_id, voided_by) — CPA_OWNER only
     - generate_invoice_pdf(invoice_id) — WeasyPrint PDF output

  2. Invoice PDF generation (WeasyPrint):
     - Professional layout with:
       - Firm name and address (from settings)
       - Client name and address
       - Invoice number, date, due date
       - Line items table with descriptions, quantities, amounts
       - Subtotal, tax (if applicable), total
       - Payment terms and instructions
     - HTML template at /backend/templates/invoice.html
     - CSS styling for print-quality PDF
     - Save generated PDF to /data/documents/[client_id]/invoices/

  3. Overdue detection:
     - get_overdue_invoices(client_id) — invoices past due_date
     - Aging buckets: Current, 1-30, 31-60, 61-90, 90+ days

  4. AR reporting:
     - get_ar_aging(client_id) — AR aging summary
     - get_customer_balance(client_id, customer_name) — total owed
     - get_invoices(client_id, filters) — filter by status, date, customer

  API endpoints:
  - POST /api/clients/{client_id}/invoices — create invoice
  - GET /api/clients/{client_id}/invoices — list invoices
  - GET /api/clients/{client_id}/invoices/{id} — get invoice
  - POST /api/clients/{client_id}/invoices/{id}/submit — submit
  - POST /api/clients/{client_id}/invoices/{id}/approve — approve (CPA_OWNER)
  - POST /api/clients/{client_id}/invoices/{id}/pay — record payment
  - POST /api/clients/{client_id}/invoices/{id}/void — void (CPA_OWNER)
  - GET /api/clients/{client_id}/invoices/{id}/pdf — download PDF
  - GET /api/clients/{client_id}/ar/aging — AR aging report

STEP 4: ROLE ENFORCEMENT CHECK
  - approve_invoice: CPA_OWNER only
  - void_invoice: CPA_OWNER only
  - create/submit/pay: both roles
  - PDF download: both roles
  - Read endpoints: both roles

STEP 5: TEST
  Write tests at: /backend/tests/services/test_accounts_receivable.py

  Required test cases:
  - test_create_invoice_with_lines: invoice + line items created
  - test_invoice_status_flow: DRAFT -> PENDING -> SENT -> PAID
  - test_approve_creates_journal_entry: GL entry on approval
  - test_payment_creates_journal_entry: GL entry on payment
  - test_partial_payment: balance updated correctly
  - test_overdue_detection: past-due invoices identified
  - test_ar_aging_buckets: correct bucket assignment
  - test_pdf_generation: WeasyPrint produces valid PDF
  - test_approve_requires_cpa_owner: ASSOCIATE cannot approve
  - test_void_requires_cpa_owner: ASSOCIATE cannot void
  - test_client_isolation: Client A invoices not visible to Client B
  - test_invoice_number_unique_per_client: no duplicate numbers

[ACCEPTANCE CRITERIA]
- [ ] Invoice lifecycle: DRAFT -> PENDING -> SENT -> PAID
- [ ] GL journal entries on approval and payment
- [ ] Partial payments tracked with remaining balance
- [ ] PDF invoice generation via WeasyPrint
- [ ] Overdue detection with aging buckets
- [ ] CPA_OWNER-only for approve and void
- [ ] Client isolation on all queries
- [ ] All test cases pass

[OUTPUT FORMAT]
End every session by printing to terminal:

  ================================
  SESSION COMPLETE
  Agent:        T2 — Accounts Receivable
  Task:         TASK-014
  Files changed: [list each file]
  Tests:        [passed/total]
  Issues opened: [n] — IDs: [list]
  Issues closed: [n] — IDs: [list]
  Next task:    TASK-015 — T3 Bank Reconciliation
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
