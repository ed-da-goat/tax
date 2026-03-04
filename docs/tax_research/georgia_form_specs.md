# Georgia Tax Form Specifications

## Research Agent: Georgia Tax Research Agent (Agent 04)
## Date Compiled: 2026-03-04
## Applicable Tax Years: 2025, 2026

---

## 1. FORM G-7 — QUARTERLY RETURN FOR WITHHOLDING TAX

### 1.1 Purpose

Form G-7 is the Georgia quarterly withholding tax return used by employers
to report and remit Georgia income tax withheld from employee wages.

```
SOURCE: Georgia Department of Revenue, Form G-7 Instructions
URL: https://dor.georgia.gov/form/form-g-7-quarterly-return-georgia-withholding-tax
VERIFIED: 2026-03-04 (from training knowledge)
REVIEW DATE: 2026-01-01
```

### 1.2 Filing Frequency Rules

Georgia assigns employers to a filing and payment frequency based on the
amount of withholding tax liability:

| Annual Liability | Payment Frequency | Return Frequency |
|-----------------|-------------------|------------------|
| $0 - $200 | Quarterly | Quarterly (Form G-7) |
| $200 - $1,000 | Monthly | Quarterly (Form G-7) |
| $1,000 - $10,000 | Monthly | Quarterly (Form G-7) |
| Over $10,000 (monthly) | Semi-weekly | Quarterly (Form G-7) |

```
SOURCE: Georgia DOR Employer's Tax Guide
URL: https://dor.georgia.gov/withholding-tax
VERIFIED: 2026-03-04 (from training knowledge)
REVIEW DATE: 2026-01-01
NOTES: Payment frequency determines when deposits are due. The quarterly
       G-7 return is filed regardless of payment frequency.
       The deposit frequency thresholds should be confirmed annually.
       # COMPLIANCE REVIEW NEEDED: Verify exact threshold amounts for
       # payment frequency assignment. Some sources list slightly different
       # thresholds.
```

### 1.3 Due Dates

| Quarter | Period | G-7 Due Date |
|---------|--------|-------------|
| Q1 | Jan 1 - Mar 31 | April 30 |
| Q2 | Apr 1 - Jun 30 | July 31 |
| Q3 | Jul 1 - Sep 30 | October 31 |
| Q4 | Oct 1 - Dec 31 | January 31 (following year) |

**Monthly payment due dates:** The 15th of the month following the month
in which the withholding occurred.

**Semi-weekly payment due dates:** Follow the IRS semi-weekly deposit
schedule (Wednesday payroll: deposit by following Friday; Friday payroll:
deposit by following Wednesday).

```
SOURCE: Georgia DOR Employer's Tax Guide
VERIFIED: 2026-03-04 (from training knowledge)
REVIEW DATE: 2026-01-01
NOTES: If a due date falls on a weekend or Georgia state holiday,
       the due date is the next business day.
```

### 1.4 Required Fields and Line Items

| Line | Description |
|------|-------------|
| Employer Name | Legal business name |
| FEIN | Federal Employer Identification Number |
| Georgia Withholding Number | GA withholding account number |
| Period Covered | Quarter start and end dates |
| Line 1 | Total Georgia income tax withheld for the quarter |
| Line 2 | Total payments/deposits already made for the quarter |
| Line 3 | Balance due (Line 1 - Line 2) or overpayment |
| Line 4 | Penalty (if applicable) |
| Line 5 | Interest (if applicable) |
| Line 6 | Total amount due |
| Signature | Authorized signer |
| Date | Date signed |

```
SOURCE: Georgia DOR Form G-7
URL: https://dor.georgia.gov/form/form-g-7-quarterly-return-georgia-withholding-tax
VERIFIED: 2026-03-04 (from training knowledge)
REVIEW DATE: 2026-01-01
NOTES: The exact line numbers and descriptions should be verified against
       the current year's form. Georgia DOR occasionally reorganizes forms.
```

### 1.5 Annual Reconciliation — Form G-1003

In addition to quarterly G-7 filings, employers must file an annual
reconciliation on Form G-1003 (Income Statement Return) along with
copies of W-2s issued to employees.

```
DUE DATE: February 28 (or March 31 if filing electronically)
SOURCE: Georgia DOR
URL: https://dor.georgia.gov/withholding-tax
VERIFIED: 2026-03-04 (from training knowledge)
REVIEW DATE: 2026-01-01
```

### 1.6 Electronic Filing Requirements

