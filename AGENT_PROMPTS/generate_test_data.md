# PROMPT: Generate Fake QBO Export CSV Files for End-to-End Testing

## YOUR TASK
Generate a complete set of fake QuickBooks Online (QBO) CSV export files that simulate a realistic CPA firm's client data. These files will be imported through the migration pipeline (`backend/app/services/migration/`) and then used to test the full accounting workflow: journal entries, approvals, AP/AR, payroll, tax exports, and reporting.

Create **4 fake clients** covering all entity types the system supports. Each client should have enough transaction history, invoices, bills, payroll, and bank activity to exercise every major feature.

---

## OUTPUT: Files to Create

Create all files under: `test_data/`

### Per-Client CSV Files (4 clients × 8 file types = 32 files)

Use this naming convention: `test_data/{client_slug}/` with one CSV per export type.

**Client 1: "Peachtree Landscaping LLC"** — `peachtree_landscaping/`
- Entity type: SOLE_PROP
- Georgia-based sole proprietor, landscaping services
- 2 employees, seasonal work
- Should have sales tax (ST-3 applicable)

**Client 2: "Atlanta Tech Solutions Inc"** — `atlanta_tech/`
- Entity type: S_CORP
- IT consulting S-Corp, 3 employees
- Higher revenue, quarterly payroll
- No sales tax (services only)

**Client 3: "Southern Manufacturing Corp"** — `southern_mfg/`
- Entity type: C_CORP
- Manufacturing company, 4 employees
- Inventory, COGS, equipment depreciation
- Sales tax applicable

**Client 4: "Buckhead Partners Group"** — `buckhead_partners/`
- Entity type: PARTNERSHIP_LLC
- Professional services partnership (2 partners + 1 employee)
- Partner draws, K-1 distributions
- No sales tax

---

## CSV FORMAT SPECIFICATIONS

### 1. Chart of Accounts (`chart_of_accounts.csv`)
```
Account,Type,Detail Type,Description,Balance,Currency,Account #
```
- Each client needs 15-25 accounts covering: bank (checking, savings), AR, AP, credit card, fixed assets, equity, revenue accounts, expense accounts (rent, utilities, payroll, insurance, supplies, etc.)
- Use QBO type names: "Bank", "Accounts Receivable (A/R)", "Accounts Payable (A/P)", "Credit Card", "Fixed Asset", "Other Current Asset", "Other Current Liability", "Equity", "Income", "Expense", "Cost of Goods Sold", "Other Income", "Other Expense"
- Use QBO detail types: "Checking", "Savings", "Accounts Receivable (A/R)", "Accounts Payable (A/P)", "Inventory", "Prepaid Expenses", "Furniture & Fixtures", "Machinery & Equipment", "Vehicles", "Accumulated Depreciation", "Payroll Liabilities", "Sales Tax Payable", "Owner's Equity", "Retained Earnings", "Owner's Draw", "Sales of Product Income", "Service/Fee Income", "Interest Earned", etc.
- Balances: use realistic dollar amounts with commas and dollar signs (e.g., "$45,678.90")
- Account numbers: use 4-digit numbers (1000-9999)

### 2. Transactions (`transactions.csv`)
```
Date,Transaction Type,No.,Name,Memo/Description,Split,Amount,Balance,Account
```
- Date format: MM/DD/YYYY
- 30-50 transactions per client spanning the last 12 months (use dates in 2025)
- Transaction types: "Check", "Deposit", "Invoice", "Bill", "Payment", "Transfer", "Journal Entry", "Credit Card Charge", "Sales Receipt"
- Amounts: signed decimals (negative for expenses/checks, positive for income/deposits)
- Include realistic memos: "Monthly rent", "Office supplies - Staples", "Client payment - Invoice #1042"
- Each transaction references an Account name from the CoA

### 3. Customers (`customers.csv`)
```
Customer,Phone,Email,Company,Billing Street,Billing City,Billing State,Billing ZIP,Open Balance
```
- 3-6 customers per client
- Georgia addresses (Atlanta, Marietta, Decatur, Roswell, Alpharetta, etc.)
- Realistic business names and contacts
- Open balances for some (unpaid invoices)

### 4. Invoices (`invoices.csv`)
```
Invoice Date,No.,Customer,Due Date,Amount,Open Balance,Status
```
- 8-15 invoices per client over the last 12 months
- Mix of statuses: "Paid", "Open", "Overdue"
- Due dates: typically Net 30 from invoice date
- Some with partial payments (Open Balance < Amount)
- Invoice numbers: sequential (e.g., 1001, 1002, ...)

### 5. Vendors (`vendors.csv`)
```
Vendor,Company,Phone,Email,Street,City,State,ZIP
```
- 4-8 vendors per client
- Include: utility companies (Georgia Power, Atlanta Gas Light), office supplies, insurance, landlord, professional services
- Georgia addresses

