# QuickBooks Online to PostgreSQL Migration Specification

**Firm Profile:** Georgia CPA firm, 26-50 clients
**Source System:** QuickBooks Online (QBO)
**Target System:** Custom PostgreSQL database
**Spec Date:** 2026-03-04

---

## 1. Required QB Online CSV Exports

Each export must be pulled from the QBO web interface using the exact menu paths below. All exports should cover the **full date range** of the client's history (or the agreed-upon cutover period).

### 1.1 Chart of Accounts

**Menu Path:** Reports > Accounting > Account List > Export to Excel

| Expected Column        | Description                              |
|------------------------|------------------------------------------|
| Account                | Account name                             |
| Type                   | Account type (e.g., Bank, Expense, Income) |
| Detail Type            | Sub-classification within the type       |
| Description            | Free-text description                    |
| Balance                | Current balance at time of export        |
| Currency               | Currency code (USD expected)             |
| Account Number         | User-assigned account number (if enabled)|

**Notes:**
- If "Account Numbers" are not enabled in QBO Settings > Advanced, the Account Number column will be blank or absent.
- [CPA_REVIEW_NEEDED] QBO may include inactive/archived accounts. Decide whether to import these as inactive or skip.

### 1.2 General Ledger / Transaction Detail by Account

**Menu Path:** Reports > All > Transaction Detail by Account > Export

| Expected Column        | Description                                    |
|------------------------|------------------------------------------------|
| Date                   | Transaction date (MM/DD/YYYY)                  |
| Transaction Type       | Type (e.g., Invoice, Bill, Journal Entry, Check) |
| Num                    | Transaction/check number                       |
| Name                   | Customer, vendor, or employee name             |
| Memo/Description       | Free-text memo                                 |
| Split                  | Contra account(s) for the entry                |
| Amount                 | Signed amount (positive = debit, negative = credit, context-dependent) |
| Balance                | Running balance                                |
| Account                | Account the line posts to                      |
| Class                  | Class tracking label (if enabled)              |
| Location               | Location/department label (if enabled)         |

**Notes:**
- Set the date range filter to cover the entire migration period before exporting.
- [CPA_REVIEW_NEEDED] The "Amount" column sign convention varies by account type in QBO. Asset/Expense accounts show debits as positive; Liability/Equity/Income accounts show credits as positive. The import script must normalize this.

### 1.3 Customer / Client List

**Menu Path:** Reports > All > Customer Contact List > Export

| Expected Column        | Description                          |
|------------------------|--------------------------------------|
| Customer               | Full display name                    |
| Company                | Company name                         |
| Phone                  | Primary phone                        |
| Email                  | Primary email                        |
| Street                 | Billing street address               |
| City                   | Billing city                         |
| State                  | Billing state                        |
| ZIP                    | Billing ZIP code                     |
| Country                | Billing country                      |
| Open Balance           | Outstanding balance                  |
| Notes                  | Internal notes                       |
| Tax Resale Number      | Resale certificate number (if set)   |
| Terms                  | Payment terms (e.g., Net 30)         |

### 1.4 Invoice List

**Menu Path:** Reports > All > Invoice List > Export

| Expected Column        | Description                          |
|------------------------|--------------------------------------|
| Invoice Date           | Date the invoice was created         |
| Num                    | Invoice number                       |
| Customer               | Customer display name                |
| Due Date               | Payment due date                     |
| Terms                  | Payment terms                        |
| Memo                   | Invoice memo                         |
| Amount                 | Total invoice amount                 |
| Open Balance           | Remaining unpaid amount              |
| Status                 | Paid, Open, Overdue, Voided          |
| Service Date           | Service/delivery date (if set)       |
| Class                  | Class label (if enabled)             |

### 1.5 Payroll Summary

**Menu Path:** Reports > Payroll > Payroll Summary > Export

