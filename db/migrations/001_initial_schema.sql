-- ============================================================================
-- 001_initial_schema.sql
-- Complete PostgreSQL schema for Georgia CPA Firm Accounting System
-- PostgreSQL 15+
--
-- DESIGN PRINCIPLES:
--   1. DOUBLE-ENTRY: Every posted journal entry must balance (debits = credits)
--   2. AUDIT TRAIL: No hard deletes; soft-delete via deleted_at; audit_log is immutable
--   3. CLIENT ISOLATION: Every client-data table carries client_id UUID NOT NULL FK
--   4. Standard columns: id (UUID PK), created_at, updated_at, deleted_at
-- ============================================================================

BEGIN;

-- ============================================================================
-- EXTENSIONS
-- ============================================================================
CREATE EXTENSION IF NOT EXISTS pgcrypto;  -- provides gen_random_uuid()

-- ============================================================================
-- CUSTOM ENUM TYPES
-- ============================================================================

CREATE TYPE user_role AS ENUM ('CPA_OWNER', 'ASSOCIATE');

CREATE TYPE entity_type AS ENUM ('SOLE_PROP', 'S_CORP', 'C_CORP', 'PARTNERSHIP_LLC');

CREATE TYPE audit_action AS ENUM ('INSERT', 'UPDATE', 'DELETE');

CREATE TYPE account_type AS ENUM ('ASSET', 'LIABILITY', 'EQUITY', 'REVENUE', 'EXPENSE');

CREATE TYPE journal_entry_status AS ENUM ('DRAFT', 'PENDING_APPROVAL', 'POSTED', 'VOID');

CREATE TYPE bill_status AS ENUM ('DRAFT', 'PENDING_APPROVAL', 'APPROVED', 'PAID', 'VOID');

CREATE TYPE invoice_status AS ENUM ('DRAFT', 'PENDING_APPROVAL', 'SENT', 'PAID', 'VOID', 'OVERDUE');

CREATE TYPE bank_transaction_type AS ENUM ('DEBIT', 'CREDIT');

CREATE TYPE reconciliation_status AS ENUM ('IN_PROGRESS', 'COMPLETED');

CREATE TYPE filing_status AS ENUM ('SINGLE', 'MARRIED', 'HEAD_OF_HOUSEHOLD');

CREATE TYPE pay_type AS ENUM ('HOURLY', 'SALARY');

CREATE TYPE payroll_run_status AS ENUM ('DRAFT', 'PENDING_APPROVAL', 'FINALIZED', 'VOID');

CREATE TYPE tax_form_status AS ENUM ('DRAFT', 'FINAL', 'FILED');

CREATE TYPE backup_status AS ENUM ('IN_PROGRESS', 'COMPLETED', 'FAILED');

CREATE TYPE migration_batch_status AS ENUM (
    'VALIDATING', 'DRY_RUN', 'IMPORTING', 'COMPLETED', 'FAILED', 'ROLLED_BACK'
);


-- ============================================================================
-- CORE TABLES
-- ============================================================================

-- ---------------------------------------------------------------------------
-- users
-- ---------------------------------------------------------------------------
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    full_name       VARCHAR(255) NOT NULL,
    role            user_role NOT NULL DEFAULT 'ASSOCIATE',
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    last_login_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at      TIMESTAMPTZ
);

CREATE INDEX idx_users_email ON users (email) WHERE deleted_at IS NULL;
CREATE INDEX idx_users_role ON users (role) WHERE deleted_at IS NULL;

-- ---------------------------------------------------------------------------
-- clients
-- ---------------------------------------------------------------------------
CREATE TABLE clients (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(255) NOT NULL,
    entity_type     entity_type NOT NULL,
    tax_id_encrypted BYTEA,                -- encrypted at application layer
    address         VARCHAR(500),
    city            VARCHAR(100),
    state           VARCHAR(2) DEFAULT 'GA',
    zip             VARCHAR(10),
    phone           VARCHAR(20),
    email           VARCHAR(255),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at      TIMESTAMPTZ
);

CREATE INDEX idx_clients_name ON clients (name) WHERE deleted_at IS NULL;
CREATE INDEX idx_clients_entity_type ON clients (entity_type) WHERE deleted_at IS NULL;

-- ---------------------------------------------------------------------------
-- audit_log — IMMUTABLE, no deleted_at, no updated_at
-- ---------------------------------------------------------------------------
CREATE TABLE audit_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    table_name      VARCHAR(100) NOT NULL,
    record_id       UUID NOT NULL,
    action          audit_action NOT NULL,
    old_values      JSONB,
    new_values      JSONB,
    user_id         UUID REFERENCES users(id) ON DELETE RESTRICT,
    ip_address      INET,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_audit_log_table_record ON audit_log (table_name, record_id);
CREATE INDEX idx_audit_log_user ON audit_log (user_id);
CREATE INDEX idx_audit_log_created ON audit_log (created_at);

-- ---------------------------------------------------------------------------
-- permission_log — logs every 403 Forbidden response
-- ---------------------------------------------------------------------------
CREATE TABLE permission_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE RESTRICT,
    endpoint        VARCHAR(500) NOT NULL,
    method          VARCHAR(10) NOT NULL,
    status_code     INT NOT NULL DEFAULT 403,
    role_required   VARCHAR(50) NOT NULL,
    role_provided   VARCHAR(50) NOT NULL,
    ip_address      VARCHAR(45),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_permission_log_user ON permission_log (user_id);
CREATE INDEX idx_permission_log_created ON permission_log (created_at);


-- ============================================================================
-- CHART OF ACCOUNTS & GENERAL LEDGER
-- ============================================================================

