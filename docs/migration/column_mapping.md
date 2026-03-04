# QBO to PostgreSQL Column Mapping — Comprehensive Reference

**Agent:** QB Format Research Agent (Agent 05)
**Date:** 2026-03-04
**Purpose:** Map every QBO CSV column to the target PostgreSQL schema, and flag unmapped/sourceless columns.

---

## Legend

- **Transform** column describes any data transformation needed during import
- **[UNMAPPED]** = QBO column exists but has no clear target in our DB schema
- **[NO_SOURCE]** = Our DB column exists but has no QBO CSV source (must be generated or manually provided)
- **[CPA_REVIEW_NEEDED]** = Mapping is ambiguous; CPA must confirm before migration

---

## 1. Customer Contact List --> `clients` Table

| # | QBO Column Name   | QBO Data Type | DB Table   | DB Column           | DB Type         | Transform                                              | Notes                                    |
|---|-------------------|---------------|------------|---------------------|-----------------|--------------------------------------------------------|------------------------------------------|
| 1 | Customer          | String        | clients    | name                | VARCHAR(255)    | TRIM whitespace; strip sub-customer prefix if present  | Primary matching key for all other exports |
| 2 | Company           | String        | clients    | (not mapped directly) | —             | —                                                      | [UNMAPPED] May duplicate Customer; use as fallback name if Customer is personal name |
| 3 | Phone             | String        | clients    | phone               | VARCHAR(20)     | Strip non-digit chars except +, -, (, ), space         |                                          |
| 4 | Email             | String        | clients    | email               | VARCHAR(255)    | Lowercase, TRIM                                        |                                          |
| 5 | Billing Street    | String        | clients    | address             | VARCHAR(500)    | TRIM                                                   |                                          |
| 6 | Billing City      | String        | clients    | city                | VARCHAR(100)    | TRIM                                                   |                                          |
| 7 | Billing State     | String        | clients    | state               | VARCHAR(2)      | Convert full state name to 2-letter abbreviation       | Default 'GA' if blank                    |
| 8 | Billing ZIP       | String        | clients    | zip                 | VARCHAR(10)     | TRIM; validate format (5 or 5+4 digits)                |                                          |
| 9 | Billing Country   | String        | clients    | (not in schema)     | —               | —                                                      | [UNMAPPED] Schema does not have country; assume all US |
| 10 | Shipping Street  | String        | —          | —                   | —               | —                                                      | [UNMAPPED] No shipping address in clients table |
| 11 | Shipping City    | String        | —          | —                   | —               | —                                                      | [UNMAPPED] No shipping address in clients table |
| 12 | Shipping State   | String        | —          | —                   | —               | —                                                      | [UNMAPPED] No shipping address in clients table |
| 13 | Shipping ZIP     | String        | —          | —                   | —               | —                                                      | [UNMAPPED] No shipping address in clients table |
| 14 | Shipping Country | String        | —          | —                   | —               | —                                                      | [UNMAPPED] No shipping address in clients table |
| 15 | Open Balance     | Currency      | —          | —                   | —               | —                                                      | [UNMAPPED] Used for reconciliation only; not stored permanently. Compare against computed AR balance after import. |
| 16 | Notes            | String        | —          | —                   | —               | —                                                      | [UNMAPPED] No notes column in clients schema. Could parse for entity_type hints. |
| 17 | Tax Resale No.   | String        | —          | —                   | —               | —                                                      | [UNMAPPED] No resale number in clients schema |
| 18 | Terms            | String        | —          | —                   | —               | —                                                      | [UNMAPPED] No default payment terms in clients schema |
| 19 | Full Name        | String        | —          | —                   | —               | —                                                      | [UNMAPPED] Contact person name, not in schema |
| 20 | Website          | String        | —          | —                   | —               | —                                                      | [UNMAPPED] Not in clients schema |
| 21 | Created          | Date          | clients    | created_at          | TIMESTAMPTZ     | Parse MM/DD/YYYY, set time to midnight UTC             | Use QBO creation date, not import date   |

### `clients` Table -- Columns Without QBO Source [NO_SOURCE]

