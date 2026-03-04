# Research Agent (Agent 00) — Review Report

**Reviewer:** Review Agent (Agent 03)
**Review Date:** 2026-03-04
**Files Reviewed:** 17 files across project structure

---

## REVIEW: SETUP.md

**Status:** ISSUES FOUND

### Checklist

- [x] All commands are copy-pasteable (no placeholder paths)
- [x] VERIFY steps exist after each major install
- [x] PostgreSQL setup includes creating the database and user
- [x] Python version specified (3.11+)
- [x] Node.js version specified (18+)
- [x] Vite dev server start command included

### Issues

1. **WARNING — Placeholder in git clone URL.** Step 5 uses `https://github.com/your-org/cpa-accounting.git` which is not a real URL. The CPA will not know what to replace this with. Should be replaced with the actual GitHub repo URL, or at minimum clearly marked as a placeholder requiring replacement (e.g., surround with `<angle brackets>` and a note explaining what to substitute).

2. **WARNING — requirements.txt path ambiguity.** Step 6b references `pip install -r requirements.txt` but the actual file is at `backend/requirements.txt`. If the user runs this from the project root (as directed in Step 5), pip will fail with "file not found." The command should be `pip install -r backend/requirements.txt`.

3. **WARNING — macOS-only instructions.** SETUP.md explicitly says "Platform: macOS" and uses `brew` for everything. This is fine if the CPA uses macOS, but should at minimum note that these instructions are macOS-specific. Given the firm profile says "local machine" without specifying OS, a note about Linux/Windows alternatives would be a good addition.

4. **SUGGESTION — Missing Claude Code installation step.** Task 1 of the Research Agent prompt says to include "Installing Claude Code and connecting to GitHub." SETUP.md does not mention Claude Code anywhere. This is a gap against the Research Agent's requirements.

5. **SUGGESTION — No reference to running the schema inside a virtual environment.** Step 8 runs `psql` to apply the migration, which is fine since psql is a system tool, but the uvicorn command in Step 10 assumes the venv is activated. A reminder to activate the venv before Step 10 is good practice (and is present), so this is minor.

---

## REVIEW: MIGRATION_SPEC.md

**Status:** ISSUES FOUND

### Checklist

- [x] QB Online menu paths are provided for each export
- [x] Every CSV column mapping accounts for QB's actual export format
- [x] Client-splitting logic handles edge cases (same name, multi-client, voided)
- [x] Rollback procedure is a real SQL ROLLBACK, not manual cleanup
- [x] [CPA_REVIEW_NEEDED] flags used where QB format is ambiguous

### Issues

1. **WARNING — QB Online menu paths may be inaccurate.** For example, "Reports > Accounting > Account List > Export to Excel" may not match the actual QBO navigation. QBO's interface uses "Reports" in the left sidebar, but the report names and paths change with QBO updates. This is inherently fragile. The [CPA_REVIEW_NEEDED] flags on Section 7 items are appropriate, but the specific menu paths in Section 1 should also carry a caveat that the CPA should verify these paths match their current QBO version.

2. **WARNING — V-010 rule conflicts with edge case handling.** Validation rule V-010 says "Client identifier (Name/Customer) is not NULL" with severity FATAL. But Section 3 (Edge Cases) explicitly says "Blank Name field: Assign client_id = NULL, flag as [UNASSIGNED]." These two rules contradict each other: one says blank names cause a FATAL abort, the other says they are handled gracefully. This must be reconciled. Recommendation: Change V-010 to WARNING severity for blank Name fields, consistent with the Section 3 logic.

3. **WARNING — client_id type inconsistency.** Column mapping tables show `client_id` as "INT / UUID" in multiple places (Sections 2.2, 2.3, 2.4, 2.5). The actual database schema uses UUID exclusively. MIGRATION_SPEC.md should commit to UUID to match the schema. Mixed type references will confuse builder agents.

4. **WARNING — No vendor list import step in Section 5.** Section 1.7 documents a Vendor List export, and the database has a `vendors` table, but Section 5 (Import Order) does not include a step for importing vendors. Vendors are needed before bills (AP) can reference them. A vendor import step should be inserted after Step 2 (Chart of Accounts) and before Step 4 (Transactions).

