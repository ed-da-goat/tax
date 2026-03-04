# Federal Payroll Tax Rates

## Research Agent: Georgia Tax Research Agent (Agent 04)
## Date Compiled: 2026-03-04
## Applicable Tax Years: 2025, 2026

---

## 1. SOCIAL SECURITY (OASDI)

### 1.1 Tax Year 2025

```
EMPLOYEE RATE: 6.2%
EMPLOYER RATE: 6.2%
COMBINED RATE: 12.4%
WAGE BASE: $176,100

SOURCE: IRS, Social Security Administration
URL: https://www.ssa.gov/oact/cola/cbb.html
VERIFIED: 2026-03-04 (from training knowledge)
REVIEW DATE: 2026-01-01
NOTES: The wage base is adjusted annually based on the national average
       wage index. Only the first $176,100 of wages per employee is
       subject to Social Security tax in 2025. Once the employee's
       year-to-date wages exceed this amount, Social Security tax
       withholding stops for the remainder of the calendar year.
```

### 1.2 Tax Year 2026

```
EMPLOYEE RATE: 6.2%
EMPLOYER RATE: 6.2%
COMBINED RATE: 12.4%
WAGE BASE: [UNVERIFIED -- SSA announces in Q4 of prior year]

# ⚠ UNVERIFIED — CPA_OWNER must confirm the 2026 Social Security wage base
# The SSA typically announces the new wage base in October/November.
# Check: https://www.ssa.gov/oact/cola/cbb.html
# Expected range: $178,000-$182,000 (based on historical increases)

SOURCE: Social Security Administration (projected)
VERIFIED: 2026-03-04 (PROJECTION ONLY)
REVIEW DATE: 2026-01-01
```

---

## 2. MEDICARE (HI)

### 2.1 Regular Medicare Tax

```
EMPLOYEE RATE: 1.45%
EMPLOYER RATE: 1.45%
COMBINED RATE: 2.9%
WAGE BASE: No limit (all wages are subject to Medicare tax)

SOURCE: IRS Publication 15 (Circular E), Tax Year 2025
URL: https://www.irs.gov/publications/p15
VERIFIED: 2026-03-04 (from training knowledge)
REVIEW DATE: 2026-01-01
NOTES: Unlike Social Security, there is no wage base cap for Medicare.
       All wages are subject to the 1.45% rate for both employee and employer.
```

### 2.2 Additional Medicare Tax (Employee Only)

```
RATE: 0.9% (employee only -- no employer match)
THRESHOLD: $200,000 in wages (all filing statuses for withholding purposes)
WAGE BASE: No limit above the threshold

SOURCE: IRS Publication 15 (Circular E); IRC Section 3101(b)(2)
URL: https://www.irs.gov/businesses/small-businesses-self-employed/questions-and-answers-for-the-additional-medicare-tax
VERIFIED: 2026-03-04 (from training knowledge)
REVIEW DATE: 2026-01-01
NOTES: The employer must begin withholding Additional Medicare Tax in the
       pay period when the employee's wages exceed $200,000 for the calendar
       year. The $200,000 threshold applies regardless of filing status
       for withholding purposes (the employee may reconcile on their
       individual return based on actual filing status thresholds:
       $250,000 MFJ, $125,000 MFS, $200,000 all others).

       The employer does NOT pay an additional employer share on these wages.
       Only the employee's 0.9% is withheld.
```

### 2.3 Combined Medicare Summary

| Wages | Employee Rate | Employer Rate |
|-------|--------------|---------------|
| $0 - $200,000 | 1.45% | 1.45% |
| Over $200,000 | 2.35% (1.45% + 0.9%) | 1.45% |

---

## 3. FICA COMBINED SUMMARY

| Tax | Employee Rate | Employer Rate | Wage Base |
|-----|--------------|---------------|-----------|
| Social Security | 6.2% | 6.2% | $176,100 (2025) |
| Medicare | 1.45% | 1.45% | No limit |
| Additional Medicare | 0.9% | -- | Over $200,000 |
| **Total (up to SS base)** | **7.65%** | **7.65%** | |
| **Total (over SS base, under $200K)** | **1.45%** | **1.45%** | |
| **Total (over $200K)** | **2.35%** | **1.45%** | |

---

## 4. FUTA (Federal Unemployment Tax Act)

### 4.1 Base Rate and Credit

```
GROSS RATE: 6.0%
NORMAL CREDIT: 5.4% (for employers who pay state unemployment tax on time)
NET EFFECTIVE RATE: 0.6% (6.0% - 5.4% credit)
WAGE BASE: $7,000 per employee per calendar year

SOURCE: IRS Publication 15 (Circular E); IRC Section 3301
URL: https://www.irs.gov/publications/p15
VERIFIED: 2026-03-04 (from training knowledge)
REVIEW DATE: 2026-01-01
NOTES: The $7,000 wage base has been unchanged since 1983. Only the
       employer pays FUTA; there is no employee portion. The 5.4%
       credit is available to employers who pay their state unemployment
       taxes in full and on time, reducing the effective rate to 0.6%.
```

