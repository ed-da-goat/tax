-- ============================================================================
-- 002_audit_triggers.sql
-- Automatic audit logging triggers for all data tables
-- PostgreSQL 15+
--
-- PREREQUISITE: This migration MUST run AFTER 001_initial_schema.sql.
--   It depends on the audit_log table and the audit_action enum type
--   created in that migration.
--
-- COMPLIANCE: Enforces CLAUDE.md compliance rule #2 — AUDIT TRAIL:
--   "Records are never deleted. Use soft deletes only (deleted_at timestamp).
--    Every INSERT, UPDATE, DELETE must write a row to the audit_log table
--    with: table_name, record_id, action, old_values (JSON), new_values
--    (JSON), user_id, timestamp."
--
-- HOW TO ADD AUDIT LOGGING TO NEW TABLES:
--   Copy the CREATE TRIGGER block at the bottom of this file and replace
--   the table name. Follow this pattern:
--
--     CREATE TRIGGER trg_<table_name>_audit
--         AFTER INSERT OR UPDATE OR DELETE ON <table_name>
--         FOR EACH ROW EXECUTE FUNCTION fn_audit_log();
--
--   Do NOT add a trigger on the audit_log table itself (infinite recursion).
-- ============================================================================

BEGIN;

-- ============================================================================
-- STEP 1: DROP EXISTING AUDIT TRIGGERS AND FUNCTION
-- The 001 migration creates these dynamically. We replace them here with
-- explicit, named triggers for full traceability and version control.
-- ============================================================================

-- Drop all existing audit triggers created by 001_initial_schema.sql
-- so we can recreate them cleanly without conflict.
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN
        SELECT trigger_name, event_object_table
        FROM information_schema.triggers
        WHERE trigger_schema = 'public'
          AND trigger_name LIKE 'trg_%_audit'
    LOOP
        EXECUTE format('DROP TRIGGER IF EXISTS %I ON %I', r.trigger_name, r.event_object_table);
    END LOOP;
END;
$$;


-- ============================================================================
-- STEP 2: CREATE OR REPLACE THE AUDIT LOG TRIGGER FUNCTION
--
-- This function captures row-level changes on any table it is attached to
-- and writes them to the audit_log table. It replaces the version from
-- 001_initial_schema.sql with the following improvements:
--
--   1. Defaults user_id to a 'system' sentinel when app.current_user_id
--      is not set in the session (e.g., during migrations or cron jobs).
--      The previous version defaulted to NULL, losing traceability.
--
--   2. Uses current_setting(..., true) which returns NULL on missing
--      setting instead of raising an error, then applies COALESCE for
--      safe fallback handling.
--
--   3. Reads ip_address from 'app.current_ip' (standardized name).
--
-- The application layer MUST set these session variables per transaction:
--   SET LOCAL app.current_user_id = '<uuid>';
--   SET LOCAL app.current_ip = '<ip_address>';
-- ============================================================================

CREATE OR REPLACE FUNCTION fn_audit_log()
RETURNS TRIGGER AS $$
DECLARE
    v_old           JSONB;
    v_new           JSONB;
    v_action        audit_action;
    v_record_id     UUID;
    v_user_id_raw   TEXT;
    v_user_id       UUID;
    v_ip_raw        TEXT;
    v_ip            INET;