| Expected Column        | Description                          |
|------------------------|--------------------------------------|
| Employee               | Employee display name                |
| Pay Period             | Start-end date of pay period         |
| Gross Pay              | Total gross compensation             |
| Federal Tax            | Federal income tax withheld          |
| State Tax              | Georgia state income tax withheld    |
| Social Security        | Employee SS withholding              |
| Medicare               | Employee Medicare withholding        |
| Net Pay                | Net pay after all deductions         |
| Employer SS            | Employer SS contribution             |
| Employer Medicare      | Employer Medicare contribution       |
| GA Unemployment        | Georgia unemployment tax (GASUI)     |
| Federal Unemployment   | FUTA contribution                    |

**Notes:**
- [CPA_REVIEW_NEEDED] QBO payroll export column names can vary between QBO Payroll tiers (Core, Premium, Elite). Confirm with actual export before finalizing column map.

### 1.6 Employee List

**Menu Path:** Reports > Payroll > Employee Details > Export

| Expected Column        | Description                          |
|------------------------|--------------------------------------|
| Employee               | Full name                            |
| SSN (last 4)          | Last four digits (if exported)       |
| Hire Date              | Date of hire                         |
| Status                 | Active / Terminated                  |
| Pay Rate               | Current pay rate                     |
| Pay Schedule           | Pay frequency                        |
| Filing Status          | Federal W-4 filing status            |
| GA Filing Status       | Georgia G-4 filing status            |

**Notes:**
- QBO may not export full SSNs. Only last-4 may be available in CSV. Full SSNs must be obtained separately and stored encrypted (AES-256 at rest).

### 1.7 Vendor List

**Menu Path:** Reports > Expenses and Vendors > Vendor Contact List > Export

| Expected Column        | Description                          |
|------------------------|--------------------------------------|
| Vendor                 | Display name                         |
| Company                | Company name                         |
| Phone                  | Primary phone                        |
| Email                  | Primary email                        |
| Street                 | Street address                       |
| City                   | City                                 |
| State                  | State                                |
| ZIP                    | ZIP code                             |
| Tax ID                 | TIN / EIN (if exported)              |
| 1099 Tracking          | Whether vendor is flagged for 1099   |
| Terms                  | Payment terms                        |
| Open Balance           | Outstanding balance owed to vendor   |

---

## 2. Column Mapping

### 2.1 Clients Table Mapping

| QB Online Column (Customer Contact List) | PostgreSQL Column   | Type            | Notes                                |
|------------------------------------------|---------------------|-----------------|--------------------------------------|
| Customer                                 | client_name         | VARCHAR(255)    | Primary matching key                 |
| Company                                  | company_name        | VARCHAR(255)    | May duplicate Customer               |
| Phone                                    | phone               | VARCHAR(20)     |                                      |
| Email                                    | email               | VARCHAR(255)    |                                      |
| Street                                   | address_street      | VARCHAR(255)    |                                      |
| City                                     | address_city        | VARCHAR(100)    |                                      |
| State                                    | address_state       | CHAR(2)         | Normalize to 2-letter code           |
| ZIP                                      | address_zip         | VARCHAR(10)     |                                      |
| Country                                  | address_country     | CHAR(2)         | Default 'US' if blank                |
| Open Balance                             | opening_balance     | NUMERIC(15,2)   | Used for reconciliation              |
| Notes                                    | notes               | TEXT            |                                      |
| Terms                                    | payment_terms       | VARCHAR(50)     |                                      |
| (generated)                              | client_id           | SERIAL / UUID   | Auto-generated primary key           |
| (generated)                              | created_at          | TIMESTAMPTZ     | Import timestamp                     |
| (generated)                              | source_system       | VARCHAR(20)     | Hardcode 'QBO'                       |

### 2.2 Chart of Accounts Mapping

QB Online account types must be mapped to a Georgia-standard chart of accounts structure.