```
THRESHOLD: Employers with 100+ W-2s must file G-1003 and W-2s electronically.
           Smaller employers are encouraged but not required to e-file.
           G-7 quarterly returns can be filed and paid online via Georgia
           Tax Center (GTC): https://gtc.dor.ga.gov/

SOURCE: Georgia DOR
URL: https://gtc.dor.ga.gov/
VERIFIED: 2026-03-04 (from training knowledge)
REVIEW DATE: 2026-01-01
NOTES: The system should generate G-7 data in a format that can be
       entered into GTC or exported for e-filing. PDF generation
       is needed for record-keeping and paper filing.
```

---

## 2. FORM 500 — GEORGIA INDIVIDUAL INCOME TAX RETURN

### 2.1 Purpose and Applicability

Form 500 is the Georgia individual income tax return. For the CPA firm's
purposes, this is relevant for:
- **Sole proprietors** (Schedule C income flows to individual return)
- **S-Corp shareholders** (K-1 income flows to individual return)
- **Partnership members** (K-1 income flows to individual return)

```
SOURCE: Georgia DOR Form 500 Instructions
URL: https://dor.georgia.gov/form/form-500-individual-income-tax-return
VERIFIED: 2026-03-04 (from training knowledge)
REVIEW DATE: 2026-01-01
```

### 2.2 Relevant Schedules for Sole Proprietors

| Schedule | Description | Use Case |
|----------|-------------|----------|
| Schedule 1 | Adjustments to Federal AGI | Additions/subtractions from federal AGI |
| Schedule C (Federal) | Profit or Loss from Business | Net business income for sole props |
| Georgia Schedule SE | Self-employment tax deduction | Deduction for 50% of SE tax |

### 2.3 Key Line Items the System Needs to Populate

| Line | Description | Source in Our System |
|------|-------------|---------------------|
| Federal AGI | Adjusted Gross Income from federal return | P&L report |
| Georgia additions | Income taxable by GA but not federal | Georgia-specific adjustments |
| Georgia subtractions | Income not taxable by GA | Retirement income exclusion, etc. |
| Georgia AGI | Federal AGI + additions - subtractions | Calculated |
| Standard deduction | Based on filing status | See withholding tables |
| Personal exemptions | Based on dependents | Employee records |
| Georgia taxable income | Georgia AGI - deductions - exemptions | Calculated |
| Tax liability | Taxable income x rate (flat rate for 2024+) | Calculated |
| Withholding credits | GA withholding from W-2s/1099s | Payroll records |
| Estimated tax payments | Quarterly estimates paid | Payment records |
| Balance due / refund | Net after credits and payments | Calculated |

```
SOURCE: Georgia DOR Form 500 Instructions
VERIFIED: 2026-03-04 (from training knowledge)
REVIEW DATE: 2026-01-01
NOTES: The system should generate a data export that can be imported
       into professional tax software or used to populate Form 500.
       Direct PDF form filling is a stretch goal.
```

### 2.4 Due Dates

```
ANNUAL RETURN: April 15 (same as federal -- Georgia follows federal due date)
EXTENSION: Georgia automatic extension to October 15 if federal extension filed
           No separate Georgia extension form needed if Form 4868 filed federally

SOURCE: Georgia DOR
VERIFIED: 2026-03-04 (from training knowledge)
REVIEW DATE: 2026-01-01
NOTES: If April 15 falls on a weekend or holiday, the due date is
       the next business day.
```

### 2.5 Estimated Tax Payments (Form 500-ES)

| Payment | Period | Due Date |
|---------|--------|----------|
| 1st | Jan 1 - Mar 31 | April 15 |
| 2nd | Apr 1 - May 31 | June 15 |
| 3rd | Jun 1 - Aug 31 | September 15 |
| 4th | Sep 1 - Dec 31 | January 15 (following year) |

```
SOURCE: Georgia DOR Form 500-ES Instructions
VERIFIED: 2026-03-04 (from training knowledge)
REVIEW DATE: 2026-01-01
```

---

## 3. FORM 600 — GEORGIA CORPORATE INCOME TAX RETURN

### 3.1 Purpose and Applicability

Form 600 is the Georgia corporate income tax return for **C-Corporations only**.
S-Corporations file Form 600-S (an informational return).

```
SOURCE: Georgia DOR Form 600 Instructions
URL: https://dor.georgia.gov/form/form-600-corporation-tax-return
VERIFIED: 2026-03-04 (from training knowledge)
REVIEW DATE: 2026-01-01
```

### 3.2 Tax Rate

