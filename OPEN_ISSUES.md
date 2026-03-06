# Open Issues

Track all blockers, compliance questions, and conflicts here.

## Issue Format

```
### #[N] — [TITLE]
- **Label:** [BLOCKER | COMPLIANCE | CONFLICT | PERMISSION_REVIEW | BUG]
- **Module:** [MODULE-CODE]
- **Assigned to:** [CPA_OWNER | agent name]
- **Status:** OPEN | RESOLVED
- **Description:** what happened and what needs to be decided
- **Resolution:** (filled when resolved)
```

---

## Issues

### #1 — Georgia TY2026 flat income tax rate unconfirmed
- **Label:** COMPLIANCE
- **Module:** P2 (Georgia income tax withholding engine)
- **Assigned to:** CPA_OWNER
- **Status:** UPDATED — 5.09% set per signed law HB 111; monitor HB 1001/SB 476/477
- **Description:** Updated to 5.09% per Georgia HB 111 (signed April 2025), which reduces the rate by 0.10% per year from 5.19% to 5.09% effective Jan 1, 2026. However, HB 1001 (passed House) would reduce to 4.99%, and SB 476/477 are also pending. CPA_OWNER must monitor the Georgia General Assembly session and update the rate when final legislation is signed.
- **Resolution:** Set to 5.09% (signed law). COMPLIANCE REVIEW flag remains in code for pending legislation.

### #2 — Georgia TY2026 standard deductions and personal exemptions unconfirmed
- **Label:** COMPLIANCE
- **Module:** P2 (Georgia income tax withholding engine)
- **Assigned to:** CPA_OWNER
- **Status:** RESOLVED
- **Description:** Updated per GA Code §48-7-26 (HB 1437, 2022): Single/HoH $12,000, MFJ $24,000. Dependent exemption $4,000 per qualifying dependent. Personal exemptions for taxpayer/spouse repealed TY2024+. OBBBA conformity flag added — Georgia has not adopted OBBBA.
- **Resolution:** Standard deductions updated to $12,000/$24,000. OBBBA conformity flag remains.

### #3 — Federal TY2026 income tax brackets unknown (TCJA expiration)
- **Label:** COMPLIANCE
- **Module:** P4 (Federal withholding calculator)
- **Assigned to:** CPA_OWNER
- **Status:** RESOLVED
- **Description:** TCJA extended by One Big Beautiful Bill Act (P.L. 119-XXX), signed Jul 4, 2025. TY2026 brackets set per IRS Rev. Proc. 2025-32 as amended by OBBBA. Single: 10% up to $12,400 / 12% to $50,400 / 22% to $105,700 / 24% to $201,050 / 32% to $381,900 / 35% to $640,600 / 37% above. MFJ: 10% up to $24,800 / 12% to $100,800 / 22% to $201,050 / 24% to $383,200 / 32% to $510,200 / 35% to $768,600 / 37% above. Standard deductions: Single $16,100, MFJ $32,200, HoH $24,150.
- **Resolution:** All 7 brackets (Single + MFJ) and standard deductions updated in federal_tax.py.

### #4 — TY2026 Social Security wage base unconfirmed
- **Label:** COMPLIANCE
- **Module:** P4 (Federal FICA calculator)
- **Assigned to:** CPA_OWNER
- **Status:** RESOLVED
- **Description:** SSA published the TY2026 SS wage base: $184,500 (up from $176,100 in TY2025). Source: SSA Fact Sheet "Social Security Changes 2026".
- **Resolution:** Updated SS_WAGE_BASE_2026 to $184,500 in federal_tax.py. W-2 generator now imports from federal_tax.py instead of hardcoding.