| QB Online Type   | QB Detail Type (examples)            | GA Standard Category | Account Range |
|------------------|--------------------------------------|----------------------|---------------|
| Bank             | Checking, Savings, Money Market      | Cash & Equivalents   | 1000-1099     |
| Accounts Receivable | Accounts Receivable              | Receivables          | 1100-1199     |
| Other Current Asset | Prepaid Expenses, Undeposited Funds | Other Current Assets | 1200-1499   |
| Fixed Asset      | Furniture, Vehicles, Equipment       | Fixed Assets         | 1500-1799     |
| Other Asset      | Security Deposits, Long-term         | Other Assets         | 1800-1999     |
| Accounts Payable | Accounts Payable                     | Current Liabilities  | 2000-2099     |
| Credit Card      | Credit Card                          | Current Liabilities  | 2100-2199     |
| Other Current Liability | Payroll Liabilities, Sales Tax | Current Liabilities  | 2200-2499     |
| Long Term Liability | Notes Payable, Mortgages          | Long-term Liabilities| 2500-2999     |
| Equity           | Owner's Equity, Retained Earnings    | Equity               | 3000-3999     |
| Income           | Sales, Service Revenue               | Revenue              | 4000-4999     |
| Other Income     | Interest Income, Gain on Sale        | Other Revenue        | 5000-5199     |
| Cost of Goods Sold | COGS, Materials, Labor             | Cost of Sales        | 5200-5999     |
| Expense          | Rent, Utilities, Office Supplies     | Operating Expenses   | 6000-7999     |
| Other Expense    | Depreciation, Amortization           | Other Expenses       | 8000-8999     |

| QB Online Column (Account List) | PostgreSQL Column       | Type            | Notes                              |
|----------------------------------|-------------------------|-----------------|------------------------------------|
| Account                          | account_name            | VARCHAR(255)    |                                    |
| Account Number                   | qbo_account_number      | VARCHAR(20)     | Original QBO number (if any)       |
| Type                             | account_type            | VARCHAR(50)     | Mapped per table above             |
| Detail Type                      | account_subtype         | VARCHAR(100)    |                                    |
| Description                      | description             | TEXT            |                                    |
| Balance                          | qbo_export_balance      | NUMERIC(15,2)   | Snapshot for reconciliation only   |
| (generated)                      | account_id              | SERIAL          | Auto-generated                     |
| (generated)                      | account_number          | VARCHAR(10)     | Assigned from GA range above       |
| (generated)                      | client_id               | INT / UUID      | FK to clients table                |
| (generated)                      | is_active               | BOOLEAN         | Default TRUE                       |

### 2.3 Transactions Mapping (Double-Entry)

Each QBO transaction line becomes **two or more journal entry lines** in the target system to enforce double-entry bookkeeping.

| QB Online Column (Transaction Detail) | PostgreSQL Column       | Type            | Notes                                    |
|---------------------------------------|-------------------------|-----------------|------------------------------------------|
| Date                                  | transaction_date        | DATE            | Parse from MM/DD/YYYY                    |
| Transaction Type                      | source_type             | VARCHAR(50)     | Original QBO type for audit trail        |
| Num                                   | reference_number        | VARCHAR(50)     |                                          |
| Name                                  | counterparty_name       | VARCHAR(255)    | Used for client-splitting (see Section 3)|
| Memo/Description                      | memo                    | TEXT            | Truncate at 1000 chars, flag if longer   |
| Account                               | account_id              | INT             | FK - resolved via chart of accounts      |
| Amount (positive)                     | debit_amount            | NUMERIC(15,2)   | See sign convention note                 |
| Amount (negative)                     | credit_amount           | NUMERIC(15,2)   | Absolute value of negative amounts       |
| Split                                 | contra_account_id       | INT             | FK - used to generate contra entry       |
| Class                                 | class_label             | VARCHAR(100)    | [CPA_REVIEW_NEEDED] See Section 7        |
| Location                              | location_label          | VARCHAR(100)    |                                          |
| (generated)                           | journal_entry_id        | SERIAL          | Groups debit + credit lines              |
| (generated)                           | line_number             | SMALLINT        | Line within the journal entry            |
| (generated)                           | client_id               | INT / UUID      | FK - determined by splitting logic       |
| (generated)                           | created_at              | TIMESTAMPTZ     | Import timestamp                         |
| (generated)                           | source_system           | VARCHAR(20)     | 'QBO'                                    |

**Sign Convention Normalization:**
```
IF account_type IN (Asset, Expense):
    positive Amount = debit_amount
    negative Amount = credit_amount (absolute value)
ELSE (Liability, Equity, Income):
    positive Amount = credit_amount
    negative Amount = debit_amount (absolute value)
```

