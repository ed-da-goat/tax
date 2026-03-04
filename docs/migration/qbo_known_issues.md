# QBO Export Known Issues and Quirks

**Agent:** QB Format Research Agent (Agent 05)
**Date:** 2026-03-04
**Purpose:** Document known issues, gotchas, and format quirks in QuickBooks Online CSV exports that the migration parser must handle.

---

## 1. File Encoding Issues

### 1.1 Character Encoding

**Issue:** QBO exports use inconsistent character encoding depending on browser, OS, and export method.

| Export Method           | Typical Encoding     | BOM Present? | Notes                                |
|-------------------------|----------------------|--------------|--------------------------------------|
| Export to Excel (XLSX)  | UTF-8 (in XML)       | No           | Re-save as CSV with UTF-8 encoding   |
| Export to CSV (direct)  | Windows-1252 (CP1252)| Sometimes    | Common on Windows machines            |
| Print to PDF > copy     | UTF-8                | No           | Not recommended for data migration    |

**Parser requirement:**
```python
# Try UTF-8 first, fall back to CP1252
encodings_to_try = ['utf-8-sig', 'utf-8', 'cp1252', 'latin-1']

def detect_encoding(file_path: str) -> str:
    for encoding in encodings_to_try:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                f.read(1024)  # Read first 1KB to test
            return encoding
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Cannot determine encoding for {file_path}")
```

### 1.2 BOM (Byte Order Mark)

**Issue:** Some QBO exports include a UTF-8 BOM (`\xef\xbb\xbf`) at the start of the file. This invisible prefix will corrupt the first column header name.

**Symptom:**
```python
# Without BOM handling:
headers[0] == '\ufeffDate'  # Instead of 'Date'
# This causes column lookup failures
```

**Parser requirement:**
- Always use `utf-8-sig` encoding first (auto-strips BOM)
- If reading with `csv.DictReader`, verify first column header does not start with `\ufeff`

### 1.3 Special Characters in Names

**Issue:** QBO allows special characters in customer/vendor names that may cause CSV parsing problems.