```
RATE: 5.75% of Georgia net taxable income (C-Corps)
SOURCE: Georgia Code Section 48-7-21
VERIFIED: 2026-03-04 (from training knowledge)
REVIEW DATE: 2026-01-01
NOTES: Georgia's corporate income tax rate is separate from the individual
       income tax flat rate reform. The corporate rate has remained at
       5.75% but CPA_OWNER should verify for Tax Year 2026.

       # COMPLIANCE REVIEW NEEDED: Verify whether HB 1015 or subsequent
       # legislation affects the corporate income tax rate for 2026.
```

**[UNVERIFIED] -- CPA_OWNER must confirm the 2026 corporate income tax rate.**

### 3.3 Key Line Items

| Line | Description | Source in Our System |
|------|-------------|---------------------|
| Federal taxable income | From federal Form 1120 | Federal data export |
| Georgia additions | Items added back per GA law | Georgia-specific adjustments |
| Georgia subtractions | Items subtracted per GA law | Georgia-specific adjustments |
| Georgia net income | Federal TI + additions - subtractions | Calculated |
| Apportionment factor | For multi-state corps (see 3.4) | Client settings |
| Georgia taxable income | Net income x apportionment factor | Calculated |
| Tax liability | Taxable income x 5.75% | Calculated |
| Credits | Various Georgia tax credits | Credit records |
| Estimated payments | Quarterly estimated payments | Payment records |
| Balance due / overpayment | Net after credits and payments | Calculated |

### 3.4 Apportionment Requirements (Multi-State Corporations)

Georgia uses a **single-factor sales apportionment formula** for most
corporations (effective for tax years beginning on or after January 1, 2008).

```
APPORTIONMENT FORMULA: 100% sales factor
  Georgia Sales / Total Sales Everywhere = Apportionment %

SOURCE: Georgia Code Section 48-7-31
VERIFIED: 2026-03-04 (from training knowledge)
REVIEW DATE: 2026-01-01
NOTES: - "Sales" includes gross receipts from tangible personal property
         and income-producing activity.
       - Manufacturing, selling, or processing tangible personal property:
         destination test (where the property is delivered).
       - Services and intangibles: income-producing activity test
         (where the benefit is received).
       - If a client operates only in Georgia, the apportionment
         factor is 100% (no apportionment needed).
       - The system should store per-client apportionment data and
         flag multi-state clients for CPA review.
```

### 3.5 Due Dates

```
C-CORP RETURN: April 15 (for calendar year filers), or the 15th day
               of the 4th month after the fiscal year end
EXTENSION: Georgia follows federal extension. If federal Form 7004 is
           filed, Georgia grants an automatic 6-month extension.
           However, estimated tax must still be paid by the original due date.

SOURCE: Georgia DOR Form 600 Instructions
VERIFIED: 2026-03-04 (from training knowledge)
REVIEW DATE: 2026-01-01
```

### 3.6 Estimated Tax Payments (Form 600-ES)

C-Corporations must make estimated tax payments if they expect to owe
$800 or more in Georgia income tax.

| Payment | Due Date (Calendar Year) |
|---------|------------------------|
| 1st | April 15 |
| 2nd | June 15 |
| 3rd | September 15 |
| 4th | December 15 |

```
SOURCE: Georgia DOR Form 600-ES Instructions
VERIFIED: 2026-03-04 (from training knowledge)
REVIEW DATE: 2026-01-01
```

---

## 4. FORM 600-S — GEORGIA S-CORPORATION TAX RETURN

### 4.1 Purpose

Form 600-S is the informational return for S-Corporations. S-Corps
themselves do not pay Georgia income tax; income passes through to
shareholders who report it on their individual Form 500.

```
SOURCE: Georgia DOR Form 600-S Instructions
URL: https://dor.georgia.gov/form/form-600s-corporation-tax-return
VERIFIED: 2026-03-04 (from training knowledge)
REVIEW DATE: 2026-01-01
NOTES: Georgia recognizes federal S-Corp elections. No separate Georgia
       S-Corp election is required.
```

### 4.2 Due Dates

```
DUE DATE: March 15 (for calendar year filers), or the 15th day of the
          3rd month after the fiscal year end
EXTENSION: Follows federal Form 7004. Automatic 6-month extension.

SOURCE: Georgia DOR
VERIFIED: 2026-03-04 (from training knowledge)
REVIEW DATE: 2026-01-01
```

### 4.3 Georgia Nonresident Shareholder Tax

Georgia requires S-Corps to withhold and remit tax on behalf of
nonresident shareholders at the highest individual tax rate.