### 2.4 Invoices Mapping

| QB Online Column (Invoice List) | PostgreSQL Column       | Type            | Notes                          |
|----------------------------------|-------------------------|-----------------|--------------------------------|
| Num                              | invoice_number          | VARCHAR(50)     | Unique within client           |
| Invoice Date                     | invoice_date            | DATE            |                                |
| Customer                         | client_id               | INT / UUID      | FK resolved via client name    |
| Due Date                         | due_date                | DATE            |                                |
| Terms                            | payment_terms           | VARCHAR(50)     |                                |
| Memo                             | memo                    | TEXT            |                                |
| Amount                           | total_amount            | NUMERIC(15,2)   |                                |
| Open Balance                     | balance_due             | NUMERIC(15,2)   |                                |
| Status                           | status                  | VARCHAR(20)     | Map: Paid/Open/Overdue/Voided  |
| (generated)                      | invoice_id              | SERIAL          |                                |
| (generated)                      | created_at              | TIMESTAMPTZ     |                                |

### 2.5 Payroll Records Mapping

| QB Online Column (Payroll Summary)  | PostgreSQL Column          | Type            | Notes                     |
|--------------------------------------|----------------------------|-----------------|---------------------------|
| Employee                             | employee_name              | VARCHAR(255)    |                           |
| Pay Period                           | pay_period_start           | DATE            | Parse start from range    |
| Pay Period                           | pay_period_end             | DATE            | Parse end from range      |
| Gross Pay                            | gross_pay                  | NUMERIC(12,2)   |                           |
| Federal Tax                          | federal_tax_withheld       | NUMERIC(12,2)   |                           |
| State Tax                            | ga_state_tax_withheld      | NUMERIC(12,2)   | Georgia-specific          |
| Social Security                      | employee_ss               | NUMERIC(12,2)   |                           |
| Medicare                             | employee_medicare          | NUMERIC(12,2)   |                           |
| Net Pay                              | net_pay                    | NUMERIC(12,2)   |                           |
| Employer SS                          | employer_ss               | NUMERIC(12,2)   |                           |
| Employer Medicare                    | employer_medicare          | NUMERIC(12,2)   |                           |
| GA Unemployment                      | ga_sui                    | NUMERIC(12,2)   | Georgia SUTA              |
| Federal Unemployment                 | futa                      | NUMERIC(12,2)   |                           |
| (generated)                          | payroll_record_id          | SERIAL          |                           |
| (generated)                          | client_id                  | INT / UUID      | FK - from splitting logic |
| (generated)                          | created_at                 | TIMESTAMPTZ     |                           |

---

## 3. Client-Splitting Logic

### Problem

QuickBooks Online stores all clients within a single company file. The target PostgreSQL schema isolates each client into its own ledger via `client_id` foreign keys on every table.

### Matching Strategy

```
Primary Key:   "Customer" or "Name" field from QBO exports
Fallback:      "Company" field (if Customer is blank)
Normalization: TRIM + UPPER + collapse whitespace
```

**Step-by-step process:**

1. **Build the client registry** from the Customer Contact List export. Each unique `Customer` value becomes a row in the `clients` table with a generated `client_id`.

2. **Match transactions** by comparing the `Name` column in the Transaction Detail export against the client registry using normalized string matching.

3. **Match invoices** by comparing the `Customer` column in the Invoice List against the client registry.

4. **Match payroll** by associating employees with clients. This requires a supplemental mapping file (see below).

### Supplemental Mapping File

Because QBO does not natively link employees to specific clients in a multi-client firm, the CPA must provide a CSV:

```
employee_name,client_name
"John Smith","ABC Corp"
"Jane Doe","XYZ LLC"
```

### Edge Cases

