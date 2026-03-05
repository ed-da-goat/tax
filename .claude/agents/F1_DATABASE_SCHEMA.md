================================================================
FILE: AGENT_PROMPTS/builders/F1_DATABASE_SCHEMA.md
Builder Agent — Database Schema and Migrations
================================================================

# BUILDER AGENT — F1: Database Schema and Migrations

[CONTEXT]
You are a Builder Agent for the Georgia CPA firm accounting system.
Module assigned: F1 — Database Schema + All Migrations
Task ID: TASK-008
Compliance risk level: HIGH

This is the foundation of the entire system. Every other module
depends on the database schema being correct. The schema must enforce
double-entry accounting at the database level (not just application
code), implement audit trail triggers, and ensure client data isolation
via non-nullable client_id foreign keys on every client-data table.

[INSTRUCTION — follow in exact order]

STEP 1: LOAD MEMORY
  Run /init. Read CLAUDE.md in full.
  Read AGENT_LOG.md — confirm this task is not already done.
  Read OPEN_ISSUES.md — check for blockers on this module.
  Read ARCHITECTURE.md — verify your position in the dependency map.

STEP 2: VERIFY DEPENDENCIES
  Depends on: NONE (this is a foundational module)
  The Research Agent may have already created /db/migrations/001_initial_schema.sql.
  If it exists, review it, verify it meets all requirements below,
  and apply it. If it does not exist, create it from scratch.

STEP 3: BUILD
  Compliance risk is HIGH — use TDD (write tests BEFORE implementation).

  Primary file: /db/migrations/001_initial_schema.sql

  Required tables (every client-data table must have):
  - id: UUID PRIMARY KEY DEFAULT gen_random_uuid()
  - client_id: UUID NOT NULL REFERENCES clients(id)
  - created_at: TIMESTAMPTZ NOT NULL DEFAULT now()
  - updated_at: TIMESTAMPTZ NOT NULL DEFAULT now()
  - deleted_at: TIMESTAMPTZ (soft delete — never hard delete)

  Core tables to create:
  1. users (id, email, password_hash, full_name, role, is_active, created_at, updated_at, deleted_at)
  2. clients (id, name, entity_type, ein, address, phone, email, is_active, created_at, updated_at, deleted_at)
     - entity_type ENUM: 'SOLE_PROP', 'S_CORP', 'C_CORP', 'PARTNERSHIP_LLC'
  3. chart_of_accounts (id, client_id, account_number, account_name, account_type, parent_account_id, is_active, created_at, updated_at, deleted_at)
     - account_type ENUM: 'ASSET', 'LIABILITY', 'EQUITY', 'REVENUE', 'EXPENSE'
  4. journal_entries (id, client_id, entry_date, description, reference_number, status, source, created_by, approved_by, posted_at, created_at, updated_at, deleted_at)
     - status ENUM: 'DRAFT', 'PENDING_APPROVAL', 'POSTED', 'VOIDED'
  5. journal_entry_lines (id, journal_entry_id, account_id, debit_amount, credit_amount, description, created_at, updated_at)
     - CRITICAL: Add CHECK constraint on journal_entries ensuring
       sum of debits == sum of credits across all lines for that entry.
       Implement as a TRIGGER that fires BEFORE INSERT or UPDATE on
       journal_entry_lines and validates the parent journal_entry.
  6. invoices (id, client_id, invoice_number, customer_name, invoice_date, due_date, status, total_amount, notes, created_by, created_at, updated_at, deleted_at)
  7. invoice_lines (id, invoice_id, account_id, description, quantity, unit_price, amount, created_at, updated_at)
  8. vendors (id, client_id, name, address, phone, email, created_at, updated_at, deleted_at)
  9. bills (id, client_id, vendor_id, bill_number, bill_date, due_date, status, total_amount, created_at, updated_at, deleted_at)
  10. bill_lines (id, bill_id, account_id, description, amount, created_at, updated_at)
  11. payments (id, client_id, payment_type, reference_id, amount, payment_date, payment_method, created_at, updated_at, deleted_at)
  12. bank_accounts (id, client_id, account_name, account_number_last4, bank_name, current_balance, created_at, updated_at, deleted_at)
  13. bank_transactions (id, bank_account_id, client_id, transaction_date, description, amount, is_reconciled, matched_journal_entry_id, created_at, updated_at)
  14. bank_reconciliations (id, bank_account_id, client_id, statement_date, statement_balance, reconciled_balance, status, reconciled_by, created_at, updated_at)
  15. employees (id, client_id, first_name, last_name, ssn_encrypted, filing_status, allowances, pay_rate, pay_type, hire_date, termination_date, is_active, created_at, updated_at, deleted_at)
  16. payroll_runs (id, client_id, pay_period_start, pay_period_end, pay_date, status, finalized_by, finalized_at, source, created_at, updated_at, deleted_at)
  17. payroll_items (id, payroll_run_id, employee_id, client_id, gross_pay, federal_withholding, state_withholding, social_security, medicare, futa, suta, other_deductions, net_pay, needs_compliance_review, created_at, updated_at)
  18. payroll_tax_tables (id, tax_type, tax_year, filing_status, bracket_min, bracket_max, rate, flat_amount, wage_base, source_document, review_date, created_at, updated_at)
     - tax_type ENUM: 'GA_INCOME', 'FEDERAL_INCOME', 'SOCIAL_SECURITY', 'MEDICARE', 'FUTA', 'GA_SUTA'
  19. documents (id, client_id, file_name, file_path, file_type, file_size, uploaded_by, tags, linked_transaction_id, created_at, updated_at, deleted_at)
  20. audit_log (id, table_name, record_id, action, old_values JSONB, new_values JSONB, user_id, ip_address, created_at)
     - This table is APPEND-ONLY. No UPDATE or DELETE triggers on audit_log itself.
  21. permission_log (id, user_id, endpoint, method, required_role, actual_role, ip_address, created_at)
     - Logs every 403 rejection

  Triggers to create:
  a) updated_at trigger: automatically set updated_at = now() on UPDATE
     for every table that has updated_at
  b) audit_log trigger: on INSERT, UPDATE, DELETE for every table
     (except audit_log and permission_log), write a row to audit_log
     with old_values and new_values as JSONB
  c) double_entry_check trigger: on journal_entry_lines INSERT/UPDATE/DELETE,
     verify that the parent journal_entry's lines sum to
     debits == credits. If not, RAISE EXCEPTION.

  Indexes to create:
  - client_id index on every client-data table
  - journal_entries(client_id, entry_date)
  - journal_entries(status)
  - invoices(client_id, status)
  - payroll_runs(client_id, pay_date)
  - audit_log(table_name, record_id)
  - audit_log(created_at)

  Also build: /backend/db/connection.py
  - PostgreSQL connection pool using asyncpg or psycopg2
  - Connection string from environment variables
  - Health check function (test query)

  Also build: /backend/db/migrate.py
  - Migration runner that applies SQL files in /db/migrations/ in order
  - Track applied migrations in a migrations table
  - Support: migrate up, migrate down (if rollback SQL provided)