| # | DB Column           | DB Type           | Source / Default Value                                  |
|---|---------------------|-------------------|---------------------------------------------------------|
| 1 | id                  | UUID              | Auto-generated via `gen_random_uuid()`                  |
| 2 | entity_type         | entity_type ENUM  | [NO_SOURCE] CPA must provide supplemental CSV mapping customer names to entity types (SOLE_PROP, S_CORP, C_CORP, PARTNERSHIP_LLC) |
| 3 | tax_id_encrypted    | BYTEA             | [NO_SOURCE] QBO does not export TINs. CPA must provide separately. Store encrypted. |
| 4 | is_active           | BOOLEAN           | Default TRUE                                            |
| 5 | updated_at          | TIMESTAMPTZ       | Set to import timestamp                                 |
| 6 | deleted_at          | TIMESTAMPTZ       | NULL (not deleted)                                      |

---

## 2. Chart of Accounts Export --> `chart_of_accounts` Table

| # | QBO Column Name | QBO Data Type | DB Table            | DB Column        | DB Type       | Transform                                              | Notes                                    |
|---|-----------------|---------------|---------------------|------------------|---------------|--------------------------------------------------------|------------------------------------------|
| 1 | Account         | String        | chart_of_accounts   | account_name     | VARCHAR(255)  | TRIM; preserve colon-delimited hierarchy in name       | If sub-account, full path stored         |
| 2 | Type            | String        | chart_of_accounts   | account_type     | account_type ENUM | Map QBO type string to ENUM (see mapping table below) |                                          |
| 3 | Detail Type     | String        | chart_of_accounts   | sub_type         | VARCHAR(100)  | TRIM; store as-is                                      |                                          |
| 4 | Description     | String        | —                   | —                | —             | —                                                      | [UNMAPPED] No description column in chart_of_accounts schema |
| 5 | Balance         | Currency      | —                   | —                | —             | —                                                      | [UNMAPPED] Used for post-import reconciliation only. Not stored; compared against computed GL balance. |
| 6 | Currency        | String        | —                   | —                | —             | —                                                      | [UNMAPPED] System assumes USD only. If non-USD found, HALT and flag [CPA_REVIEW_NEEDED]. |
| 7 | Account #       | String        | chart_of_accounts   | account_number   | VARCHAR(20)   | TRIM; if blank, assign from GA standard range          | If QBO has account numbers, preserve them. If not, auto-assign. |

### QBO Type --> DB account_type ENUM Mapping

| QBO Type String                | DB account_type ENUM | Notes                                    |
|--------------------------------|----------------------|------------------------------------------|
| `Bank`                         | `ASSET`              |                                          |
| `Accounts Receivable (A/R)`    | `ASSET`              |                                          |
| `Other Current Assets`         | `ASSET`              |                                          |
| `Fixed Assets`                 | `ASSET`              |                                          |
| `Other Assets`                 | `ASSET`              |                                          |
| `Accounts Payable (A/P)`       | `LIABILITY`          |                                          |
| `Credit Card`                  | `LIABILITY`          |                                          |
| `Other Current Liabilities`    | `LIABILITY`          |                                          |
| `Long Term Liabilities`        | `LIABILITY`          |                                          |
| `Equity`                       | `EQUITY`             |                                          |
| `Income`                       | `REVENUE`            |                                          |
| `Other Income`                 | `REVENUE`            |                                          |
| `Cost of Goods Sold`           | `EXPENSE`            | COGS maps to EXPENSE type in our schema  |
| `Expenses`                     | `EXPENSE`            |                                          |
| `Other Expenses`               | `EXPENSE`            |                                          |

### `chart_of_accounts` Table -- Columns Without QBO Source [NO_SOURCE]

| # | DB Column    | DB Type       | Source / Default Value                                  |
|---|--------------|---------------|---------------------------------------------------------|
| 1 | id           | UUID          | Auto-generated                                          |
| 2 | client_id    | UUID FK       | [NO_SOURCE] Determined by client-splitting logic. For Chart of Accounts, each client gets a copy of the full chart. |
| 3 | is_active    | BOOLEAN       | Default TRUE; set FALSE if QBO account is inactive      |
| 4 | created_at   | TIMESTAMPTZ   | Import timestamp                                        |
| 5 | updated_at   | TIMESTAMPTZ   | Import timestamp                                        |
| 6 | deleted_at   | TIMESTAMPTZ   | NULL                                                    |

---

## 3. Transaction Detail by Account --> `journal_entries` + `journal_entry_lines` Tables

### Header-Level Mapping (one row per unique Date + No. combination --> `journal_entries`)