| Scenario                                  | Handling                                                          |
|-------------------------------------------|-------------------------------------------------------------------|
| Transaction Name matches no client        | Assign `client_id = NULL`, flag as `[UNASSIGNED]` for CPA review  |
| Transaction Name matches multiple clients | Flag as `[AMBIGUOUS]` for CPA review, do not auto-assign          |
| Transaction spans multiple clients        | Split not attempted automatically; flag as `[MULTI_CLIENT]`       |
| Blank Name field                          | Assign `client_id = NULL`, flag as `[UNASSIGNED]`                 |
| Client name variations (e.g., "ABC Corp" vs "ABC Corporation") | Use fuzzy match (Levenshtein distance <= 3) and flag as `[FUZZY_MATCH]` for CPA confirmation |
| Inter-client transactions                 | Flag as `[INTER_CLIENT]` for CPA review; do not auto-resolve     |

### Output

After splitting, generate a summary report:

```
Client Splitting Summary
========================
Total transactions processed:  X
Assigned to clients:           X (Y%)
Flagged [UNASSIGNED]:          X
Flagged [AMBIGUOUS]:           X
Flagged [MULTI_CLIENT]:        X
Flagged [FUZZY_MATCH]:         X
Flagged [INTER_CLIENT]:        X
```

---

## 4. Data Validation Rules

All validations run **before** any data is written to the database. A single validation failure aborts the entire import.

### 4.1 Structural Validations

| Rule ID | Check                                  | Applies To           | Severity |
|---------|----------------------------------------|----------------------|----------|
| V-001   | Required columns present in CSV header | All exports          | FATAL    |
| V-002   | No empty/zero-row CSV files            | All exports          | FATAL    |
| V-003   | UTF-8 encoding (or convertible)        | All exports          | FATAL    |
| V-004   | No BOM characters corrupting headers   | All exports          | WARNING  |

### 4.2 Referential Validations

| Rule ID | Check                                           | Applies To           | Severity |
|---------|-------------------------------------------------|----------------------|----------|
| V-010   | Client identifier (Name/Customer) is not NULL   | Transactions, Invoices | FATAL  |
| V-011   | All Account references resolve to chart of accounts | Transactions      | FATAL    |
| V-012   | All Customer references resolve to clients table | Invoices             | FATAL    |
| V-013   | All Employee references resolve to employee list | Payroll              | FATAL    |
| V-014   | Split/contra account references resolve          | Transactions         | WARNING  |

### 4.3 Data Integrity Validations

| Rule ID | Check                                           | Applies To           | Severity |
|---------|-------------------------------------------------|----------------------|----------|
| V-020   | Dates parseable as MM/DD/YYYY or YYYY-MM-DD     | All dated records    | FATAL    |
| V-021   | All dates within reasonable range (2000-01-01 to today) | All dated records | WARNING |
| V-022   | Amounts parseable as numeric (strip $ and commas)| All monetary fields  | FATAL    |
| V-023   | No duplicate transaction IDs (Num + Date + Amount combo) | Transactions  | FATAL    |
| V-024   | Debits = Credits per journal entry (tolerance: $0.01) | Transactions     | FATAL    |
| V-025   | Invoice amounts are non-negative                 | Invoices             | WARNING  |
| V-026   | Net Pay = Gross Pay - sum(deductions) (tolerance: $0.01) | Payroll        | WARNING  |

### 4.4 Georgia-Specific Validations

| Rule ID | Check                                           | Applies To           | Severity |
|---------|-------------------------------------------------|----------------------|----------|
| V-030   | State tax field labeled/mapped for Georgia       | Payroll              | WARNING  |
| V-031   | GA SUI rate within expected range (0.04%-8.1%)   | Payroll              | WARNING  |

### 4.5 Validation Output

```
Validation Report
=================
File: transaction_detail.csv
Records scanned: 12,456
FATAL errors:    0
WARNINGS:        3

[WARNING] V-021: 2 records have dates before 2010-01-01 (rows 445, 1023)
[WARNING] V-014: 1 record has unresolved Split account "Ask My Accountant" (row 8821)
[WARNING] V-031: GA SUI rate 9.2% exceeds expected max of 8.1% for client "XYZ LLC"

Result: PASS (0 fatal errors)
```

---

## 5. Import Order

The import must follow this exact sequence due to foreign key dependencies.