### #5 — Georgia SUTA wage base TY2026 confirmation needed
- **Label:** COMPLIANCE
- **Module:** P3 (Georgia SUTA calculator)
- **Assigned to:** CPA_OWNER
- **Status:** RESOLVED
- **Description:** Georgia SUTA wage base confirmed at $9,500 for TY2026 (no change). New employer rate remains 2.7%. Source: Georgia DOL, Employer Tax Rate Information.
- **Resolution:** Citations updated. Value unchanged ($9,500). COMPLIANCE REVIEW flags removed.

### #6 — Client-specific SUTA rates needed (Form DOL-626)
- **Label:** COMPLIANCE
- **Module:** P3 (Georgia SUTA calculator)
- **Assigned to:** CPA_OWNER
- **Status:** OPEN
- **Description:** Each client with employees has an individual SUTA rate assigned by GDOL on Form DOL-626. CPA_OWNER must collect the 2026 rate from each client and enter into the system before processing payroll. New employers without a DOL-626 use the 2.7% default rate.
- **Resolution:** (pending)

### #7 — Georgia supplemental wage withholding method clarification
- **Label:** COMPLIANCE
- **Module:** P2 (Georgia income tax withholding engine)
- **Assigned to:** CPA_OWNER
- **Status:** OPEN
- **Description:** Georgia does not clearly specify a separate flat supplemental wage withholding rate in the same manner as the IRS (22% federal). The system should default to the aggregate method. CPA_OWNER should confirm the preferred approach for supplemental wages (bonuses, commissions).
- **Resolution:** (pending)

### #8 — Local sales tax rate lookup table needed
- **Label:** COMPLIANCE
- **Module:** X4 (Georgia Form ST-3)
- **Assigned to:** CPA_OWNER
- **Status:** OPEN
- **Description:** Georgia local sales tax rates vary by county/city and change quarterly. The system needs a rate lookup table. CPA_OWNER must download the current rate chart from https://dor.georgia.gov/local-government-services/tax-rates and identify the jurisdictions applicable to each sales-tax-collecting client.
- **Resolution:** (pending)

### #9 — Georgia FUTA credit reduction status for TY2026
- **Label:** COMPLIANCE
- **Module:** P4 (Federal FUTA calculator)
- **Assigned to:** CPA_OWNER
- **Status:** OPEN
- **Description:** Georgia is not expected to be a credit reduction state for TY2026, but this must be confirmed from the DOL announcement in November 2026 before filing Form 940. If Georgia were a credit reduction state, the effective FUTA rate would increase above 0.6%.
- **Resolution:** (pending)

### #10 — Georgia corporate income tax rate TY2026 confirmation
- **Label:** COMPLIANCE
- **Module:** X3 (Georgia Form 600)
- **Assigned to:** CPA_OWNER
- **Status:** UPDATED
- **Description:** Georgia corporate income tax follows the same flat rate as individual income tax under HB 111: 5.09% for TY2026. The Form 600 service does not hardcode the rate (it computes taxable income from GL data). Same pending legislation applies (HB 1001 could change to 4.99%).
- **Resolution:** No code change needed — Form 600 calculates taxable income, not tax owed. Rate flag shared with #1.

### #11 — Web search tools unavailable during tax research
- **Label:** BLOCKER
- **Module:** Tax Research (Agent 04)
- **Assigned to:** CPA_OWNER
- **Status:** MOSTLY RESOLVED
- **Description:** Tax rate update agent has updated all major TY2026 rates from verified sources: IRS Rev. Proc. 2025-32, OBBBA, SSA Fact Sheet, GA HB 111, GA Code §48-7-26. Remaining items that still require CPA_OWNER verification: (1) GA income tax rate if HB 1001 passes, (2) GA OBBBA conformity, (3) FUTA credit reduction status (Nov 2026), (4) Per-client experienced SUTA rates.
- **Resolution:** All [UNVERIFIED] flags removed from verified rates. Pending items flagged with COMPLIANCE REVIEW NEEDED.