5. **SUGGESTION — Transaction Detail report may not export as a single flat CSV.** QBO's Transaction Detail by Account report groups transactions under account headers, and when exported to CSV/Excel, the output includes section headers, subtotals, and blank rows that are not standard CSV rows. The parser must handle these non-data rows. This is a known QBO quirk that should be explicitly called out in the spec.

6. **SUGGESTION — Debit/credit sign convention needs explicit testing.** The sign convention normalization in Section 2.3 is correct in principle, but QBO's actual sign behavior is more nuanced. For example, within Expense accounts, a refund appears as a negative number (credit). The normalization logic should be tested against real QBO exports before production use.

---

## REVIEW: db/migrations/001_initial_schema.sql

**Status:** ISSUES FOUND

### Checklist

- [x] client_id (UUID) on every client-data table, NOT NULL, FK
- [x] created_at, updated_at, deleted_at on every table (where applicable)
- [x] audit_log table has: id, table_name, record_id, action, old_values (JSONB), new_values (JSONB), user_id, ip_address, created_at
- [x] transactions table has CHECK constraint via trigger (debits = credits on POSTED)
- [x] chart_of_accounts covers all 4 entity types
- [x] payroll_tax_tables parameterized by tax_year + filing_status
- [x] permission_log table exists
- [ ] All FKs have ON DELETE RESTRICT (not CASCADE)
- [x] Indexes on client_id (every client table), transaction date, account number, user_id
- [x] UUID generation uses gen_random_uuid() (via pgcrypto)

### Issues

1. **CRITICAL — Foreign keys use default ON DELETE behavior (NO ACTION) instead of explicit ON DELETE RESTRICT.** The review criteria require `ON DELETE RESTRICT` to protect the audit trail. While PostgreSQL's default `NO ACTION` is functionally similar to `RESTRICT` at the end of a transaction, they behave differently within a transaction that has deferred constraints. For safety and explicitness, all foreign key constraints should include `ON DELETE RESTRICT` explicitly. This applies to every REFERENCES clause in the schema.

   Affected tables (non-exhaustive): `chart_of_accounts.client_id`, `journal_entries.client_id`, `journal_entries.created_by`, `journal_entries.approved_by`, `journal_entry_lines.journal_entry_id`, `journal_entry_lines.account_id`, `vendors.client_id`, `bills.client_id`, `bills.vendor_id`, `bill_lines.bill_id`, `bill_lines.account_id`, `bill_payments.bill_id`, `invoices.client_id`, `invoice_lines.invoice_id`, `invoice_lines.account_id`, `invoice_payments.invoice_id`, `bank_accounts.client_id`, `bank_accounts.account_id`, `bank_transactions.bank_account_id`, `bank_transactions.journal_entry_id`, `reconciliations.bank_account_id`, `reconciliations.completed_by`, `documents.client_id`, `documents.uploaded_by`, `documents.journal_entry_id`, `employees.client_id`, `payroll_runs.client_id`, `payroll_runs.finalized_by`, `payroll_items.payroll_run_id`, `payroll_items.employee_id`, `tax_form_exports.client_id`, `tax_form_exports.generated_by`, `migration_errors.batch_id`.

2. **CRITICAL — Double-entry enforcement is trigger-based, not a CHECK constraint.** CLAUDE.md Section "COMPLIANCE RULES" Item 1 states: "Enforce at the database level with a CHECK constraint, not just application logic." The schema uses a BEFORE UPDATE trigger (`trg_je_balance_check`) rather than a CHECK constraint. While the trigger is functionally effective and arguably more appropriate for this cross-table validation (since CHECK constraints cannot reference other tables), this deviates from the literal CLAUDE.md mandate. Recommendation: (a) acknowledge this deviation with a comment in the schema explaining why a trigger is necessary (CHECK constraints cannot cross-reference tables), and (b) confirm with CPA_OWNER that the trigger approach is acceptable.

3. **WARNING — journal_entry_lines is missing client_id.** CLAUDE.md compliance rule #4 says "Every table that holds client data must have client_id as a non-nullable foreign key." The `journal_entry_lines` table does not have a direct `client_id` column. It can be joined through `journal_entries`, but the rule says every table, not every parent table. Same issue affects: `bill_lines`, `bill_payments`, `invoice_lines`, `invoice_payments`, `bank_transactions`. This is a design trade-off (denormalization vs strict compliance), but it technically violates the letter of the CLAUDE.md rule. At minimum, add a comment justifying why these child tables inherit client_id through their parent FK rather than having their own direct FK.