| # | QBO Column Name    | QBO Data Type | DB Table         | DB Column          | DB Type       | Transform                                              | Notes                                    |
|---|--------------------|---------------|------------------|--------------------|---------------|--------------------------------------------------------|------------------------------------------|
| 1 | Date               | Date          | journal_entries  | entry_date         | DATE          | Parse MM/DD/YYYY                                       |                                          |
| 2 | No.                | String        | journal_entries  | reference_number   | VARCHAR(100)  | TRIM; preserve original QBO reference                  |                                          |
| 3 | Transaction Type   | String        | journal_entries  | description        | TEXT          | Prepend to description: "[QBO: {Transaction Type}] "   | Preserves original QBO transaction type for audit trail |
| 4 | Memo/Description   | String        | journal_entries  | description        | TEXT          | Append to description after transaction type prefix    | Truncation warning if > 1000 chars       |

### Line-Level Mapping (one row per CSV line --> `journal_entry_lines`)

| # | QBO Column Name    | QBO Data Type | DB Table              | DB Column    | DB Type        | Transform                                              | Notes                                    |
|---|--------------------|---------------|-----------------------|--------------|----------------|--------------------------------------------------------|------------------------------------------|
| 1 | Account            | String        | journal_entry_lines   | account_id   | UUID FK        | Resolve account name to chart_of_accounts.id via name match | FATAL if account not found           |
| 2 | Amount (positive)  | Currency      | journal_entry_lines   | debit        | NUMERIC(15,2)  | See sign convention normalization rules below           |                                          |
| 3 | Amount (negative)  | Currency      | journal_entry_lines   | credit       | NUMERIC(15,2)  | See sign convention normalization rules below           |                                          |
| 4 | Memo/Description   | String        | journal_entry_lines   | description  | TEXT           | TRIM; store per-line memo if different from header      |                                          |
| 5 | Split              | String        | —                     | —            | —              | [UNMAPPED] Used during parsing to identify contra account for 2-line entries; not stored separately |
| 6 | Balance            | Currency      | —                     | —            | —              | [UNMAPPED] Running balance is computed, not stored. Used for post-import verification only. |
| 7 | Name               | String        | —                     | —            | —              | Used for client-splitting logic (see client_splitting_logic.md). Not stored on journal_entry_lines. |
| 8 | Class              | String        | —                     | —            | —              | [UNMAPPED] [CPA_REVIEW_NEEDED] No class column in schema. May be used as client identifier. Store in description if needed. |
| 9 | Location           | String        | —                     | —            | —              | [UNMAPPED] No location column in schema. Store in description if needed. |

### Sign Convention Normalization Rules

```python
# For Transaction Detail by Account report (single Amount column):

def normalize_amount(amount: Decimal, account_type: str) -> tuple[Decimal, Decimal]:
    """
    Returns (debit_amount, credit_amount) for journal_entry_lines.

    QBO sign convention:
    - ASSET/EXPENSE accounts: positive = debit, negative = credit
    - LIABILITY/EQUITY/REVENUE accounts: positive = credit, negative = debit
    """
    if account_type in ('ASSET', 'EXPENSE'):
        if amount >= 0:
            return (amount, Decimal('0.00'))
        else:
            return (Decimal('0.00'), abs(amount))
    else:  # LIABILITY, EQUITY, REVENUE
        if amount >= 0:
            return (Decimal('0.00'), amount)
        else:
            return (abs(amount), Decimal('0.00'))
```

```python
# For General Journal report (separate Debit/Credit columns):
# No normalization needed -- use Debit and Credit values directly.
```

### `journal_entries` Table -- Columns Without QBO Source [NO_SOURCE]

| # | DB Column        | DB Type                | Source / Default Value                                  |
|---|------------------|------------------------|---------------------------------------------------------|
| 1 | id               | UUID                   | Auto-generated                                          |
| 2 | client_id        | UUID FK                | [NO_SOURCE] Determined by client-splitting logic from Name field |
| 3 | status           | journal_entry_status   | Set to 'POSTED' for migrated data (already approved in QBO) |
| 4 | created_by       | UUID FK                | [NO_SOURCE] Set to migration system user ID              |
| 5 | approved_by      | UUID FK                | [NO_SOURCE] Set to CPA_OWNER user ID (implicit approval) |
| 6 | posted_at        | TIMESTAMPTZ            | Set to entry_date at midnight UTC                       |
| 7 | created_at       | TIMESTAMPTZ            | Import timestamp                                        |
| 8 | updated_at       | TIMESTAMPTZ            | Import timestamp                                        |
| 9 | deleted_at       | TIMESTAMPTZ            | NULL                                                    |

### `journal_entry_lines` Table -- Columns Without QBO Source [NO_SOURCE]

