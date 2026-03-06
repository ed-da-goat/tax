-- Migration 004: Redact PII fields in audit trigger
--
-- Updates the fn_audit_log() trigger function to replace sensitive fields
-- (ssn_encrypted, tax_id_encrypted, account_number_encrypted, routing_number)
-- with '***REDACTED***' before storing in audit_log.old_values / new_values.
--
-- This prevents PII from being stored in plaintext JSON in the audit trail.
-- The encrypted BYTEA values would appear as hex in JSONB anyway, but after
-- this migration the audit log explicitly redacts them.
--
-- Run: psql -U postgres -d ga_cpa -f db/migrations/004_audit_pii_redaction.sql

BEGIN;

CREATE OR REPLACE FUNCTION public.fn_audit_log()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
DECLARE
    v_old           JSONB;
    v_new           JSONB;
    v_action        audit_action;
    v_record_id     UUID;
    v_user_id_raw   TEXT;
    v_user_id       UUID;
    v_ip_raw        TEXT;
    v_ip            INET;
    -- PII fields to redact from audit log JSON
    v_pii_fields    TEXT[] := ARRAY[
        'ssn_encrypted',
        'tax_id_encrypted',
        'account_number_encrypted',
        'routing_number'
    ];
    v_field         TEXT;
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
    -- Redact PII fields from old_values and new_values
    -- -----------------------------------------------------------------------
    FOREACH v_field IN ARRAY v_pii_fields LOOP
        IF v_old IS NOT NULL AND v_old ? v_field THEN
            v_old := jsonb_set(v_old, ARRAY[v_field], '"***REDACTED***"');
        END IF;
        IF v_new IS NOT NULL AND v_new ? v_field THEN
            v_new := jsonb_set(v_new, ARRAY[v_field], '"***REDACTED***"');
        END IF;
    END LOOP;

    -- -----------------------------------------------------------------------
    -- Resolve user_id from session variable
    -- -----------------------------------------------------------------------
    v_user_id_raw := current_setting('app.current_user_id', true);

    IF v_user_id_raw IS NOT NULL AND v_user_id_raw <> '' AND v_user_id_raw <> 'system' THEN
        BEGIN
            v_user_id := v_user_id_raw::UUID;
        EXCEPTION WHEN invalid_text_representation THEN
            v_user_id := NULL;
        END;
    ELSE
        v_user_id := NULL;
    END IF;

    -- -----------------------------------------------------------------------
    -- Resolve IP address from session variable
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
    -- Return the appropriate row
    -- -----------------------------------------------------------------------
    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;

    RETURN NEW;
END;
$function$;

COMMIT;