4. **WARNING — reconciliations table is missing client_id.** The `reconciliations` table references `bank_account_id` which references `bank_accounts.client_id`, but `reconciliations` itself does not have a direct `client_id` column. Client isolation queries on reconciliations would need a JOIN through bank_accounts, making it harder to enforce isolation.

5. **WARNING — payroll_items table is missing client_id.** Same issue as above. Payroll items are reached through payroll_runs, but do not have their own client_id for direct isolation.

6. **WARNING — No index on journal_entry_lines.account_id specifically for client-scoped queries.** While `idx_jel_account` exists, queries filtering by both client_id and account would need to go through journal_entries first. Consider a composite index or denormalized client_id.

7. **WARNING — Audit trigger uses DELETE on soft-delete tables, but hard-delete prevention trigger is also present.** The `fn_audit_log` trigger handles TG_OP = 'DELETE', but `fn_prevent_hard_delete` will raise an exception before the audit trigger fires (since prevent_hard_delete is a BEFORE trigger and audit is an AFTER trigger). This means audit_log will never capture DELETE operations on soft-delete tables, which is actually fine (the UPDATE setting deleted_at will be captured instead). However, this should be documented so future developers understand why DELETE rows never appear in audit_log for those tables.

8. **WARNING — Seed data uses a hardcoded template client UUID.** `'00000000-0000-0000-0000-000000000001'` is inserted as a template client with `is_active = FALSE`. This is a reasonable approach for seed data, but the migration should document how builder agents should copy these accounts to real clients (presumably by cloning from this template). No such documentation exists.

9. **SUGGESTION — The filing_status enum only has SINGLE, MARRIED, HEAD_OF_HOUSEHOLD.** Georgia's G-4 form also supports "Married Filing Separately" and potentially "Nonresident Alien." The payroll_tax_tables table uses a VARCHAR for filing_status which is flexible, but the employees table uses the filing_status enum which is restrictive. Consider expanding the enum or changing the employees table to use VARCHAR.

10. **SUGGESTION — The `v_trial_balance` view joins journal_entry_lines to journal_entries but applies the `je.status = 'POSTED'` filter on the LEFT JOIN, not in a WHERE clause.** This means unposted entries will still appear as rows with zero balances rather than being excluded. This is a minor cosmetic issue but could confuse reporting.

11. **SUGGESTION — Missing `employer_ss` and `employer_medicare` columns on payroll_items.** The MIGRATION_SPEC.md maps these QBO fields but the payroll_items table only has employee-side SS and Medicare fields. Employer-side FICA contributions need columns too (or a separate employer_contributions table).

---

## REVIEW: WORK_QUEUE.md

**Status:** ISSUES FOUND

### Checklist

- [x] All 34 modules present (M1-M7, F1-F5, T1-T4, D1-D3, P1-P6, X1-X9, R1-R5, O1-O4)
- [ ] Dependencies form a valid DAG (no circular deps)
- [x] Compliance risk ratings are reasonable

### Issues

1. **CRITICAL — Circular dependency in TASK-033 (X8 / Form 1065).** TASK-033 lists its dependencies as "TASK-010, TASK-033" -- it depends on itself. This is clearly a typo. It should probably depend on `TASK-010` (F3 - General Ledger) only, matching the pattern of the other tax form tasks in Phase 5. This circular dependency will break any automated dependency resolver.

2. **WARNING — Phase ordering conflict between WORK_QUEUE and ARCHITECTURE.** WORK_QUEUE.md has Tax Forms (Phase 5) depending on Reporting tasks (TASK-033 = R1 via TASK-027, TASK-028, etc.), but ARCHITECTURE.md shows Reporting as Phase 6, which comes AFTER Phase 5. If X2, X3, X5, X6, X7, X8 all depend on R1 (Profit & Loss), then Reporting (Phase 6) must be built BEFORE Tax Forms (Phase 5). This is a sequencing error. Either: (a) move R1 to Phase 4.5 or Phase 5 prerequisite, or (b) remove the R1 dependency from tax form tasks and have them query the GL directly.

