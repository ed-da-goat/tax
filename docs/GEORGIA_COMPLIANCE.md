# Georgia Compliance Guide

This document lists every module that touches Georgia-specific tax rules and what the CPA must manually verify before each tax filing season.

## Modules with Georgia-Specific Rules

### P2 — Georgia Income Tax Withholding
- **Source:** Georgia Form G-4 instructions + DOR withholding tables
- **What changes annually:** Tax brackets, standard deduction amounts, personal allowance values
- **CPA must verify:** Download current year's withholding tables from Georgia DOR and update `payroll_tax_tables` in the database
- **Risk if outdated:** Incorrect withholding on employee paychecks

### P3 — Georgia SUTA (State Unemployment Tax)
- **Source:** Georgia Department of Labor
- **Default rate:** 2.7% on first $9,500 of wages (new employer)
- **What changes annually:** Wage base may change; experienced employer rates vary
- **CPA must verify:** Each client's assigned SUTA rate letter from GA DOL; update per-client rate in system
- **Risk if outdated:** Under/over-payment of unemployment tax

### X1 — Georgia Form G-7 (Quarterly Withholding Return)
- **Due dates:** April 30, July 31, October 31, January 31
- **CPA must verify:** Form layout matches current DOR version; withholding totals tie to payroll records
- **Source:** Georgia DOR Form G-7 instructions

### X2 — Georgia Form 500 (Individual Income Tax)
- **Applies to:** Sole proprietor clients (Schedule C income flows here)
- **CPA must verify:** Current year tax rates, standard deduction, personal exemptions
- **Source:** Georgia DOR Form 500 instructions

### X3 — Georgia Form 600 (Corporate Income Tax)
- **Applies to:** C-Corp clients
- **Rate:** 5.75% flat (as of 2024 — verify annually)
- **CPA must verify:** Current corporate tax rate, apportionment rules if multi-state
- **Source:** Georgia DOR Form 600 instructions

### X4 — Georgia Form ST-3 (Sales Tax Return)
- **Applies to:** Clients who collect sales tax
- **CPA must verify:** Current state + local sales tax rates per jurisdiction; filing frequency (monthly/quarterly/annual)
- **Source:** Georgia DOR Sales & Use Tax page

## Annual Pre-Filing Checklist

Before each tax filing season, the CPA_OWNER must complete these steps:

- [ ] Download latest Georgia DOR withholding tables → update `payroll_tax_tables`
- [ ] Confirm each client's SUTA rate from GA DOL rate notice
- [ ] Verify Georgia corporate tax rate has not changed
- [ ] Verify Georgia sales tax rates for each applicable jurisdiction
- [ ] Verify Form G-7 layout matches current DOR version
- [ ] Verify Form 500 instructions for any changes to deductions/exemptions
- [ ] Verify Form 600 instructions for any changes to corporate rate
- [ ] Verify Form ST-3 layout and jurisdiction codes
- [ ] Verify federal withholding tables (IRS Publication 15-T)
- [ ] Verify FICA rates and wage bases (Social Security wage base changes annually)
- [ ] Verify FUTA rate and credit reduction states

## Code Convention for Tax Rates

Every hardcoded tax rate in the codebase MUST have this comment format directly above it:

```python
# SOURCE: Georgia DOR [document name], Tax Year [YYYY], Page [n]
# REVIEW DATE: [date this was last verified]
```

If a rate cannot be cited, it must be flagged:
```python
# COMPLIANCE REVIEW NEEDED: [describe what needs verification]
```

## Where Tax Data Lives

| Data | Location | Update Method |
|------|----------|---------------|
| GA withholding brackets | `payroll_tax_tables` DB table | SQL UPDATE by tax_year |
| SUTA rates | Per-client field in `clients` or `payroll_config` | Edit per client |
| Federal withholding | `payroll_tax_tables` DB table | SQL UPDATE by tax_year |
| FICA rates | `payroll_tax_tables` DB table | SQL UPDATE by tax_year |
| Sales tax rates | Per-client configuration | Edit per client |
| Form templates | `/backend/app/services/tax_forms/` | Code update + test |