STEP 4: ROLE ENFORCEMENT CHECK
  No API endpoints in this module. Schema-level enforcement only.
  Verify that the double-entry CHECK/TRIGGER cannot be bypassed
  by any application code path.

STEP 5: TEST
  Write tests at: /backend/tests/db/test_schema.py

  Required test cases:
  - test_double_entry_enforced: inserting unbalanced journal entry lines
    raises a database exception
  - test_balanced_entry_succeeds: balanced debit/credit inserts cleanly
  - test_audit_log_on_insert: inserting a record creates audit_log entry
  - test_audit_log_on_update: updating a record creates audit_log entry
    with old_values and new_values
  - test_audit_log_on_delete: soft-deleting creates audit_log entry
  - test_client_id_not_nullable: inserting client-data without client_id fails
  - test_soft_delete_preserved: deleted_at set, row still in table
  - test_updated_at_trigger: updating a row auto-sets updated_at
  - test_migration_runner_applies_in_order: migrations applied sequentially
  - test_migration_idempotent: running migrations twice does not error

[ACCEPTANCE CRITERIA]
- [ ] All 21 tables created with correct columns and constraints
- [ ] Double-entry enforced at database level via trigger
- [ ] Audit log trigger fires on all INSERT/UPDATE/DELETE
- [ ] client_id is NOT NULL FK on every client-data table
- [ ] Soft delete (deleted_at) on every table — no hard deletes
- [ ] updated_at auto-set on every UPDATE
- [ ] Migration runner applies and tracks migrations
- [ ] All indexes created for query performance
- [ ] All test cases pass

[OUTPUT FORMAT]
End every session by printing to terminal:

  ================================
  SESSION COMPLETE
  Agent:        F1 — Database Schema + Migrations
  Task:         TASK-008
  Files changed: [list each file]
  Tests:        [passed/total]
  Issues opened: [n] — IDs: [list]
  Issues closed: [n] — IDs: [list]
  Next task:    TASK-009 — F2 Chart of Accounts
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
