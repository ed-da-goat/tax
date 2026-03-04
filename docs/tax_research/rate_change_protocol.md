# Rate Change Monitoring Protocol

## Research Agent: Georgia Tax Research Agent (Agent 04)
## Date Compiled: 2026-03-04

---

## 1. PURPOSE

This document defines the protocol for monitoring, identifying, and
implementing tax rate changes in the Georgia CPA firm accounting system.
Tax rates change on predictable schedules. This protocol ensures the
CPA firm is never caught using stale rates for payroll processing or
tax form generation.

---

## 2. RATE CHANGE CALENDAR

### 2.1 When Changes Typically Occur

| Rate Type | Announcing Authority | Typical Announcement | Effective Date |
|-----------|---------------------|---------------------|----------------|
| Georgia income tax (flat rate) | Georgia General Assembly / DOR | Q1-Q2 (legislative session) | January 1 |
| Georgia standard deduction | Georgia DOR (Employer's Tax Guide) | November-December | January 1 |
| Georgia personal exemptions | Georgia DOR (Employer's Tax Guide) | November-December | January 1 |
| Georgia SUTA wage base | Georgia DOL | Q4 (October-November) | January 1 |
| Georgia SUTA rates (experienced) | Georgia DOL (Form DOL-626) | Q4 (November-December) | January 1 |
| Georgia sales tax (state) | Georgia General Assembly | During legislative session | Varies |
| Georgia sales tax (local) | County/city governments | Varies | January 1, April 1, July 1, or October 1 |
| Federal SS wage base | SSA | October-November | January 1 |
| Federal income tax brackets | IRS (Rev. Proc.) | October-November | January 1 |
| FUTA rate / credit reduction | DOL / IRS | November | January 1 |
| Medicare rates | Congress (rare changes) | Varies | January 1 |

### 2.2 Georgia Legislative Session

The Georgia General Assembly typically convenes on the **second Monday
of January** and adjourns by **Sine Die** (usually late March or early
April, Day 40 of the session). Tax legislation enacted during the
session typically takes effect:
- January 1 of the following year (most common), OR
- July 1 of the current year (mid-year effective), OR
- Upon signature by the Governor (immediate)

```
SOURCE: Georgia General Assembly calendar
URL: https://www.legis.ga.gov/
VERIFIED: 2026-03-04 (from training knowledge)
REVIEW DATE: 2026-01-01
```

---

## 3. RATES MOST LIKELY TO CHANGE

### 3.1 High Frequency (Check Quarterly)

| Rate | Reason for Frequent Change |
|------|---------------------------|
| Local sales tax rates | Counties adopt/sunset SPLOST, LOST, HOST regularly |
| Georgia flat income tax rate | HB 1015 transition schedule reduces rate annually |

### 3.2 Medium Frequency (Check Annually)

| Rate | Reason |
|------|--------|
| Georgia standard deduction | May be adjusted with rate reform |
| Georgia personal exemptions | May be adjusted with rate reform |
| Federal SS wage base | Inflation-indexed annually by SSA |
| Federal income tax brackets | Inflation-indexed annually by IRS |
| Georgia SUTA wage base | Legislature may increase (rare but possible) |
| FUTA credit reduction | Depends on state trust fund solvency |

### 3.3 Low Frequency (Check Every 2-5 Years)

| Rate | Reason |
|------|--------|
| Social Security rate (6.2%) | Requires act of Congress |
| Medicare rate (1.45%) | Requires act of Congress |
| Additional Medicare (0.9%) | Set by ACA, requires legislative change |
| FUTA gross rate (6.0%) | Unchanged since inception, requires Congress |
| Georgia state sales tax (4.0%) | Requires legislative action |
| Georgia corporate rate (5.75%) | Requires legislative action |

---

## 4. SYSTEM UPDATE PROCEDURE

### 4.1 When a Rate Change is Identified

```
STEP 1: VERIFY THE CHANGE
  - Confirm from the official source (DOR, DOL, IRS, SSA)
  - Document: old rate, new rate, effective date, source URL
  - Save a copy of the official announcement in
    /data/documents/system/rate_changes/

STEP 2: UPDATE THE DATABASE
  - DO NOT overwrite the old rate. Insert a new row in payroll_tax_tables
    with the new effective_date.
  - The system uses effective_date to select the correct rate for each
    pay period (historical payroll uses historical rates).

STEP 3: VERIFY THE UPDATE
  - Run the payroll calculation test suite with the new rate
  - Manually verify 2-3 sample calculations match expected results
  - CPA_OWNER must approve the rate change before production use

STEP 4: DOCUMENT THE CHANGE
  - Update the relevant file in /docs/tax_research/ with new rate
  - Add source citation and VERIFIED date
  - Log the change in AGENT_LOG.md

STEP 5: NOTIFY
  - Create an entry in the system dashboard notification area
  - Flag any upcoming payroll runs that will use the new rate
```

### 4.2 Mid-Year Rate Changes

Mid-year rate changes are the most dangerous. The system must:

1. **Not retroactively recalculate** prior pay periods unless explicitly
   instructed by CPA_OWNER
2. **Apply new rate only to pay periods on or after the effective date**
3. **Log the transition** in the audit trail
4. **Flag affected clients** for CPA review

```
IMPLEMENTATION NOTE: The payroll_tax_tables table uses effective_date
to determine which rate applies to each pay period. The system should
use the rate whose effective_date is the most recent date that is
on or before the pay period end date.

Example query:
  SELECT rate FROM payroll_tax_tables
  WHERE tax_type = 'GA_FLAT_RATE'
    AND effective_date <= pay_period_end_date
  ORDER BY effective_date DESC
  LIMIT 1;
```

---

## 5. ANNUAL REVIEW CHECKLIST FOR CPA_OWNER

This checklist should be completed each year, ideally in **December**
before processing any payroll for the new tax year.

### 5.1 November Checklist (Pre-Season)

- [ ] Check SSA for new Social Security wage base announcement
- [ ] Check IRS Rev. Proc. for new federal income tax brackets
- [ ] Check DOL for FUTA credit reduction state list
- [ ] Review Georgia DOL communications for SUTA changes
- [ ] Collect Form DOL-626 (SUTA rate notices) from all clients

### 5.2 December Checklist

- [ ] Download new Georgia DOR Employer's Tax Guide
- [ ] Verify Georgia flat income tax rate for new year
- [ ] Verify Georgia standard deduction amounts
- [ ] Verify Georgia personal exemption amounts
- [ ] Download new IRS Publication 15-T
- [ ] Download new IRS Publication 15 (Circular E)
- [ ] Update payroll_tax_tables in database with all new rates
- [ ] Run test payroll for each client using new rates
- [ ] Verify test results match manual calculations

### 5.3 January Checklist

- [ ] Confirm all new rates are active in the system
- [ ] Process first payroll of the new year
- [ ] Verify first payroll withholdings are correct
- [ ] Check for any local sales tax rate changes (quarterly)

### 5.4 Quarterly Checklist

- [ ] Check Georgia DOR local sales tax rate chart
  URL: https://dor.georgia.gov/local-government-services/tax-rates
- [ ] Update sales_tax_rates table if any client jurisdictions changed
- [ ] File all quarterly returns (G-7, DOL-4N, ST-3) by due dates
- [ ] Reconcile quarterly filings against system records

### 5.5 Legislative Session Monitor (January-April)

- [ ] Monitor Georgia General Assembly for tax legislation
  URL: https://www.legis.ga.gov/
- [ ] Check for income tax rate changes (HB 1015 transition)
- [ ] Check for corporate tax rate changes
- [ ] Check for sales tax exemption changes
- [ ] Check for SUTA wage base changes
- [ ] Review any signed bills for effective dates

---

## 6. AUTOMATED MONITORING (FUTURE ENHANCEMENT)

When the system matures, consider implementing:

1. **Rate expiration warnings:** The system flags any rate in
   payroll_tax_tables where the tax_year is about to expire
   (e.g., November 1 warning for upcoming January 1 rates)

2. **Dashboard alerts:** The firm-level dashboard (Module R5)
   displays upcoming rate review deadlines

3. **Filing deadline reminders:** The system generates calendar
   entries for all quarterly and annual filing deadlines

4. **Data validation:** Before processing any payroll, verify that
   the rates in payroll_tax_tables have been reviewed for the
   current tax year (check verified_date is within the current year)

---

## 7. EMERGENCY RATE CHANGE PROCEDURE

If a rate change is discovered AFTER payroll has been processed
with the wrong rate:

```
STEP 1: STOP processing any additional payroll for affected clients
STEP 2: Calculate the difference between old rate and correct rate
STEP 3: Determine if the difference is material (CPA judgment)
STEP 4: Options:
  (a) Issue corrected pay stubs and adjust next pay period
  (b) File amended quarterly returns
  (c) If immaterial, document and adjust at year-end
STEP 5: Log the error and correction in audit trail
STEP 6: Update payroll_tax_tables with correct rate
STEP 7: CPA_OWNER signs off on correction approach
```

---

## 8. SOURCE URLS FOR MONITORING

| Source | URL | Check Frequency |
|--------|-----|-----------------|
| Georgia DOR main | https://dor.georgia.gov/ | Monthly |
| Georgia DOR withholding | https://dor.georgia.gov/withholding-tax | Annually (Dec) |
| Georgia DOR sales tax rates | https://dor.georgia.gov/local-government-services/tax-rates | Quarterly |
| Georgia Tax Center (GTC) | https://gtc.dor.ga.gov/ | Monthly |
| Georgia DOL employer | https://dol.georgia.gov/employer-resources | Annually (Nov) |
| Georgia General Assembly | https://www.legis.ga.gov/ | Jan-Apr (session) |
| IRS Pub 15 | https://www.irs.gov/publications/p15 | Annually (Dec) |
| IRS Pub 15-T | https://www.irs.gov/publications/p15t | Annually (Dec) |
| SSA wage base | https://www.ssa.gov/oact/cola/cbb.html | Annually (Oct) |
| DOL FUTA credit reduction | https://oui.doleta.gov/unemploy/futa_credit.asp | Annually (Nov) |