### 4.2 Credit Reduction States

```
GEORGIA STATUS: Georgia is NOT a credit reduction state (as of 2025)

SOURCE: IRS, Department of Labor
URL: https://oui.doleta.gov/unemploy/futa_credit.asp
VERIFIED: 2026-03-04 (from training knowledge)
REVIEW DATE: 2026-11-01 (credit reduction is announced annually in November)
NOTES: A credit reduction applies to states that borrowed from the federal
       unemployment trust fund and have not repaid the loan within the
       required timeframe. Georgia repaid its federal UI loan and is NOT
       currently subject to a credit reduction. However, CPA_OWNER should
       verify this annually -- the DOL publishes the list of credit
       reduction states each November.

       If Georgia were ever designated a credit reduction state, the 5.4%
       credit would be reduced, increasing the effective FUTA rate above 0.6%.
```

**[UNVERIFIED] -- CPA_OWNER should confirm Georgia is not a credit reduction
state for Tax Year 2026. Check DOL announcement in November 2026.**

### 4.3 FUTA Deposit Schedule

| Quarterly Liability | Deposit Due |
|-------------------|-------------|
| Q1 (Jan-Mar) | April 30 |
| Q2 (Apr-Jun) | July 31 |
| Q3 (Jul-Sep) | October 31 |
| Q4 (Oct-Dec) | January 31 (following year) |

```
SOURCE: IRS Publication 15 (Circular E)
VERIFIED: 2026-03-04 (from training knowledge)
REVIEW DATE: 2026-01-01
NOTES: If accumulated FUTA liability is $500 or less for any quarter,
       no deposit is required -- carry forward to next quarter. If
       accumulated liability exceeds $500, deposit is due by the last
       day of the month following the quarter end.

       Annual FUTA return is filed on Form 940, due January 31 of the
       following year (or February 10 if all FUTA tax was deposited
       on time throughout the year).
```

---

## 5. FEDERAL INCOME TAX WITHHOLDING

### 5.1 Reference Publication

```
SOURCE: IRS Publication 15-T (Federal Income Tax Withholding Methods)
URL: https://www.irs.gov/publications/p15t
VERIFIED: 2026-03-04 (from training knowledge)
REVIEW DATE: 2026-01-01 (new Pub 15-T published annually)
NOTES: Federal income tax withholding is calculated using the tables and
       methods in IRS Publication 15-T. The system should implement the
       Percentage Method (the wage bracket method is an alternative but
       the percentage method is more suitable for automated systems).
```

### 5.2 2025 Federal Withholding -- Percentage Method (Post-2020 W-4)

The IRS Percentage Method for employees who submitted a 2020 or later W-4:

**Step 1:** Adjust wage amount
- Start with gross wages for the pay period
- Add any other taxable compensation
- Subtract pre-tax deductions (401(k), health insurance, etc.)

**Step 2:** Adjust for pay frequency (the adjusted annual wage)
- Multiply adjusted wages by number of pay periods

**Step 3:** Account for W-4 inputs
- Subtract Step 3 amount (credits for dependents) annualized equivalent
- Subtract Step 4(b) deductions
- Add Step 4(a) other income

**Step 4:** Apply tax brackets (2025 brackets -- MFJ rates shown)

| Taxable Over | But Not Over | Rate |
|-------------|-------------|------|
| $0 | $24,300 | 10% |
| $24,300 | $102,500 | 12% |
| $102,500 | $212,500 | 22% |
| $212,500 | $393,600 | 24% |
| $393,600 | $504,050 | 32% |
| $504,050 | $753,600 | 35% |
| $753,600 | -- | 37% |

**Single/MFS brackets (2025):**

| Taxable Over | But Not Over | Rate |
|-------------|-------------|------|
| $0 | $12,150 | 10% |
| $12,150 | $51,250 | 12% |
| $51,250 | $106,250 | 22% |
| $106,250 | $196,800 | 24% |
| $196,800 | $252,025 | 32% |
| $252,025 | $376,800 | 35% |
| $376,800 | -- | 37% |

**Head of Household brackets (2025):**

| Taxable Over | But Not Over | Rate |
|-------------|-------------|------|
| $0 | $18,200 | 10% |
| $18,200 | $76,850 | 12% |
| $76,850 | $159,350 | 22% |
| $159,350 | $295,200 | 24% |
| $295,200 | $378,025 | 32% |
| $378,025 | $565,200 | 35% |
| $565,200 | -- | 37% |

```
SOURCE: IRS Publication 15-T, Tax Year 2025
URL: https://www.irs.gov/publications/p15t
VERIFIED: 2026-03-04 (from training knowledge)
REVIEW DATE: 2026-01-01
NOTES: These brackets are inflation-adjusted annually by the IRS.
       The Tax Cuts and Jobs Act (TCJA) brackets were set to expire
       after 2025. CPA_OWNER MUST verify whether Congress extended
       or modified these rates for Tax Year 2026.
```

