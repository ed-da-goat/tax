TAX RATE UPDATE — COMPLETION REPORT
====================================
Date: 2026-03-06
Agent: Tax Rate Update Agent

RATES UPDATED:
  [x] Federal income tax brackets (7 brackets, Single + MFJ) — Rev. Proc. 2025-32 + OBBBA
  [x] Federal standard deduction ($16,100 / $32,200 / $24,150) — Rev. Proc. 2025-32
  [x] Social Security wage base ($184,500) — SSA Fact Sheet 2026
  [x] Medicare rates (unchanged, citation updated to TY2026)
  [x] FUTA rate and wage base (unchanged, citation updated to TY2026)
  [x] Georgia income tax rate (5.09% per HB 111 signed law)
  [x] Georgia standard deduction ($12,000 / $24,000 per HB 1437)
  [x] Georgia dependent exemption ($4,000 per GA Code §48-7-26)
  [x] Georgia SUTA wage base ($9,500 unchanged, citation updated)
  [x] W-2 wage base reference (was hardcoded $168,600 — now imports from federal_tax.py)
  [x] Seed data tax tables (added TY2026 entries for all rate types)
  [x] Seed data SS wage base ($168,600 -> $184,500)

FILES MODIFIED:
  backend/app/services/payroll/federal_tax.py      — TY2026 brackets, SS wage base, deductions, citations
  backend/app/services/payroll/ga_withholding.py   — GA flat rate 5.09%, standard deductions $12K/$24K
  backend/app/services/payroll/ga_suta.py          — Citation updates, removed COMPLIANCE REVIEW flags
  backend/app/services/payroll/w2_generator.py     — Import SS_WAGE_BASES from federal_tax.py (was hardcoded)
  backend/scripts/seed_test_data.py                — SS wage base $184,500, added TY2026 tax table entries
  backend/tests/test_ga_withholding.py             — Updated TY2026 test expected values
  backend/tests/test_w2_generator.py               — Updated import (SS_WAGE_BASES instead of removed constant)
  OPEN_ISSUES.md                                   — Updated #1-#5, #10, #11

COMPLIANCE FLAGS RESOLVED: 5 of 11
  #2  GA standard deductions:     RESOLVED ($12K/$24K per HB 1437)
  #3  Federal TY2026 brackets:    RESOLVED (Rev. Proc. 2025-32 + OBBBA)
  #4  SS wage base TY2026:        RESOLVED ($184,500 per SSA)
  #5  SUTA wage base TY2026:      RESOLVED ($9,500 unchanged)
  #11 Unverified rates:           MOSTLY RESOLVED

COMPLIANCE FLAGS UPDATED (still require monitoring):
  #1  GA income tax rate:          SET to 5.09% (signed law HB 111), pending HB 1001
  #10 GA corporate tax rate:       Uses same flat rate — no code change needed

COMPLIANCE FLAGS UNCHANGED (require CPA_OWNER action):
  #6  Client-specific SUTA rates:  Requires per-client DOL-626 collection
  #7  GA supplemental wage method: Requires CPA_OWNER decision
  #8  Local sales tax rates:       Requires per-jurisdiction rate table
  #9  FUTA credit reduction:       Verify after Nov 10, 2026

TESTS: 900 passed / 2 updated (test_ga_withholding.py, test_w2_generator.py)

CPA_OWNER ACTION STILL REQUIRED:
  1. Monitor GA General Assembly for HB 1001 / SB 476/477 final passage
  2. When GA rate is finalized, update GA_FLAT_RATE_2026 in ga_withholding.py
  3. Collect experienced SUTA rates from each client's GA DOL notice (Form DOL-626)
  4. After Nov 10, 2026, check IRS for FUTA credit reduction states
  5. When GA adopts OBBBA conformity, verify standard deduction alignment
  6. Re-seed database: cd backend && PYTHONPATH=. .venv/bin/python scripts/seed_test_data.py --reset