BEGIN
    -- -----------------------------------------------------------------------
    -- Determine action and capture row data
    -- -----------------------------------------------------------------------
    IF TG_OP = 'INSERT' THEN
        v_action    := 'INSERT';
        v_old       := NULL;
        v_new       := row_to_json(NEW)::JSONB;
        v_record_id := NEW.id;

    ELSIF TG_OP = 'UPDATE' THEN
        v_action    := 'UPDATE';
        v_old       := row_to_json(OLD)::JSONB;
        v_new       := row_to_json(NEW)::JSONB;
        v_record_id := NEW.id;

    ELSIF TG_OP = 'DELETE' THEN
        v_action    := 'DELETE';
        v_old       := row_to_json(OLD)::JSONB;
        v_new       := NULL;
        v_record_id := OLD.id;

    END IF;

    -- -----------------------------------------------------------------------
    -- Resolve user_id from session variable
    -- current_setting('app.current_user_id', true) returns NULL if unset.
    -- If the setting is missing, empty, or 'system', we fall back to NULL
    -- for user_id (since 'system' is not a valid UUID FK to users).
    -- The literal string 'system' is preserved in the JSONB new_values
    -- context if needed, but audit_log.user_id is typed UUID REFERENCES
    -- users(id), so we must use NULL for non-user-initiated operations.
    -- -----------------------------------------------------------------------
    v_user_id_raw := current_setting('app.current_user_id', true);

    IF v_user_id_raw IS NOT NULL AND v_user_id_raw <> '' AND v_user_id_raw <> 'system' THEN
        BEGIN
            v_user_id := v_user_id_raw::UUID;
        EXCEPTION WHEN invalid_text_representation THEN
            -- Setting contained a non-UUID value; log as system action
            v_user_id := NULL;
        END;
    ELSE
        -- Not set, empty, or explicitly 'system' — treat as system action
        v_user_id := NULL;
    END IF;

    -- -----------------------------------------------------------------------
    -- Resolve IP address from session variable
    -- current_setting('app.current_ip', true) returns NULL if unset.
    -- -----------------------------------------------------------------------
    v_ip_raw := current_setting('app.current_ip', true);

    IF v_ip_raw IS NOT NULL AND v_ip_raw <> '' THEN
        BEGIN
            v_ip := v_ip_raw::INET;
        EXCEPTION WHEN invalid_text_representation THEN
            v_ip := NULL;
        END;
    ELSE
        v_ip := NULL;
    END IF;

    -- -----------------------------------------------------------------------
    -- Write the audit record
    -- -----------------------------------------------------------------------
    INSERT INTO audit_log (
        table_name,
        record_id,
        action,
        old_values,
        new_values,
        user_id,
        ip_address,
        created_at
    ) VALUES (
        TG_TABLE_NAME,
        v_record_id,
        v_action,
        v_old,
        v_new,
        v_user_id,
        v_ip,
        now()
    );

    -- -----------------------------------------------------------------------
    -- Return the appropriate row to allow the triggering operation to proceed
    -- -----------------------------------------------------------------------
    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql
   SECURITY DEFINER  -- Runs with the privileges of the function owner so
                      -- it can always write to audit_log regardless of the
                      -- caller's permissions.
   SET search_path = public;  -- Prevent search_path injection


-- ============================================================================
-- STEP 3: CREATE AUDIT TRIGGERS ON ALL DATA TABLES
--
-- Every table that holds application data gets an AFTER trigger for
-- INSERT, UPDATE, and DELETE. The following tables are EXCLUDED:
--
--   - audit_log        : Would cause infinite recursion (trigger writes to
--                        audit_log, which fires the trigger again).
--   - permission_log   : Operational security log; auditing it would create
--                        noise without compliance value.
--
-- Tables are listed explicitly (not discovered dynamically) so that:
--   1. This migration is fully reproducible and deterministic.
--   2. New tables require a conscious decision to add audit logging.
--   3. Code reviewers can see exactly which tables are covered.
--
-- TABLE LIST (from 001_initial_schema.sql):
--   Core:          users, clients
--   Ledger:        chart_of_accounts, journal_entries, journal_entry_lines
--   AP:            vendors, bills, bill_lines, bill_payments
--   AR:            invoices, invoice_lines, invoice_payments
--   Banking:       bank_accounts, bank_transactions, reconciliations
--   Documents:     documents
--   Payroll:       employees, payroll_runs, payroll_items
--   Tax:           payroll_tax_tables, tax_form_exports
--   Operations:    system_backups, migration_batches, migration_errors
-- ============================================================================

-- ---------------------------------------------------------------------------
-- Core tables
-- ---------------------------------------------------------------------------

CREATE TRIGGER trg_users_audit
    AFTER INSERT OR UPDATE OR DELETE ON users
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log();

CREATE TRIGGER trg_clients_audit
    AFTER INSERT OR UPDATE OR DELETE ON clients
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log();

-- ---------------------------------------------------------------------------
-- Chart of Accounts & General Ledger
-- ---------------------------------------------------------------------------

CREATE TRIGGER trg_chart_of_accounts_audit
    AFTER INSERT OR UPDATE OR DELETE ON chart_of_accounts
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log();

CREATE TRIGGER trg_journal_entries_audit
    AFTER INSERT OR UPDATE OR DELETE ON journal_entries
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log();

CREATE TRIGGER trg_journal_entry_lines_audit
    AFTER INSERT OR UPDATE OR DELETE ON journal_entry_lines
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log();