| # | DB Column        | DB Type        | Source / Default Value                                  |
|---|------------------|----------------|---------------------------------------------------------|
| 1 | id               | UUID           | Auto-generated                                          |
| 2 | journal_entry_id | UUID FK        | FK to parent journal_entries.id                         |
| 3 | created_at       | TIMESTAMPTZ    | Import timestamp                                        |
| 4 | updated_at       | TIMESTAMPTZ    | Import timestamp                                        |
| 5 | deleted_at       | TIMESTAMPTZ    | NULL                                                    |

---

## 4. Invoice List --> `invoices` Table

| # | QBO Column Name    | QBO Data Type | DB Table   | DB Column      | DB Type          | Transform                                              | Notes                                    |
|---|--------------------|---------------|------------|----------------|------------------|--------------------------------------------------------|------------------------------------------|
| 1 | Invoice Date       | Date          | invoices   | invoice_date   | DATE             | Parse MM/DD/YYYY                                       |                                          |
| 2 | No.                | String        | invoices   | invoice_number | VARCHAR(100)     | TRIM                                                   |                                          |
| 3 | Customer           | String        | invoices   | customer_name  | VARCHAR(255)     | TRIM; also used to resolve client_id via splitting logic |                                         |
| 4 | Due Date           | Date          | invoices   | due_date       | DATE             | Parse MM/DD/YYYY                                       |                                          |
| 5 | Terms              | String        | —          | —              | —                | —                                                      | [UNMAPPED] No payment_terms column on invoices table |
| 6 | Memo/Description   | String        | —          | —              | —                | —                                                      | [UNMAPPED] No memo column on invoices table |
| 7 | Amount             | Currency      | invoices   | total_amount   | NUMERIC(15,2)    | Strip $ and commas; parse as decimal                   |                                          |
| 8 | Open Balance       | Currency      | —          | —              | —                | —                                                      | [UNMAPPED] Not stored directly. Balance computed from total_amount minus sum(invoice_payments.amount). Used for verification. |
| 9 | Status             | String        | invoices   | status         | invoice_status ENUM | Map QBO status to ENUM (see table below)             |                                          |
| 10 | Service Date      | Date          | —          | —              | —                | —                                                      | [UNMAPPED] No service_date in invoices schema |
| 11 | Class             | String        | —          | —              | —                | —                                                      | [UNMAPPED] No class column in invoices schema |

### QBO Invoice Status --> DB invoice_status ENUM

| QBO Status  | DB ENUM Value | Notes                                              |
|-------------|---------------|----------------------------------------------------|
| `Paid`      | `PAID`        |                                                    |
| `Deposited` | `PAID`        | Variant of Paid in some QBO versions               |
| `Open`      | `SENT`        | Using SENT as closest equivalent to "open"         |
| `Overdue`   | `OVERDUE`     |                                                    |
| `Voided`    | `VOID`        |                                                    |
| (blank)     | `SENT`        | Default if status column is missing                |

### `invoices` Table -- Columns Without QBO Source [NO_SOURCE]

| # | DB Column    | DB Type            | Source / Default Value                                  |
|---|--------------|--------------------|---------------------------------------------------------|
| 1 | id           | UUID               | Auto-generated                                          |
| 2 | client_id    | UUID FK            | [NO_SOURCE] Resolved from Customer via splitting logic  |
| 3 | created_at   | TIMESTAMPTZ        | Import timestamp (or invoice_date if preserving original) |
| 4 | updated_at   | TIMESTAMPTZ        | Import timestamp                                        |
| 5 | deleted_at   | TIMESTAMPTZ        | NULL                                                    |

### Invoice Line Items -- [NO_SOURCE] Warning

**[CPA_REVIEW_NEEDED]:** The Invoice List report does NOT include line item detail. It provides only the invoice-level summary (total amount, customer, dates). To import invoice line items into the `invoice_lines` table, one of these approaches is needed:

1. **Preferred:** Export individual invoices from QBO as PDFs and parse them (complex, not recommended for initial migration)
2. **Alternative:** Import header-only from Invoice List; line items populated later via Transaction Detail entries
3. **Alternative:** Accept that migrated invoices will have a single line item per invoice with the total amount

---

## 5. Payroll Summary/Detail --> `payroll_runs` + `payroll_items` Tables

### Payroll Run Mapping (one row per unique pay period --> `payroll_runs`)

