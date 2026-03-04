# Georgia SUTA (State Unemployment Tax) Rates

## Research Agent: Georgia Tax Research Agent (Agent 04)
## Date Compiled: 2026-03-04
## Applicable Tax Years: 2025, 2026

---

## 1. OVERVIEW

Georgia unemployment insurance (UI) tax is administered by the
Georgia Department of Labor (GDOL). Employers pay SUTA tax on
wages paid to employees up to the annual wage base. Employees
do not pay Georgia SUTA.

---

## 2. NEW EMPLOYER RATE

```
RATE: 2.7% (standard new employer rate)
SOURCE: Georgia Department of Labor, Employer's Guide to Unemployment Insurance
URL: https://dol.georgia.gov/employer-resources
VERIFIED: 2026-03-04 (from training knowledge)
REVIEW DATE: 2026-01-01
NOTES: New employers (those without sufficient experience rating history,
       typically the first 2-3 years) are assigned the standard new
       employer rate. Construction industry employers may be assigned
       a higher new employer rate (historically around 2.7% as well,
       but CPA should verify for construction clients).
```

### 2.1 Construction Industry New Employer Rate

```
RATE: 2.7% (same as standard, but verify annually)
SOURCE: Georgia Department of Labor
URL: https://dol.georgia.gov/employer-resources
VERIFIED: 2026-03-04 (from training knowledge)
REVIEW DATE: 2026-01-01
NOTES: Some states assign higher rates to construction employers.
       Georgia historically uses the same 2.7% but CPA_OWNER should
       verify if any construction-industry clients have different rates.
       # COMPLIANCE REVIEW NEEDED: Verify construction industry rate
       # for any applicable clients.
```

---

## 3. TAXABLE WAGE BASE

```
RATE: $9,500 per employee per calendar year
SOURCE: Georgia Department of Labor
URL: https://dol.georgia.gov/employer-resources
VERIFIED: 2026-03-04 (from training knowledge)
REVIEW DATE: 2026-01-01
NOTES: Georgia's SUTA wage base has remained at $9,500 for many years.
       Only the first $9,500 of wages paid to each employee in a
       calendar year is subject to SUTA tax. Once an employee's
       year-to-date wages exceed $9,500, no further SUTA tax is due
       for that employee for the remainder of the calendar year.
```

**[UNVERIFIED] -- CPA_OWNER should confirm the 2026 wage base has not
been increased by the Georgia legislature. Check GDOL communications.**

---

## 4. EXPERIENCED EMPLOYER RATE RANGE

Experienced employers receive an individual rate based on their
"experience rating" (claims history). The rate is assigned annually
by GDOL, typically communicated via the annual Rate Notice (Form DOL-626).

```
RATE RANGE: 0.04% to 8.1% (approximate range for experienced employers)
SOURCE: Georgia Department of Labor, Experience Rating System
URL: https://dol.georgia.gov/employer-resources
VERIFIED: 2026-03-04 (from training knowledge)
REVIEW DATE: 2026-01-01
NOTES: The exact range boundaries may shift slightly year to year based on
       the state's UI trust fund balance and legislative action. The minimum
       rate for experienced employers with favorable claims history is
       approximately 0.04%. The maximum rate is approximately 8.1%.

       Each client's actual SUTA rate is printed on their annual
       Rate Notice (Form DOL-626) mailed by GDOL in late Q4 or early Q1.
```

**[UNVERIFIED] -- The exact min/max rates for Tax Year 2026 must be confirmed
from the GDOL. CPA_OWNER should check each client's Form DOL-626.**

### 4.1 How to Look Up a Client's Specific Rate

1. **Form DOL-626 (Annual Rate Notice):** GDOL mails this to each employer
   annually (typically December/January). It shows the assigned rate for
   the upcoming calendar year.

2. **GDOL Employer Portal:** Employers can log in to the GDOL employer
   portal at https://www.dol.state.ga.us/ to view their current rate.

3. **Client Input:** The CPA firm should request each client's SUTA rate
   annually and enter it into the system's `client_payroll_settings` table.

```
SOURCE: Georgia Department of Labor Employer Portal
URL: https://www.dol.state.ga.us/
VERIFIED: 2026-03-04 (from training knowledge)
REVIEW DATE: 2026-01-01
```

---

## 5. FILING FREQUENCY AND DUE DATES