| Character | Problem                                   | Example                          |
|-----------|-------------------------------------------|----------------------------------|
| Comma (,) | Breaks CSV column boundaries if unquoted  | `Smith, Jones & Associates`      |
| Quote (") | Breaks CSV quoting if not escaped         | `The "Best" Plumber`             |
| Newline   | Breaks CSV row boundaries                 | Multi-line memo/description      |
| Ampersand (&) | Generally safe but may confuse XML parsers | `Johnson & Johnson`          |
| Apostrophe (') | Generally safe                       | `O'Brien Construction`           |
| Non-ASCII | Encoding issues (accented characters)     | `Gonzalez Construccion`          |

**Parser requirement:**
- Use Python `csv` module with `quotechar='"'` and `doublequote=True` (handles escaped quotes)
- Use `quoting=csv.QUOTE_ALL` when writing intermediate files
- Test with names containing commas, quotes, and ampersands

---

## 2. Report Header and Footer Rows

### 2.1 Report Header Metadata Rows

**Issue:** QBO report exports include 3-5 metadata rows before the actual CSV data headers.

**Typical structure:**
```
"Transaction Detail by Account"        <- Row 1: Report name
"Peachtree CPA Firm"                   <- Row 2: Company name
"All Dates"                            <- Row 3: Date range
""                                     <- Row 4: Blank separator
Date,Transaction Type,No.,Name,...     <- Row 5: Actual column headers
03/15/2025,Invoice,1042,...            <- Row 6: First data row
```

**Variations observed:**
- Some reports have 3 header rows (no blank separator)
- Some reports have 5 header rows (extra line with report parameters)
- The report name row may be enclosed in quotes or not
- The company name row may include the plan tier (e.g., "Peachtree CPA Firm - Plus")

**Parser requirement:**
```python
def find_header_row(file_path: str) -> int:
    """
    Scan the file to find the actual CSV header row.
    Returns the 0-indexed row number of the header.

    Strategy: The header row is the first row where known column
    names are found (Date, Account, Customer, etc.)
    """
    known_headers = {
        'Date', 'Transaction Type', 'No.', 'Name', 'Account',
        'Customer', 'Vendor', 'Employee', 'Amount', 'Balance',
        'Memo/Description', 'Split', 'Invoice Date', 'Gross Pay',
        'Type', 'Detail Type', 'Description', 'Open Balance',
        'Hire Date', 'Status', 'Pay Rate', 'Billing Street',
    }

    with open(file_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        for row_num, row in enumerate(reader):
            # Check if this row contains known column headers
            row_set = set(col.strip() for col in row)
            if len(row_set.intersection(known_headers)) >= 2:
                return row_num

    raise ValueError(f"Could not find header row in {file_path}")
```

### 2.2 Account Section Headers in Transaction Detail

**Issue:** The "Transaction Detail by Account" report groups transactions by account with section headers and subtotals interspersed with data rows.

**Section structure:**
```csv
"Checking",,,,,,,,,                 <- Section header (account name)
03/01/2025,Deposit,...              <- Data row
03/05/2025,Check,...                <- Data row
"Total for Checking",,,,,,,"45,678.90",,  <- Subtotal row
"",,,,,,,,,                         <- Blank separator
"Accounts Receivable (A/R)",,,,,,,,,  <- Next section header
```

**Detection rules:**
- **Section header row:** First cell has value, all other cells are empty
- **Subtotal row:** First cell starts with "Total for " (note the space after "for")
- **Blank separator row:** All cells are empty
- **Data row:** Has a parseable date in the first cell

**Parser requirement:**
```python
def classify_row(row: list) -> str:
    """Returns: 'header', 'subtotal', 'blank', or 'data'"""
    if all(cell.strip() == '' for cell in row):
        return 'blank'
    if row[0].strip().startswith('Total for '):
        return 'subtotal'
    # Check if first non-blank cell is alone (section header)
    non_empty = [i for i, cell in enumerate(row) if cell.strip()]
    if len(non_empty) == 1 and non_empty[0] == 0:
        return 'header'
    # Try to parse first cell as date
    try:
        datetime.strptime(row[0].strip(), '%m/%d/%Y')
        return 'data'
    except ValueError:
        return 'header'  # If it's not a date and not a total, treat as header
```

### 2.3 Report Footer / Grand Total Row

**Issue:** Some QBO reports include a grand total row at the bottom.

```csv
...last data row...
"TOTAL",,,,,,,"234,567.89",,
```

**Parser requirement:** Stop processing when encountering a row where the first cell equals "TOTAL" (case-insensitive).

---

## 3. Row and Data Limits

### 3.1 Maximum Row Limits

**Issue:** QBO exports may be truncated if the report exceeds certain row limits.

| Report Type                   | Approximate Row Limit | Behavior When Exceeded              |
|-------------------------------|----------------------|--------------------------------------|
| Transaction Detail by Account | ~10,000 rows         | Silently truncates; no warning       |
| Invoice List                  | ~10,000 rows         | Silently truncates                   |
| Customer Contact List         | ~2,000 rows          | Usually not an issue for 50 clients  |
| Payroll Summary               | ~5,000 rows          | Usually not an issue                 |
| General Journal               | ~10,000 rows         | May truncate for long history        |

**Workarounds for exceeding row limits:**
1. Export in date range chunks (e.g., by quarter or by year)
2. Export by individual account (for Transaction Detail)
3. Use QBO API instead of CSV export (requires developer access)

**Parser requirement:**
- After import, compare record counts against QBO dashboard totals
- If counts don't match, warn CPA that export may be truncated
- Check if the last row is a complete record (not cut off mid-transaction)

### 3.2 Date Range Limitations

**Issue:** QBO requires a date range for most report exports. "All Dates" is available but may trigger row limits for firms with long histories.

**Recommended approach:**
1. First try "All Dates" export
2. If truncated (detected by record count mismatch), re-export in chunks:
   - Year by year (2020, 2021, 2022, ...)
   - Or quarter by quarter for the current year
3. Concatenate chunked exports (remove duplicate header rows from subsequent files)

**Parser requirement:**
```python
def merge_chunked_exports(file_paths: list) -> str:
    """
    Merge multiple date-range exports into a single CSV.
    Removes duplicate headers and checks for overlapping date ranges.
    """
    # Implementation must:
    # 1. Read header from first file
    # 2. For subsequent files: skip header rows, append data rows
    # 3. Check for duplicate transactions (same Date + No. + Amount)
    # 4. Sort final output by Date
    pass
```

---

## 4. Date Format Variations

### 4.1 Date Formats Observed

**Issue:** QBO date format depends on the firm's QBO locale settings and the export method.

| Locale Setting | Date Format    | Example          |
|----------------|----------------|------------------|
| US (default)   | MM/DD/YYYY     | 03/15/2025       |
| US (variant)   | M/D/YYYY       | 3/15/2025        |
| US (variant)   | MM/DD/YY       | 03/15/25         |
| International  | DD/MM/YYYY     | 15/03/2025       |
| ISO (rare)     | YYYY-MM-DD     | 2025-03-15       |

**Parser requirement:**
```python
from datetime import datetime

DATE_FORMATS = [
    '%m/%d/%Y',   # 03/15/2025
    '%m/%d/%y',   # 03/15/25
    '%Y-%m-%d',   # 2025-03-15
    '%d/%m/%Y',   # 15/03/2025 (international)
]

def parse_date(date_str: str) -> datetime:
    """
    Parse a date string trying multiple formats.
    Raises ValueError if none match.
    """
    date_str = date_str.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"Cannot parse date: '{date_str}'")
```

**Ambiguity warning:** For dates like `01/02/2025`, it is ambiguous whether this is January 2 (US) or February 1 (international). The parser should:
1. Detect the locale from the first 100 rows (if any day value > 12, the format is unambiguous)
2. Default to US format (MM/DD/YYYY) since this is a US-based CPA firm
3. Log a warning if ambiguous dates are detected

### 4.2 Date Range Strings in Payroll

The "Pay Period" field in payroll exports uses date range strings:

| Format Observed                  | Example                          |
|----------------------------------|----------------------------------|
| `MM/DD/YYYY to MM/DD/YYYY`      | `03/01/2025 to 03/15/2025`      |
| `MM/DD/YYYY - MM/DD/YYYY`       | `03/01/2025 - 03/15/2025`       |
| `M/D/YYYY - M/D/YYYY`           | `3/1/2025 - 3/15/2025`          |

**Parser requirement:**
```python
import re

def parse_pay_period(period_str: str) -> tuple:
    """
    Parse a pay period string into (start_date, end_date).
    Returns tuple of datetime objects.
    """
    # Split on " to " or " - "
    parts = re.split(r'\s+(?:to|-)\s+', period_str.strip())
    if len(parts) != 2:
        raise ValueError(f"Cannot parse pay period: '{period_str}'")
    return (parse_date(parts[0]), parse_date(parts[1]))
```

---

## 5. Currency and Number Format Issues

### 5.1 Currency Formatting

**Issue:** QBO exports monetary values with various formatting inconsistencies.

| Format Observed  | Example         | Notes                                        |
|------------------|-----------------|----------------------------------------------|
| Plain number     | `1500.00`       | Ideal format                                  |
| With commas      | `1,500.00`      | Most common in QBO exports                    |
| With $ prefix    | `$1,500.00`     | Sometimes present, sometimes not              |
| Negative (parens)| `(1,500.00)`    | Accounting-style negatives                    |
| Negative (minus) | `-1,500.00`     | Standard negative notation                    |
| With $ and parens| `($1,500.00)`   | Combination of styles                         |
| Blank/empty      | ``              | Missing value, treat as $0.00                 |
| Zero variants    | `0.00`, `-`, `$0.00` | Various representations of zero         |

**Parser requirement:**
```python
import re
from decimal import Decimal

def parse_currency(value: str) -> Decimal:
    """
    Parse a QBO currency string into a Decimal.
    Handles all known QBO formatting variations.
    """
    if not value or value.strip() in ('', '-', '--'):
        return Decimal('0.00')

    value = value.strip()

    # Detect negative (parentheses notation)
    is_negative = '(' in value and ')' in value

    # Remove $, commas, parentheses, spaces
    value = re.sub(r'[$,\(\)\s]', '', value)

    # Handle remaining minus sign
    if is_negative and not value.startswith('-'):
        value = '-' + value

    try:
        return Decimal(value).quantize(Decimal('0.01'))
    except Exception:
        raise ValueError(f"Cannot parse currency value: '{value}'")
```

### 5.2 Percentage Formatting in Payroll

Payroll tax rates may appear as percentages in some exports:
- `6.20%` (with percent sign)
- `0.062` (as decimal)
- `6.2` (as number without percent sign)

**Parser requirement:** The parser should not import tax rates from the CSV (rates are stored in `payroll_tax_tables`). Only import calculated dollar amounts.

---

## 6. Voided and Deleted Records

### 6.1 Voided Transactions

**Issue:** Voided transactions remain in QBO and appear in exports with specific markers.

**How voided transactions appear:**

| Field             | Original Value         | After Voiding                       |
|--------------------|------------------------|-------------------------------------|
| Amount             | `1,500.00`             | `0.00`                              |
| Memo/Description   | `Monthly service`      | `Void: Monthly service`             |
| Transaction Type   | `Invoice`              | `Invoice` (unchanged)               |
| Date               | `03/15/2025`           | `03/15/2025` (unchanged)            |
| No.                | `1042`                 | `1042` (unchanged)                  |

**Detection rule:**
```python
def is_voided(row: dict) -> bool:
    """Detect if a transaction row represents a voided transaction."""
    memo = row.get('Memo/Description', '') or ''
    amount = parse_currency(row.get('Amount', '0'))

    # Primary detection: memo starts with "Void:"
    if memo.strip().lower().startswith('void:'):
        return True

    # Secondary detection: amount is 0.00 (less reliable, may be false positive)
    # Only flag if combined with other indicators
    return False
```

**Import handling:**
- **[CPA_REVIEW_NEEDED]:** Decide whether to import voided transactions:
  - **Option A (recommended):** Import as `status = 'VOID'` for audit trail
  - **Option B:** Skip voided transactions entirely
  - Regardless: voided transactions must NOT affect GL balances

### 6.2 Deleted Transactions

**Issue:** Deleted transactions do NOT appear in QBO CSV exports at all. They are permanently removed from the export data.

**Implications:**
- There is no way to detect deleted transactions from a single CSV export
- If the CPA exports data at two different times, the diff could reveal deletions
- For migration purposes: deleted transactions are simply absent and cannot be recovered from CSV
- The migration is inherently a snapshot in time

**Recommendation:** The CPA should export all data at the same time (same day, ideally within the same hour) to ensure consistency across all export files.

### 6.3 Inactive / Archived Accounts

**Issue:** QBO Chart of Accounts may include inactive (archived) accounts in the export, depending on report settings.

**Detection:** There is no explicit "Status" or "Active" column in the Account List export. However:
- Inactive accounts may have a `Balance` of `$0.00`
- Some QBO versions prefix inactive account names with `(inactive)` or similar marker
- The CPA should check "Include inactive" checkbox setting before export

**Import handling:**
- Import all accounts (active and inactive)
- Set `is_active = FALSE` for accounts identified as inactive
- Inactive accounts should still be available for viewing historical transactions

---

## 7. Payroll Export Specific Issues

### 7.1 Payroll Subscription Required

**Issue:** Payroll data exports require an active QBO Payroll subscription. If the subscription has lapsed or been canceled:
- The "Reports > Payroll" section may not be accessible
- Historical payroll data may still be viewable but not exportable
- The CPA may need to reactivate the subscription temporarily for export

**[CPA_REVIEW_NEEDED]:** Verify that QBO Payroll subscription is active before attempting payroll export.

### 7.2 Payroll Summary Report Structure

**Issue:** The Payroll Summary report is NOT a standard flat CSV. It uses a pivot-table style layout with:
- Two-level column headers (EMPLOYEE taxes vs EMPLOYER taxes)
- Employee names as row headers
- Subtotals by department or pay period (depending on grouping)
- Grand totals at the bottom

**Parser requirement:** The parser must handle the two-level header structure and properly associate values with the correct column semantics. A dedicated payroll report parser (separate from the generic CSV parser) is recommended.

### 7.3 Missing Payroll Tax Breakdown

**Issue:** Some QBO Payroll tiers (especially Core) may not break down all tax categories individually. Instead, they may show:
- "Total Taxes" as a lump sum instead of individual Federal, State, SS, Medicare columns
- "Employee Taxes" and "Employer Taxes" as aggregate columns

**Parser requirement:**
- Detect whether individual tax columns are present
- If only aggregate columns exist: flag as `[PAYROLL_BREAKDOWN_MISSING]`
- Import gross pay and net pay; set individual tax fields to NULL with a warning
- CPA must provide individual tax breakdowns manually or from a different source

### 7.4 Payroll Adjustments and Corrections

**Issue:** Payroll corrections in QBO may appear as:
- Negative payroll amounts (reversal of a prior pay period)
- A second payroll entry for the same period (correction)
- A manual journal entry instead of a payroll transaction

**Parser requirement:**
- Allow negative payroll amounts (they represent reversals)
- Flag pay periods with multiple entries for the same employee for CPA review
- Cross-reference payroll journal entries with payroll summary data

### 7.5 Year-End Payroll Forms (W-2, 1099)

**Issue:** QBO generates W-2 and 1099 forms, but these are NOT available as CSV exports. They are PDF-only.

**Implication:** W-2 and 1099 data must be derived from imported payroll records, not imported directly from QBO exports.

---

## 8. Multi-Currency Issues

### 8.1 Multi-Currency Detection

**Issue:** If multi-currency is enabled in QBO, additional columns appear in exports:

| Additional Column   | Description                          |
|---------------------|--------------------------------------|
| Currency            | Transaction currency (e.g., USD, EUR) |
| Exchange Rate       | Rate at time of transaction          |
| Home Currency Amount| Amount in home (USD) currency        |
| Foreign Amount      | Amount in foreign currency           |

**Parser requirement:**
- Check for presence of Currency column in any export
- If ALL values are "USD" or column is absent: proceed normally
- If ANY non-USD values are found: HALT immediately with error:
  ```
  MULTI-CURRENCY DETECTED
  =======================
  Non-USD transactions found. This migration tool currently
  supports USD-only data.

  Action required:
  1. Review non-USD transactions in QBO
  2. Decide conversion approach with CPA
  3. Contact migration team for multi-currency support

  Non-USD currencies found: EUR (12 transactions), CAD (3 transactions)
  ```

---

## 9. Column Header Variations

### 9.1 Known Header Variations Across QBO Versions

The same logical column may have different header text across QBO versions and subscription tiers:

| Logical Column       | Variation 1              | Variation 2               | Variation 3                 |
|----------------------|--------------------------|---------------------------|-----------------------------|
| Transaction number   | `No.`                    | `Num`                     | `Number`                    |
| Description          | `Memo/Description`       | `Memo`                    | `Description`               |
| Customer name        | `Customer`               | `Customer/Vendor`         | `Name`                      |
| Amount               | `Amount`                 | `Total`                   | `Total Amount`              |
| Open Balance         | `Open Balance`           | `Balance Due`             | `Balance`                   |
| Account number       | `Account #`              | `Account Number`          | `Acct. #`                   |
| Invoice date         | `Invoice Date`           | `Date`                    | `Txn Date`                  |
| 1099 tracking        | `1099 Tracking`          | `Track payments for 1099` | `1099`                      |
| State tax            | `GA Withholding`         | `State Withholding`       | `State Tax`                 |
| State unemployment   | `GA SUI`                 | `GA Unemployment`         | `State Unemployment`        |
| Federal unemployment | `Federal Unemployment`   | `FUTA`                    | `Federal Unemp.`            |

**Parser requirement:**
```python
# Column name alias mapping
COLUMN_ALIASES = {
    'transaction_number': ['No.', 'Num', 'Number', 'No', 'Ref #'],
    'description': ['Memo/Description', 'Memo', 'Description'],
    'customer': ['Customer', 'Customer/Vendor', 'Name'],
    'amount': ['Amount', 'Total', 'Total Amount'],
    'open_balance': ['Open Balance', 'Balance Due', 'Balance'],
    'account_number': ['Account #', 'Account Number', 'Acct. #', 'Acct #'],
    'invoice_date': ['Invoice Date', 'Date', 'Txn Date'],
    'is_1099': ['1099 Tracking', 'Track payments for 1099', '1099'],
    'state_tax': ['GA Withholding', 'State Withholding', 'State Tax',
                  'Georgia Withholding', 'State Withholding - GA'],
    'state_unemployment': ['GA SUI', 'GA Unemployment', 'State Unemployment',
                          'GA SUTA', 'State Unemployment - GA'],
    'federal_unemployment': ['Federal Unemployment', 'FUTA', 'Federal Unemp.'],
    'social_security_ee': ['Social Security Employee', 'SS Employee',
                          'Social Security', 'Employee SS'],
    'social_security_er': ['Social Security Employer', 'SS Employer',
                          'Employer SS'],
    'medicare_ee': ['Medicare Employee', 'Employee Medicare', 'Medicare'],
    'medicare_er': ['Medicare Employer', 'Employer Medicare'],
}

def resolve_column(headers: list, canonical_name: str) -> str:
    """Find the actual column header that matches a canonical name."""
    aliases = COLUMN_ALIASES.get(canonical_name, [canonical_name])
    for alias in aliases:
        # Case-insensitive, whitespace-normalized match
        for header in headers:
            if header.strip().lower() == alias.lower():
                return header
    return None  # Column not found -- may be optional
```

---

## 10. Field Truncation Issues

### 10.1 Known Truncation Limits in QBO Exports

| Field               | QBO Storage Limit | CSV Export Limit | Notes                                |
|---------------------|-------------------|------------------|--------------------------------------|
| Customer name       | 500 chars         | 500 chars        | Rarely truncated                     |
| Vendor name         | 500 chars         | 500 chars        | Rarely truncated                     |
| Memo/Description    | 4,000 chars       | 4,000 chars      | May be truncated in some report views |
| Account name        | 100 chars         | 100 chars        | Rarely truncated                     |
| Address fields      | 500 chars each    | 500 chars        | Rarely truncated                     |
| Notes               | 4,000 chars       | 1,000 chars      | MAY BE TRUNCATED in CSV export       |
| Invoice line desc.  | 4,000 chars       | 4,000 chars      | Usually not in list export           |

**Parser requirement:** The parser should warn if any field value appears truncated (reaches exact limit length without natural ending). However, there is no reliable way to detect truncation from the CSV alone.

### 10.2 Account Name Hierarchy Truncation

**Issue:** Long sub-account hierarchies may be truncated:
```
Original: "Operating Expenses:Office Supplies:Printer Supplies:Toner Cartridges"
Truncated: "Operating Expenses:Office Supplies:Printer Suppl..."
```

**Parser requirement:** If an account name ends with `...`, flag as `[TRUNCATED_ACCOUNT]` and attempt to match using the available prefix.

---

## 11. Export Timing and Consistency

### 11.1 Real-Time Data Issue

**Issue:** QBO data is live. If transactions are entered between exports, the data across files will be inconsistent.

**Example scenario:**
1. Export Chart of Accounts at 10:00 AM
2. New account "Marketing Expenses" created at 10:15 AM
3. Transaction posted to "Marketing Expenses" at 10:20 AM
4. Export Transaction Detail at 10:30 AM
5. Result: Transaction references account not in Chart of Accounts export

**Recommendation:**
- Export ALL files within 15 minutes
- Do NOT enter any transactions during the export window
- Ideally export during non-business hours (early morning or weekend)
- After export, verify that account references in transactions resolve to Chart of Accounts

### 11.2 Accrual vs. Cash Basis

**Issue:** QBO reports can be exported in either Accrual or Cash basis, and the amounts will differ.

**Parser requirement:**
- The CPA must confirm which basis is used for the export
- All exports must use the SAME basis (all Accrual or all Cash)
- Verify basis is stated in the report header rows
- If basis is mixed across exports, HALT and request re-export

---

## 12. QBO Plan Tier Differences Affecting Exports

| Feature                    | Simple Start | Essentials | Plus  | Advanced |
|----------------------------|-------------|------------|-------|----------|
| Class Tracking             | No          | No         | Yes   | Yes      |
| Location Tracking          | No          | No         | Yes   | Yes      |
| Budgets                    | No          | No         | Yes   | Yes      |
| Inventory Tracking         | No          | No         | Yes   | Yes      |
| Custom fields              | No          | No         | No    | Yes      |
| Multiple custom fields     | No          | No         | No    | Yes      |
| Batch transactions         | No          | No         | No    | Yes      |
| Payroll (add-on)           | Add-on      | Add-on     | Add-on| Included |

**Implication:** The presence or absence of columns like Class, Location, and custom fields depends on the QBO plan tier. The parser must handle missing columns gracefully.

---

## 13. Known QBO Bugs and Workarounds

### 13.1 Duplicate Header Rows

**Bug:** Some QBO exports intermittently produce duplicate header rows mid-file (header row appears again after a certain number of data rows).

**Workaround:** After finding the header row, skip any subsequent rows that exactly match the header row values.

### 13.2 Empty Export with Data Present

**Bug:** Occasionally, QBO exports produce an empty file (just headers, no data) even when data exists in the date range.

**Workaround:**
1. Clear browser cache
2. Try a different browser (Chrome recommended for QBO)
3. Reduce the date range
4. Try the alternative menu path for the same report

### 13.3 Excel Format Issues

**Bug:** QBO "Export to Excel" produces XLSX files that some CSV converters mishandle (especially with formulas in total rows).

**Workaround:**
1. Open the XLSX in Excel/LibreOffice
2. Select all cells (Ctrl+A)
3. Copy and Paste Special > Values Only
4. Save As > CSV (UTF-8)

### 13.4 Number Stored as Text

**Bug:** Some QBO export cells store numbers as text (Excel will show a green triangle warning). This can cause issues with automated number parsing.

**Workaround:** The Python CSV parser treats everything as strings anyway, so this is only an issue if the CPA converts to CSV via Excel and Excel "helpfully" reformats values.

---

## 14. Pre-Migration Validation Checklist for QBO Exports

Before processing any export file, run these checks:

| # | Check                                          | How to Verify                                         | Severity |
|---|------------------------------------------------|-------------------------------------------------------|----------|
| 1 | File is not empty                              | File size > 0 bytes                                   | FATAL    |
| 2 | File is valid CSV (or can be converted)        | Open with csv.reader without error                    | FATAL    |
| 3 | Encoding is detected and readable              | All characters decode without errors                  | FATAL    |
| 4 | Header row is found                            | At least 2 known column names detected                | FATAL    |
| 5 | BOM is handled                                 | First column name does not start with \ufeff           | FATAL    |
| 6 | At least one data row exists                   | Row count after header > 0                            | FATAL    |
| 7 | No duplicate header rows mid-file              | Header values appear only once (or detected/skipped)  | WARNING  |
| 8 | Dates are parseable                            | All date fields match expected format                 | FATAL    |
| 9 | Amounts are parseable                          | All currency fields parse to Decimal                  | FATAL    |
| 10| No multi-currency                              | No non-USD values in Currency column                  | FATAL    |
| 11| Section headers are identified (for Transaction Detail) | Non-data rows classified correctly          | WARNING  |
| 12| Export basis is confirmed (Accrual vs Cash)    | Stated in report metadata rows                        | WARNING  |
| 13| Row count is reasonable                        | Not suspiciously low (possible truncation)            | WARNING  |
| 14| All account references resolve                 | Every account in transactions exists in Chart of Accounts | FATAL |
| 15| All customer references resolve                | Every customer in invoices exists in Customer List    | FATAL    |
