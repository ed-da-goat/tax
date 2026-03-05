-- Migration 003: W-2/1099 support, check printing
-- Adds employee address fields, vendor 1099 flag, check number tracking

-- Employee address fields (required for W-2)
ALTER TABLE employees ADD COLUMN IF NOT EXISTS address VARCHAR(500);
ALTER TABLE employees ADD COLUMN IF NOT EXISTS city VARCHAR(100);
ALTER TABLE employees ADD COLUMN IF NOT EXISTS state VARCHAR(2) DEFAULT 'GA';
ALTER TABLE employees ADD COLUMN IF NOT EXISTS zip VARCHAR(10);

-- Vendor 1099 eligibility flag
ALTER TABLE vendors ADD COLUMN IF NOT EXISTS is_1099_eligible BOOLEAN NOT NULL DEFAULT FALSE;

-- Check number on bill payments
ALTER TABLE bill_payments ADD COLUMN IF NOT EXISTS check_number INTEGER;

-- Per-client check number sequence
CREATE TABLE IF NOT EXISTS client_check_sequences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE RESTRICT UNIQUE,
    next_check_number INTEGER NOT NULL DEFAULT 1001,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Audit trigger for client_check_sequences
CREATE TRIGGER trg_client_check_sequences_audit
    AFTER INSERT OR UPDATE OR DELETE ON client_check_sequences
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log();
