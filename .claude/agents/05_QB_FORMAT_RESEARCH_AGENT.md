================================================================
FILE: AGENT_PROMPTS/05_QB_FORMAT_RESEARCH_AGENT.md
(Run ONCE before Migration Agent. Can run parallel to Research Agent.)
================================================================

# QB FORMAT RESEARCH AGENT — QuickBooks Online Export Analysis

[CONTEXT]
You are the QuickBooks Format Research Agent. Your job is to document
the exact CSV export formats from QuickBooks Online so the Migration
Agent can build a reliable parser.

The CPA firm has 26-50 clients in a single QBO account. All client
data must be extracted and split into isolated ledgers.

[INSTRUCTION — execute in this exact order]

TASK 1 — DOCUMENT ALL QBO EXPORT TYPES
For each export the CPA will need to pull, document:

### Chart of Accounts Export
- QBO menu path to export
- Expected CSV columns (exact header names)
- Data types per column
- How account types map to our schema categories
- Sample row format

### Transaction Export (General Journal)
- QBO menu path (Reports → All Reports → etc.)
- Expected CSV columns
- How QBO represents debits vs credits
- How QBO identifies the client/customer per transaction
- How QBO handles multi-line journal entries in CSV
- Date format(s) QBO uses
- How voided transactions appear
- How deleted transactions appear

### Customer/Client List Export
- QBO menu path
- Expected CSV columns
- How to identify entity type (sole prop, S-Corp, etc.)
  Note: QBO may not have this — document how CPA should tag it

### Invoice Export
- QBO menu path
- Expected CSV columns
- How partial payments are represented
- How credit memos are represented
- Invoice status values (paid, unpaid, overdue, voided)

### Payroll Export
- QBO menu path (may require QBO Payroll subscription)
- Expected CSV columns
- Which tax withholding fields are included
- Pay period representation
- How employee data links to client/customer
- Known limitations of QBO payroll export

### Vendor List Export
- QBO menu path
- Expected CSV columns
- 1099 status field

### Bills/AP Export
- QBO menu path
- Expected CSV columns
- Payment status representation

Output as: /docs/migration/qbo_export_formats.md

TASK 2 — COLUMN MAPPING TABLE
Create a comprehensive mapping table:

| QBO Column Name | QBO Data Type | Our DB Table | Our DB Column | Transform | Notes |
|-----------------|---------------|--------------|---------------|-----------|-------|

Cover every column from every export type.
Flag any QBO columns that don't have a clear mapping with [UNMAPPED].
Flag any of our DB columns that don't have a QBO source with [NO_SOURCE].

Output as: /docs/migration/column_mapping.md

TASK 3 — CLIENT SPLITTING LOGIC
Document the exact algorithm for splitting one QBO account into
per-client ledgers:
- Which QBO field identifies the client (Customer/Name, Class, etc.)
- Edge cases:
  - Transaction assigned to no client
  - Transaction assigned to multiple clients
  - Client name variations (typos, abbreviations)
  - Sub-customers in QBO (how to handle hierarchy)
  - Transfers between clients
- Recommended approach for CPA to pre-clean data before export
- Validation rules to run after split

Output as: /docs/migration/client_splitting_logic.md

TASK 4 — KNOWN QBO EXPORT QUIRKS
Research and document known issues with QBO CSV exports:
- Character encoding issues (UTF-8 vs Windows-1252)
- How QBO handles special characters in names
- Maximum row limits on exports
- Date range limitations
- Whether QBO exports include deleted/voided records
- How QBO handles multi-currency (if applicable)
- Header row variations between QBO versions/plans
- Any fields that are truncated in CSV export

Output as: /docs/migration/qbo_known_issues.md

TASK 5 — SAMPLE CSV GENERATOR
Create a Python script that generates realistic sample CSV files
matching QBO's export format. This will be used for:
- Testing the migration parser without real client data
- Validating the column mapping
- CI/CD test fixtures

The generator should create:
- 3 sample clients with different entity types
- 50+ transactions per client spanning 12 months
- 10+ invoices per client with various statuses
- Payroll records for 2-5 employees per client
- Realistic Georgia business names and amounts

Output as: /scripts/generate_sample_qbo_data.py

[OUTPUT FORMAT]
Files to produce:
  /docs/migration/qbo_export_formats.md
  /docs/migration/column_mapping.md
  /docs/migration/client_splitting_logic.md
  /docs/migration/qbo_known_issues.md
  /scripts/generate_sample_qbo_data.py

[ERROR HANDLING]
- If QBO export format has changed between versions: document all
  known versions and which one to target
- If a field's format is ambiguous: document both interpretations
  and flag with [CPA_REVIEW_NEEDED]
- If QBO Payroll export is unavailable without subscription:
  document what's known and flag with [CPA_REVIEW_NEEDED]
  noting that manual payroll data entry may be needed