### 6. Employees (`employees.csv`)
```
Employee,SSN (last 4),Hire Date,Status,Pay Type,Pay Rate,Filing Status
```
- SSN: last 4 digits only (fake, e.g., "1234")
- Hire dates: various, some multi-year tenure
- Pay types: mix of "Hourly" and "Salary"
- Pay rates: realistic for Georgia (hourly $15-$45, salary $3,000-$8,000/mo)
- Filing statuses: "Single", "Married", "Head of Household"
- All Active status (no terminated for test data)

### 7. Payroll Summary (`payroll_summary.csv`)
```
Employee,Gross Pay,Federal Withholding,Social Security Employee,Medicare Employee,GA Withholding,Net Pay,Federal Unemployment,GA SUI
```
- One row per employee per pay period
- Include 4-6 pay periods (monthly or bi-weekly)
- Tax calculations should be approximately correct:
  - Federal withholding: ~12-22% of gross depending on filing status
  - Social Security: 6.2% of gross (up to $168,600 wage base)
  - Medicare: 1.45% of gross
  - GA withholding: ~2-5.75% of gross
  - FUTA: 0.6% of gross (up to $7,000 wage base) — employer only
  - GA SUTA: 2.7% of gross (up to $9,500 wage base) — employer only
- Net pay = Gross - Federal WH - SS - Medicare - GA WH

### 8. General Journal (`general_journal.csv`)
```
Date,No.,Account,Debit,Credit,Name,Memo/Description
```
- 5-10 journal entries per client
- Each entry: 2+ lines that balance (total debits = total credits)
- Types: depreciation, adjusting entries, accruals, owner draws
- Entry numbers: JE-001, JE-002, etc.
- Only one of Debit or Credit per line (never both)

---

## DATA REALISM REQUIREMENTS

1. **Georgia-specific**: All addresses in Georgia. Use real city names (Atlanta, Marietta, Decatur, Roswell, Alpharetta, Savannah, Augusta, Kennesaw, Sandy Springs, Duluth). Use ZIP codes that match (30301-30399 Atlanta area, 30060-30069 Marietta, etc.).

2. **Financial consistency**:
   - Trial balance should roughly balance (total debits ≈ total credits across all accounts)
   - Revenue should exceed expenses for at least 2 of 4 clients (profitable businesses)
   - One client can show a loss (realistic for newer business)
   - Payroll expenses should match payroll summary totals

3. **Seasonal patterns** (for landscaping client): Higher revenue in spring/summer (March-September), lower in winter.

4. **Entity-type appropriate**:
   - SOLE_PROP: Owner's equity, owner's draw, Schedule C categories
   - S_CORP: Shareholder distributions, reasonable salary, 1120-S categories
   - C_CORP: Retained earnings, corporate tax accounts, 1120 categories
   - PARTNERSHIP_LLC: Partner equity accounts, partner draws, 1065 categories

5. **Amounts**: Use realistic Georgia small business ranges:
   - Annual revenue: $150K-$800K
   - Monthly rent: $1,500-$4,000
   - Monthly utilities: $200-$600
   - Insurance: $500-$1,500/month
   - Supplies: $200-$1,000/month

6. **Dates**: All transactions in 2025 calendar year (01/01/2025 through 12/31/2025). Use a full year of data.

7. **DO NOT** use real SSNs, real tax IDs, or real people's names. All data must be clearly fictional.

---

## VALIDATION CHECKLIST

After generating, verify:
- [ ] Every CSV has the correct header row with exact column names listed above
- [ ] All dates are MM/DD/YYYY format
- [ ] All amounts use comma separators for thousands (e.g., "1,500.00")
- [ ] Each journal entry balances (sum of debits = sum of credits per entry number)
- [ ] Each employee appears in both employees.csv AND payroll_summary.csv
- [ ] Each customer in invoices.csv appears in customers.csv
- [ ] Each vendor referenced in transactions appears in vendors.csv
- [ ] Account names in transactions.csv match accounts in chart_of_accounts.csv
- [ ] No real PII — all names, SSNs, tax IDs, addresses are fictional
- [ ] File encoding is UTF-8
- [ ] 4 client folders created, each with all 8 CSV files

---

## DIRECTORY STRUCTURE
```
test_data/
├── peachtree_landscaping/
│   ├── chart_of_accounts.csv
│   ├── transactions.csv
│   ├── customers.csv
│   ├── invoices.csv
│   ├── vendors.csv
│   ├── employees.csv
│   ├── payroll_summary.csv
│   └── general_journal.csv
├── atlanta_tech/
│   ├── (same 8 files)
├── southern_mfg/
│   ├── (same 8 files)
└── buckhead_partners/
    └── (same 8 files)
```

## IMPORTANT
- Generate ALL 32 files. Do not skip any.
- Each CSV must be parseable by Python's `csv.DictReader` with no errors.
- Use double quotes around fields that contain commas.
- Do not include BOM characters.
- Do not include subtotal or total rows — raw data only.
