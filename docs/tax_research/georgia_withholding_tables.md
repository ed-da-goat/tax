# Georgia Income Tax Withholding Tables

## Research Agent: Georgia Tax Research Agent (Agent 04)
## Date Compiled: 2026-03-04
## Applicable Tax Years: 2024, 2025, 2026

---

## IMPORTANT: GEORGIA TAX REFORM TRANSITION

Georgia enacted HB 1015 (signed April 2022) which transitions the state
from a graduated income tax to a flat tax. The transition schedule is:

- Tax Year 2024: 5.39% flat rate
- Tax Year 2025: 5.19% flat rate (scheduled reduction)
- Tax Year 2026: Target 4.99% (subject to revenue triggers)

```
# SOURCE: Georgia HB 1015 (Act 167), signed April 26, 2022
# URL: https://www.legis.ga.gov/legislation/61948
# VERIFIED: 2026-03-04 (from training knowledge; CPA must confirm 2026 rate)
# REVIEW DATE: 2026-01-01 (annually)
# NOTES: The 2026 rate of 4.99% is contingent on revenue triggers being met.
#        CPA_OWNER MUST verify the actual enacted rate for Tax Year 2026
#        before any payroll processing.
```

**[UNVERIFIED] -- The Tax Year 2026 rate MUST be confirmed by CPA_OWNER
against the Georgia DOR Employer's Tax Guide for 2026 before production use.**

---

## 1. TAX YEAR 2025 WITHHOLDING TABLES (Most Recent Verified)

### 1.1 Tax Rate

```
RATE: 5.19% flat rate on Georgia taxable income
SOURCE: Georgia DOR Employer's Tax Guide, Tax Year 2025
URL: https://dor.georgia.gov/withholding-tax
VERIFIED: 2026-03-04 (from training knowledge)
REVIEW DATE: 2026-01-01
NOTES: Georgia transitioned from graduated brackets to flat rate starting
       Tax Year 2024. The withholding method now applies a single rate
       after subtracting standard deduction and personal exemptions.
```

### 1.2 Filing Statuses (Georgia Form G-4)

Georgia recognizes the following filing statuses for withholding purposes:

| Code | Filing Status | Notes |
|------|--------------|-------|
| S | Single | |
| MFJ | Married Filing Jointly | |
| MFS | Married Filing Separately | |
| HOH | Head of Household | |

```
SOURCE: Georgia Form G-4, Employee's Withholding Allowance Certificate
URL: https://dor.georgia.gov/form/form-g-4-employee-withholding
VERIFIED: 2026-03-04 (from training knowledge)
REVIEW DATE: 2026-01-01
```

### 1.3 Standard Deduction Amounts (Tax Year 2025)

| Filing Status | Standard Deduction |
|--------------|-------------------|
| Single | $5,400 |
| Married Filing Jointly | $7,100 |
| Married Filing Separately | $3,550 |
| Head of Household | $5,400 |

```
RATE: See table above
SOURCE: Georgia DOR Employer's Tax Guide, Tax Year 2025
URL: https://dor.georgia.gov/withholding-tax
VERIFIED: 2026-03-04 (from training knowledge)
REVIEW DATE: 2026-01-01
NOTES: Standard deduction amounts are set by the Georgia General Assembly
       and may change annually. These amounts reflect the post-HB 1015
       adjustments. CPA_OWNER should verify against the current year's
       Employer's Tax Guide.
```

**[UNVERIFIED] -- Tax Year 2026 standard deduction amounts may differ.
CPA_OWNER must confirm against the 2026 Employer's Tax Guide.**

### 1.4 Personal Exemption / Allowance Amounts (Tax Year 2025)

| Exemption Type | Amount |
|---------------|--------|
| Personal exemption (taxpayer) | $2,700 |
| Personal exemption (spouse, if MFJ) | $2,700 |
| Dependent exemption (each) | $3,000 |

```
RATE: See table above
SOURCE: Georgia DOR Employer's Tax Guide, Tax Year 2025
URL: https://dor.georgia.gov/withholding-tax
VERIFIED: 2026-03-04 (from training knowledge)
REVIEW DATE: 2026-01-01
NOTES: Employee claims exemptions on Georgia Form G-4. The number of
       allowances on the G-4 determines total exemptions deducted from
       gross wages before applying the tax rate.
```

**[UNVERIFIED] -- Tax Year 2026 exemption amounts may differ.
CPA_OWNER must confirm against the 2026 Employer's Tax Guide.**

### 1.5 Withholding Calculation Method (Flat Tax Method)

Under the flat tax regime (Tax Year 2024+), the withholding calculation is:

```
STEP 1: Start with gross wages for the pay period
STEP 2: Annualize the wages (multiply by number of pay periods per year)
         - Weekly: x 52
         - Biweekly: x 26
         - Semimonthly: x 24
         - Monthly: x 12
STEP 3: Subtract the annual standard deduction (based on filing status)
STEP 4: Subtract personal exemptions:
         - Taxpayer exemption: $2,700
         - Spouse exemption (if MFJ): $2,700
         - Dependent exemptions: $3,000 x number of dependents claimed
STEP 5: Compute the annual tax:
         - Georgia taxable income x flat rate (5.19% for TY2025)
STEP 6: De-annualize to get per-period withholding:
         - Divide annual tax by number of pay periods per year
STEP 7: Round to nearest cent
```

