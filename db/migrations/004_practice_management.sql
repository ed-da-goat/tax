-- Migration 004: Practice Management — Phases 9-12
-- Time tracking, billing, workflow, client portal, analytics, fixed assets
-- Run after all 003 migrations

-- ============================================================
-- PM1: TIME TRACKING
-- ============================================================
CREATE TYPE time_entry_status AS ENUM ('DRAFT', 'SUBMITTED', 'APPROVED', 'BILLED');

CREATE TABLE IF NOT EXISTS time_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE RESTRICT,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    -- Optional links
    workflow_task_id UUID,  -- FK added after workflow_tasks table created
    -- Time data
    date DATE NOT NULL,
    duration_minutes INTEGER NOT NULL CHECK (duration_minutes > 0),
    description TEXT,
    -- Billing
    is_billable BOOLEAN NOT NULL DEFAULT TRUE,
    hourly_rate NUMERIC(10,2),
    amount NUMERIC(12,2),  -- auto-calc: duration * rate
    status time_entry_status NOT NULL DEFAULT 'DRAFT',
    -- Service categorization
    service_type VARCHAR(100),  -- e.g. 'Tax Prep', 'Bookkeeping', 'Advisory'
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_time_entries_client ON time_entries(client_id);
CREATE INDEX idx_time_entries_user ON time_entries(user_id);
CREATE INDEX idx_time_entries_date ON time_entries(date);
CREATE INDEX idx_time_entries_status ON time_entries(status);

-- Staff rate table
CREATE TABLE IF NOT EXISTS staff_rates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    rate_name VARCHAR(100) NOT NULL DEFAULT 'Standard',
    hourly_rate NUMERIC(10,2) NOT NULL,
    effective_date DATE NOT NULL,
    end_date DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    UNIQUE(user_id, rate_name, effective_date)
);

-- Timer sessions (active timers)
CREATE TABLE IF NOT EXISTS timer_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    client_id UUID REFERENCES clients(id) ON DELETE RESTRICT,
    description TEXT,
    service_type VARCHAR(100),
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    stopped_at TIMESTAMPTZ,
    is_running BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- PM2: CLIENT INVOICING & BILLING (firm-to-client service invoices)