3. **WARNING — TASK-005 (M5) depends on TASK-013 (T2 - Accounts Receivable).** M5 is a Phase 0 migration task but depends on a Phase 2 task. This makes the migration impossible to run before Phase 2 is complete, which contradicts the intent of Phase 0 running before any other phase. The invoice importer should write directly to the `invoices` table without requiring the AR module's business logic.

4. **WARNING — TASK-006 (M6) depends on TASK-020 (P1 - Employee Records).** Same issue as above. Payroll history import (Phase 0) depends on Employee Records (Phase 4). This means Phase 0 migration cannot run until Phase 4 is started, contradicting "run ONCE before any other phase." The importer should write directly to the employees/payroll tables.

5. **WARNING — TASK numbering gaps.** There are 43 tasks (TASK-001 through TASK-043) for 34 modules. The math works out (34 modules = tasks 001-034 for modules, but tasks actually go to 043 because of Phase 1+ additions). This is correct but the document header says "34 modules" while the task count is 43. The header should clarify: "34 modules across 43 tasks."

6. **SUGGESTION — M1 (TASK-001) has no dependency but needs the database schema to validate against.** The parser validates CSV data, which is reasonable without a DB. But M3 and M4 write to DB tables. If M1 is truly standalone (parse + validate CSVs only), this is fine. Confirm that M1 does NOT require database connectivity.

---

## REVIEW: ARCHITECTURE.md

**Status:** ISSUES FOUND

### Checklist

- [ ] Dependency map matches WORK_QUEUE.md dependencies
- [x] No module listed as "no dependencies" if it clearly needs the DB

### Issues

1. **WARNING — Dependency mismatches with WORK_QUEUE.md.** Several modules have different dependency lists:
   - ARCHITECTURE.md shows X2 (Form 500) depends on F3, R1. WORK_QUEUE.md shows TASK-027 depends on TASK-010, TASK-033. TASK-010 is F3 and TASK-033 is X8 (Form 1065), not R1. These do not match. WORK_QUEUE likely has a typo (TASK-033 should be TASK-035 for R1).
   - ARCHITECTURE.md shows M5 depends on M2, M3, T2. WORK_QUEUE shows TASK-005 depends on TASK-002, TASK-003, TASK-013. TASK-013 is T1 (Accounts Payable), not T2 (Accounts Receivable). These do not match.
   - ARCHITECTURE.md shows M3 depends on M1, F2. WORK_QUEUE shows TASK-003 depends on TASK-001, TASK-008. TASK-008 is F1, not F2. These do not match (F2 = TASK-009).

2. **WARNING — Build order critical path diagram is oversimplified.** The ASCII diagram shows D1/D2/D3 after X9 in the critical path, but Documents (Phase 3) have no dependency on Tax Forms (Phase 5). Documents depend only on F4 and F5. The diagram should show them branching off earlier.

3. **SUGGESTION — ARCHITECTURE.md should include the M-series (migration) modules in the dependency table with clearer notation about when they can be built vs when they can be run.** The note at the bottom mentions this but the table itself does not distinguish "build dependency" from "runtime dependency."

---

## REVIEW: docs/GEORGIA_COMPLIANCE.md

**Status:** PASS (minor suggestions only)

### Checklist

- [x] Lists all Georgia-specific modules
- [x] Documents what must be verified annually
- [x] Includes code convention for tax rate citations
- [x] Documents where tax data lives in the system

### Issues

1. **SUGGESTION — Missing mention of Georgia Form 600 corporate tax rate change.** The document references 5.75% "as of 2024 -- verify annually." Georgia has been phasing in corporate tax rate reductions. The 2024 rate was actually 5.39% (reduced from 5.75% under HB 1437). This should carry a [CPA_REVIEW_NEEDED] flag. The CPA must confirm the current rate for each tax year.

2. **SUGGESTION — No mention of Georgia Net Worth Tax.** C-Corps in Georgia are also subject to a net worth tax (Form 600, Schedule 1). This is not mentioned anywhere in the compliance guide and may need its own module or at least a flag.

---

## REVIEW: AGENT_LOG.md

**Status:** PASS

No entries yet, which is correct since this is the initial scaffolding. Format template is present and follows the expected structure.