```
Step 1: Clients
   |
   v
Step 2: Chart of Accounts (per client)
   |
   v
Step 3: Opening Balances (as journal entries dated = cutover date)
   |
   v
Step 4: Transactions (ordered by date ASC, then by Num ASC)
   |
   v
Step 5: Invoices
   |
   v
Step 6: Payroll Records
```

### Details per Step

| Step | Table(s) Written         | Depends On        | Estimated Records (26-50 clients) |
|------|--------------------------|-------------------|-----------------------------------|
| 1    | clients                  | None              | 26-50                             |
| 2    | chart_of_accounts        | clients           | 500-2,500 (10-50 per client)      |
| 3    | journal_entries, journal_entry_lines | clients, chart_of_accounts | 26-50 (one per client) |
| 4    | journal_entries, journal_entry_lines | clients, chart_of_accounts | 10,000-100,000+        |
| 5    | invoices                 | clients           | 1,000-25,000                      |
| 6    | payroll_records          | clients           | 500-10,000                        |

### Idempotency

Each import run is identified by an `import_batch_id` (UUID). If re-running, all records from a previous batch must be deleted before re-importing. The script must check for existing batch data and prompt before overwriting.

---

## 6. Rollback Procedure

### Transaction Wrapping

```sql
BEGIN;

-- Step 1: Insert clients
-- Step 2: Insert chart of accounts
-- Step 3: Insert opening balances
-- Step 4: Insert transactions
-- Step 5: Insert invoices
-- Step 6: Insert payroll records

-- If we reach here with no errors:
COMMIT;
```

### On Failure

```sql
-- Automatic on any unhandled error:
ROLLBACK;
```

**Post-rollback actions:**

1. Print the exact error message and the step/row where it occurred.
2. Print the CSV filename and row number causing the failure.
3. Print recovery steps:
   ```
   IMPORT FAILED
   =============
   Error:    [error message]
   Step:     4 (Transactions)
   File:     transaction_detail.csv
   Row:      8,821
   Detail:   Account "Office Supplies 2" not found in chart of accounts

   Recovery Steps:
   1. No data was written to the database (transaction rolled back).
   2. Fix the source CSV or add the missing account to the chart of accounts export.
   3. Re-run the import from the beginning.

   QB CSV files were NOT modified (read-only access).
   ```

### Safety Guarantees

- All QB Online CSV files are opened in **read-only mode**. The import script must never write to, rename, or delete source files.
- The database connection uses a dedicated `migration_user` role with INSERT/SELECT privileges only (no DROP, TRUNCATE, or ALTER).
- A `pg_dump` backup of the target database is taken automatically before each import attempt.

---

## 7. Ambiguities and CPA Review Items

The following items require CPA review before or during the migration. Each is tagged `[CPA_REVIEW_NEEDED]` for searchability.

### 7.1 QB Class Tracking vs client_id

**[CPA_REVIEW_NEEDED]** If the QBO company file uses Class Tracking to distinguish between clients, the Class field may be a more reliable client identifier than the Name field. The CPA must confirm:

- Is Class Tracking enabled?
- Does each class map 1:1 to a client?
- Should Class override Name for client assignment?

### 7.2 Multi-Currency Handling

**[CPA_REVIEW_NEEDED]** If any QBO transactions involve non-USD currencies:

- QBO exports may include `Currency` and `Exchange Rate` columns not listed above.
- The target schema currently assumes USD only.
- If multi-currency is present, the migration script will flag all non-USD transactions and halt. The CPA must decide:
  - Convert to USD at historical rate?
  - Convert to USD at a fixed rate?
  - Store in original currency with separate exchange rate table?

### 7.3 Memo/Description Field Truncation

**[CPA_REVIEW_NEEDED]** QBO memo fields can be up to 4,000 characters. The target schema's `memo` column is `TEXT` (unlimited), but downstream reports may truncate at 1,000 characters. Any memo exceeding 1,000 characters will be flagged for review. The CPA must confirm whether truncation is acceptable.

### 7.4 Undeposited Funds Account

**[CPA_REVIEW_NEEDED]** QBO uses an automatic "Undeposited Funds" account as a clearing account for payments received but not yet deposited. This may result in:

- Duplicate-looking entries (payment received + bank deposit).
- The CPA must confirm whether to preserve this two-step flow or collapse it into a single entry per payment.

### 7.5 Voided and Deleted Transactions

**[CPA_REVIEW_NEEDED]** QBO Transaction Detail exports may include voided transactions (amount = $0.00 with original memo prefixed "Void:"). The CPA must confirm:

- Import voided transactions for audit trail?
- Skip voided transactions entirely?
- Deleted transactions do NOT appear in QBO exports and cannot be recovered from CSV.

### 7.6 Payroll Tier Variability

**[CPA_REVIEW_NEEDED]** QBO Payroll exports vary by subscription tier:

| Tier    | Columns Available                                    |
|---------|------------------------------------------------------|
| Core    | Basic pay and tax withholdings                       |
| Premium | Adds workers' comp, time tracking fields             |
| Elite   | Adds tax penalty protection fields, project tracking |

The import script must detect which columns are present and map accordingly. Missing columns are set to NULL with a warning.

### 7.7 Georgia-Specific Tax Items

**[CPA_REVIEW_NEEDED]** Confirm handling of:

- **Georgia sales tax** (state rate 4% + local varies): Are sales tax liabilities tracked in QBO or via a separate integration (e.g., Avalara)?
- **Georgia withholding** (Form G-4): Is the GA filing status captured in the employee export, or must it be entered manually?
- **Georgia annual registration** (Secretary of State): Not a QBO data item, but confirm it is tracked elsewhere in the new system.

### 7.8 Accounts Named "Ask My Accountant"

**[CPA_REVIEW_NEEDED]** QBO has a default account called "Ask My Accountant" (or similar) where uncertain transactions are parked. These must be:

- Identified in the chart of accounts export.
- All transactions posted to this account must be flagged for reclassification before final import.

### 7.9 Sub-Accounts and Account Hierarchy

**[CPA_REVIEW_NEEDED]** QBO supports sub-accounts (e.g., "Utilities:Electric", "Utilities:Water"). The export may show these as:

- A single column with colon-delimited hierarchy: `Utilities:Electric`
- Or as a parent-child relationship across rows.

The CPA must confirm whether to:
- Flatten into a single account name.
- Preserve hierarchy with a `parent_account_id` foreign key.

---

## Appendix A: Pre-Migration Checklist

| #  | Task                                                        | Owner | Done |
|----|-------------------------------------------------------------|-------|------|
| 1  | Confirm QBO subscription tier and enabled features          | CPA   |      |
| 2  | Enable Account Numbers in QBO (if not already)              | CPA   |      |
| 3  | Run all 7 CSV exports and verify column headers             | CPA   |      |
| 4  | Provide employee-to-client mapping CSV                      | CPA   |      |
| 5  | Confirm Class Tracking usage and mapping                    | CPA   |      |
| 6  | Review and reclassify "Ask My Accountant" transactions      | CPA   |      |
| 7  | Confirm cutover date for opening balances                   | CPA   |      |
| 8  | Take pg_dump backup of target database                      | Dev   |      |
| 9  | Run validation suite on all CSV files                       | Dev   |      |
| 10 | Review validation report and resolve all FATAL errors       | Both  |      |
| 11 | Execute import in staging environment                       | Dev   |      |
| 12 | CPA reviews imported data in staging                        | CPA   |      |
| 13 | Execute import in production                                | Dev   |      |
| 14 | Post-import reconciliation: compare QBO trial balance to PG | Both  |      |

## Appendix B: File Naming Convention

All CSV exports should follow this naming pattern:

```
{export_type}_{qbo_company_name}_{YYYY-MM-DD}.csv
```

Examples:
```
chart_of_accounts_smithcpa_2026-03-04.csv
transaction_detail_smithcpa_2026-03-04.csv
customer_list_smithcpa_2026-03-04.csv
invoice_list_smithcpa_2026-03-04.csv
payroll_summary_smithcpa_2026-03-04.csv
employee_details_smithcpa_2026-03-04.csv
vendor_list_smithcpa_2026-03-04.csv
```