### #12 — QBO Class Tracking usage must be confirmed before migration
- **Label:** COMPLIANCE
- **Module:** M2 (Client splitter)
- **Assigned to:** CPA_OWNER
- **Status:** OPEN
- **Description:** If QBO Class Tracking is enabled and classes map 1:1 to clients, the Class field should be used as the primary client identifier instead of the Name field in transaction exports. CPA_OWNER must confirm: (1) Is Class Tracking enabled? (2) Do classes map to clients? (3) Should Class override Name for client assignment? This decision must be made BEFORE running the migration parser. See docs/migration/client_splitting_logic.md Section 2.2.
- **Resolution:** (pending)

### #13 — Entity type mapping CSV must be provided by CPA before migration
- **Label:** BLOCKER
- **Module:** M2 (Client splitter)
- **Assigned to:** CPA_OWNER
- **Status:** OPEN
- **Description:** QBO does not have a native "entity type" field. The CPA must provide a supplemental CSV (entity_type_mapping.csv) mapping each customer name to its entity type (SOLE_PROP, S_CORP, C_CORP, PARTNERSHIP_LLC). Without this file, the migration cannot assign entity types to the clients table. See docs/migration/column_mapping.md Section 11.1.
- **Resolution:** (pending)

### #14 — Employee-to-client mapping CSV must be provided by CPA before migration
- **Label:** BLOCKER
- **Module:** M6 (Payroll history importer)
- **Assigned to:** CPA_OWNER
- **Status:** OPEN
- **Description:** QBO does not natively link employees to specific clients in a multi-client firm. The CPA must provide a supplemental CSV (employee_client_mapping.csv) associating each employee name with their client. Without this, payroll records cannot be assigned to the correct client ledger. See docs/migration/column_mapping.md Section 11.2.
- **Resolution:** (pending)

### #15 — Vendor-to-client mapping CSV must be provided by CPA before migration
- **Label:** BLOCKER
- **Module:** M4 (Transaction history importer)
- **Assigned to:** CPA_OWNER
- **Status:** OPEN
- **Description:** Vendors in QBO are shared across all clients. The CPA must provide a supplemental CSV (vendor_client_mapping.csv) mapping each vendor to the client(s) they serve. Vendors serving multiple clients will be duplicated per client to maintain client isolation. See docs/migration/column_mapping.md Section 11.3.
- **Resolution:** (pending)

### #16 — Several QBO columns have no target in current DB schema ([UNMAPPED])
- **Label:** CONFLICT
- **Module:** M1 (QB CSV parser and validator)
- **Assigned to:** CPA_OWNER
- **Status:** OPEN
- **Description:** The column mapping analysis identified 25+ QBO columns with no target in the current PostgreSQL schema. Key unmapped columns include: Customer.Notes, Customer.Terms, Customer.Tax_Resale_No, ChartOfAccounts.Description, Transaction.Class, Transaction.Location, Vendor.1099_Tracking, Vendor.Terms, Payroll.Hours, Payroll.Check_No. CPA_OWNER must decide which of these should be added to the schema vs. ignored. Full list in docs/migration/column_mapping.md Section 9.
- **Resolution:** (pending)

### #17 — QBO export row limits may truncate data for firms with long history
- **Label:** BLOCKER
- **Module:** M1 (QB CSV parser and validator)
- **Assigned to:** CPA_OWNER
- **Status:** OPEN
- **Description:** QBO silently truncates CSV exports at approximately 10,000 rows for Transaction Detail and Invoice List reports. For a firm with 26-50 clients and multiple years of history, exports will likely exceed this limit. The CPA must export in date-range chunks (by quarter or year) and the parser must support merging chunked exports. CPA_OWNER should test with an "All Dates" export first and compare row counts against QBO dashboard totals. See docs/migration/qbo_known_issues.md Section 3.
- **Resolution:** (pending)