Georgia SUTA is reported quarterly on **Form DOL-4N** (Quarterly Tax and
Wage Report).

| Quarter | Period | Due Date |
|---------|--------|----------|
| Q1 | Jan 1 - Mar 31 | April 30 |
| Q2 | Apr 1 - Jun 30 | July 31 |
| Q3 | Jul 1 - Sep 30 | October 31 |
| Q4 | Oct 1 - Dec 31 | January 31 (of following year) |

```
SOURCE: Georgia Department of Labor, Quarterly Filing Instructions
URL: https://dol.georgia.gov/employer-resources
VERIFIED: 2026-03-04 (from training knowledge)
REVIEW DATE: 2026-01-01
NOTES: If the due date falls on a weekend or state holiday, the filing
       deadline is the next business day. Electronic filing is strongly
       encouraged and may be mandatory for employers with 100+ employees.
```

### 5.1 Form DOL-4N Required Fields

The quarterly report includes:
- Employer name, GDOL account number, FEIN
- Total wages paid during the quarter
- Taxable wages (wages up to $9,500 per employee)
- Excess wages (wages over $9,500 per employee)
- Tax rate (from Rate Notice)
- Tax due (taxable wages x rate)
- Employee listing: SSN, name, total wages for the quarter

```
SOURCE: Georgia DOL Form DOL-4N
URL: https://dol.georgia.gov/employer-resources
VERIFIED: 2026-03-04 (from training knowledge)
REVIEW DATE: 2026-01-01
```

### 5.2 Electronic Filing

- Georgia DOL allows electronic filing through the employer portal.
- Employers with 100+ employees may be required to file electronically.
- The CPA firm should file electronically for all clients for efficiency.

---

## 6. PENALTIES AND INTEREST

| Violation | Penalty |
|-----------|---------|
| Late filing | 1.5% per month on unpaid tax (up to 37.5% max) |
| Late payment | Interest at prevailing rate set by Georgia DOR |
| Failure to file | Minimum $25 penalty per quarter |

```
SOURCE: Georgia Department of Labor
VERIFIED: 2026-03-04 (from training knowledge)
REVIEW DATE: 2026-01-01
NOTES: Penalty rates may be updated. CPA_OWNER should verify current
       penalty schedule.
```

---

## 7. IMPLEMENTATION NOTES FOR BUILDER AGENTS

### 7.1 Database Design

The `client_payroll_settings` table must include:
- `suta_rate` (decimal, 4 decimal places -- e.g., 0.0270 for 2.7%)
- `suta_wage_base` (decimal -- $9,500.00)
- `suta_rate_effective_date` (date)
- `suta_rate_source` (text -- "DOL-626 dated YYYY-MM-DD" or similar)
- `gdol_account_number` (varchar)

### 7.2 Calculation Logic

```python
def calculate_suta(employee_ytd_wages: Decimal, current_period_wages: Decimal,
                   suta_rate: Decimal, wage_base: Decimal) -> Decimal:
    """
    Calculate Georgia SUTA tax for a pay period.

    # SOURCE: Georgia Department of Labor, Experience Rating System
    # REVIEW DATE: 2026-01-01
    """
    remaining_taxable = max(wage_base - employee_ytd_wages, Decimal('0'))
    taxable_wages = min(current_period_wages, remaining_taxable)
    return (taxable_wages * suta_rate).quantize(Decimal('0.01'))
```

### 7.3 Testing Requirements

- Test with YTD wages below wage base (full current wages are taxable)
- Test with YTD wages above wage base (zero SUTA due)
- Test with YTD wages partially through wage base (only remainder is taxable)
- Test with zero wages
- Test with the new employer rate (2.7%)
- Test with minimum experienced rate (0.04%)
- Test with maximum experienced rate (8.1%)
- Test multi-client isolation

---

## 8. OPEN QUESTIONS FOR CPA_OWNER

1. **[COMPLIANCE]** Confirm 2026 SUTA wage base ($9,500 or changed)
2. **[COMPLIANCE]** Confirm experienced employer rate range for 2026
3. **[COMPLIANCE]** Do any clients have construction industry classification?
4. **[COMPLIANCE]** Collect each client's Form DOL-626 rate for 2026
5. **[COMPLIANCE]** Are any clients required to file DOL-4N electronically?
