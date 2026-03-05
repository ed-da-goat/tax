-- ============================================================================
-- Migration 003: Direct Deposit (Employee Bank Accounts, NACHA Batches)
--                and Tax E-Filing Submissions
-- ============================================================================
-- Phase 8A: Direct deposit infrastructure for NACHA file generation
-- Phase 8B: Tax e-filing submission tracking
-- ============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- ENUM types
-- ---------------------------------------------------------------------------
CREATE TYPE dd_account_type AS ENUM ('CHECKING', 'SAVINGS');
CREATE TYPE dd_batch_status AS ENUM ('GENERATED', 'DOWNLOADED', 'SUBMITTED', 'CONFIRMED', 'FAILED');
CREATE TYPE prenote_status AS ENUM ('PENDING', 'VERIFIED', 'FAILED');
CREATE TYPE tax_filing_status AS ENUM ('DRAFT', 'SUBMITTED', 'ACCEPTED', 'REJECTED', 'ERROR');
CREATE TYPE tax_filing_provider AS ENUM ('TAXBANDITS', 'GA_FSET', 'MANUAL');

-- ---------------------------------------------------------------------------
-- employee_bank_accounts
-- Stores encrypted bank account info for direct deposit enrollment.
-- Compliance (CLAUDE.md rule #4): client_id is non-nullable for isolation.
-- Compliance (CLAUDE.md rule #2): soft deletes only.
-- NACHA compliance: account numbers encrypted at rest.
-- ---------------------------------------------------------------------------
CREATE TABLE employee_bank_accounts (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id             UUID NOT NULL REFERENCES employees(id) ON DELETE RESTRICT,
    client_id               UUID NOT NULL REFERENCES clients(id) ON DELETE RESTRICT,
    account_holder_name     VARCHAR(255) NOT NULL,
    account_number_encrypted BYTEA NOT NULL,
    routing_number          VARCHAR(9) NOT NULL,
    account_type            dd_account_type NOT NULL DEFAULT 'CHECKING',
    is_primary              BOOLEAN NOT NULL DEFAULT TRUE,
    -- Direct deposit enrollment tracking
    enrollment_date         DATE,
    authorization_on_file   BOOLEAN NOT NULL DEFAULT FALSE,
    -- Prenote verification (NACHA recommended)
    prenote_status          prenote_status NOT NULL DEFAULT 'PENDING',
    prenote_sent_at         TIMESTAMPTZ,
    prenote_verified_at     TIMESTAMPTZ,
    -- Timestamps
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at              TIMESTAMPTZ
);

CREATE INDEX idx_emp_bank_employee ON employee_bank_accounts (employee_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_emp_bank_client ON employee_bank_accounts (client_id) WHERE deleted_at IS NULL;

-- Ensure only one primary account per employee
CREATE UNIQUE INDEX idx_emp_bank_primary
    ON employee_bank_accounts (employee_id)
    WHERE is_primary = TRUE AND deleted_at IS NULL;

-- ---------------------------------------------------------------------------
-- direct_deposit_batches
-- Tracks NACHA file generation and submission for payroll runs.
-- ---------------------------------------------------------------------------
CREATE TABLE direct_deposit_batches (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payroll_run_id      UUID NOT NULL REFERENCES payroll_runs(id) ON DELETE RESTRICT,
    client_id           UUID NOT NULL REFERENCES clients(id) ON DELETE RESTRICT,
    -- NACHA file metadata
    batch_number        INTEGER NOT NULL,
    file_id_modifier    CHAR(1) NOT NULL DEFAULT 'A',
    entry_count         INTEGER NOT NULL DEFAULT 0,
    total_credit_amount NUMERIC(15,2) NOT NULL DEFAULT 0,
    -- Company identification for NACHA header
    company_name        VARCHAR(16) NOT NULL,
    company_id          VARCHAR(10) NOT NULL,
    -- Status tracking
    status              dd_batch_status NOT NULL DEFAULT 'GENERATED',
    generated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    downloaded_at       TIMESTAMPTZ,
    submitted_at        TIMESTAMPTZ,
    confirmed_at        TIMESTAMPTZ,
    -- File storage
    nacha_file_path     VARCHAR(500),
    -- Audit
    generated_by        UUID REFERENCES users(id) ON DELETE RESTRICT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at          TIMESTAMPTZ
);

CREATE INDEX idx_dd_batch_payroll ON direct_deposit_batches (payroll_run_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_dd_batch_client ON direct_deposit_batches (client_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_dd_batch_status ON direct_deposit_batches (status) WHERE deleted_at IS NULL;

-- ---------------------------------------------------------------------------
-- tax_filing_submissions
-- Tracks electronic tax filing submissions to IRS and Georgia DOR.
-- Supports TaxBandits API (1099/W-2), Georgia FSET (G-7), and manual filing.
-- ---------------------------------------------------------------------------
CREATE TABLE tax_filing_submissions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id           UUID NOT NULL REFERENCES clients(id) ON DELETE RESTRICT,
    -- Filing details
    form_type           VARCHAR(20) NOT NULL,  -- '941', '940', 'G-7', 'W-2', '1099-NEC', etc.
    tax_year            INTEGER NOT NULL,
    tax_quarter         INTEGER,               -- 1-4 for quarterly filings, NULL for annual
    filing_period_start DATE,
    filing_period_end   DATE,
    -- Provider and submission tracking
    provider            tax_filing_provider NOT NULL DEFAULT 'MANUAL',
    provider_submission_id VARCHAR(100),        -- External ID from TaxBandits, FSET, etc.
    provider_reference  VARCHAR(255),           -- Additional reference info
    -- Status
    status              tax_filing_status NOT NULL DEFAULT 'DRAFT',
    submitted_at        TIMESTAMPTZ,
    accepted_at         TIMESTAMPTZ,
    rejected_at         TIMESTAMPTZ,
    rejection_reason    TEXT,
    -- Data snapshot (JSON of the submitted data for audit trail)
    submission_data     JSONB,
    response_data       JSONB,
    -- Audit
    submitted_by        UUID REFERENCES users(id) ON DELETE RESTRICT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at          TIMESTAMPTZ
);

CREATE INDEX idx_tax_filing_client ON tax_filing_submissions (client_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_tax_filing_form ON tax_filing_submissions (form_type, tax_year) WHERE deleted_at IS NULL;
CREATE INDEX idx_tax_filing_status ON tax_filing_submissions (status) WHERE deleted_at IS NULL;
CREATE INDEX idx_tax_filing_provider ON tax_filing_submissions (provider) WHERE deleted_at IS NULL;

-- ---------------------------------------------------------------------------
-- Audit triggers (same pattern as 002_audit_triggers.sql)
-- ---------------------------------------------------------------------------
CREATE TRIGGER audit_employee_bank_accounts
    AFTER INSERT OR UPDATE OR DELETE ON employee_bank_accounts
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log();

CREATE TRIGGER audit_direct_deposit_batches
    AFTER INSERT OR UPDATE OR DELETE ON direct_deposit_batches
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log();

CREATE TRIGGER audit_tax_filing_submissions
    AFTER INSERT OR UPDATE OR DELETE ON tax_filing_submissions
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log();

COMMIT;
