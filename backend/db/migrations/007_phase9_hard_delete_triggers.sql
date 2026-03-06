-- Migration 007: Add hard-delete protection triggers to Phase 9 tables
-- These 18 tables have deleted_at (soft-delete) but were missing the
-- fn_prevent_hard_delete trigger that guards against accidental hard deletes.
--
-- The function fn_prevent_hard_delete() already exists (created in 001).
-- This migration only adds the BEFORE DELETE triggers.

BEGIN;

CREATE TRIGGER trg_prevent_hard_delete_budgets
    BEFORE DELETE ON budgets FOR EACH ROW
    EXECUTE FUNCTION fn_prevent_hard_delete();

CREATE TRIGGER trg_prevent_hard_delete_contacts
    BEFORE DELETE ON contacts FOR EACH ROW
    EXECUTE FUNCTION fn_prevent_hard_delete();

CREATE TRIGGER trg_prevent_hard_delete_direct_deposit_batches
    BEFORE DELETE ON direct_deposit_batches FOR EACH ROW
    EXECUTE FUNCTION fn_prevent_hard_delete();

CREATE TRIGGER trg_prevent_hard_delete_due_dates
    BEFORE DELETE ON due_dates FOR EACH ROW
    EXECUTE FUNCTION fn_prevent_hard_delete();

CREATE TRIGGER trg_prevent_hard_delete_employee_bank_accounts
    BEFORE DELETE ON employee_bank_accounts FOR EACH ROW
    EXECUTE FUNCTION fn_prevent_hard_delete();

CREATE TRIGGER trg_prevent_hard_delete_engagements
    BEFORE DELETE ON engagements FOR EACH ROW
    EXECUTE FUNCTION fn_prevent_hard_delete();

CREATE TRIGGER trg_prevent_hard_delete_fixed_assets
    BEFORE DELETE ON fixed_assets FOR EACH ROW
    EXECUTE FUNCTION fn_prevent_hard_delete();

CREATE TRIGGER trg_prevent_hard_delete_messages
    BEFORE DELETE ON messages FOR EACH ROW
    EXECUTE FUNCTION fn_prevent_hard_delete();

CREATE TRIGGER trg_prevent_hard_delete_portal_users
    BEFORE DELETE ON portal_users FOR EACH ROW
    EXECUTE FUNCTION fn_prevent_hard_delete();

CREATE TRIGGER trg_prevent_hard_delete_questionnaires
    BEFORE DELETE ON questionnaires FOR EACH ROW
    EXECUTE FUNCTION fn_prevent_hard_delete();

CREATE TRIGGER trg_prevent_hard_delete_recurring_template_lines
    BEFORE DELETE ON recurring_template_lines FOR EACH ROW
    EXECUTE FUNCTION fn_prevent_hard_delete();

CREATE TRIGGER trg_prevent_hard_delete_recurring_templates
    BEFORE DELETE ON recurring_templates FOR EACH ROW
    EXECUTE FUNCTION fn_prevent_hard_delete();

CREATE TRIGGER trg_prevent_hard_delete_service_invoices
    BEFORE DELETE ON service_invoices FOR EACH ROW
    EXECUTE FUNCTION fn_prevent_hard_delete();

CREATE TRIGGER trg_prevent_hard_delete_staff_rates
    BEFORE DELETE ON staff_rates FOR EACH ROW
    EXECUTE FUNCTION fn_prevent_hard_delete();

CREATE TRIGGER trg_prevent_hard_delete_tax_filing_submissions
    BEFORE DELETE ON tax_filing_submissions FOR EACH ROW
    EXECUTE FUNCTION fn_prevent_hard_delete();

CREATE TRIGGER trg_prevent_hard_delete_time_entries
    BEFORE DELETE ON time_entries FOR EACH ROW
    EXECUTE FUNCTION fn_prevent_hard_delete();

CREATE TRIGGER trg_prevent_hard_delete_workflow_tasks
    BEFORE DELETE ON workflow_tasks FOR EACH ROW
    EXECUTE FUNCTION fn_prevent_hard_delete();

CREATE TRIGGER trg_prevent_hard_delete_workflows
    BEFORE DELETE ON workflows FOR EACH ROW
    EXECUTE FUNCTION fn_prevent_hard_delete();

COMMIT;