| # | QBO Column Name | QBO Data Type | DB Table       | DB Column          | DB Type   | Transform                                              | Notes                                    |
|---|-----------------|---------------|----------------|--------------------|-----------|--------------------------------------------------------|------------------------------------------|
| 1 | Pay Period      | String        | payroll_runs   | pay_period_start   | DATE      | Parse start date from range string "MM/DD/YYYY to MM/DD/YYYY" |                                   |
| 2 | Pay Period      | String        | payroll_runs   | pay_period_end     | DATE      | Parse end date from range string                       |                                          |
| 3 | Pay Date        | Date          | payroll_runs   | pay_date           | DATE      | Parse MM/DD/YYYY; if absent, use pay_period_end + 5 days | Only available in Payroll Detail report  |

### Payroll Item Mapping (one row per employee per pay period --> `payroll_items`)

| # | QBO Column Name               | QBO Data Type | DB Table        | DB Column             | DB Type        | Transform                            | Notes                                    |
|---|-------------------------------|---------------|-----------------|-----------------------|----------------|--------------------------------------|------------------------------------------|
| 1 | Employee                      | String        | payroll_items   | employee_id           | UUID FK        | Resolve employee name to employees.id | FATAL if employee not found in employees table |
| 2 | Gross Pay                     | Currency      | payroll_items   | gross_pay             | NUMERIC(15,2)  | Strip $ and commas                   |                                          |
| 3 | Federal Withholding           | Currency      | payroll_items   | federal_withholding   | NUMERIC(15,2)  | Strip $ and commas                   |                                          |
| 4 | GA Withholding / State Tax    | Currency      | payroll_items   | state_withholding     | NUMERIC(15,2)  | Strip $ and commas                   | Column header varies; match on partial name |
| 5 | Social Security Employee      | Currency      | payroll_items   | social_security       | NUMERIC(15,2)  | Strip $ and commas                   |                                          |
| 6 | Medicare Employee             | Currency      | payroll_items   | medicare              | NUMERIC(15,2)  | Strip $ and commas                   |                                          |
| 7 | Net Pay                       | Currency      | payroll_items   | net_pay               | NUMERIC(15,2)  | Strip $ and commas                   |                                          |
| 8 | GA SUI / GA Unemployment      | Currency      | payroll_items   | ga_suta               | NUMERIC(15,2)  | Strip $ and commas                   | Employer-side tax                        |
| 9 | Federal Unemployment / FUTA   | Currency      | payroll_items   | futa                  | NUMERIC(15,2)  | Strip $ and commas                   | Employer-side tax                        |
| 10 | Social Security Employer     | Currency      | —               | —                     | —              | —                                    | [UNMAPPED] No employer_ss column in payroll_items. Should match employee SS amount. Validate but do not store separately. |
| 11 | Medicare Employer            | Currency      | —               | —                     | —              | —                                    | [UNMAPPED] No employer_medicare column in payroll_items. Should match employee Medicare amount. Validate but do not store separately. |
| 12 | Hours                        | Numeric       | —               | —                     | —              | —                                    | [UNMAPPED] No hours column in payroll_items schema |
| 13 | Check No.                    | String        | —               | —                     | —              | —                                    | [UNMAPPED] No check number in payroll_items schema |
| 14 | Workers' Comp                | Currency      | —               | —                     | —              | —                                    | [UNMAPPED] Premium tier only; no column in schema |

### `payroll_runs` Table -- Columns Without QBO Source [NO_SOURCE]

| # | DB Column     | DB Type               | Source / Default Value                                  |
|---|---------------|-----------------------|---------------------------------------------------------|
| 1 | id            | UUID                  | Auto-generated                                          |
| 2 | client_id     | UUID FK               | [NO_SOURCE] Determined by employee-to-client mapping CSV provided by CPA |
| 3 | status        | payroll_run_status    | Set to 'FINALIZED' for migrated data                    |
| 4 | finalized_by  | UUID FK               | [NO_SOURCE] Set to CPA_OWNER user ID                    |
| 5 | finalized_at  | TIMESTAMPTZ           | Set to pay_date at midnight UTC                         |
| 6 | created_at    | TIMESTAMPTZ           | Import timestamp                                        |
| 7 | updated_at    | TIMESTAMPTZ           | Import timestamp                                        |
| 8 | deleted_at    | TIMESTAMPTZ           | NULL                                                    |

### `payroll_items` Table -- Columns Without QBO Source [NO_SOURCE]

| # | DB Column      | DB Type        | Source / Default Value                                  |
|---|----------------|----------------|---------------------------------------------------------|
| 1 | id             | UUID           | Auto-generated                                          |
| 2 | payroll_run_id | UUID FK        | FK to parent payroll_runs.id                            |
| 3 | created_at     | TIMESTAMPTZ    | Import timestamp                                        |
| 4 | updated_at     | TIMESTAMPTZ    | Import timestamp                                        |
| 5 | deleted_at     | TIMESTAMPTZ    | NULL                                                    |