**[UNVERIFIED] -- Tax Year 2026 federal brackets depend on whether
the TCJA provisions were extended. CPA_OWNER MUST verify the 2026
Publication 15-T before processing 2026 payroll.**

### 5.3 Supplemental Wage Rate (Federal)

```
RATE: 22% (for supplemental wages up to $1,000,000)
RATE: 37% (for supplemental wages over $1,000,000)

SOURCE: IRS Publication 15 (Circular E), Tax Year 2025
URL: https://www.irs.gov/publications/p15
VERIFIED: 2026-03-04 (from training knowledge)
REVIEW DATE: 2026-01-01
NOTES: The 22% flat rate applies when supplemental wages are paid
       separately from regular wages (or identified separately) and
       federal income tax has been withheld from regular wages in the
       current or prior year. The employer may alternatively use the
       aggregate method. The 37% rate is the top marginal rate for
       supplemental wages exceeding $1 million YTD.
```

### 5.4 Pre-2020 W-4 Method

For employees who have NOT submitted a 2020+ W-4, the employer uses
the legacy withholding method based on the number of allowances claimed.
Publication 15-T includes separate tables for these employees.

```
SOURCE: IRS Publication 15-T, Tax Year 2025
VERIFIED: 2026-03-04 (from training knowledge)
NOTES: Builder agents should implement both the post-2020 W-4 method
       and the pre-2020 W-4 method, as migrated employees from QB may
       still be on the old W-4. The employee_payroll_settings table
       should include a w4_version field (PRE_2020 or POST_2020).
```

---

## 6. SELF-EMPLOYMENT TAX (for Sole Proprietors and Partners)

```
RATE: 15.3% (12.4% Social Security + 2.9% Medicare)
       on 92.35% of net self-employment income

SOCIAL SECURITY PORTION: 12.4% on first $176,100 of net SE income (2025)
MEDICARE PORTION: 2.9% on all net SE income (no cap)
ADDITIONAL MEDICARE: 0.9% on SE income exceeding $200,000 (S), $250,000 (MFJ)

SOURCE: IRS Schedule SE, IRC Section 1401
URL: https://www.irs.gov/forms-pubs/about-schedule-se-form-1040
VERIFIED: 2026-03-04 (from training knowledge)
REVIEW DATE: 2026-01-01
NOTES: This applies to sole proprietors (Schedule C filers) and partners.
       S-Corp shareholders pay themselves a reasonable salary subject to
       payroll taxes, and take remaining income as distributions not subject
       to SE tax.
```

---

## 7. IMPLEMENTATION NOTES FOR BUILDER AGENTS

### 7.1 Database Design

The `payroll_tax_tables` table should store federal rates parameterized by:
- `tax_year`
- `jurisdiction` (FEDERAL)
- `tax_type` (SOCIAL_SECURITY, MEDICARE, ADDITIONAL_MEDICARE, FUTA, FIT)
- `rate` (decimal)
- `wage_base` (decimal, nullable -- null means no cap)
- `threshold` (decimal, nullable -- for Additional Medicare)
- `filing_status` (nullable -- for FIT brackets)
- `bracket_floor` (decimal -- for FIT brackets)
- `bracket_ceiling` (decimal, nullable -- for FIT brackets)
- `source_citation` (text)
- `effective_date` (date)

### 7.2 Critical TCJA Expiration Note

**The Tax Cuts and Jobs Act provisions were scheduled to expire after Tax Year 2025.**
This means Tax Year 2026 federal income tax brackets, standard deductions, and
other provisions may change significantly. The system MUST NOT hardcode 2025
rates for 2026 use. CPA_OWNER must provide confirmed 2026 rates.

```
# ⚠ UNVERIFIED — Tax Year 2026 federal income tax brackets are UNKNOWN
# at this time. TCJA may have been extended, modified, or allowed to expire.
# CPA_OWNER MUST verify and update payroll_tax_tables for 2026 before
# processing any 2026 payroll.
```

### 7.3 Testing Requirements

- Test Social Security wage base cutoff (YTD at boundary)
- Test Additional Medicare threshold ($200,000)
- Test FUTA $7,000 wage base cutoff
- Test all filing statuses for FIT withholding
- Test supplemental wage flat rate method
- Test zero wages
- Test maximum realistic wages ($1,000,000+)
- Test post-2020 W-4 and pre-2020 W-4 methods

---

## 8. OPEN QUESTIONS FOR CPA_OWNER

1. **[COMPLIANCE]** Confirm 2026 Social Security wage base (SSA announcement)
2. **[COMPLIANCE]** Confirm whether TCJA was extended for 2026 (critical for FIT brackets)
3. **[COMPLIANCE]** Confirm Georgia credit reduction status for FUTA 2026
4. **[COMPLIANCE]** Identify any clients with employees on pre-2020 W-4s
5. **[COMPLIANCE]** Confirm supplemental wage rate for 2026 (22% if TCJA extended, may revert to 25% if not)