-- Note: This is SEPARATE from existing AR invoices (client's customer invoices)
-- These are invoices FROM the CPA firm TO the client for services rendered
-- ============================================================
CREATE TYPE service_invoice_status AS ENUM ('DRAFT', 'SENT', 'VIEWED', 'PAID', 'PARTIAL', 'OVERDUE', 'VOID');
CREATE TYPE payment_method AS ENUM ('CHECK', 'ACH', 'CREDIT_CARD', 'CASH', 'OTHER');

CREATE TABLE IF NOT EXISTS service_invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE RESTRICT,
    invoice_number VARCHAR(50) NOT NULL,
    -- Dates
    invoice_date DATE NOT NULL,
    due_date DATE NOT NULL,
    -- Amounts
    subtotal NUMERIC(12,2) NOT NULL DEFAULT 0,
    discount_amount NUMERIC(12,2) NOT NULL DEFAULT 0,
    tax_amount NUMERIC(12,2) NOT NULL DEFAULT 0,
    total_amount NUMERIC(12,2) NOT NULL DEFAULT 0,
    amount_paid NUMERIC(12,2) NOT NULL DEFAULT 0,
    balance_due NUMERIC(12,2) NOT NULL DEFAULT 0,
    -- Status
    status service_invoice_status NOT NULL DEFAULT 'DRAFT',
    -- Notes
    notes TEXT,
    terms TEXT,
    -- Recurring
    is_recurring BOOLEAN NOT NULL DEFAULT FALSE,
    recurrence_interval VARCHAR(20),  -- 'WEEKLY', 'MONTHLY', 'QUARTERLY', 'ANNUALLY'
    next_recurrence_date DATE,
    -- Engagement link
    engagement_id UUID,  -- FK added after engagements table
    -- Timestamps
    sent_at TIMESTAMPTZ,
    viewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_service_invoices_client ON service_invoices(client_id);
CREATE INDEX idx_service_invoices_status ON service_invoices(status);

CREATE TABLE IF NOT EXISTS service_invoice_lines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id UUID NOT NULL REFERENCES service_invoices(id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    quantity NUMERIC(10,2) NOT NULL DEFAULT 1,
    unit_price NUMERIC(10,2) NOT NULL,
    amount NUMERIC(12,2) NOT NULL,
    -- Link to time entries
    time_entry_id UUID REFERENCES time_entries(id),
    service_type VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS service_invoice_payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id UUID NOT NULL REFERENCES service_invoices(id) ON DELETE RESTRICT,
    payment_date DATE NOT NULL,
    amount NUMERIC(12,2) NOT NULL CHECK (amount > 0),
    payment_method payment_method NOT NULL DEFAULT 'CHECK',
    reference_number VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- PM3: ENGAGEMENT LETTERS & PROPOSALS
-- ============================================================
CREATE TYPE engagement_status AS ENUM ('DRAFT', 'SENT', 'VIEWED', 'SIGNED', 'DECLINED', 'EXPIRED');

CREATE TABLE IF NOT EXISTS engagements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE RESTRICT,
    -- Content
    title VARCHAR(255) NOT NULL,
    engagement_type VARCHAR(100) NOT NULL,  -- 'Tax Prep', 'Bookkeeping', 'Audit', 'Advisory'
    description TEXT,
    terms_and_conditions TEXT,
    -- Pricing
    fee_type VARCHAR(20) NOT NULL DEFAULT 'FIXED',  -- 'FIXED', 'HOURLY', 'RETAINER'
    fixed_fee NUMERIC(12,2),
    hourly_rate NUMERIC(10,2),
    estimated_hours NUMERIC(10,2),
    retainer_amount NUMERIC(12,2),
    -- Period
    start_date DATE,
    end_date DATE,
    tax_year INTEGER,
    -- Status
    status engagement_status NOT NULL DEFAULT 'DRAFT',
    sent_at TIMESTAMPTZ,
    signed_at TIMESTAMPTZ,
    signed_by VARCHAR(255),
    signature_data TEXT,  -- base64 signature image
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_engagements_client ON engagements(client_id);
CREATE INDEX idx_engagements_status ON engagements(status);

-- Now add FK from service_invoices to engagements
ALTER TABLE service_invoices
    ADD CONSTRAINT fk_service_invoices_engagement
    FOREIGN KEY (engagement_id) REFERENCES engagements(id);

-- ============================================================
-- PM4: CONTACTS / CRM
-- ============================================================
CREATE TABLE IF NOT EXISTS contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE RESTRICT,
    -- Basic info
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(20),
    mobile VARCHAR(20),
    -- Role/relationship
    title VARCHAR(100),  -- 'Owner', 'CFO', 'Bookkeeper'
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    -- Address
    address VARCHAR(500),
    city VARCHAR(100),
    state VARCHAR(2),
    zip VARCHAR(10),
    -- Notes
    notes TEXT,
    -- Tags stored as JSON array
    tags JSONB NOT NULL DEFAULT '[]',
    -- Custom fields stored as JSON object
    custom_fields JSONB NOT NULL DEFAULT '{}',
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_contacts_client ON contacts(client_id);
CREATE INDEX idx_contacts_email ON contacts(email);

-- ============================================================
-- WF1-WF4: WORKFLOW ENGINE
-- ============================================================
CREATE TYPE workflow_status AS ENUM ('TEMPLATE', 'ACTIVE', 'COMPLETED', 'ARCHIVED');
CREATE TYPE task_status AS ENUM ('NOT_STARTED', 'IN_PROGRESS', 'WAITING_CLIENT', 'IN_REVIEW', 'COMPLETED', 'BLOCKED');
CREATE TYPE task_priority AS ENUM ('LOW', 'MEDIUM', 'HIGH', 'URGENT');
CREATE TYPE recurrence_type AS ENUM ('NONE', 'WEEKLY', 'BIWEEKLY', 'MONTHLY', 'QUARTERLY', 'ANNUALLY');

-- Workflow templates / active workflows
CREATE TABLE IF NOT EXISTS workflows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID REFERENCES clients(id) ON DELETE RESTRICT,  -- NULL for templates
    -- Info
    name VARCHAR(255) NOT NULL,
    description TEXT,
    workflow_type VARCHAR(100) NOT NULL,  -- 'Tax Prep', 'Bookkeeping', 'Onboarding', 'Audit'
    -- Status
    status workflow_status NOT NULL DEFAULT 'TEMPLATE',
    -- Template info
    is_template BOOLEAN NOT NULL DEFAULT FALSE,
    template_id UUID REFERENCES workflows(id),  -- which template this was created from
    -- Assignment
    assigned_to UUID REFERENCES users(id),
    -- Dates
    due_date DATE,
    start_date DATE,
    completed_at TIMESTAMPTZ,
    -- Recurrence
    recurrence recurrence_type NOT NULL DEFAULT 'NONE',
    next_recurrence_date DATE,
    -- Tax year (for tax workflows)
    tax_year INTEGER,
    -- Kanban stage
    current_stage VARCHAR(100) NOT NULL DEFAULT 'Not Started',
    stage_order INTEGER NOT NULL DEFAULT 0,
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_workflows_client ON workflows(client_id);
CREATE INDEX idx_workflows_status ON workflows(status);
CREATE INDEX idx_workflows_assigned ON workflows(assigned_to);
CREATE INDEX idx_workflows_due ON workflows(due_date);
CREATE INDEX idx_workflows_template ON workflows(is_template);

-- Workflow stages (Kanban columns) per workflow type
CREATE TABLE IF NOT EXISTS workflow_stages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_type VARCHAR(100) NOT NULL,
    stage_name VARCHAR(100) NOT NULL,
    stage_order INTEGER NOT NULL,
    color VARCHAR(7) DEFAULT '#6B7280',  -- hex color
    is_completion_stage BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(workflow_type, stage_name)
);

-- Workflow tasks (subtasks within a workflow)
CREATE TABLE IF NOT EXISTS workflow_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
    -- Task info
    title VARCHAR(255) NOT NULL,
    description TEXT,
    -- Assignment
    assigned_to UUID REFERENCES users(id),
    -- Status
    status task_status NOT NULL DEFAULT 'NOT_STARTED',
    priority task_priority NOT NULL DEFAULT 'MEDIUM',
    -- Dates
    due_date DATE,
    completed_at TIMESTAMPTZ,
    -- Ordering
    sort_order INTEGER NOT NULL DEFAULT 0,
    -- Dependencies
    depends_on UUID REFERENCES workflow_tasks(id),
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_workflow_tasks_workflow ON workflow_tasks(workflow_id);
CREATE INDEX idx_workflow_tasks_assigned ON workflow_tasks(assigned_to);
CREATE INDEX idx_workflow_tasks_status ON workflow_tasks(status);

-- Now add FK from time_entries to workflow_tasks
ALTER TABLE time_entries
    ADD CONSTRAINT fk_time_entries_task
    FOREIGN KEY (workflow_task_id) REFERENCES workflow_tasks(id);

-- Task comments / activity log
CREATE TABLE IF NOT EXISTS task_comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES workflow_tasks(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Reminders / notifications
CREATE TYPE reminder_type AS ENUM ('DEADLINE', 'FOLLOW_UP', 'OVERDUE', 'CUSTOM');
CREATE TYPE reminder_channel AS ENUM ('IN_APP', 'EMAIL');

CREATE TABLE IF NOT EXISTS reminders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    -- Target
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    client_id UUID REFERENCES clients(id),
    workflow_id UUID REFERENCES workflows(id),
    task_id UUID REFERENCES workflow_tasks(id),
    -- Reminder info
    reminder_type reminder_type NOT NULL,
    channel reminder_channel NOT NULL DEFAULT 'IN_APP',
    title VARCHAR(255) NOT NULL,
    message TEXT,
    -- Schedule
    remind_at TIMESTAMPTZ NOT NULL,
    is_sent BOOLEAN NOT NULL DEFAULT FALSE,
    sent_at TIMESTAMPTZ,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    read_at TIMESTAMPTZ,
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_reminders_user ON reminders(user_id);
CREATE INDEX idx_reminders_remind_at ON reminders(remind_at);
CREATE INDEX idx_reminders_sent ON reminders(is_sent);

-- Due date calendar entries
CREATE TABLE IF NOT EXISTS due_dates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID REFERENCES clients(id),
    -- Date info
    title VARCHAR(255) NOT NULL,
    due_date DATE NOT NULL,
    form_type VARCHAR(50),  -- 'G-7', '941', '1120-S', etc.
    filing_type VARCHAR(50),  -- 'ORIGINAL', 'EXTENSION', 'AMENDED'
    tax_year INTEGER,
    -- Status
    is_completed BOOLEAN NOT NULL DEFAULT FALSE,
    completed_at TIMESTAMPTZ,
    completed_by UUID REFERENCES users(id),
    -- Notes
    notes TEXT,
    -- Auto-remind days before
    remind_days_before INTEGER DEFAULT 7,
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_due_dates_date ON due_dates(due_date);
CREATE INDEX idx_due_dates_client ON due_dates(client_id);

-- ============================================================
-- CP1-CP4: CLIENT PORTAL
-- ============================================================

-- Client portal users (separate from staff users)
CREATE TABLE IF NOT EXISTS portal_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE RESTRICT,
    contact_id UUID REFERENCES contacts(id),
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_login_at TIMESTAMPTZ,
    -- Magic link support
    magic_token VARCHAR(255),
    magic_token_expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_portal_users_client ON portal_users(client_id);
CREATE INDEX idx_portal_users_email ON portal_users(email);

-- Secure messages (firm <-> client communication)
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE RESTRICT,
    -- Thread
    thread_id UUID,  -- NULL = start of thread, else references parent message
    subject VARCHAR(255),
    body TEXT NOT NULL,
    -- Sender
    sender_type VARCHAR(10) NOT NULL CHECK (sender_type IN ('STAFF', 'CLIENT')),
    sender_user_id UUID REFERENCES users(id),         -- if STAFF
    sender_portal_user_id UUID REFERENCES portal_users(id),  -- if CLIENT
    -- Read status
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    read_at TIMESTAMPTZ,
    -- Attachments
    has_attachments BOOLEAN NOT NULL DEFAULT FALSE,
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_messages_client ON messages(client_id);
CREATE INDEX idx_messages_thread ON messages(thread_id);
CREATE INDEX idx_messages_unread ON messages(is_read) WHERE is_read = FALSE;

-- Message attachments
CREATE TABLE IF NOT EXISTS message_attachments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    file_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size INTEGER,
    mime_type VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Client questionnaires / organizers
CREATE TYPE questionnaire_status AS ENUM ('DRAFT', 'SENT', 'IN_PROGRESS', 'SUBMITTED', 'REVIEWED');

CREATE TABLE IF NOT EXISTS questionnaires (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE RESTRICT,
    -- Info
    title VARCHAR(255) NOT NULL,
    description TEXT,
    questionnaire_type VARCHAR(100) NOT NULL,  -- 'Tax Organizer', 'New Client Intake', 'Document Request'
    tax_year INTEGER,
    -- Status
    status questionnaire_status NOT NULL DEFAULT 'DRAFT',
    sent_at TIMESTAMPTZ,
    submitted_at TIMESTAMPTZ,
    reviewed_at TIMESTAMPTZ,
    reviewed_by UUID REFERENCES users(id),
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_questionnaires_client ON questionnaires(client_id);
CREATE INDEX idx_questionnaires_status ON questionnaires(status);

-- Questionnaire questions
CREATE TYPE question_type AS ENUM ('TEXT', 'TEXTAREA', 'NUMBER', 'DATE', 'YES_NO', 'SELECT', 'MULTI_SELECT', 'FILE_UPLOAD');

CREATE TABLE IF NOT EXISTS questionnaire_questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    questionnaire_id UUID NOT NULL REFERENCES questionnaires(id) ON DELETE CASCADE,
    question_text TEXT NOT NULL,
    question_type question_type NOT NULL DEFAULT 'TEXT',
    is_required BOOLEAN NOT NULL DEFAULT FALSE,
    sort_order INTEGER NOT NULL DEFAULT 0,
    options JSONB,  -- for SELECT/MULTI_SELECT types
    section VARCHAR(100),  -- group questions into sections
    help_text TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Questionnaire responses
CREATE TABLE IF NOT EXISTS questionnaire_responses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_id UUID NOT NULL REFERENCES questionnaire_questions(id) ON DELETE CASCADE,
    response_text TEXT,
    response_data JSONB,  -- for complex responses (multi-select, file refs)
    responded_by UUID REFERENCES portal_users(id),
    responded_at TIMESTAMPTZ DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- E-Signature requests
CREATE TYPE signature_status AS ENUM ('PENDING', 'SIGNED', 'DECLINED', 'EXPIRED');

CREATE TABLE IF NOT EXISTS signature_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE RESTRICT,
    -- Document to sign
    document_id UUID REFERENCES documents(id),
    engagement_id UUID REFERENCES engagements(id),
    -- Signer info
    signer_name VARCHAR(255) NOT NULL,
    signer_email VARCHAR(255) NOT NULL,
    portal_user_id UUID REFERENCES portal_users(id),
    -- Status
    status signature_status NOT NULL DEFAULT 'PENDING',
    -- Signature data
    signature_data TEXT,  -- base64 encoded signature image
    signed_at TIMESTAMPTZ,
    ip_address VARCHAR(45),
    -- Expiry
    expires_at TIMESTAMPTZ,
    -- Token for signing link
    signing_token VARCHAR(255) NOT NULL UNIQUE,
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_signature_requests_client ON signature_requests(client_id);
CREATE INDEX idx_signature_requests_status ON signature_requests(status);
CREATE INDEX idx_signature_requests_token ON signature_requests(signing_token);

-- ============================================================
-- AN1: FIRM ANALYTICS (views/materialized views)
-- ============================================================

-- Service types lookup
CREATE TABLE IF NOT EXISTS service_types (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    default_hourly_rate NUMERIC(10,2),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Insert default service types
INSERT INTO service_types (name, description, default_hourly_rate) VALUES
    ('Tax Preparation', 'Individual and business tax return preparation', 250.00),
    ('Bookkeeping', 'Monthly bookkeeping and reconciliation', 150.00),
    ('Payroll Processing', 'Payroll calculation, filing, and payment', 125.00),
    ('Advisory', 'Tax planning and business advisory services', 300.00),
    ('Audit & Assurance', 'Financial statement audit and review', 275.00),
    ('Entity Formation', 'Business entity setup and registration', 200.00),
    ('IRS Representation', 'IRS audit and collections representation', 350.00),
    ('Sales Tax', 'Sales tax return preparation and filing', 125.00)
ON CONFLICT (name) DO NOTHING;

-- ============================================================
-- AN3: FIXED ASSET MANAGEMENT
-- ============================================================
CREATE TYPE depreciation_method AS ENUM ('STRAIGHT_LINE', 'MACRS_GDS', 'MACRS_ADS', 'SECTION_179', 'BONUS', 'NONE');
CREATE TYPE asset_status AS ENUM ('ACTIVE', 'FULLY_DEPRECIATED', 'DISPOSED', 'TRANSFERRED');

CREATE TABLE IF NOT EXISTS fixed_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE RESTRICT,
    -- Asset info
    asset_name VARCHAR(255) NOT NULL,
    asset_number VARCHAR(50),
    description TEXT,
    category VARCHAR(100),  -- 'Office Equipment', 'Vehicles', 'Furniture', 'Buildings', etc.
    -- Acquisition
    acquisition_date DATE NOT NULL,
    acquisition_cost NUMERIC(14,2) NOT NULL,
    -- Depreciation
    depreciation_method depreciation_method NOT NULL DEFAULT 'MACRS_GDS',
    useful_life_years INTEGER,
    salvage_value NUMERIC(14,2) NOT NULL DEFAULT 0,
    macrs_class VARCHAR(20),  -- '3-year', '5-year', '7-year', '15-year', '27.5-year', '39-year'
    bonus_depreciation_pct NUMERIC(5,2) DEFAULT 0,
    section_179_amount NUMERIC(14,2) DEFAULT 0,
    -- Current state
    accumulated_depreciation NUMERIC(14,2) NOT NULL DEFAULT 0,
    book_value NUMERIC(14,2) NOT NULL,
    status asset_status NOT NULL DEFAULT 'ACTIVE',
    -- Disposal
    disposal_date DATE,
    disposal_amount NUMERIC(14,2),
    disposal_method VARCHAR(50),  -- 'SOLD', 'SCRAPPED', 'DONATED', 'TRADED'
    gain_loss NUMERIC(14,2),
    -- GL accounts
    asset_account_id UUID REFERENCES chart_of_accounts(id),
    depreciation_expense_account_id UUID REFERENCES chart_of_accounts(id),
    accumulated_depreciation_account_id UUID REFERENCES chart_of_accounts(id),
    -- Location/tracking
    location VARCHAR(255),
    serial_number VARCHAR(100),
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_fixed_assets_client ON fixed_assets(client_id);
CREATE INDEX idx_fixed_assets_status ON fixed_assets(status);

-- Depreciation schedule entries (pre-calculated per period)
CREATE TABLE IF NOT EXISTS depreciation_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_id UUID NOT NULL REFERENCES fixed_assets(id) ON DELETE CASCADE,
    -- Period
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    fiscal_year INTEGER NOT NULL,
    -- Amounts
    depreciation_amount NUMERIC(14,2) NOT NULL,
    accumulated_total NUMERIC(14,2) NOT NULL,
    book_value_end NUMERIC(14,2) NOT NULL,
    -- Posting
    is_posted BOOLEAN NOT NULL DEFAULT FALSE,
    journal_entry_id UUID REFERENCES journal_entries(id),
    posted_at TIMESTAMPTZ,
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_depreciation_entries_asset ON depreciation_entries(asset_id);
CREATE INDEX idx_depreciation_entries_year ON depreciation_entries(fiscal_year);

-- ============================================================
-- AN2: BUDGETS
-- ============================================================
CREATE TABLE IF NOT EXISTS budgets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE RESTRICT,
    name VARCHAR(255) NOT NULL,
    fiscal_year INTEGER NOT NULL,
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    UNIQUE(client_id, name, fiscal_year)
);

CREATE TABLE IF NOT EXISTS budget_lines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    budget_id UUID NOT NULL REFERENCES budgets(id) ON DELETE CASCADE,
    account_id UUID NOT NULL REFERENCES chart_of_accounts(id),
    -- Monthly amounts
    month_1 NUMERIC(14,2) NOT NULL DEFAULT 0,
    month_2 NUMERIC(14,2) NOT NULL DEFAULT 0,
    month_3 NUMERIC(14,2) NOT NULL DEFAULT 0,
    month_4 NUMERIC(14,2) NOT NULL DEFAULT 0,
    month_5 NUMERIC(14,2) NOT NULL DEFAULT 0,
    month_6 NUMERIC(14,2) NOT NULL DEFAULT 0,
    month_7 NUMERIC(14,2) NOT NULL DEFAULT 0,
    month_8 NUMERIC(14,2) NOT NULL DEFAULT 0,
    month_9 NUMERIC(14,2) NOT NULL DEFAULT 0,
    month_10 NUMERIC(14,2) NOT NULL DEFAULT 0,
    month_11 NUMERIC(14,2) NOT NULL DEFAULT 0,
    month_12 NUMERIC(14,2) NOT NULL DEFAULT 0,
    annual_total NUMERIC(14,2) NOT NULL DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_budget_lines_budget ON budget_lines(budget_id);

-- ============================================================
-- AUDIT TRIGGERS for all new tables
-- ============================================================
CREATE TRIGGER trg_time_entries_audit
    AFTER INSERT OR UPDATE OR DELETE ON time_entries
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log();

CREATE TRIGGER trg_staff_rates_audit
    AFTER INSERT OR UPDATE OR DELETE ON staff_rates
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log();

CREATE TRIGGER trg_service_invoices_audit
    AFTER INSERT OR UPDATE OR DELETE ON service_invoices
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log();

CREATE TRIGGER trg_service_invoice_lines_audit
    AFTER INSERT OR UPDATE OR DELETE ON service_invoice_lines
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log();

CREATE TRIGGER trg_service_invoice_payments_audit
    AFTER INSERT OR UPDATE OR DELETE ON service_invoice_payments
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log();

CREATE TRIGGER trg_engagements_audit
    AFTER INSERT OR UPDATE OR DELETE ON engagements
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log();

CREATE TRIGGER trg_contacts_audit
    AFTER INSERT OR UPDATE OR DELETE ON contacts
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log();

CREATE TRIGGER trg_workflows_audit
    AFTER INSERT OR UPDATE OR DELETE ON workflows
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log();

CREATE TRIGGER trg_workflow_tasks_audit
    AFTER INSERT OR UPDATE OR DELETE ON workflow_tasks
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log();

CREATE TRIGGER trg_task_comments_audit
    AFTER INSERT OR UPDATE OR DELETE ON task_comments
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log();

CREATE TRIGGER trg_reminders_audit
    AFTER INSERT OR UPDATE OR DELETE ON reminders
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log();

CREATE TRIGGER trg_due_dates_audit
    AFTER INSERT OR UPDATE OR DELETE ON due_dates
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log();

CREATE TRIGGER trg_portal_users_audit
    AFTER INSERT OR UPDATE OR DELETE ON portal_users
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log();

CREATE TRIGGER trg_messages_audit
    AFTER INSERT OR UPDATE OR DELETE ON messages
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log();

CREATE TRIGGER trg_questionnaires_audit
    AFTER INSERT OR UPDATE OR DELETE ON questionnaires
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log();

CREATE TRIGGER trg_signature_requests_audit
    AFTER INSERT OR UPDATE OR DELETE ON signature_requests
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log();

CREATE TRIGGER trg_fixed_assets_audit
    AFTER INSERT OR UPDATE OR DELETE ON fixed_assets
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log();

CREATE TRIGGER trg_depreciation_entries_audit
    AFTER INSERT OR UPDATE OR DELETE ON depreciation_entries
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log();

CREATE TRIGGER trg_budgets_audit
    AFTER INSERT OR UPDATE OR DELETE ON budgets
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log();

CREATE TRIGGER trg_budget_lines_audit
    AFTER INSERT OR UPDATE OR DELETE ON budget_lines
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log();

-- ============================================================
-- SEED: Default workflow stages
-- ============================================================
INSERT INTO workflow_stages (workflow_type, stage_name, stage_order, color, is_completion_stage) VALUES
    -- Tax Preparation workflow
    ('Tax Prep', 'Not Started', 0, '#6B7280', false),
    ('Tax Prep', 'Waiting on Client', 1, '#F59E0B', false),
    ('Tax Prep', 'Documents Received', 2, '#3B82F6', false),
    ('Tax Prep', 'In Preparation', 3, '#8B5CF6', false),
    ('Tax Prep', 'In Review', 4, '#EC4899', false),
    ('Tax Prep', 'Ready for Signature', 5, '#10B981', false),
    ('Tax Prep', 'E-Filed', 6, '#059669', false),
    ('Tax Prep', 'Complete', 7, '#047857', true),
    -- Bookkeeping workflow
    ('Bookkeeping', 'Not Started', 0, '#6B7280', false),
    ('Bookkeeping', 'Bank Feeds Imported', 1, '#3B82F6', false),
    ('Bookkeeping', 'Categorization', 2, '#8B5CF6', false),
    ('Bookkeeping', 'Reconciliation', 3, '#F59E0B', false),
    ('Bookkeeping', 'Review', 4, '#EC4899', false),
    ('Bookkeeping', 'Reports Sent', 5, '#10B981', false),
    ('Bookkeeping', 'Complete', 6, '#047857', true),
    -- Payroll workflow
    ('Payroll', 'Not Started', 0, '#6B7280', false),
    ('Payroll', 'Hours Collected', 1, '#3B82F6', false),
    ('Payroll', 'Processing', 2, '#8B5CF6', false),
    ('Payroll', 'Review', 3, '#EC4899', false),
    ('Payroll', 'Approved', 4, '#10B981', false),
    ('Payroll', 'Complete', 5, '#047857', true),
    -- Onboarding workflow
    ('Onboarding', 'Initial Contact', 0, '#6B7280', false),
    ('Onboarding', 'Proposal Sent', 1, '#3B82F6', false),
    ('Onboarding', 'Engagement Signed', 2, '#8B5CF6', false),
    ('Onboarding', 'Documents Requested', 3, '#F59E0B', false),
    ('Onboarding', 'Setup Complete', 4, '#10B981', false),
    ('Onboarding', 'Complete', 5, '#047857', true),
    -- Advisory workflow
    ('Advisory', 'Scheduled', 0, '#6B7280', false),
    ('Advisory', 'Data Collection', 1, '#3B82F6', false),
    ('Advisory', 'Analysis', 2, '#8B5CF6', false),
    ('Advisory', 'Report Preparation', 3, '#EC4899', false),
    ('Advisory', 'Client Meeting', 4, '#F59E0B', false),
    ('Advisory', 'Follow-Up', 5, '#10B981', false),
    ('Advisory', 'Complete', 6, '#047857', true)
ON CONFLICT (workflow_type, stage_name) DO NOTHING;
