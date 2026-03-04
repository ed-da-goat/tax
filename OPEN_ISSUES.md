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
- **Status:** OPEN
- **Description:** Georgia HB 1015 projects a 4.99% flat rate for TY2026, contingent on revenue triggers. The actual rate for 2026 has not been verified from the Georgia DOR. CPA_OWNER must download the 2026 Employer's Tax Guide from https://dor.georgia.gov/withholding-tax and confirm the rate before any 2026 payroll is processed.
- **Resolution:** (pending)

### #2 — Georgia TY2026 standard deductions and personal exemptions unconfirmed
- **Label:** COMPLIANCE
- **Module:** P2 (Georgia income tax withholding engine)
- **Assigned to:** CPA_OWNER
- **Status:** OPEN
- **Description:** The standard deduction and personal exemption amounts for Tax Year 2026 have not been published or confirmed. TY2025 values are documented in /docs/tax_research/georgia_withholding_tables.md. CPA_OWNER must verify TY2026 amounts from the Georgia DOR Employer's Tax Guide before processing 2026 payroll.
- **Resolution:** (pending)

### #3 — Federal TY2026 income tax brackets unknown (TCJA expiration)
- **Label:** COMPLIANCE
- **Module:** P4 (Federal withholding calculator)
- **Assigned to:** CPA_OWNER
- **Status:** OPEN
- **Description:** The Tax Cuts and Jobs Act provisions were scheduled to expire after TY2025. The status of federal income tax brackets, standard deductions, and supplemental wage rates for TY2026 depends on whether Congress extended, modified, or allowed TCJA to expire. CPA_OWNER MUST verify from the 2026 IRS Publication 15-T before processing any 2026 payroll. This is the single highest-risk compliance item.
- **Resolution:** (pending)

### #4 — TY2026 Social Security wage base unconfirmed
- **Label:** COMPLIANCE
- **Module:** P4 (Federal FICA calculator)
- **Assigned to:** CPA_OWNER
- **Status:** OPEN
- **Description:** SSA announces the new Social Security wage base in Q4 of the prior year. The TY2026 wage base has not been confirmed in this research. CPA_OWNER should check https://www.ssa.gov/oact/cola/cbb.html for the official 2026 figure.
- **Resolution:** (pending)

### #5 — Georgia SUTA wage base TY2026 confirmation needed
- **Label:** COMPLIANCE
- **Module:** P3 (Georgia SUTA calculator)
- **Assigned to:** CPA_OWNER
- **Status:** OPEN
- **Description:** The Georgia SUTA wage base has historically been $9,500. CPA_OWNER should confirm this has not changed for 2026 via GDOL communications.
- **Resolution:** (pending)

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
- **Status:** OPEN
- **Description:** The Georgia corporate income tax rate is 5.75%. CPA_OWNER should verify whether any legislation has changed this rate for TY2026, particularly in light of the individual income tax reform under HB 1015.
- **Resolution:** (pending)

### #11 — Web search tools unavailable during tax research
- **Label:** BLOCKER
- **Module:** Tax Research (Agent 04)
- **Assigned to:** CPA_OWNER
- **Status:** OPEN
- **Description:** During execution of the Georgia Tax Research Agent, both WebSearch and WebFetch tools were denied. All research was conducted from the agent's training knowledge (verified through early 2025). All TY2026-specific rates are flagged as [UNVERIFIED]. CPA_OWNER must independently verify all rates against current official sources before production use.
- **Resolution:** (pending -- CPA_OWNER manual verification required)

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