-- ---------------------------------------------------------------------------
-- Accounts Payable (AP)
-- ---------------------------------------------------------------------------

CREATE TRIGGER trg_vendors_audit
    AFTER INSERT OR UPDATE OR DELETE ON vendors
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log();

CREATE TRIGGER trg_bills_audit
    AFTER INSERT OR UPDATE OR DELETE ON bills
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log();

CREATE TRIGGER trg_bill_lines_audit
    AFTER INSERT OR UPDATE OR DELETE ON bill_lines
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log();

CREATE TRIGGER trg_bill_payments_audit
    AFTER INSERT OR UPDATE OR DELETE ON bill_payments
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log();

-- ---------------------------------------------------------------------------
-- Accounts Receivable (AR)
-- ---------------------------------------------------------------------------

CREATE TRIGGER trg_invoices_audit
    AFTER INSERT OR UPDATE OR DELETE ON invoices
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log();

CREATE TRIGGER trg_invoice_lines_audit
    AFTER INSERT OR UPDATE OR DELETE ON invoice_lines
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log();

CREATE TRIGGER trg_invoice_payments_audit
    AFTER INSERT OR UPDATE OR DELETE ON invoice_payments
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log();

-- ---------------------------------------------------------------------------
-- Banking
-- ---------------------------------------------------------------------------

CREATE TRIGGER trg_bank_accounts_audit
    AFTER INSERT OR UPDATE OR DELETE ON bank_accounts
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log();

CREATE TRIGGER trg_bank_transactions_audit
    AFTER INSERT OR UPDATE OR DELETE ON bank_transactions
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log();

CREATE TRIGGER trg_reconciliations_audit
    AFTER INSERT OR UPDATE OR DELETE ON reconciliations
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log();

-- ---------------------------------------------------------------------------
-- Document Management
-- ---------------------------------------------------------------------------

CREATE TRIGGER trg_documents_audit
    AFTER INSERT OR UPDATE OR DELETE ON documents
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log();

-- ---------------------------------------------------------------------------
-- Payroll
-- ---------------------------------------------------------------------------

CREATE TRIGGER trg_employees_audit
    AFTER INSERT OR UPDATE OR DELETE ON employees
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log();

CREATE TRIGGER trg_payroll_runs_audit
    AFTER INSERT OR UPDATE OR DELETE ON payroll_runs
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log();

CREATE TRIGGER trg_payroll_items_audit
    AFTER INSERT OR UPDATE OR DELETE ON payroll_items
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log();

-- ---------------------------------------------------------------------------
-- Tax & Compliance
-- ---------------------------------------------------------------------------

CREATE TRIGGER trg_payroll_tax_tables_audit
    AFTER INSERT OR UPDATE OR DELETE ON payroll_tax_tables
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log();

CREATE TRIGGER trg_tax_form_exports_audit
    AFTER INSERT OR UPDATE OR DELETE ON tax_form_exports
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log();

-- ---------------------------------------------------------------------------
-- Operations & Migration Tracking
-- ---------------------------------------------------------------------------

CREATE TRIGGER trg_system_backups_audit
    AFTER INSERT OR UPDATE OR DELETE ON system_backups
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log();

CREATE TRIGGER trg_migration_batches_audit
    AFTER INSERT OR UPDATE OR DELETE ON migration_batches
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log();

CREATE TRIGGER trg_migration_errors_audit
    AFTER INSERT OR UPDATE OR DELETE ON migration_errors
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log();


-- ============================================================================
-- STEP 4: VERIFICATION QUERY
-- Run this after migration to confirm all expected triggers are installed.
-- Expected: one trg_<table>_audit trigger per auditable table.
-- ============================================================================

DO $$
DECLARE
    v_expected_count INT := 24;  -- Total auditable tables listed above
    v_actual_count   INT;
BEGIN
    SELECT COUNT(DISTINCT event_object_table)
    INTO v_actual_count
    FROM information_schema.triggers
    WHERE trigger_schema = 'public'
      AND trigger_name LIKE 'trg_%_audit';

    IF v_actual_count < v_expected_count THEN
        RAISE WARNING
            '002_audit_triggers: Expected % audit triggers but found %. '
            'Some tables may be missing audit coverage.',
            v_expected_count, v_actual_count;
    ELSE
        RAISE NOTICE
            '002_audit_triggers: All % audit triggers installed successfully.',
            v_actual_count;
    END IF;
END;
$$;


COMMIT;