---

## 6. Employee Details --> `employees` Table

| # | QBO Column Name            | QBO Data Type | DB Table   | DB Column          | DB Type        | Transform                            | Notes                                    |
|---|----------------------------|---------------|------------|--------------------|----------------|--------------------------------------|------------------------------------------|
| 1 | Employee                   | String        | employees  | first_name         | VARCHAR(100)   | Split on space: first token = first_name | Handle "Last, First" format too       |
| 2 | Employee                   | String        | employees  | last_name          | VARCHAR(100)   | Split on space: remaining tokens = last_name |                                      |
| 3 | SSN (last 4)               | String        | —          | —                  | —              | —                                    | [UNMAPPED] Only last 4 digits; full SSN must be provided separately by CPA for ssn_encrypted |
| 4 | Hire Date                  | Date          | employees  | hire_date          | DATE           | Parse MM/DD/YYYY                     |                                          |
| 5 | Status                     | String        | employees  | is_active          | BOOLEAN        | 'Active' -> TRUE; 'Terminated'/'Inactive' -> FALSE |                              |
| 6 | Status                     | String        | employees  | termination_date   | DATE           | If 'Terminated', need termination date from QBO (may not be in export) | [CPA_REVIEW_NEEDED] QBO may not export termination date |
| 7 | Pay Rate                   | Currency      | employees  | pay_rate           | NUMERIC(15,2)  | Strip $ and commas                   |                                          |
| 8 | Pay Type                   | String        | employees  | pay_type           | pay_type ENUM  | 'Hourly' -> 'HOURLY'; 'Salary' -> 'SALARY' |                                     |
| 9 | Pay Schedule               | String        | —          | —                  | —              | —                                    | [UNMAPPED] No pay_schedule in employees schema |
| 10 | Filing Status (Federal)   | String        | employees  | filing_status      | filing_status ENUM | 'Single' -> 'SINGLE'; 'Married' -> 'MARRIED'; etc. |                          |
| 11 | Allowances/Withholding    | String        | employees  | allowances         | INT            | Parse integer; if extra withholding amount, store separately | May be "$50.00" instead of count |

### `employees` Table -- Columns Without QBO Source [NO_SOURCE]

| # | DB Column          | DB Type        | Source / Default Value                                  |
|---|--------------------|----------------|---------------------------------------------------------|
| 1 | id                 | UUID           | Auto-generated                                          |
| 2 | client_id          | UUID FK        | [NO_SOURCE] Determined by employee-to-client mapping CSV |
| 3 | ssn_encrypted      | BYTEA          | [NO_SOURCE] CPA must provide full SSNs separately       |
| 4 | termination_date   | DATE           | [NO_SOURCE] If status = Terminated, CPA must provide dates |
| 5 | created_at         | TIMESTAMPTZ    | Import timestamp                                        |
| 6 | updated_at         | TIMESTAMPTZ    | Import timestamp                                        |
| 7 | deleted_at         | TIMESTAMPTZ    | NULL                                                    |

---

## 7. Vendor Contact List --> `vendors` Table

| # | QBO Column Name | QBO Data Type | DB Table | DB Column          | DB Type       | Transform                            | Notes                                    |
|---|-----------------|---------------|----------|--------------------|---------------|--------------------------------------|------------------------------------------|
| 1 | Vendor          | String        | vendors  | name               | VARCHAR(255)  | TRIM                                 |                                          |
| 2 | Company         | String        | —        | —                  | —             | —                                    | [UNMAPPED] May duplicate Vendor name     |
| 3 | Phone           | String        | vendors  | phone              | VARCHAR(20)   | Strip formatting except +, -, (, )   |                                          |
| 4 | Email           | String        | vendors  | email              | VARCHAR(255)  | Lowercase, TRIM                      |                                          |
| 5 | Street          | String        | vendors  | address            | VARCHAR(500)  | TRIM                                 |                                          |
| 6 | City            | String        | vendors  | city               | VARCHAR(100)  | TRIM                                 |                                          |
| 7 | State           | String        | vendors  | state              | VARCHAR(2)    | Convert to 2-letter abbreviation     |                                          |
| 8 | ZIP             | String        | vendors  | zip                | VARCHAR(10)   | TRIM                                 |                                          |
| 9 | Country         | String        | —        | —                  | —             | —                                    | [UNMAPPED] Not in vendors schema         |
| 10 | Tax ID         | String        | vendors  | tax_id_encrypted   | BYTEA         | Encrypt at application layer (AES-256) | May be masked (XX-XXXXX89); if masked, CPA must provide full TIN |
| 11 | 1099 Tracking  | String        | —        | —                  | —             | —                                    | [UNMAPPED] No 1099_tracking column in vendors schema. Should be added or tracked separately. |
| 12 | Terms          | String        | —        | —                  | —             | —                                    | [UNMAPPED] No terms column in vendors schema |
| 13 | Open Balance   | Currency      | —        | —                  | —             | —                                    | [UNMAPPED] Computed from AP records; used for verification only |
| 14 | Website        | String        | —        | —                  | —             | —                                    | [UNMAPPED] Not in vendors schema         |
| 15 | Account No.    | String        | —        | —                  | —             | —                                    | [UNMAPPED] Your account number with vendor; not in schema |