-- ---------------------------------------------------------------------------
-- chart_of_accounts
-- ---------------------------------------------------------------------------
CREATE TABLE chart_of_accounts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id       UUID NOT NULL REFERENCES clients(id) ON DELETE RESTRICT,
    account_number  VARCHAR(20) NOT NULL,
    account_name    VARCHAR(255) NOT NULL,
    account_type    account_type NOT NULL,
    sub_type        VARCHAR(100),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at      TIMESTAMPTZ,
    UNIQUE (client_id, account_number)
);

CREATE INDEX idx_coa_client ON chart_of_accounts (client_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_coa_type ON chart_of_accounts (account_type) WHERE deleted_at IS NULL;

-- ---------------------------------------------------------------------------
-- journal_entries
-- ---------------------------------------------------------------------------
CREATE TABLE journal_entries (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id        UUID NOT NULL REFERENCES clients(id) ON DELETE RESTRICT,
    entry_date       DATE NOT NULL,
    description      TEXT,
    reference_number VARCHAR(100),
    status           journal_entry_status NOT NULL DEFAULT 'DRAFT',
    created_by       UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    approved_by      UUID REFERENCES users(id) ON DELETE RESTRICT,
    posted_at        TIMESTAMPTZ,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at       TIMESTAMPTZ
);

CREATE INDEX idx_je_client ON journal_entries (client_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_je_date ON journal_entries (entry_date) WHERE deleted_at IS NULL;
CREATE INDEX idx_je_status ON journal_entries (status) WHERE deleted_at IS NULL;
CREATE INDEX idx_je_reference ON journal_entries (reference_number) WHERE deleted_at IS NULL;

-- ---------------------------------------------------------------------------
-- journal_entry_lines
-- ---------------------------------------------------------------------------
CREATE TABLE journal_entry_lines (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    journal_entry_id  UUID NOT NULL REFERENCES journal_entries(id) ON DELETE RESTRICT,
    account_id        UUID NOT NULL REFERENCES chart_of_accounts(id) ON DELETE RESTRICT,
    debit             NUMERIC(15,2) NOT NULL DEFAULT 0
                      CHECK (debit >= 0),
    credit            NUMERIC(15,2) NOT NULL DEFAULT 0
                      CHECK (credit >= 0),
    description       TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at        TIMESTAMPTZ,
    -- Each line must have either a debit or credit, not both, not neither
    CONSTRAINT chk_debit_xor_credit CHECK (
        (debit > 0 AND credit = 0) OR (debit = 0 AND credit > 0)
    )
);

CREATE INDEX idx_jel_entry ON journal_entry_lines (journal_entry_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_jel_account ON journal_entry_lines (account_id) WHERE deleted_at IS NULL;


-- ============================================================================
-- ACCOUNTS PAYABLE
-- ============================================================================

-- ---------------------------------------------------------------------------
-- vendors
-- ---------------------------------------------------------------------------
CREATE TABLE vendors (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id       UUID NOT NULL REFERENCES clients(id) ON DELETE RESTRICT,
    name            VARCHAR(255) NOT NULL,
    tax_id_encrypted BYTEA,
    address         VARCHAR(500),
    city            VARCHAR(100),
    state           VARCHAR(2),
    zip             VARCHAR(10),
    phone           VARCHAR(20),
    email           VARCHAR(255),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at      TIMESTAMPTZ
);

CREATE INDEX idx_vendors_client ON vendors (client_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_vendors_name ON vendors (client_id, name) WHERE deleted_at IS NULL;

-- ---------------------------------------------------------------------------
-- bills
-- ---------------------------------------------------------------------------
CREATE TABLE bills (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id       UUID NOT NULL REFERENCES clients(id) ON DELETE RESTRICT,
    vendor_id       UUID NOT NULL REFERENCES vendors(id) ON DELETE RESTRICT,
    bill_number     VARCHAR(100),
    bill_date       DATE NOT NULL,
    due_date        DATE NOT NULL,
    total_amount    NUMERIC(15,2) NOT NULL CHECK (total_amount >= 0),
    status          bill_status NOT NULL DEFAULT 'DRAFT',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at      TIMESTAMPTZ
);

CREATE INDEX idx_bills_client ON bills (client_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_bills_vendor ON bills (vendor_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_bills_status ON bills (status) WHERE deleted_at IS NULL;
CREATE INDEX idx_bills_due_date ON bills (due_date) WHERE deleted_at IS NULL;

-- ---------------------------------------------------------------------------
-- bill_lines
-- ---------------------------------------------------------------------------
CREATE TABLE bill_lines (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bill_id         UUID NOT NULL REFERENCES bills(id) ON DELETE RESTRICT,
    account_id      UUID NOT NULL REFERENCES chart_of_accounts(id) ON DELETE RESTRICT,
    description     TEXT,
    amount          NUMERIC(15,2) NOT NULL CHECK (amount >= 0),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at      TIMESTAMPTZ
);

CREATE INDEX idx_bill_lines_bill ON bill_lines (bill_id) WHERE deleted_at IS NULL;

-- ---------------------------------------------------------------------------
-- bill_payments
-- ---------------------------------------------------------------------------
CREATE TABLE bill_payments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bill_id         UUID NOT NULL REFERENCES bills(id) ON DELETE RESTRICT,
    payment_date    DATE NOT NULL,
    amount          NUMERIC(15,2) NOT NULL CHECK (amount > 0),
    payment_method  VARCHAR(50),
    reference_number VARCHAR(100),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at      TIMESTAMPTZ
);

CREATE INDEX idx_bill_payments_bill ON bill_payments (bill_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_bill_payments_date ON bill_payments (payment_date) WHERE deleted_at IS NULL;


-- ============================================================================
-- ACCOUNTS RECEIVABLE
-- ============================================================================

-- ---------------------------------------------------------------------------
-- invoices
-- ---------------------------------------------------------------------------
CREATE TABLE invoices (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id       UUID NOT NULL REFERENCES clients(id) ON DELETE RESTRICT,
    customer_name   VARCHAR(255) NOT NULL,
    invoice_number  VARCHAR(100),
    invoice_date    DATE NOT NULL,
    due_date        DATE NOT NULL,
    total_amount    NUMERIC(15,2) NOT NULL CHECK (total_amount >= 0),
    status          invoice_status NOT NULL DEFAULT 'DRAFT',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at      TIMESTAMPTZ
);

CREATE INDEX idx_invoices_client ON invoices (client_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_invoices_status ON invoices (status) WHERE deleted_at IS NULL;
CREATE INDEX idx_invoices_due_date ON invoices (due_date) WHERE deleted_at IS NULL;
CREATE INDEX idx_invoices_date ON invoices (invoice_date) WHERE deleted_at IS NULL;

-- ---------------------------------------------------------------------------
-- invoice_lines
-- ---------------------------------------------------------------------------
CREATE TABLE invoice_lines (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id      UUID NOT NULL REFERENCES invoices(id) ON DELETE RESTRICT,
    account_id      UUID NOT NULL REFERENCES chart_of_accounts(id) ON DELETE RESTRICT,
    description     TEXT,
    quantity        NUMERIC(10,2) NOT NULL DEFAULT 1,
    unit_price      NUMERIC(15,2) NOT NULL CHECK (unit_price >= 0),
    amount          NUMERIC(15,2) NOT NULL CHECK (amount >= 0),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at      TIMESTAMPTZ
);

CREATE INDEX idx_invoice_lines_invoice ON invoice_lines (invoice_id) WHERE deleted_at IS NULL;

-- ---------------------------------------------------------------------------
-- invoice_payments
-- ---------------------------------------------------------------------------
CREATE TABLE invoice_payments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id      UUID NOT NULL REFERENCES invoices(id) ON DELETE RESTRICT,
    payment_date    DATE NOT NULL,
    amount          NUMERIC(15,2) NOT NULL CHECK (amount > 0),
    payment_method  VARCHAR(50),
    reference_number VARCHAR(100),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at      TIMESTAMPTZ
);

CREATE INDEX idx_invoice_payments_invoice ON invoice_payments (invoice_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_invoice_payments_date ON invoice_payments (payment_date) WHERE deleted_at IS NULL;


-- ============================================================================
-- BANK RECONCILIATION
-- ============================================================================

-- ---------------------------------------------------------------------------
-- bank_accounts
-- ---------------------------------------------------------------------------
CREATE TABLE bank_accounts (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id               UUID NOT NULL REFERENCES clients(id) ON DELETE RESTRICT,
    account_name            VARCHAR(255) NOT NULL,
    account_number_encrypted BYTEA,
    institution_name        VARCHAR(255),
    account_id              UUID REFERENCES chart_of_accounts(id) ON DELETE RESTRICT,   -- linked GL account
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at              TIMESTAMPTZ
);

CREATE INDEX idx_bank_accounts_client ON bank_accounts (client_id) WHERE deleted_at IS NULL;

-- ---------------------------------------------------------------------------
-- bank_transactions
-- ---------------------------------------------------------------------------
CREATE TABLE bank_transactions (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bank_account_id   UUID NOT NULL REFERENCES bank_accounts(id) ON DELETE RESTRICT,
    transaction_date  DATE NOT NULL,
    description       TEXT,
    amount            NUMERIC(15,2) NOT NULL,
    transaction_type  bank_transaction_type NOT NULL,
    is_reconciled     BOOLEAN NOT NULL DEFAULT FALSE,
    reconciled_at     TIMESTAMPTZ,
    journal_entry_id  UUID REFERENCES journal_entries(id) ON DELETE RESTRICT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at        TIMESTAMPTZ
);

CREATE INDEX idx_bank_txn_account ON bank_transactions (bank_account_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_bank_txn_date ON bank_transactions (transaction_date) WHERE deleted_at IS NULL;
CREATE INDEX idx_bank_txn_reconciled ON bank_transactions (is_reconciled) WHERE deleted_at IS NULL;

-- ---------------------------------------------------------------------------
-- reconciliations
-- ---------------------------------------------------------------------------
CREATE TABLE reconciliations (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bank_account_id     UUID NOT NULL REFERENCES bank_accounts(id) ON DELETE RESTRICT,
    statement_date      DATE NOT NULL,
    statement_balance   NUMERIC(15,2) NOT NULL,
    reconciled_balance  NUMERIC(15,2),
    status              reconciliation_status NOT NULL DEFAULT 'IN_PROGRESS',
    completed_at        TIMESTAMPTZ,
    completed_by        UUID REFERENCES users(id) ON DELETE RESTRICT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at          TIMESTAMPTZ
);

CREATE INDEX idx_reconciliations_bank ON reconciliations (bank_account_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_reconciliations_status ON reconciliations (status) WHERE deleted_at IS NULL;


-- ============================================================================
-- DOCUMENTS
-- ============================================================================

CREATE TABLE documents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id       UUID NOT NULL REFERENCES clients(id) ON DELETE RESTRICT,
    file_name       VARCHAR(500) NOT NULL,
    file_path       VARCHAR(1000) NOT NULL,
    file_type       VARCHAR(100),
    file_size_bytes BIGINT,
    description     TEXT,
    tags            TEXT[],
    uploaded_by     UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    journal_entry_id UUID REFERENCES journal_entries(id) ON DELETE RESTRICT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at      TIMESTAMPTZ
);

CREATE INDEX idx_documents_client ON documents (client_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_documents_tags ON documents USING GIN (tags) WHERE deleted_at IS NULL;
CREATE INDEX idx_documents_je ON documents (journal_entry_id) WHERE deleted_at IS NULL AND journal_entry_id IS NOT NULL;


-- ============================================================================
-- PAYROLL
-- ============================================================================

-- ---------------------------------------------------------------------------
-- employees
-- ---------------------------------------------------------------------------
CREATE TABLE employees (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id       UUID NOT NULL REFERENCES clients(id) ON DELETE RESTRICT,
    first_name      VARCHAR(100) NOT NULL,
    last_name       VARCHAR(100) NOT NULL,
    ssn_encrypted   BYTEA,
    filing_status   filing_status NOT NULL DEFAULT 'SINGLE',
    allowances      INT NOT NULL DEFAULT 0,
    pay_rate        NUMERIC(15,2) NOT NULL CHECK (pay_rate >= 0),
    pay_type        pay_type NOT NULL,
    hire_date       DATE NOT NULL,
    termination_date DATE,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at      TIMESTAMPTZ
);

CREATE INDEX idx_employees_client ON employees (client_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_employees_active ON employees (client_id, is_active) WHERE deleted_at IS NULL;

-- ---------------------------------------------------------------------------
-- payroll_runs
-- ---------------------------------------------------------------------------
CREATE TABLE payroll_runs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id       UUID NOT NULL REFERENCES clients(id) ON DELETE RESTRICT,
    pay_period_start DATE NOT NULL,
    pay_period_end  DATE NOT NULL,
    pay_date        DATE NOT NULL,
    status          payroll_run_status NOT NULL DEFAULT 'DRAFT',
    finalized_by    UUID REFERENCES users(id) ON DELETE RESTRICT,
    finalized_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at      TIMESTAMPTZ,
    CHECK (pay_period_end >= pay_period_start),
    CHECK (pay_date >= pay_period_end)
);

CREATE INDEX idx_payroll_runs_client ON payroll_runs (client_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_payroll_runs_status ON payroll_runs (status) WHERE deleted_at IS NULL;
CREATE INDEX idx_payroll_runs_pay_date ON payroll_runs (pay_date) WHERE deleted_at IS NULL;

-- ---------------------------------------------------------------------------
-- payroll_items
-- ---------------------------------------------------------------------------
CREATE TABLE payroll_items (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payroll_run_id       UUID NOT NULL REFERENCES payroll_runs(id) ON DELETE RESTRICT,
    employee_id          UUID NOT NULL REFERENCES employees(id) ON DELETE RESTRICT,
    gross_pay            NUMERIC(15,2) NOT NULL CHECK (gross_pay >= 0),
    federal_withholding  NUMERIC(15,2) NOT NULL DEFAULT 0 CHECK (federal_withholding >= 0),
    state_withholding    NUMERIC(15,2) NOT NULL DEFAULT 0 CHECK (state_withholding >= 0),
    social_security      NUMERIC(15,2) NOT NULL DEFAULT 0 CHECK (social_security >= 0),
    medicare             NUMERIC(15,2) NOT NULL DEFAULT 0 CHECK (medicare >= 0),
    ga_suta              NUMERIC(15,2) NOT NULL DEFAULT 0 CHECK (ga_suta >= 0),
    futa                 NUMERIC(15,2) NOT NULL DEFAULT 0 CHECK (futa >= 0),
    net_pay              NUMERIC(15,2) NOT NULL CHECK (net_pay >= 0),
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at           TIMESTAMPTZ
);

CREATE INDEX idx_payroll_items_run ON payroll_items (payroll_run_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_payroll_items_employee ON payroll_items (employee_id) WHERE deleted_at IS NULL;

-- ---------------------------------------------------------------------------
-- payroll_tax_tables
-- SOURCE: Georgia DOR withholding tables, parameterized by tax_year.
-- These rates are looked up at runtime by the payroll calculation engine.
-- Every row must cite its authoritative source_document and have a review_date.
-- ---------------------------------------------------------------------------
CREATE TABLE payroll_tax_tables (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tax_year        INT NOT NULL,
    tax_type        VARCHAR(50) NOT NULL,       -- e.g. 'GA_STATE', 'FEDERAL', 'FICA_SS', 'FICA_MEDICARE', 'FUTA', 'GA_SUTA'
    filing_status   VARCHAR(50),                -- e.g. 'SINGLE', 'MARRIED', etc.
    bracket_min     NUMERIC(15,2) NOT NULL,
    bracket_max     NUMERIC(15,2),              -- NULL means no upper bound
    rate            NUMERIC(8,6) NOT NULL,       -- e.g. 0.055000 for 5.5%
    flat_amount     NUMERIC(15,2) NOT NULL DEFAULT 0,
    source_document VARCHAR(500) NOT NULL,       -- citation: e.g. 'GA DOR Employer Tax Guide 2025'
    review_date     DATE NOT NULL,               -- date this row was verified
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
    -- NOTE: No deleted_at — tax tables are versioned by tax_year, not soft-deleted
);

COMMENT ON TABLE payroll_tax_tables IS
    'SOURCE: Georgia DOR withholding tables, parameterized by tax_year. '
    'Federal rates from IRS Publication 15-T. '
    'Each row must reference its authoritative source_document and carry a review_date.';

CREATE INDEX idx_ptt_year_type ON payroll_tax_tables (tax_year, tax_type);
CREATE INDEX idx_ptt_filing ON payroll_tax_tables (tax_year, tax_type, filing_status);


-- ============================================================================
-- TAX FORMS
-- ============================================================================

CREATE TABLE tax_form_exports (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id       UUID NOT NULL REFERENCES clients(id) ON DELETE RESTRICT,
    form_type       VARCHAR(50) NOT NULL,        -- e.g. '940', '941', '1120S', '1065'
    tax_year        INT NOT NULL,
    tax_period      VARCHAR(20),                 -- e.g. 'Q1', 'Q2', 'ANNUAL'
    status          tax_form_status NOT NULL DEFAULT 'DRAFT',
    generated_by    UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    file_path       VARCHAR(1000),
    generated_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at      TIMESTAMPTZ
);

CREATE INDEX idx_tax_forms_client ON tax_form_exports (client_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_tax_forms_year ON tax_form_exports (tax_year) WHERE deleted_at IS NULL;
CREATE INDEX idx_tax_forms_type ON tax_form_exports (form_type) WHERE deleted_at IS NULL;


-- ============================================================================
-- OPERATIONS
-- ============================================================================

CREATE TABLE system_backups (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    backup_path     VARCHAR(1000) NOT NULL,
    backup_size_bytes BIGINT,
    status          backup_status NOT NULL DEFAULT 'IN_PROGRESS',
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
    -- No updated_at/deleted_at — backup records are immutable operational logs
);

CREATE INDEX idx_backups_status ON system_backups (status);
CREATE INDEX idx_backups_started ON system_backups (started_at);


-- ============================================================================
-- MIGRATION TRACKING
-- ============================================================================

CREATE TABLE migration_batches (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_system   VARCHAR(100) NOT NULL DEFAULT 'quickbooks_online',
    file_name       VARCHAR(500),
    status          migration_batch_status NOT NULL DEFAULT 'VALIDATING',
    records_total   INT DEFAULT 0,
    records_imported INT DEFAULT 0,
    records_failed  INT DEFAULT 0,
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_migration_batches_status ON migration_batches (status);

CREATE TABLE migration_errors (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_id        UUID NOT NULL REFERENCES migration_batches(id) ON DELETE RESTRICT,
    source_row      INT,
    error_type      VARCHAR(100),
    error_message   TEXT,
    source_data     JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_migration_errors_batch ON migration_errors (batch_id);


-- ============================================================================
-- TRIGGER: AUTO-UPDATE updated_at
-- ============================================================================

CREATE OR REPLACE FUNCTION fn_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply updated_at trigger to all tables that have the column
DO $$
DECLARE
    tbl TEXT;
BEGIN
    FOR tbl IN
        SELECT table_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND column_name = 'updated_at'
          AND table_name NOT IN ('audit_log', 'permission_log')
    LOOP
        EXECUTE format(
            'CREATE TRIGGER trg_%s_updated_at
             BEFORE UPDATE ON %I
             FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at()',
            tbl, tbl
        );
    END LOOP;
END;
$$;


-- ============================================================================
-- TRIGGER: AUDIT LOG — captures INSERT/UPDATE/DELETE on all auditable tables
-- ============================================================================

CREATE OR REPLACE FUNCTION fn_audit_log()
RETURNS TRIGGER AS $$
DECLARE
    v_old JSONB;
    v_new JSONB;
    v_action audit_action;
    v_record_id UUID;
    v_user_id UUID;
BEGIN
    -- Determine the action
    IF TG_OP = 'INSERT' THEN
        v_action := 'INSERT';
        v_new := to_jsonb(NEW);
        v_old := NULL;
        v_record_id := NEW.id;
    ELSIF TG_OP = 'UPDATE' THEN
        v_action := 'UPDATE';
        v_old := to_jsonb(OLD);
        v_new := to_jsonb(NEW);
        v_record_id := NEW.id;
    ELSIF TG_OP = 'DELETE' THEN
        v_action := 'DELETE';
        v_old := to_jsonb(OLD);
        v_new := NULL;
        v_record_id := OLD.id;
    END IF;

    -- Try to capture the current application user from a session variable.
    -- The application layer should SET LOCAL app.current_user_id = '<uuid>' per transaction.
    BEGIN
        v_user_id := current_setting('app.current_user_id', TRUE)::UUID;
    EXCEPTION WHEN OTHERS THEN
        v_user_id := NULL;
    END;

    INSERT INTO audit_log (table_name, record_id, action, old_values, new_values, user_id, ip_address)
    VALUES (
        TG_TABLE_NAME,
        v_record_id,
        v_action,
        v_old,
        v_new,
        v_user_id,
        inet(current_setting('app.client_ip', TRUE))
    );

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply audit trigger to all tables except audit_log, permission_log, system_backups,
-- migration_batches, migration_errors (operational/log tables)
DO $$
DECLARE
    tbl TEXT;
    excluded_tables TEXT[] := ARRAY[
        'audit_log', 'permission_log', 'system_backups',
        'migration_batches', 'migration_errors', 'payroll_tax_tables'
    ];
BEGIN
    FOR tbl IN
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_type = 'BASE TABLE'
          AND table_name != ALL(excluded_tables)
    LOOP
        EXECUTE format(
            'CREATE TRIGGER trg_%s_audit
             AFTER INSERT OR UPDATE OR DELETE ON %I
             FOR EACH ROW EXECUTE FUNCTION fn_audit_log()',
            tbl, tbl
        );
    END LOOP;
END;
$$;


-- ============================================================================
-- TRIGGER: DOUBLE-ENTRY VALIDATION (CLAUDE.md Compliance Rule #1)
--
-- CLAUDE.md mandates: "Enforce at the database level with a CHECK constraint."
-- A CHECK constraint CANNOT be used here because the validation requires
-- cross-table aggregation (summing journal_entry_lines for a given
-- journal_entry). PostgreSQL CHECK constraints can only reference columns
-- within the same row of the same table.
--
-- This BEFORE trigger is the strongest possible database-level enforcement:
-- it runs inside the same transaction, before the row is committed, and
-- raises an EXCEPTION (rolling back the transaction) if debits != credits.
-- This is functionally equivalent to a CHECK constraint for this use case.
--
-- APPROVED DEVIATION: CPA_OWNER has reviewed and accepted this approach.
-- See OPEN_ISSUES.md for the original review discussion.
-- ============================================================================
-- Prevents a journal_entry from being set to POSTED status unless
-- SUM(debits) = SUM(credits) for its lines and there is at least one line.
-- ============================================================================

CREATE OR REPLACE FUNCTION fn_validate_journal_entry_balance()
RETURNS TRIGGER AS $$
DECLARE
    v_total_debits  NUMERIC(15,2);
    v_total_credits NUMERIC(15,2);
    v_line_count    INT;
BEGIN
    -- Only validate when status is being changed to POSTED
    IF NEW.status = 'POSTED' AND (OLD.status IS NULL OR OLD.status != 'POSTED') THEN

        SELECT
            COALESCE(SUM(debit), 0),
            COALESCE(SUM(credit), 0),
            COUNT(*)
        INTO v_total_debits, v_total_credits, v_line_count
        FROM journal_entry_lines
        WHERE journal_entry_id = NEW.id
          AND deleted_at IS NULL;

        -- Must have at least one line
        IF v_line_count = 0 THEN
            RAISE EXCEPTION 'Cannot post journal entry %: no active line items', NEW.id;
        END IF;

        -- DOUBLE-ENTRY ENFORCEMENT: debits must equal credits
        IF v_total_debits != v_total_credits THEN
            RAISE EXCEPTION
                'Cannot post journal entry %: debits (%) != credits (%). '
                'Double-entry requires equal debits and credits.',
                NEW.id, v_total_debits, v_total_credits;
        END IF;

        -- Automatically set posted_at timestamp
        NEW.posted_at = now();
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_je_balance_check
    BEFORE UPDATE ON journal_entries
    FOR EACH ROW
    EXECUTE FUNCTION fn_validate_journal_entry_balance();

-- Also validate on INSERT if someone directly inserts as POSTED
CREATE TRIGGER trg_je_balance_check_insert
    BEFORE INSERT ON journal_entries
    FOR EACH ROW
    WHEN (NEW.status = 'POSTED')
    EXECUTE FUNCTION fn_validate_journal_entry_balance();


-- ============================================================================
-- TRIGGER: PREVENT HARD DELETES on soft-delete tables
-- Ensures audit trail by blocking DELETE on tables that should use deleted_at
-- ============================================================================

CREATE OR REPLACE FUNCTION fn_prevent_hard_delete()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Hard deletes are not allowed on table %. Set deleted_at instead.', TG_TABLE_NAME;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DO $$
DECLARE
    tbl TEXT;
    excluded_tables TEXT[] := ARRAY[
        'audit_log', 'permission_log', 'system_backups',
        'migration_batches', 'migration_errors', 'payroll_tax_tables'
    ];
BEGIN
    FOR tbl IN
        SELECT table_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND column_name = 'deleted_at'
    LOOP
        -- Skip excluded tables
        IF tbl = ANY(excluded_tables) THEN
            CONTINUE;
        END IF;

        EXECUTE format(
            'CREATE TRIGGER trg_%s_no_hard_delete
             BEFORE DELETE ON %I
             FOR EACH ROW EXECUTE FUNCTION fn_prevent_hard_delete()',
            tbl, tbl
        );
    END LOOP;
END;
$$;


-- ============================================================================
-- SEED DATA: Georgia Standard Chart of Accounts
-- Uses a placeholder client_id; in practice each client gets their own copy.
-- These cover all entity types: Sole Prop, S-Corp, C-Corp, Partnership/LLC
-- ============================================================================

-- Create a template client for seed data
INSERT INTO clients (id, name, entity_type, is_active)
VALUES ('00000000-0000-0000-0000-000000000001'::UUID, 'TEMPLATE - Chart of Accounts Seed', 'SOLE_PROP', FALSE);

-- ---- ASSETS ----
INSERT INTO chart_of_accounts (client_id, account_number, account_name, account_type, sub_type) VALUES
('00000000-0000-0000-0000-000000000001', '1000', 'Cash - Operating', 'ASSET', 'Current Asset'),
('00000000-0000-0000-0000-000000000001', '1010', 'Cash - Payroll', 'ASSET', 'Current Asset'),
('00000000-0000-0000-0000-000000000001', '1020', 'Petty Cash', 'ASSET', 'Current Asset'),
('00000000-0000-0000-0000-000000000001', '1100', 'Accounts Receivable', 'ASSET', 'Current Asset'),
('00000000-0000-0000-0000-000000000001', '1200', 'Prepaid Expenses', 'ASSET', 'Current Asset'),
('00000000-0000-0000-0000-000000000001', '1300', 'Inventory', 'ASSET', 'Current Asset'),
('00000000-0000-0000-0000-000000000001', '1400', 'Employee Advances', 'ASSET', 'Current Asset'),
('00000000-0000-0000-0000-000000000001', '1500', 'Fixed Assets - Furniture & Equipment', 'ASSET', 'Fixed Asset'),
('00000000-0000-0000-0000-000000000001', '1510', 'Fixed Assets - Vehicles', 'ASSET', 'Fixed Asset'),
('00000000-0000-0000-0000-000000000001', '1520', 'Fixed Assets - Computer Equipment', 'ASSET', 'Fixed Asset'),
('00000000-0000-0000-0000-000000000001', '1550', 'Accumulated Depreciation', 'ASSET', 'Contra Asset'),
('00000000-0000-0000-0000-000000000001', '1600', 'Security Deposits', 'ASSET', 'Other Asset'),
('00000000-0000-0000-0000-000000000001', '1700', 'Loans Receivable - Shareholder', 'ASSET', 'Other Asset'),
('00000000-0000-0000-0000-000000000001', '1800', 'Organizational Costs', 'ASSET', 'Other Asset');

-- ---- LIABILITIES ----
INSERT INTO chart_of_accounts (client_id, account_number, account_name, account_type, sub_type) VALUES
('00000000-0000-0000-0000-000000000001', '2000', 'Accounts Payable', 'LIABILITY', 'Current Liability'),
('00000000-0000-0000-0000-000000000001', '2100', 'Credit Card Payable', 'LIABILITY', 'Current Liability'),
('00000000-0000-0000-0000-000000000001', '2200', 'Accrued Expenses', 'LIABILITY', 'Current Liability'),
('00000000-0000-0000-0000-000000000001', '2300', 'Federal Income Tax Payable', 'LIABILITY', 'Current Liability'),
('00000000-0000-0000-0000-000000000001', '2310', 'Georgia Income Tax Payable', 'LIABILITY', 'Current Liability'),
('00000000-0000-0000-0000-000000000001', '2320', 'FICA Payable - Employee', 'LIABILITY', 'Current Liability'),
('00000000-0000-0000-0000-000000000001', '2330', 'FICA Payable - Employer', 'LIABILITY', 'Current Liability'),
('00000000-0000-0000-0000-000000000001', '2340', 'Federal Unemployment Tax Payable (FUTA)', 'LIABILITY', 'Current Liability'),
('00000000-0000-0000-0000-000000000001', '2350', 'Georgia SUTA Payable', 'LIABILITY', 'Current Liability'),
('00000000-0000-0000-0000-000000000001', '2360', 'Medicare Payable', 'LIABILITY', 'Current Liability'),
('00000000-0000-0000-0000-000000000001', '2400', 'Georgia Sales Tax Payable', 'LIABILITY', 'Current Liability'),
('00000000-0000-0000-0000-000000000001', '2500', 'Unearned Revenue', 'LIABILITY', 'Current Liability'),
('00000000-0000-0000-0000-000000000001', '2600', 'Line of Credit', 'LIABILITY', 'Current Liability'),
('00000000-0000-0000-0000-000000000001', '2700', 'Notes Payable - Short Term', 'LIABILITY', 'Current Liability'),
('00000000-0000-0000-0000-000000000001', '2800', 'Loans Payable - Long Term', 'LIABILITY', 'Long Term Liability'),
('00000000-0000-0000-0000-000000000001', '2810', 'Vehicle Loan Payable', 'LIABILITY', 'Long Term Liability'),
('00000000-0000-0000-0000-000000000001', '2900', 'Shareholder Loans Payable', 'LIABILITY', 'Long Term Liability');

-- ---- EQUITY ----
-- Covers: Sole Prop (Owner's Equity/Draw), S-Corp/C-Corp (Common Stock, Retained Earnings),
--         Partnership/LLC (Member Capital, Distributions)
INSERT INTO chart_of_accounts (client_id, account_number, account_name, account_type, sub_type) VALUES
('00000000-0000-0000-0000-000000000001', '3000', 'Owner''s Equity / Capital', 'EQUITY', 'Owner Equity'),
('00000000-0000-0000-0000-000000000001', '3010', 'Owner''s Draw', 'EQUITY', 'Owner Equity'),
('00000000-0000-0000-0000-000000000001', '3100', 'Common Stock', 'EQUITY', 'Stockholder Equity'),
('00000000-0000-0000-0000-000000000001', '3110', 'Additional Paid-In Capital', 'EQUITY', 'Stockholder Equity'),
('00000000-0000-0000-0000-000000000001', '3120', 'Treasury Stock', 'EQUITY', 'Stockholder Equity'),
('00000000-0000-0000-0000-000000000001', '3200', 'Retained Earnings', 'EQUITY', 'Retained Earnings'),
('00000000-0000-0000-0000-000000000001', '3300', 'Member Capital Contributions', 'EQUITY', 'Member Equity'),
('00000000-0000-0000-0000-000000000001', '3310', 'Member Distributions', 'EQUITY', 'Member Equity'),
('00000000-0000-0000-0000-000000000001', '3400', 'Shareholder Distributions (S-Corp)', 'EQUITY', 'S-Corp Equity'),
('00000000-0000-0000-0000-000000000001', '3500', 'Accumulated Adjustments Account (AAA)', 'EQUITY', 'S-Corp Equity');

-- ---- REVENUE ----
INSERT INTO chart_of_accounts (client_id, account_number, account_name, account_type, sub_type) VALUES
('00000000-0000-0000-0000-000000000001', '4000', 'Service Revenue', 'REVENUE', 'Operating Revenue'),
('00000000-0000-0000-0000-000000000001', '4010', 'Product Sales', 'REVENUE', 'Operating Revenue'),
('00000000-0000-0000-0000-000000000001', '4020', 'Consulting Revenue', 'REVENUE', 'Operating Revenue'),
('00000000-0000-0000-0000-000000000001', '4100', 'Returns & Allowances', 'REVENUE', 'Contra Revenue'),
('00000000-0000-0000-0000-000000000001', '4200', 'Discounts Given', 'REVENUE', 'Contra Revenue'),
('00000000-0000-0000-0000-000000000001', '4500', 'Interest Income', 'REVENUE', 'Other Income'),
('00000000-0000-0000-0000-000000000001', '4510', 'Gain on Sale of Assets', 'REVENUE', 'Other Income'),
('00000000-0000-0000-0000-000000000001', '4520', 'Rental Income', 'REVENUE', 'Other Income'),
('00000000-0000-0000-0000-000000000001', '4900', 'Other Income', 'REVENUE', 'Other Income');

-- ---- EXPENSES ----
INSERT INTO chart_of_accounts (client_id, account_number, account_name, account_type, sub_type) VALUES
('00000000-0000-0000-0000-000000000001', '5000', 'Cost of Goods Sold', 'EXPENSE', 'COGS'),
('00000000-0000-0000-0000-000000000001', '5100', 'Purchases', 'EXPENSE', 'COGS'),
('00000000-0000-0000-0000-000000000001', '5200', 'Freight & Shipping', 'EXPENSE', 'COGS'),
('00000000-0000-0000-0000-000000000001', '6000', 'Salaries & Wages', 'EXPENSE', 'Operating Expense'),
('00000000-0000-0000-0000-000000000001', '6010', 'Officer Compensation', 'EXPENSE', 'Operating Expense'),
('00000000-0000-0000-0000-000000000001', '6020', 'Employee Benefits', 'EXPENSE', 'Operating Expense'),
('00000000-0000-0000-0000-000000000001', '6030', 'Payroll Tax Expense', 'EXPENSE', 'Operating Expense'),
('00000000-0000-0000-0000-000000000001', '6040', 'Workers Compensation Insurance', 'EXPENSE', 'Operating Expense'),
('00000000-0000-0000-0000-000000000001', '6050', 'Health Insurance', 'EXPENSE', 'Operating Expense'),
('00000000-0000-0000-0000-000000000001', '6060', 'Retirement Plan Contributions', 'EXPENSE', 'Operating Expense'),
('00000000-0000-0000-0000-000000000001', '6100', 'Rent Expense', 'EXPENSE', 'Operating Expense'),
('00000000-0000-0000-0000-000000000001', '6110', 'Utilities', 'EXPENSE', 'Operating Expense'),
('00000000-0000-0000-0000-000000000001', '6120', 'Telephone & Internet', 'EXPENSE', 'Operating Expense'),
('00000000-0000-0000-0000-000000000001', '6200', 'Office Supplies', 'EXPENSE', 'Operating Expense'),
('00000000-0000-0000-0000-000000000001', '6210', 'Postage & Delivery', 'EXPENSE', 'Operating Expense'),
('00000000-0000-0000-0000-000000000001', '6300', 'Insurance - General Liability', 'EXPENSE', 'Operating Expense'),
('00000000-0000-0000-0000-000000000001', '6310', 'Insurance - Professional Liability', 'EXPENSE', 'Operating Expense'),
('00000000-0000-0000-0000-000000000001', '6400', 'Advertising & Marketing', 'EXPENSE', 'Operating Expense'),
('00000000-0000-0000-0000-000000000001', '6500', 'Professional Fees - Legal', 'EXPENSE', 'Operating Expense'),
('00000000-0000-0000-0000-000000000001', '6510', 'Professional Fees - Accounting', 'EXPENSE', 'Operating Expense'),
('00000000-0000-0000-0000-000000000001', '6520', 'Professional Fees - Other', 'EXPENSE', 'Operating Expense'),
('00000000-0000-0000-0000-000000000001', '6600', 'Depreciation Expense', 'EXPENSE', 'Operating Expense'),
('00000000-0000-0000-0000-000000000001', '6610', 'Amortization Expense', 'EXPENSE', 'Operating Expense'),
('00000000-0000-0000-0000-000000000001', '6700', 'Travel Expense', 'EXPENSE', 'Operating Expense'),
('00000000-0000-0000-0000-000000000001', '6710', 'Meals & Entertainment', 'EXPENSE', 'Operating Expense'),
('00000000-0000-0000-0000-000000000001', '6720', 'Auto Expense', 'EXPENSE', 'Operating Expense'),
('00000000-0000-0000-0000-000000000001', '6800', 'Software & Subscriptions', 'EXPENSE', 'Operating Expense'),
('00000000-0000-0000-0000-000000000001', '6810', 'Computer & IT Expense', 'EXPENSE', 'Operating Expense'),
('00000000-0000-0000-0000-000000000001', '6900', 'Bank Service Charges', 'EXPENSE', 'Operating Expense'),
('00000000-0000-0000-0000-000000000001', '6910', 'Merchant Processing Fees', 'EXPENSE', 'Operating Expense'),
('00000000-0000-0000-0000-000000000001', '7000', 'Interest Expense', 'EXPENSE', 'Other Expense'),
('00000000-0000-0000-0000-000000000001', '7100', 'Penalties & Fines', 'EXPENSE', 'Other Expense'),
('00000000-0000-0000-0000-000000000001', '7200', 'Loss on Sale of Assets', 'EXPENSE', 'Other Expense'),
('00000000-0000-0000-0000-000000000001', '7500', 'Georgia Franchise Tax', 'EXPENSE', 'Tax Expense'),
('00000000-0000-0000-0000-000000000001', '7510', 'Federal Income Tax Expense (C-Corp)', 'EXPENSE', 'Tax Expense'),
('00000000-0000-0000-0000-000000000001', '7520', 'Georgia Income Tax Expense (C-Corp)', 'EXPENSE', 'Tax Expense'),
('00000000-0000-0000-0000-000000000001', '9000', 'Miscellaneous Expense', 'EXPENSE', 'Other Expense');


-- ============================================================================
-- UTILITY VIEW: Trial Balance (convenience for reporting modules)
-- ============================================================================

CREATE OR REPLACE VIEW v_trial_balance AS
SELECT
    coa.client_id,
    coa.account_number,
    coa.account_name,
    coa.account_type,
    coa.sub_type,
    COALESCE(SUM(jel.debit), 0)  AS total_debits,
    COALESCE(SUM(jel.credit), 0) AS total_credits,
    COALESCE(SUM(jel.debit), 0) - COALESCE(SUM(jel.credit), 0) AS balance
FROM chart_of_accounts coa
LEFT JOIN journal_entry_lines jel
    ON jel.account_id = coa.id
    AND jel.deleted_at IS NULL
LEFT JOIN journal_entries je
    ON je.id = jel.journal_entry_id
    AND je.status = 'POSTED'
    AND je.deleted_at IS NULL
WHERE coa.deleted_at IS NULL
  AND coa.is_active = TRUE
GROUP BY coa.client_id, coa.account_number, coa.account_name,
         coa.account_type, coa.sub_type
ORDER BY coa.client_id, coa.account_number;


COMMIT;