---

## REVIEW: OPEN_ISSUES.md

**Status:** PASS

No issues logged yet, which is correct for initial scaffolding. Issue template format is present and follows the expected structure.

---

## REVIEW: README.md Files (all 6)

**Status:** PASS

All six README files (backend, frontend, db, docs, data, scripts) are present and describe their directory's purpose. The `data/README.md` correctly notes that contents are not committed to git. The `db/README.md` includes the rule about never modifying applied migrations.

---

## REVIEW: .gitignore

**Status:** PASS

Correctly excludes:
- Python artifacts, venvs
- Node modules, Vite build output
- .env files
- IDE files
- OS files
- data/documents/ and data/backups/
- Credentials files
- Test coverage artifacts

---

## REVIEW: backend/requirements.txt

**Status:** PASS (minor suggestion)

All required packages are present: FastAPI, SQLAlchemy, psycopg2, Alembic, python-jose, passlib, weasyprint, pandas, pydantic, pytest, httpx.

### Issues

1. **SUGGESTION — Consider pinning WeasyPrint system dependencies.** WeasyPrint 63.1 requires specific versions of Pango, GDK-Pixbuf, and Cairo. SETUP.md mentions installing these but does not pin versions. This could cause build failures on different machines.

---

## REVIEW: frontend/package.json

**Status:** PASS

Includes React 18, react-router-dom, axios, Vite 6, and TypeScript types. All appropriate for the stated tech stack.

---

## REVIEW: AGENT_PROMPTS/ (04, 05)

**Status:** PASS

Both additional agent prompts (Georgia Tax Research Agent and QB Format Research Agent) are well-structured and include proper error handling, citation requirements, and output file locations. These were not required by the Research Agent's Task list but are valuable additions that will help downstream agents.

---

# SUMMARY OF FINDINGS

## Statistics

| Severity | Count |
|----------|-------|
| CRITICAL | 3     |
| WARNING  | 16    |
| SUGGESTION | 10 |

## Critical Issues (must fix before commit)

1. **001_initial_schema.sql — Foreign keys lack explicit ON DELETE RESTRICT.** All REFERENCES clauses should include `ON DELETE RESTRICT` to protect audit trail integrity per review criteria.

2. **001_initial_schema.sql — Double-entry enforcement uses a trigger instead of a CHECK constraint.** CLAUDE.md mandates a CHECK constraint. A trigger was used because CHECK constraints cannot reference other tables. This deviation must be acknowledged with a comment and confirmed acceptable by CPA_OWNER.

3. **WORK_QUEUE.md — TASK-033 (X8 / Form 1065) has a circular self-dependency.** `Depends on: TASK-010, TASK-033` is invalid. Remove the self-reference.

## High-Priority Warnings (fix before builder agents start)

1. **MIGRATION_SPEC.md — V-010 validation rule contradicts Section 3 edge case handling for blank names.** Reconcile the FATAL vs graceful handling.

2. **MIGRATION_SPEC.md — client_id typed as "INT / UUID" in multiple mappings.** Commit to UUID to match the actual schema.

3. **MIGRATION_SPEC.md — Missing vendor import step in Section 5 import order.**

4. **WORK_QUEUE.md — Phase 5 (Tax Forms) depends on Phase 6 (Reporting) tasks.** Circular phase dependency must be resolved.

5. **WORK_QUEUE.md — Phase 0 migration tasks depend on Phase 2 and Phase 4 tasks.** This makes Phase 0 unable to run first as intended.

6. **ARCHITECTURE.md — Multiple dependency mismatches with WORK_QUEUE.md.** These two files must be synchronized.

7. **001_initial_schema.sql — Several child tables (journal_entry_lines, bill_lines, bill_payments, invoice_lines, invoice_payments, bank_transactions, reconciliations, payroll_items) lack direct client_id columns.** This technically violates CLAUDE.md compliance rule #4.

8. **001_initial_schema.sql — Missing employer_ss and employer_medicare columns on payroll_items.** MIGRATION_SPEC maps these fields but the schema has no place for them.

9. **SETUP.md — requirements.txt path is wrong (should be backend/requirements.txt).**

---

*Report generated by Review Agent (Agent 03) on 2026-03-04.*
