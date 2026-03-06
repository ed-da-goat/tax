-- Migration 005: Recurring transaction templates (C3)
-- Creates recurring_templates and recurring_template_lines tables.

CREATE TYPE recurring_frequency AS ENUM ('WEEKLY', 'BIWEEKLY', 'MONTHLY', 'QUARTERLY', 'ANNUALLY');
CREATE TYPE recurring_source_type AS ENUM ('JOURNAL_ENTRY', 'BILL');
CREATE TYPE recurring_template_status AS ENUM ('ACTIVE', 'PAUSED', 'EXPIRED');

CREATE TABLE IF NOT EXISTS recurring_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE RESTRICT,
    source_type recurring_source_type NOT NULL,
    description TEXT NOT NULL,
    frequency recurring_frequency NOT NULL,
    next_date DATE NOT NULL,
    end_date DATE,
    total_amount NUMERIC(15,2) NOT NULL DEFAULT 0,
    status recurring_template_status NOT NULL DEFAULT 'ACTIVE',

    -- For BILL templates
    vendor_id UUID REFERENCES vendors(id) ON DELETE RESTRICT,

    -- Tracking
    occurrences_generated INTEGER NOT NULL DEFAULT 0,
    max_occurrences INTEGER,
    last_generated_date DATE,
    created_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS recurring_template_lines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id UUID NOT NULL REFERENCES recurring_templates(id) ON DELETE CASCADE,
    account_id UUID NOT NULL REFERENCES chart_of_accounts(id) ON DELETE RESTRICT,
    description TEXT,
    debit NUMERIC(15,2) NOT NULL DEFAULT 0,
    credit NUMERIC(15,2) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_recurring_templates_client ON recurring_templates(client_id);
CREATE INDEX IF NOT EXISTS idx_recurring_templates_next_date ON recurring_templates(next_date) WHERE status = 'ACTIVE' AND deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_recurring_template_lines_template ON recurring_template_lines(template_id);

-- Audit triggers
CREATE OR REPLACE TRIGGER trg_recurring_templates_audit
AFTER INSERT OR UPDATE OR DELETE ON recurring_templates
FOR EACH ROW EXECUTE FUNCTION fn_audit_log();

CREATE OR REPLACE TRIGGER trg_recurring_template_lines_audit
AFTER INSERT OR UPDATE OR DELETE ON recurring_template_lines
FOR EACH ROW EXECUTE FUNCTION fn_audit_log();