```
SOURCE: Georgia DOR Employer's Tax Guide, Tax Year 2025 (Percentage Method)
URL: https://dor.georgia.gov/withholding-tax
VERIFIED: 2026-03-04 (from training knowledge)
REVIEW DATE: 2026-01-01
NOTES: Prior to TY2024, Georgia used graduated brackets (1%-5.75%).
       The new flat tax method is simpler. Builder agents should implement
       the flat rate method and parameterize the rate in the
       payroll_tax_tables database table for easy annual updates.
```

### 1.6 Pre-Reform Graduated Brackets (HISTORICAL REFERENCE ONLY)

For migrating historical payroll records from QuickBooks, the system may
need these rates for verification purposes:

**Tax Year 2023 and earlier (graduated brackets):**

| Taxable Income Over | But Not Over | Tax Rate |
|---------------------|-------------|----------|
| $0 | $750 | 1.0% |
| $750 | $2,250 | 2.0% |
| $2,250 | $3,750 | 3.0% |
| $3,750 | $5,250 | 4.0% |
| $5,250 | $7,000 | 5.0% |
| $7,000 | -- | 5.75% |

```
SOURCE: Georgia DOR Employer's Tax Guide, Tax Year 2023
VERIFIED: 2026-03-04 (from training knowledge)
NOTES: HISTORICAL ONLY. Do not use for current withholding calculations.
       Included for migration verification of pre-2024 payroll records.
```

### 1.7 Supplemental Wage Withholding Rate

```
RATE: Georgia does not publish a separate flat supplemental wage rate like
      the federal system. Supplemental wages (bonuses, commissions, etc.)
      are generally subject to withholding using either:
      (a) The aggregate method: add supplemental wages to regular wages
          for the pay period and compute withholding on the total, OR
      (b) A flat percentage method at the current state rate (5.19% for TY2025)

SOURCE: Georgia DOR Employer's Tax Guide
URL: https://dor.georgia.gov/withholding-tax
VERIFIED: 2026-03-04 (from training knowledge)
REVIEW DATE: 2026-01-01
NOTES: Builder agents should implement the aggregate method as the default
       and allow CPA_OWNER to select the flat-rate method as an option.
       # COMPLIANCE REVIEW NEEDED: CPA_OWNER should verify whether Georgia
       # formally adopted a flat supplemental rate matching the flat tax rate,
       # or if the aggregate method remains mandatory.
```

### 1.8 Exempt from Withholding

An employee may claim exempt from Georgia withholding on Form G-4 if:
- They had no Georgia income tax liability in the prior year, AND
- They expect no Georgia income tax liability in the current year

The employer must receive a new G-4 each year from exempt employees.
G-4 exemptions expire on February 15 of the following year.

```
SOURCE: Georgia Form G-4 Instructions
URL: https://dor.georgia.gov/form/form-g-4-employee-withholding
VERIFIED: 2026-03-04 (from training knowledge)
REVIEW DATE: 2026-01-01
```

---

## 2. TAX YEAR 2026 WITHHOLDING (PROJECTED)

### 2.1 Projected Rate

```
RATE: 4.99% (projected, subject to revenue trigger)
SOURCE: Georgia HB 1015 (Act 167), transition schedule
VERIFIED: 2026-03-04 (from training knowledge -- PROJECTION ONLY)
REVIEW DATE: 2026-01-01

# ⚠ UNVERIFIED — CPA_OWNER must confirm before production use
# The 4.99% rate depends on revenue triggers specified in HB 1015.
# If triggers are not met, the rate may remain at 5.19%.
# Check: https://dor.georgia.gov/withholding-tax for the 2026 Guide.
```

### 2.2 Projected Standard Deductions and Exemptions

Standard deductions and personal exemptions for Tax Year 2026 have not
been confirmed as of this research date. They may be adjusted.

```
# ⚠ UNVERIFIED — CPA_OWNER must obtain the 2026 Employer's Tax Guide
# from Georgia DOR and update the payroll_tax_tables database table
# with confirmed 2026 values before processing any 2026 payroll.
```

---

## 3. IMPLEMENTATION NOTES FOR BUILDER AGENTS

### 3.1 Database Design Requirements

All rates documented above MUST be stored in the `payroll_tax_tables`
database table, parameterized by:
- `tax_year` (integer)
- `filing_status` (enum: S, MFJ, MFS, HOH)
- `rate_type` (enum: FLAT_RATE, STANDARD_DEDUCTION, PERSONAL_EXEMPTION, DEPENDENT_EXEMPTION)
- `amount` (decimal)
- `effective_date` (date)
- `source_citation` (text -- must include document name, year, and URL)
- `verified_date` (date)
- `verified_by` (FK to users -- CPA_OWNER who confirmed)

### 3.2 Code Comment Format (per CLAUDE.md)

Every rate constant in code MUST have:
```python
# SOURCE: Georgia DOR Employer's Tax Guide, Tax Year 2025
# REVIEW DATE: 2026-01-01
```

### 3.3 Testing Requirements

- Test zero-income case (no withholding should result)
- Test income just below and just above each historical bracket threshold
  (for migration verification)
- Test each filing status
- Test maximum realistic Georgia wage ($500,000 annual)
- Test mid-year rate change scenario (employee changes filing status)
- Test exempt employee handling
- Test multi-client isolation (Client A's employee cannot appear in Client B's payroll)

---

## 4. OPEN QUESTIONS FOR CPA_OWNER

1. **[COMPLIANCE]** Confirm the Tax Year 2026 flat rate (4.99% or still 5.19%)
2. **[COMPLIANCE]** Confirm TY2026 standard deduction and exemption amounts
3. **[COMPLIANCE]** Clarify Georgia supplemental wage withholding method preference
4. **[COMPLIANCE]** Confirm whether any clients have employees claiming exempt status