```
RATE: Flat rate (5.19% for TY2025, verify for TY2026)
SOURCE: Georgia Code Section 48-7-129
VERIFIED: 2026-03-04 (from training knowledge)
REVIEW DATE: 2026-01-01
NOTES: The system should track shareholder residency and calculate
       nonresident withholding for applicable S-Corp clients.
       # COMPLIANCE REVIEW NEEDED: Verify if any clients have
       # nonresident shareholders requiring this withholding.
```

---

## 5. FORM ST-3 — GEORGIA SALES AND USE TAX RETURN

### 5.1 Purpose and Applicability

Form ST-3 is the Georgia sales and use tax return. It is required for
businesses that sell tangible personal property or certain services
subject to Georgia sales tax.

```
SOURCE: Georgia DOR Form ST-3 Instructions
URL: https://dor.georgia.gov/sales-use-tax
VERIFIED: 2026-03-04 (from training knowledge)
REVIEW DATE: 2026-01-01
```

### 5.2 Tax Rates

#### 5.2.1 State Rate

```
STATE RATE: 4.0%
SOURCE: Georgia Code Section 48-8-30
URL: https://dor.georgia.gov/sales-use-tax
VERIFIED: 2026-03-04 (from training knowledge)
REVIEW DATE: 2026-01-01
```

#### 5.2.2 Local Rates

Georgia allows counties and certain cities to impose additional
local option sales taxes (LOST, SPLOST, ELOST, MARTA, HOST, etc.).
The combined rate (state + local) varies by county.

```
COMBINED RATE RANGE: 7.0% to 9.0% (state 4% + local 3%-5%)
MOST COMMON COMBINED RATE: 7.0% to 8.0%

SOURCE: Georgia DOR Local Tax Rate Charts
URL: https://dor.georgia.gov/local-government-services/tax-rates
VERIFIED: 2026-03-04 (from training knowledge)
REVIEW DATE: Quarterly (local rates change frequently)
NOTES: Local sales tax rates change on a quarterly basis as
       jurisdictions adopt, renew, or sunset special purpose
       taxes. The system must look up the applicable combined
       rate based on the point of sale location (county/city).

       CPA_OWNER should download the current rate chart from
       Georgia DOR quarterly.
```

**[UNVERIFIED] -- Local sales tax rates change quarterly. The system
must use a rate lookup table that CPA_OWNER updates quarterly from
the Georgia DOR rate charts.**

### 5.3 Filing Frequency

| Monthly Liability | Filing Frequency |
|------------------|-----------------|
| $0 - $200 | Quarterly |
| $200 - $600 | Monthly |
| Over $600 | Monthly |

Some high-volume retailers may be assigned semi-monthly frequency.

```
SOURCE: Georgia DOR Sales Tax Filing Instructions
VERIFIED: 2026-03-04 (from training knowledge)
REVIEW DATE: 2026-01-01
NOTES: Filing frequency is assigned by Georgia DOR based on the
       taxpayer's average monthly liability. The exact thresholds
       should be confirmed for the current year.
       # COMPLIANCE REVIEW NEEDED: Verify exact filing frequency
       # thresholds for 2026.
```

### 5.4 Due Dates

**Monthly filers:** 20th of the month following the reporting period.

**Quarterly filers:**

| Quarter | Period | Due Date |
|---------|--------|----------|
| Q1 | Jan - Mar | April 20 |
| Q2 | Apr - Jun | July 20 |
| Q3 | Jul - Sep | October 20 |
| Q4 | Oct - Dec | January 20 (following year) |

```
SOURCE: Georgia DOR
VERIFIED: 2026-03-04 (from training knowledge)
REVIEW DATE: 2026-01-01
NOTES: If due date falls on a weekend or holiday, the next business
       day applies. Georgia offers a vendor's compensation (discount)
       for timely filing, typically 3% of the first $3,000 of tax
       due per reporting period.
```

### 5.5 Vendor's Compensation (Timely Filing Discount)

```
RATE: 3% of the first $3,000 of tax due, capped at $90 per period
SOURCE: Georgia Code Section 48-8-50
VERIFIED: 2026-03-04 (from training knowledge)
REVIEW DATE: 2026-01-01
NOTES: The discount is available only if the return is filed and
       payment is made on time. The system should calculate this
       automatically when generating ST-3 returns.
       # COMPLIANCE REVIEW NEEDED: Verify the vendor's compensation
       # rate and cap for 2026 -- these have been modified in the past.
```

### 5.6 Exempt Categories

Major categories exempt from Georgia sales tax include:

| Category | Code Reference |
|----------|---------------|
| Food for home consumption (groceries) | 48-8-3.2 |
| Prescription drugs | 48-8-3(20) |
| Medical equipment (with prescription) | 48-8-3(23) |
| Agricultural equipment and supplies | 48-8-3(29) |
| Manufacturing machinery (direct use) | 48-8-3(34) |
| Motor fuels (subject to motor fuel tax instead) | 48-8-3(1) |
| Sales for resale (with valid exemption certificate) | 48-8-3(2) |
| Sales to federal/state/local government | 48-8-3(5) |
| Sales to nonprofit hospitals | 48-8-3(6) |
| Certain energy used in manufacturing | 48-8-3.2 |

```
SOURCE: Georgia Code Title 48, Chapter 8 (Sales Tax)
VERIFIED: 2026-03-04 (from training knowledge)
REVIEW DATE: 2026-01-01
NOTES: Exemptions are frequently modified by the Georgia General Assembly.
       CPA_OWNER should review the current exemption list annually.
       The system should maintain a configurable exemption category list
       rather than hardcoding exemptions.
```

### 5.7 Required Fields on Form ST-3

| Field | Description |
|-------|-------------|
| Business name and address | Legal entity info |
| Sales tax number | Georgia sales tax account number |
| FEIN | Federal Employer ID Number |
| Period covered | Month or quarter |
| Gross sales | Total gross sales for the period |
| Exempt sales | Sales in exempt categories |
| Taxable sales | Gross sales - exempt sales |
| State tax collected | Taxable sales x 4% |
| Local taxes collected | By jurisdiction, at applicable rates |
| Total tax due | State + local |
| Vendor's compensation | Discount for timely filing |
| Net tax due | Total tax - vendor's compensation |

---

## 6. FORM 1065 DATA — GEORGIA PARTNERSHIP RETURN (FORM 700)

### 6.1 Purpose

Georgia partnerships file Form 700 (Partnership Return). This is an
informational return; income passes through to partners.

```
SOURCE: Georgia DOR Form 700 Instructions
URL: https://dor.georgia.gov/form/form-700-partnership-tax-return
VERIFIED: 2026-03-04 (from training knowledge)
REVIEW DATE: 2026-01-01
```

### 6.2 Due Dates

```
DUE DATE: March 15 (calendar year) or 15th day of 3rd month after FY end
EXTENSION: Follows federal Form 7004
SOURCE: Georgia DOR
VERIFIED: 2026-03-04 (from training knowledge)
REVIEW DATE: 2026-01-01
```

### 6.3 Nonresident Withholding

Similar to S-Corps, partnerships must withhold Georgia tax on behalf
of nonresident partners.

```
SOURCE: Georgia Code Section 48-7-129
VERIFIED: 2026-03-04 (from training knowledge)
REVIEW DATE: 2026-01-01
```

---

## 7. IMPLEMENTATION NOTES FOR BUILDER AGENTS

### 7.1 Form Generation Priority

The system should generate forms in this priority order:
1. Form G-7 (quarterly -- most frequent filing)
2. Form ST-3 (monthly or quarterly -- frequent)
3. Form 500 (annual -- sole proprietor clients)
4. Form 600/600-S (annual -- corporate clients)
5. Form 700 (annual -- partnership clients)
6. Form G-1003 (annual reconciliation)

### 7.2 PDF Generation

Use WeasyPrint (per tech stack) to generate PDFs that match the
official Georgia DOR form layouts. The PDFs should be:
- Print-ready at standard letter size (8.5" x 11")
- Fillable where possible (for e-filing or manual review)
- Stored in /data/documents/[client_id]/tax_forms/

### 7.3 E-Filing Integration

Georgia Tax Center (GTC) at https://gtc.dor.ga.gov/ supports:
- Online filing of G-7, ST-3
- Bulk W-2 upload for G-1003
- Payment submission

The system should generate data in GTC-compatible format where possible.
Full API integration with GTC is out of scope for the initial build.

---

## 8. OPEN QUESTIONS FOR CPA_OWNER

1. **[COMPLIANCE]** Confirm 2026 corporate income tax rate (5.75% or changed)
2. **[COMPLIANCE]** Identify which clients collect sales tax and their filing frequency
3. **[COMPLIANCE]** Confirm which clients are S-Corps vs C-Corps vs partnerships
4. **[COMPLIANCE]** Identify any clients with nonresident shareholders/partners
5. **[COMPLIANCE]** Verify current local sales tax rates for each client's jurisdiction
6. **[COMPLIANCE]** Confirm vendor's compensation rate and cap for 2026