### `vendors` Table -- Columns Without QBO Source [NO_SOURCE]

| # | DB Column          | DB Type    | Source / Default Value                                  |
|---|--------------------|-----------|---------------------------------------------------------|
| 1 | id                 | UUID      | Auto-generated                                          |
| 2 | client_id          | UUID FK   | [NO_SOURCE] Determined by which client uses this vendor. May need CPA mapping if vendors are shared across clients. |
| 3 | created_at         | TIMESTAMPTZ | Import timestamp                                      |
| 4 | updated_at         | TIMESTAMPTZ | Import timestamp                                      |
| 5 | deleted_at         | TIMESTAMPTZ | NULL                                                  |

---

## 8. Bills / AP Export --> `bills` + `bill_lines` Tables

| # | QBO Column Name    | QBO Data Type | DB Table | DB Column    | DB Type       | Transform                            | Notes                                    |
|---|--------------------|---------------|----------|--------------|---------------|--------------------------------------|------------------------------------------|
| 1 | Date               | Date          | bills    | bill_date    | DATE          | Parse MM/DD/YYYY                     |                                          |
| 2 | No.                | String        | bills    | bill_number  | VARCHAR(100)  | TRIM                                 |                                          |
| 3 | Vendor             | String        | bills    | vendor_id    | UUID FK       | Resolve vendor name to vendors.id     | FATAL if vendor not found               |
| 4 | Due Date           | Date          | bills    | due_date     | DATE          | Parse MM/DD/YYYY                     |                                          |
| 5 | Amount             | Currency      | bills    | total_amount | NUMERIC(15,2) | Strip $ and commas                   |                                          |
| 6 | Open Balance       | Currency      | —        | —            | —             | —                                    | [UNMAPPED] Used for status derivation and verification |
| 7 | Terms              | String        | —        | —            | —             | —                                    | [UNMAPPED] No terms column on bills table |
| 8 | Memo/Description   | String        | —        | —            | —             | —                                    | [UNMAPPED] No memo column on bills table  |
| 9 | Status (derived)   | String        | bills    | status       | bill_status   | Derive from Open Balance: 0 = PAID, >0 = APPROVED, voided = VOID |                    |
| 10 | Account           | String        | bill_lines | account_id | UUID FK       | Resolve to chart_of_accounts.id      | Used to create bill line items           |

### `bills` Table -- Columns Without QBO Source [NO_SOURCE]

| # | DB Column    | DB Type        | Source / Default Value                                  |
|---|--------------|----------------|---------------------------------------------------------|
| 1 | id           | UUID           | Auto-generated                                          |
| 2 | client_id    | UUID FK        | [NO_SOURCE] Resolved from vendor-to-client relationship |
| 3 | created_at   | TIMESTAMPTZ    | Import timestamp                                        |
| 4 | updated_at   | TIMESTAMPTZ    | Import timestamp                                        |
| 5 | deleted_at   | TIMESTAMPTZ    | NULL                                                    |

---

## 9. Summary of All [UNMAPPED] QBO Columns

These QBO columns exist in exports but have no target in the current database schema:

| QBO Export           | QBO Column          | Recommendation                                        |
|----------------------|---------------------|-------------------------------------------------------|
| Customer List        | Company             | Store in notes or add company_name column to clients   |
| Customer List        | Shipping address    | Not needed for CPA firm (services, not products)       |
| Customer List        | Open Balance        | Use for post-import verification only                  |
| Customer List        | Notes               | Parse for entity_type hints; consider adding notes col |
| Customer List        | Tax Resale No.      | Consider adding to clients schema if needed for ST-3   |
| Customer List        | Terms               | Consider adding default_terms to clients schema        |
| Customer List        | Full Name           | Store as contact_name or ignore                        |
| Customer List        | Website             | Not needed                                             |
| Chart of Accounts   | Description         | Consider adding description column to chart_of_accounts |
| Chart of Accounts   | Balance             | Post-import verification only                          |
| Chart of Accounts   | Currency            | Halt on non-USD                                        |
| Transactions         | Split               | Used during parsing only                               |
| Transactions         | Balance             | Post-import verification only                          |
| Transactions         | Class               | [CPA_REVIEW_NEEDED] May be used for client splitting   |
| Transactions         | Location            | Not needed unless CPA uses for reporting               |
| Invoice List         | Terms               | Consider adding to invoices schema                     |
| Invoice List         | Memo/Description    | Consider adding memo column to invoices schema         |
| Invoice List         | Open Balance        | Computed from payments                                 |
| Invoice List         | Service Date        | Not needed                                             |
| Payroll              | Employer SS         | Validate only; equals Employee SS                      |
| Payroll              | Employer Medicare   | Validate only; equals Employee Medicare                |
| Payroll              | Hours               | Consider adding hours column to payroll_items          |
| Payroll              | Check No.           | Consider adding check_number to payroll_items          |
| Vendor List          | Company             | Duplicate of Vendor name typically                     |
| Vendor List          | 1099 Tracking       | Consider adding is_1099 boolean to vendors schema      |
| Vendor List          | Terms               | Consider adding default_terms to vendors schema        |
| Vendor List          | Open Balance        | Computed from AP records                               |

---

## 10. Summary of All [NO_SOURCE] DB Columns

These database columns need values but have no direct QBO CSV source:

| DB Table             | DB Column           | Resolution                                             |
|----------------------|---------------------|-------------------------------------------------------|
| clients              | entity_type         | CPA must provide supplemental CSV                      |
| clients              | tax_id_encrypted    | CPA must provide TINs separately                       |
| chart_of_accounts    | client_id           | Assigned via client-splitting logic                    |
| journal_entries      | client_id           | Assigned via client-splitting logic                    |
| journal_entries      | created_by          | System migration user                                  |
| journal_entries      | approved_by         | CPA_OWNER user                                         |
| journal_entries      | status              | Set to POSTED for migrated data                        |
| invoices             | client_id           | Resolved from Customer name                            |
| payroll_runs         | client_id           | Resolved from employee-to-client mapping               |
| payroll_runs         | status              | Set to FINALIZED for migrated data                     |
| payroll_runs         | finalized_by        | CPA_OWNER user                                         |
| payroll_items        | payroll_run_id      | FK to parent payroll_runs                              |
| employees            | client_id           | CPA must provide employee-to-client mapping CSV        |
| employees            | ssn_encrypted       | CPA must provide full SSNs separately                  |
| employees            | termination_date    | CPA must provide for terminated employees              |
| vendors              | client_id           | CPA must provide vendor-to-client mapping              |
| bills                | client_id           | Inferred from vendor's client_id                       |

---

## 11. Supplemental CSV Files Required from CPA

Before migration, the CPA must prepare and provide these mapping files:

### 11.1 Entity Type Mapping (`entity_type_mapping.csv`)

```csv
customer_name,entity_type
"Peachtree Landscaping LLC","PARTNERSHIP_LLC"
"Smith Consulting","SOLE_PROP"
"Atlanta Tech Solutions Inc","S_CORP"
```

### 11.2 Employee-to-Client Mapping (`employee_client_mapping.csv`)

```csv
employee_name,client_name
"John Smith","Peachtree Landscaping LLC"
"Jane Doe","Atlanta Tech Solutions Inc"
"Mike Johnson","Smith Consulting"
```

### 11.3 Vendor-to-Client Mapping (`vendor_client_mapping.csv`)

```csv
vendor_name,client_name
"Georgia Power","Peachtree Landscaping LLC"
"Georgia Power","Atlanta Tech Solutions Inc"
"Office Depot","Smith Consulting"
```

Note: Vendors may serve multiple clients. The vendor record will be duplicated per client to maintain client isolation.

### 11.4 Full SSN File (`employee_ssn.csv`) -- SENSITIVE

```csv
employee_name,ssn
"John Smith","123-45-6789"
"Jane Doe","987-65-4321"
```

**WARNING:** This file must be encrypted at rest and deleted after import. Never commit to version control.
