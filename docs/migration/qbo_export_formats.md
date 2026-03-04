# QuickBooks Online Export Formats — Comprehensive Reference

**Agent:** QB Format Research Agent (Agent 05)
**Date:** 2026-03-04
**Purpose:** Document exact CSV export formats from QuickBooks Online so the Migration Agent can build a reliable parser.

---

## Table of Contents

1. [Chart of Accounts Export](#1-chart-of-accounts-export)
2. [Transaction Detail by Account Export](#2-transaction-detail-by-account-export)
3. [Customer Contact List Export](#3-customer-contact-list-export)
4. [Invoice List Export](#4-invoice-list-export)
5. [Payroll Summary Export](#5-payroll-summary-export)
6. [Payroll Detail Export](#6-payroll-detail-export)
7. [Employee Details Export](#7-employee-details-export)
8. [Vendor Contact List Export](#8-vendor-contact-list-export)
9. [Bills / AP Export](#9-bills--ap-export)
10. [General Journal Export](#10-general-journal-export)

---

## 1. Chart of Accounts Export

### QBO Menu Path

```
Settings (gear icon) > Chart of Accounts
  > Click "Run Report" (top-right, above the chart)
  > This opens the "Account List" report
  > Click the Export icon (top-right) > Export to Excel
```

**Alternative path:**
```
Reports (left sidebar) > Standard > For my accountant > Account List
  > Click the Export icon > Export to Excel
```

**Note:** The exported file is an XLSX that can be saved as CSV. QBO does not offer a direct CSV export from Chart of Accounts -- the CPA must open the XLSX in Excel/Sheets and re-save as CSV with UTF-8 encoding.

### Expected CSV Columns

| Column Name       | Data Type      | Required | Description                                           | Sample Value                    |
|--------------------|----------------|----------|-------------------------------------------------------|----------------------------------|
| Account            | String         | Yes      | Full account name, colon-delimited for sub-accounts    | `Utilities:Electric`            |
| Type               | String         | Yes      | QBO account type category                              | `Expense`                       |
| Detail Type        | String         | Yes      | QBO sub-classification within the type                 | `Utilities`                     |
| Description        | String         | No       | User-entered description                               | `Monthly electric bill`         |
| Balance            | Currency       | Yes      | Current balance at time of export (signed)             | `1,234.56`                      |
| Currency           | String         | No       | ISO currency code (only if multi-currency enabled)     | `USD`                           |
| Account #          | String         | No       | User-assigned account number (blank if feature off)    | `6200`                          |

### QBO Account Types (Complete List)

These are the exact string values QBO uses in the "Type" column:

**Asset Types:**
- `Bank`
- `Accounts Receivable (A/R)`
- `Other Current Assets`
- `Fixed Assets`
- `Other Assets`

**Liability Types:**
- `Accounts Payable (A/P)`
- `Credit Card`
- `Other Current Liabilities`
- `Long Term Liabilities`

**Equity Types:**
- `Equity`

**Revenue Types:**
- `Income`
- `Other Income`

**Expense Types:**
- `Cost of Goods Sold`
- `Expenses`
- `Other Expenses`

### Detail Types (Common Examples)

| Type              | Detail Type Examples                                              |
|--------------------|-------------------------------------------------------------------|
| Bank               | Checking, Savings, Money Market, Rents Held in Trust, Cash on hand |
| Accounts Receivable | Accounts Receivable (A/R)                                        |
| Other Current Assets | Prepaid Expenses, Undeposited Funds, Allowance for Bad Debts, Development Costs, Employee Cash Advances, Inventory, Investment - Mortgage/Real Estate Loans, Investment - Tax-Exempt Securities, Investment - U.S. Government Obligations, Loans To Officers, Loans to Others, Loans to Stockholders, Other Current Assets, Retainage |
| Fixed Assets       | Furniture & Fixtures, Vehicles, Machinery & Equipment, Buildings, Leasehold Improvements, Land, Accumulated Depreciation, Other fixed assets |
| Other Assets       | Goodwill, Licenses, Organizational Costs, Security Deposits, Lease Buyout, Other Long-term Assets, Accumulated Amortization |
| Accounts Payable   | Accounts Payable (A/P)                                            |
| Credit Card        | Credit Card                                                       |
| Other Current Liabilities | Payroll Clearing, Payroll Tax Payable, Line of Credit, Loan Payable, Sales Tax Payable, Prepaid Revenue, Federal Income Tax Payable, State/Local Income Tax Payable, Trust Accounts - Liabilities, Other Current Liabilities |
| Long Term Liabilities | Notes Payable, Other Long Term Liabilities, Shareholder Notes Payable |
| Equity             | Opening Balance Equity, Retained Earnings, Owner's Equity, Partner's Equity, Accumulated Adjustment, Common Stock, Preferred Stock, Paid-In Capital or Surplus, Partner Distributions, Treasury Stock |
| Income             | Discounts/Refunds Given, Non-Profit Income, Sales of Product Income, Service/Fee Income, Unapplied Cash Payment Income, Other Primary Income |
| Other Income       | Dividend Income, Interest Earned, Other Investment Income, Other Miscellaneous Income, Tax-Exempt Interest, Unrealized Loss on Securities |
| Cost of Goods Sold | Supplies & Materials - COGS, Cost of labor - COS, Equipment Rental - COS, Shipping, Freight & Delivery - COS, Other Costs of Services - COS |
| Expenses           | Advertising/Promotional, Auto, Bank Charges & Fees, Charitable Contributions, Commissions & fees, Dues & Subscriptions, Entertainment, Entertainment Meals, Equipment Rental, Insurance, Interest Paid, Legal & Professional Fees, Office/General Administrative Expenses, Other Business Expenses, Other Miscellaneous Service Cost, Payroll Expenses, Rent or Lease of Buildings, Repair & Maintenance, Shipping, Freight & Delivery, Stationery & Printing, Supplies, Taxes Paid, Travel, Travel Meals, Utilities |
| Other Expenses     | Amortization, Depreciation, Exchange Gain or Loss, Penalties & Settlements, Other Miscellaneous Expense |

### Sample Row

```csv
Account,Type,Detail Type,Description,Balance,Currency,Account #
"Checking","Bank","Checking","Primary business checking","45,678.90","USD","1000"
"Utilities:Electric","Expenses","Utilities","Monthly electric service","1,234.56","USD","6200"
"Accounts Receivable (A/R)","Accounts Receivable (A/R)","Accounts Receivable (A/R)","","12,500.00","USD","1100"
```

### Sub-Account Representation

QBO represents sub-accounts using colon (`:`) delimiters in the Account column:
```
Utilities                    <-- parent account
Utilities:Electric           <-- sub-account
Utilities:Water              <-- sub-account
Utilities:Gas                <-- sub-account
Travel:Airfare               <-- sub-account
Travel:Lodging               <-- sub-account
```

The parser must handle colon-delimited hierarchy. See `client_splitting_logic.md` for hierarchy handling decisions.

---

## 2. Transaction Detail by Account Export

### QBO Menu Path

```
Reports (left sidebar) > Standard > For my accountant
  > Transaction Detail by Account
  > Set "Report period" to "All Dates" (or custom range covering full history)
  > Click "Run report"
  > Click the Export icon (top-right) > Export to Excel
```

**Alternative:**
```
Reports > Standard > All Reports > Transaction Detail by Account
```

### Expected CSV Columns

| Column Name        | Data Type      | Required | Description                                              | Sample Value                      |
|---------------------|----------------|----------|----------------------------------------------------------|-----------------------------------|
| Date                | Date           | Yes      | Transaction date in MM/DD/YYYY format                     | `03/15/2025`                     |
| Transaction Type    | String         | Yes      | QBO transaction type (see list below)                     | `Invoice`                        |
| No.                 | String         | No       | Transaction number / check number                         | `1042`                           |
| Name                | String         | No       | Customer, vendor, or employee name                        | `Peachtree Landscaping LLC`      |
| Memo/Description    | String         | No       | Free-text memo                                            | `Monthly landscaping service`    |
| Split               | String         | No       | Contra account(s) for the entry                           | `Landscaping Income`             |
| Amount              | Currency       | Yes      | Signed amount (sign convention varies by account type)    | `-1,500.00`                      |
| Balance             | Currency       | Yes      | Running balance within the account                        | `23,456.78`                      |

**Columns present if features are enabled:**

| Column Name        | Data Type      | Condition                         | Description                   |
|---------------------|----------------|-----------------------------------|-------------------------------|
| Account             | String         | Always in "by Account" report     | Account this line posts to    |
| Class               | String         | Only if Class Tracking enabled    | Class label                   |
| Location            | String         | Only if Location Tracking enabled | Location/department label     |

### QBO Transaction Types (Complete List)

These are the exact string values that appear in the "Transaction Type" column:

| Transaction Type     | Description                                          |
|----------------------|------------------------------------------------------|
| Bill                 | Vendor bill / accounts payable entry                 |
| Bill Payment (Check) | Payment of a bill by check                           |
| Bill Payment (Credit Card) | Payment of a bill by credit card               |
| Cash Expense         | Cash purchase (no bill created)                       |
| Check                | Check written                                        |
| Credit Card Credit   | Credit card refund/return                            |
| Credit Card Expense  | Credit card purchase                                 |
| Credit Memo          | Customer credit memo (reduces AR)                    |
| Deposit              | Bank deposit                                         |
| Estimate             | Quote/estimate (non-posting)                         |
| Expense              | Generic expense transaction                          |
| Invoice              | Customer invoice (increases AR)                      |
| Journal Entry        | Manual journal entry                                 |
| Payment              | Customer payment received                            |
| Purchase Order       | Purchase order (non-posting)                         |
| Refund Receipt       | Customer refund                                      |
| Sales Receipt        | Cash sale (no invoice created)                       |
| Statement Charge     | Statement charge to customer                         |
| Transfer             | Bank-to-bank transfer                                |
| Vendor Credit        | Vendor credit memo (reduces AP)                      |

### Sign Convention (CRITICAL)

QBO uses context-dependent sign conventions. The "Amount" column sign depends on the account type in which the transaction appears:

```
ASSET accounts (Bank, AR, Other Current Assets, Fixed Assets):
    Positive amount = DEBIT (increases the account)
    Negative amount = CREDIT (decreases the account)

LIABILITY accounts (AP, Credit Card, Other Current Liabilities):
    Positive amount = CREDIT (increases the account)
    Negative amount = DEBIT (decreases the account)

EQUITY accounts:
    Positive amount = CREDIT (increases the account)
    Negative amount = DEBIT (decreases the account)

INCOME accounts:
    Positive amount = CREDIT (increases the account)
    Negative amount = DEBIT (decreases the account)

EXPENSE accounts:
    Positive amount = DEBIT (increases the account)
    Negative amount = CREDIT (decreases the account)

COGS accounts:
    Positive amount = DEBIT (increases the account)
    Negative amount = CREDIT (decreases the account)
```

### Multi-Line Journal Entries in CSV

QBO represents multi-line journal entries as multiple rows in the CSV. Each row is a separate line of the entry. They share:
- The same `Date`
- The same `No.` (transaction number)
- The same `Transaction Type` (usually "Journal Entry")

But each row has a different `Account` and `Amount`. The parser must group these rows together to reconstruct the complete journal entry.

**Important:** The "Split" column behavior varies:
- For 2-line entries: Split shows the other account name
- For 3+ line entries: Split shows `-Split-` (literal string) indicating multiple contra accounts
- For single-line views: Split shows the contra account

### Voided Transactions

Voided transactions appear in the export with:
- Original amounts zeroed out (Amount = `0.00`)
- Memo/Description prefixed with `Void: ` followed by original memo
- Original date is preserved
- Transaction Type is preserved (not changed to "Void")

### Deleted Transactions

Deleted transactions do **NOT** appear in QBO CSV exports. They are permanently removed from the export. The only way to detect deleted transactions is by comparing sequential exports.

### Sample Rows

```csv
Date,Transaction Type,No.,Name,Memo/Description,Split,Amount,Balance,Account,Class
03/15/2025,Invoice,1042,"Peachtree Landscaping LLC","Monthly landscaping service","Landscaping Income","1,500.00","13,500.00","Accounts Receivable (A/R)",""
03/15/2025,Invoice,1042,"Peachtree Landscaping LLC","Monthly landscaping service","Accounts Receivable (A/R)","1,500.00","45,000.00","Landscaping Income",""
03/20/2025,Check,5501,"Georgia Power","March electric bill","Utilities:Electric","-850.00","44,828.90","Checking",""
03/20/2025,Journal Entry,JE-001,"","Depreciation - March 2025","-Split-","2,500.00","7,500.00","Depreciation Expense",""
03/20/2025,Journal Entry,JE-001,"","Depreciation - March 2025","-Split-","-2,500.00","22,500.00","Accumulated Depreciation",""
```

### Report Header Rows

**WARNING:** QBO export files include metadata rows above the actual data:

```
"Transaction Detail by Account"
"Your Company Name"
"All Dates"
""
Date,Transaction Type,No.,Name,...
```

The parser must skip these header/metadata rows (typically 4 rows before the actual CSV header). See `qbo_known_issues.md` for details on header row detection.

### Account Section Headers

The "Transaction Detail by Account" report groups transactions by account. Each account group has a section header row and subtotal row:

```csv
"Checking",,,,,,,,
03/01/2025,Deposit,DEP-001,...
03/05/2025,Check,5500,...
"Total for Checking",,,,,,,"45,678.90",,
"",,,,,,,,
"Accounts Receivable (A/R)",,,,,,,,
03/10/2025,Invoice,1040,...
```

The parser must identify and skip:
- Account section header rows (single value in first column, rest empty)
- Subtotal rows (start with "Total for")
- Blank separator rows

---

## 3. Customer Contact List Export

### QBO Menu Path

```
Reports (left sidebar) > Standard > Sales and customers
  > Customer Contact List
  > Click "Run report"
  > Click the Export icon > Export to Excel
```

**Alternative (direct customer export):**
```
Sales (left sidebar) > Customers
  > Click the Export icon (top-right, near "New customer") > Export to Excel
```

### Expected CSV Columns

| Column Name           | Data Type  | Required | Description                              | Sample Value                      |
|------------------------|------------|----------|------------------------------------------|-----------------------------------|
| Customer               | String     | Yes      | Full display name (colon-delimited for sub-customers) | `Peachtree Landscaping LLC`     |
| Phone                  | String     | No       | Primary phone number                      | `(770) 555-1234`                |
| Email                  | String     | No       | Primary email address                     | `info@peachtreelandscaping.com` |
| Full Name              | String     | No       | Contact person's full name                | `James Williams`                 |
| Company                | String     | No       | Company/business name                     | `Peachtree Landscaping LLC`     |
| Billing Street         | String     | No       | Billing address line 1                    | `456 Magnolia Blvd`             |
| Billing City           | String     | No       | Billing city                              | `Marietta`                       |
| Billing State          | String     | No       | Billing state (abbreviation or full)      | `GA`                             |
| Billing ZIP            | String     | No       | Billing ZIP code                          | `30060`                          |
| Billing Country        | String     | No       | Billing country                           | `US`                             |
| Shipping Street        | String     | No       | Shipping address line 1                   | `456 Magnolia Blvd`             |
| Shipping City          | String     | No       | Shipping city                             | `Marietta`                       |
| Shipping State         | String     | No       | Shipping state                            | `GA`                             |
| Shipping ZIP           | String     | No       | Shipping ZIP code                         | `30060`                          |
| Shipping Country       | String     | No       | Shipping country                          | `US`                             |
| Open Balance           | Currency   | No       | Outstanding balance                       | `3,500.00`                       |
| Notes                  | String     | No       | Internal notes                            | `Net 30 terms, S-Corp`          |
| Tax Resale No.         | String     | No       | Resale certificate number                 | `GA-12345678`                    |
| Terms                  | String     | No       | Payment terms                             | `Net 30`                         |
| Website                | String     | No       | Website URL                               | `www.peachtreelandscaping.com`  |
| Other                  | String     | No       | Custom field value                        | `` (varies)                      |
| Created                | Date       | No       | Date customer was created in QBO          | `01/15/2020`                     |

### Entity Type Identification

**[CPA_REVIEW_NEEDED]** QBO does NOT have a native "entity type" field (sole prop, S-Corp, C-Corp, Partnership/LLC). The CPA must provide entity type information via one of these methods:

1. **Preferred:** Supply a supplemental CSV mapping customer names to entity types:
   ```csv
   customer_name,entity_type
   "Peachtree Landscaping LLC","PARTNERSHIP_LLC"
   "Smith Consulting","SOLE_PROP"
   "Atlanta Tech Solutions Inc","S_CORP"
   ```

2. **Alternative:** Use the QBO "Notes" field to encode entity type (parser can extract via regex pattern like `Entity: S-Corp` or `[S_CORP]`).

3. **Alternative:** Use QBO custom fields if configured.

### Sub-Customer Representation

QBO supports sub-customers (parent-child relationships). In the export, sub-customers appear as colon-delimited names:

```
"Peachtree Landscaping LLC"                  <-- parent customer
"Peachtree Landscaping LLC:Atlanta Office"   <-- sub-customer
"Peachtree Landscaping LLC:Marietta Office"  <-- sub-customer
```

For this CPA firm, each top-level customer is a client. Sub-customers should be collapsed to the parent unless the CPA explicitly instructs otherwise.

### Sample Row

```csv
Customer,Phone,Email,Full Name,Company,Billing Street,Billing City,Billing State,Billing ZIP,Billing Country,Open Balance,Notes,Tax Resale No.,Terms
"Peachtree Landscaping LLC","(770) 555-1234","info@peachtreelandscaping.com","James Williams","Peachtree Landscaping LLC","456 Magnolia Blvd","Marietta","GA","30060","US","3,500.00","Net 30 terms, S-Corp","","Net 30"
```

---

## 4. Invoice List Export

### QBO Menu Path

```
Reports (left sidebar) > Standard > Sales and customers
  > Invoice List
  > Set "Report period" to "All Dates" (or custom range)
  > Click "Run report"
  > Click the Export icon > Export to Excel
```

### Expected CSV Columns

| Column Name        | Data Type  | Required | Description                              | Sample Value                   |
|---------------------|------------|----------|------------------------------------------|---------------------------------|
| Invoice Date        | Date       | Yes      | Date the invoice was created             | `03/15/2025`                   |
| No.                 | String     | Yes      | Invoice number                           | `1042`                         |
| Customer            | String     | Yes      | Customer display name                    | `Peachtree Landscaping LLC`    |
| Due Date            | Date       | Yes      | Payment due date                         | `04/14/2025`                   |
| Terms               | String     | No       | Payment terms                            | `Net 30`                       |
| Memo/Description    | String     | No       | Invoice-level memo                       | `Monthly landscaping service`  |
| Amount              | Currency   | Yes      | Total invoice amount                     | `1,500.00`                     |
| Open Balance        | Currency   | Yes      | Remaining unpaid amount                  | `0.00`                         |
| Status              | String     | Yes      | Current invoice status                   | `Paid`                         |
| Service Date        | Date       | No       | Service/delivery date                    | `03/01/2025`                   |
| Class               | String     | No       | Class label (if enabled)                 | `Landscaping`                  |
| Shipping Date       | Date       | No       | Shipping date (if applicable)            | `` (often blank for services)  |

### Invoice Status Values

| QBO Status Value | Description                                      | Our System Mapping           |
|-------------------|--------------------------------------------------|------------------------------|
| `Paid`            | Fully paid                                       | `PAID`                       |
| `Open`            | Unpaid, not yet overdue                          | `SENT`                       |
| `Overdue`         | Unpaid, past due date                            | `OVERDUE`                    |
| `Voided`          | Voided (amount zeroed, retained for audit)       | `VOID`                       |
| `Deposited`       | Payment deposited (variant of Paid in some exports) | `PAID`                    |

### Partial Payment Representation

When an invoice is partially paid:
- `Amount` = original total invoice amount (e.g., `$1,500.00`)
- `Open Balance` = remaining balance after payments (e.g., `$500.00`)
- `Status` = `Open` (even if past due date, unless specifically `Overdue`)

The difference (`Amount - Open Balance = $1,000.00`) represents total payments received. Individual payment records must be extracted from the Transaction Detail export (Transaction Type = `Payment`).

### Credit Memo Representation

Credit memos appear as separate rows in the Invoice List with:
- `Transaction Type` or implicit type = `Credit Memo`
- `Amount` = negative or positive depending on report format
- `No.` = credit memo number
- Credit memos in some QBO versions appear only in the Transaction Detail export, not the Invoice List

**[CPA_REVIEW_NEEDED]:** Credit memo representation varies between QBO versions. The CPA should export one sample credit memo and verify the format before migration.

### Sample Rows

```csv
Invoice Date,No.,Customer,Due Date,Terms,Memo/Description,Amount,Open Balance,Status
03/15/2025,1042,"Peachtree Landscaping LLC",04/14/2025,"Net 30","Monthly landscaping service","1,500.00","0.00","Paid"
03/20/2025,1043,"Atlanta Tech Solutions Inc",04/19/2025,"Net 30","IT consulting - March","4,500.00","4,500.00","Open"
02/01/2025,1035,"Smith Consulting",03/03/2025,"Net 30","Tax preparation services","2,000.00","2,000.00","Overdue"
```

---

## 5. Payroll Summary Export

### QBO Menu Path

```
Reports (left sidebar) > Standard > Payroll
  > Payroll Summary
  > Set "Report period" to "All Dates" (or desired period, typically by quarter or year)
  > Click "Run report"
  > Click the Export icon > Export to Excel
```

**[CPA_REVIEW_NEEDED]:** This export requires an active QBO Payroll subscription (Core, Premium, or Elite tier). If the firm's QBO Payroll subscription has lapsed, this export may not be available. Historical payroll data may need to be entered manually from paper records or prior payroll provider reports.

### Expected CSV Columns

The Payroll Summary report is structured differently from other reports. It is a **pivot-style report** with employee names as rows and pay/tax categories as columns.

| Column Name              | Data Type  | Required | Description                              | Sample Value     |
|---------------------------|------------|----------|------------------------------------------|-------------------|
| Employee                  | String     | Yes      | Employee display name                    | `John Smith`      |
| Gross Pay                 | Currency   | Yes      | Total gross compensation for the period  | `5,000.00`        |
| Federal Withholding       | Currency   | Yes      | Federal income tax withheld              | `625.00`          |
| Social Security Employee  | Currency   | Yes      | Employee FICA SS (6.2%)                  | `310.00`          |
| Medicare Employee         | Currency   | Yes      | Employee FICA Medicare (1.45%)           | `72.50`           |
| GA Withholding            | Currency   | Yes*     | Georgia state income tax withheld        | `250.00`          |
| Net Pay                   | Currency   | Yes      | Net pay after all deductions             | `3,742.50`        |
| Social Security Employer  | Currency   | Yes      | Employer FICA SS (6.2%)                  | `310.00`          |
| Medicare Employer         | Currency   | Yes      | Employer FICA Medicare (1.45%)           | `72.50`           |
| Federal Unemployment      | Currency   | Yes      | FUTA (0.6% after credit, on first $7k)  | `42.00`           |
| GA SUI                    | Currency   | Yes*     | Georgia State Unemployment Insurance     | `135.00`          |

\* Georgia-specific columns. Column header text may vary:
- "GA Withholding" may appear as "Georgia Withholding" or "State Withholding - GA"
- "GA SUI" may appear as "GA Unemployment", "State Unemployment - GA", or "GA SUTA"

### Payroll Summary Report Structure

The QBO Payroll Summary is NOT a simple flat CSV. It typically has this structure:

```
Payroll Summary
Your Company Name
Jan 1 - Dec 31, 2025

                    EMPLOYEE         EMPLOYER
                    Gross Pay  Fed WH  SS  Medicare  State WH  Net Pay  SS  Medicare  FUTA  SUI
John Smith          5,000.00   625.00  310.00  72.50  250.00  3,742.50  310.00  72.50  42.00  135.00
Jane Doe            4,200.00   504.00  260.40  60.90  210.00  3,164.70  260.40  60.90  25.20  113.40
TOTAL              9,200.00  1,129.00  570.40 133.40  460.00  6,907.20  570.40 133.40  67.20  248.40
```

**Parsing challenges:**
1. Header rows (company name, date range) must be skipped
2. Column headers may span two rows (EMPLOYEE / EMPLOYER grouping)
3. Totals row at the bottom must be detected and excluded from import
4. Some QBO versions include subtotals by pay period within the report

### Column Header Variations by QBO Payroll Tier

| Tier      | Additional Columns                                         |
|-----------|-------------------------------------------------------------|
| Core      | Base columns listed above                                   |
| Premium   | + Workers' Comp, + Time Activity (hours)                    |
| Elite     | + Tax Penalty Protection fields, + Project tracking         |

The parser must detect which columns are present by header name matching, not by column position.

### Sample Row (Flat CSV After Header Processing)

```csv
Employee,Gross Pay,Federal Withholding,Social Security Employee,Medicare Employee,GA Withholding,Net Pay,Social Security Employer,Medicare Employer,Federal Unemployment,GA SUI
"John Smith","5,000.00","625.00","310.00","72.50","250.00","3,742.50","310.00","72.50","42.00","135.00"
```

---

## 6. Payroll Detail Export

### QBO Menu Path

```
Reports (left sidebar) > Standard > Payroll
  > Payroll Details
  > Set "Report period" to desired range
  > Click "Run report"
  > Click the Export icon > Export to Excel
```

### Expected CSV Columns

The Payroll Detail report provides per-pay-period breakdown (more granular than Summary).

| Column Name              | Data Type  | Required | Description                              | Sample Value          |
|---------------------------|------------|----------|------------------------------------------|-----------------------|
| Employee                  | String     | Yes      | Employee display name                    | `John Smith`          |
| Pay Period                | String     | Yes      | Date range (e.g., "03/01/2025-03/15/2025") | `03/01/2025 to 03/15/2025` |
| Pay Date                  | Date       | No       | Actual pay date                          | `03/20/2025`          |
| Hours                     | Numeric    | No       | Hours worked (hourly employees)          | `80.00`               |
| Gross Pay                 | Currency   | Yes      | Gross pay for this period                | `2,500.00`            |
| Federal Withholding       | Currency   | Yes      | Federal income tax                       | `312.50`              |
| Social Security Employee  | Currency   | Yes      | Employee SS                              | `155.00`              |
| Medicare Employee         | Currency   | Yes      | Employee Medicare                        | `36.25`               |
| GA Withholding            | Currency   | Yes*     | Georgia state withholding                | `125.00`              |
| Net Pay                   | Currency   | Yes      | Net pay for this period                  | `1,871.25`            |
| Social Security Employer  | Currency   | Yes      | Employer SS                              | `155.00`              |
| Medicare Employer         | Currency   | Yes      | Employer Medicare                        | `36.25`               |
| Federal Unemployment      | Currency   | Yes      | FUTA for this period                     | `15.00`               |
| GA SUI                    | Currency   | Yes*     | Georgia SUTA for this period             | `67.50`               |
| Check No.                 | String     | No       | Check/direct deposit reference           | `DD-4502`             |

### Pay Period Format Variations

The "Pay Period" field format varies:
- `03/01/2025 to 03/15/2025` (most common)
- `03/01/2025 - 03/15/2025`
- `3/1/2025 - 3/15/2025` (no leading zeros)

The parser must handle all three formats and extract start/end dates.

---

## 7. Employee Details Export

### QBO Menu Path

```
Reports (left sidebar) > Standard > Payroll
  > Employee Details
  > Click "Run report"
  > Click the Export icon > Export to Excel
```

**Alternative (direct export):**
```
Payroll (left sidebar) > Employees
  > Click the Export icon > Export to CSV
```

### Expected CSV Columns

| Column Name        | Data Type  | Required | Description                              | Sample Value              |
|---------------------|------------|----------|------------------------------------------|---------------------------|
| Employee            | String     | Yes      | Full name (First Last or Last, First)    | `John Smith`              |
| SSN (last 4)       | String     | No       | Last 4 digits of SSN                     | `xxxx-xx-1234`            |
| Hire Date           | Date       | Yes      | Date of hire                             | `01/15/2020`              |
| Status              | String     | Yes      | Employment status                        | `Active`                  |
| Pay Rate            | Currency   | Yes      | Current pay rate (hourly or annual)      | `25.00` or `52,000.00`    |
| Pay Type            | String     | Yes      | Hourly or Salary                         | `Hourly`                  |
| Pay Schedule        | String     | No       | Pay frequency                            | `Every other week`        |
| Filing Status (Federal) | String | No       | W-4 filing status                        | `Single`                  |
| Allowances/Withholding | String | No       | W-4 allowances or extra withholding      | `2` or `$50.00`           |

**[CPA_REVIEW_NEEDED]:** QBO does NOT export:
- Full SSN (only last 4 digits in CSV; full SSN must be obtained separately)
- Georgia G-4 filing status (this must be entered manually or obtained from paper G-4 forms)
- State-specific allowances/exemptions

### Employee Status Values

| QBO Status   | Description                | Our System Mapping  |
|--------------|----------------------------|---------------------|
| `Active`     | Currently employed         | `is_active = TRUE`  |
| `Terminated` | No longer employed         | `is_active = FALSE`, set `termination_date` |
| `Inactive`   | Temporarily inactive       | `is_active = FALSE` |

### Sample Row

```csv
Employee,SSN (last 4),Hire Date,Status,Pay Rate,Pay Type,Pay Schedule,Filing Status (Federal)
"John Smith","xxxx-xx-1234","01/15/2020","Active","25.00","Hourly","Every other week","Single"
"Jane Doe","xxxx-xx-5678","06/01/2021","Active","52,000.00","Salary","Twice a month","Married"
```

---

## 8. Vendor Contact List Export

### QBO Menu Path

```
Reports (left sidebar) > Standard > Expenses and vendors
  > Vendor Contact List
  > Click "Run report"
  > Click the Export icon > Export to Excel
```

**Alternative (direct export):**
```
Expenses (left sidebar) > Vendors
  > Click the Export icon > Export to CSV
```

### Expected CSV Columns

| Column Name        | Data Type  | Required | Description                              | Sample Value              |
|---------------------|------------|----------|------------------------------------------|---------------------------|
| Vendor              | String     | Yes      | Vendor display name                      | `Georgia Power`           |
| Company             | String     | No       | Company name (may duplicate Vendor)      | `Georgia Power Company`   |
| Phone               | String     | No       | Primary phone                            | `(800) 555-0100`          |
| Email               | String     | No       | Primary email                            | `billing@gapower.com`     |
| Street              | String     | No       | Street address                           | `241 Ralph McGill Blvd`   |
| City                | String     | No       | City                                     | `Atlanta`                 |
| State               | String     | No       | State                                    | `GA`                      |
| ZIP                 | String     | No       | ZIP code                                 | `30308`                   |
| Country             | String     | No       | Country                                  | `US`                      |
| Tax ID              | String     | No       | TIN/EIN (may be masked or absent)        | `XX-XXXXX89`              |
| 1099 Tracking       | String     | No       | Whether vendor receives 1099             | `Yes` or `No`             |
| Terms               | String     | No       | Payment terms                            | `Net 30`                  |
| Open Balance        | Currency   | No       | Outstanding balance owed to vendor       | `850.00`                  |
| Website             | String     | No       | Vendor website                           | `www.georgiapower.com`    |
| Account No.         | String     | No       | Your account number with the vendor      | `ACCT-789456`             |

### 1099 Tracking Field

The `1099 Tracking` column in QBO is critical for year-end tax reporting:
- `Yes` = vendor is flagged to receive a 1099-NEC or 1099-MISC
- `No` = vendor is NOT flagged (typically corporations or excluded)
- Blank = not set (treat as `No` for import, flag for CPA review)

### Sample Row

```csv
Vendor,Company,Phone,Email,Street,City,State,ZIP,Country,Tax ID,1099 Tracking,Terms,Open Balance
"Georgia Power","Georgia Power Company","(800) 555-0100","billing@gapower.com","241 Ralph McGill Blvd","Atlanta","GA","30308","US","","No","Net 30","850.00"
"Davis Plumbing","Davis Plumbing Services","(770) 555-2345","mike@davisplumbing.com","123 Elm St","Kennesaw","GA","30144","US","XX-XXXXX45","Yes","Due on receipt","0.00"
```

---

## 9. Bills / AP Export

### QBO Menu Path

```
Reports (left sidebar) > Standard > Expenses and vendors
  > Unpaid Bills
  > Optionally change to "Bill List" if available
  > Set "Report period" to "All Dates"
  > Click "Run report"
  > Click the Export icon > Export to Excel
```

**For complete bill history (including paid bills):**
```
Reports > Standard > Expenses and vendors
  > Transaction List by Vendor
  > Filter "Transaction Type" to "Bill" only
  > Set date range to cover full history
  > Export to Excel
```

### Expected CSV Columns (Transaction List by Vendor, filtered to Bills)

| Column Name        | Data Type  | Required | Description                              | Sample Value              |
|---------------------|------------|----------|------------------------------------------|---------------------------|
| Date                | Date       | Yes      | Bill date                                | `03/10/2025`              |
| Transaction Type    | String     | Yes      | Should be "Bill"                         | `Bill`                    |
| No.                 | String     | No       | Bill/reference number                    | `INV-2025-0342`           |
| Vendor              | String     | Yes      | Vendor name                              | `Georgia Power`           |
| Due Date            | Date       | Yes      | Payment due date                         | `04/09/2025`              |
| Terms               | String     | No       | Payment terms                            | `Net 30`                  |
| Memo/Description    | String     | No       | Bill memo                                | `March electric service`  |
| Amount              | Currency   | Yes      | Bill total amount                        | `850.00`                  |
| Open Balance        | Currency   | Yes      | Remaining unpaid amount                  | `0.00`                    |
| Status              | String     | No       | Payment status (derived)                 | `Paid`                    |
| Account             | String     | No       | Expense account                          | `Utilities:Electric`      |

### Bill Payment Status Derivation

QBO does not always have an explicit "Status" column for bills. Status must be derived:

| Condition                    | Derived Status |
|------------------------------|----------------|
| `Open Balance` > 0 and not past due | `APPROVED` (open) |
| `Open Balance` > 0 and past due date | `APPROVED` (overdue) |
| `Open Balance` = 0           | `PAID`         |
| Amount = 0 and memo contains "Void" | `VOID`  |

### Sample Rows

```csv
Date,Transaction Type,No.,Vendor,Due Date,Terms,Memo/Description,Amount,Open Balance,Account
03/10/2025,Bill,INV-2025-0342,"Georgia Power",04/09/2025,"Net 30","March electric service","850.00","0.00","Utilities:Electric"
03/15/2025,Bill,INV-8891,"Office Depot",04/14/2025,"Net 30","Office supplies - March","234.56","234.56","Office Supplies"
```

---

## 10. General Journal Export

### QBO Menu Path

```
Reports (left sidebar) > Standard > For my accountant
  > Journal
  > Set "Report period" to "All Dates"
  > Click "Run report"
  > Click the Export icon > Export to Excel
```

This report shows only manual journal entries (Transaction Type = "Journal Entry"), not auto-generated entries from invoices, bills, etc.

### Expected CSV Columns

| Column Name        | Data Type  | Required | Description                              | Sample Value              |
|---------------------|------------|----------|------------------------------------------|---------------------------|
| Date                | Date       | Yes      | Journal entry date                       | `03/31/2025`              |
| Transaction Type    | String     | Yes      | Always "Journal Entry"                   | `Journal Entry`           |
| No.                 | String     | Yes      | Journal entry number                     | `JE-001`                  |
| Name                | String     | No       | Associated customer/vendor               | `` (often blank)          |
| Memo/Description    | String     | No       | Entry-level memo                         | `Month-end adjusting entry` |
| Account             | String     | Yes      | Account for this line                    | `Depreciation Expense`    |
| Debit               | Currency   | No       | Debit amount (blank if credit line)      | `2,500.00`                |
| Credit              | Currency   | No       | Credit amount (blank if debit line)      | `` (blank)                |

**Note:** Unlike the Transaction Detail by Account report, the General Journal report uses separate Debit and Credit columns rather than a single signed Amount column. This is the preferred format for importing journal entries because it avoids sign convention confusion.

### Sample Rows

```csv
Date,Transaction Type,No.,Name,Memo/Description,Account,Debit,Credit
03/31/2025,Journal Entry,JE-001,,"Month-end depreciation","Depreciation Expense","2,500.00",""
03/31/2025,Journal Entry,JE-001,,"Month-end depreciation","Accumulated Depreciation","","2,500.00"
03/31/2025,Journal Entry,JE-002,,"Prepaid insurance adjustment","Insurance Expense","500.00",""
03/31/2025,Journal Entry,JE-002,,"Prepaid insurance adjustment","Prepaid Insurance","","500.00"
```

---

## Appendix A: Complete List of Required QBO Exports

| #  | Export Name                    | QBO Menu Path                                         | File Naming Convention                  |
|----|--------------------------------|-------------------------------------------------------|-----------------------------------------|
| 1  | Chart of Accounts              | Settings > Chart of Accounts > Run Report > Export    | `chart_of_accounts_[company]_[date].csv` |
| 2  | Transaction Detail by Account  | Reports > For my accountant > Transaction Detail > Export | `transaction_detail_[company]_[date].csv` |
| 3  | Customer Contact List          | Reports > Sales and customers > Customer Contact List > Export | `customer_list_[company]_[date].csv` |
| 4  | Invoice List                   | Reports > Sales and customers > Invoice List > Export | `invoice_list_[company]_[date].csv`     |
| 5  | Payroll Summary                | Reports > Payroll > Payroll Summary > Export          | `payroll_summary_[company]_[date].csv`  |
| 6  | Payroll Detail                 | Reports > Payroll > Payroll Details > Export          | `payroll_detail_[company]_[date].csv`   |
| 7  | Employee Details               | Reports > Payroll > Employee Details > Export         | `employee_details_[company]_[date].csv` |
| 8  | Vendor Contact List            | Reports > Expenses and vendors > Vendor Contact List > Export | `vendor_list_[company]_[date].csv` |
| 9  | Bill List / Transaction by Vendor | Reports > Expenses and vendors > Transaction List by Vendor > Export | `bill_list_[company]_[date].csv` |
| 10 | General Journal                | Reports > For my accountant > Journal > Export        | `general_journal_[company]_[date].csv`  |

## Appendix B: QBO Export Settings Checklist

Before exporting, the CPA should verify these QBO settings:

| Setting                    | Path in QBO                           | Required Value                  |
|----------------------------|---------------------------------------|---------------------------------|
| Account Numbers            | Settings > Advanced > Chart of Accounts | Enable "Use account numbers"  |
| Class Tracking             | Settings > Advanced > Categories      | Note if enabled and how used   |
| Location Tracking          | Settings > Advanced > Categories      | Note if enabled and how used   |
| Multicurrency              | Settings > Advanced > Currency        | Note if enabled                |
| Custom Transaction Numbers | Settings > Advanced > Other preferences | Note if enabled               |
| Fiscal Year Start          | Settings > Advanced > Accounting      | Note the month                 |