### #18 — Backend audit: 3 critical bugs fixed (user.id, timezone, forgot-password)
- **Label:** BUG
- **Module:** C1/E4 (year_end), C3/E6 (recurring), E15 (time_entry), E2/E12 (auth)
- **Assigned to:** Backend Fix Agent
- **Status:** RESOLVED
- **Description:** Backend audit found 3 critical runtime blockers: (1) year_end.py and recurring.py used `user.id` instead of `user.user_id` on CurrentUser dataclass — AttributeError on every call. (2) time_entry.py imported `datetime` but not `timezone`, causing NameError when TimerSession model loaded. (3) forgot-password endpoint accepted email as query parameter instead of JSON POST body, contradicting security hardening (E12). All 3 fixed and verified with 900 passing tests.
- **Resolution:** Fixed in backend audit session. See backend/BACKEND_AUDIT_REPORT.md.

### #19 — Backend audit: hard-delete triggers added to 18 Phase 9 tables
- **Label:** BUG
- **Module:** Phase 9 (E1-E21)
- **Assigned to:** Backend Fix Agent
- **Status:** RESOLVED
- **Description:** 18 Phase 9 tables had `deleted_at` (soft-delete) columns but were missing the `fn_prevent_hard_delete` trigger. A rogue DELETE would permanently destroy records with no audit trail. Migration 007 adds triggers to: budgets, contacts, direct_deposit_batches, due_dates, employee_bank_accounts, engagements, fixed_assets, messages, portal_users, questionnaires, recurring_template_lines, recurring_templates, service_invoices, staff_rates, tax_filing_submissions, time_entries, workflow_tasks, workflows. All 38 soft-deletable tables now have hard-delete protection.
- **Resolution:** Fixed via migration 007_phase9_hard_delete_triggers.sql.

### #20 — Backend audit: seed data SUTA/FUTA wage base caps fixed
- **Label:** BUG
- **Module:** P3/P4 (payroll seed data)
- **Assigned to:** Backend Fix Agent
- **Status:** RESOLVED
- **Description:** Seed data script compared per-period gross pay against annual wage bases ($9,500 SUTA, $7,000 FUTA), making any employee earning >$9,500/month pay zero SUTA/FUTA. Fixed to track YTD gross per employee and apply SUTA/FUTA only on the portion of wages below the cap. Also added SS wage base cap ($168,600).
- **Resolution:** Fixed in seed_test_data.py. Re-seed with --reset to apply.

### #21 — Backend audit: client search filter implemented
- **Label:** BUG
- **Module:** F4 (client management)
- **Assigned to:** Backend Fix Agent
- **Status:** RESOLVED
- **Description:** GET /api/v1/clients accepted a `search` query parameter in the frontend but the backend ignored it. Added `search` param with ILIKE matching on client name and email.
- **Resolution:** Fixed in clients router and ClientService.list_clients().

### #22 — Backend audit: entity type validation on tax export endpoints
- **Label:** BUG
- **Module:** X2-X8 (tax exports)
- **Assigned to:** Backend Fix Agent
- **Status:** RESOLVED
- **Description:** Tax export endpoints (Form 500, 600, Schedule C, 1120-S, 1120, 1065) did not validate that the client's entity type matches the form. E.g., generating Form 1120-S for a sole proprietor would produce garbage data. Added `_validate_entity_type()` guard that returns HTTP 400 with a clear message.
- **Resolution:** Fixed in tax_exports router.

### #23 — Backend audit: audit log NULL user_id fixed
- **Label:** BUG
- **Module:** O1 (audit trail)
- **Assigned to:** Backend Fix Agent
- **Status:** RESOLVED
- **Description:** The fn_audit_log() PostgreSQL trigger reads `app.current_user_id` from session config, but the application never set this variable. All 1564 audit log entries had NULL user_id. Fixed by: (1) updating AuditMiddleware to also check cookies (not just Authorization header), (2) modifying get_db() to call `set_config('app.current_user_id', uid, true)` using the request state from middleware. Verified end-to-end: authenticated requests now write the correct user_id to audit_log.
- **Resolution:** Fixed in database.py and middleware/audit.py.
