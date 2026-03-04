# Architecture — Module Dependency Map

## System Overview

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend   │────▶│   Backend   │────▶│  PostgreSQL  │
│  React+Vite  │     │   FastAPI   │     │   Database   │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                    ┌──────┴──────┐
                    │  WeasyPrint │
                    │ (PDF export)│
                    └─────────────┘
```

## Module Dependency Table

| Module | Name | Depends On | Phase |
|--------|------|-----------|-------|
| **Phase 0 — Migration** | | | |
| M1 | QB CSV parser & validator | — | 0 |
| M2 | Client splitter | M1 | 0 |
| M3 | Chart of accounts mapper | M1, F2 | 0 |
| M4 | Transaction history importer | M2, M3, F3 | 0 |
| M5 | Invoice & AR history importer | M2, M3, T2 | 0 |
| M6 | Payroll history importer | M2, P1 | 0 |
| M7 | Migration audit report | M1–M6 | 0 |
| **Phase 1 — Foundation** | | | |
| F1 | Database schema + migrations | — | 1 |
| F2 | Chart of accounts (GA standard) | F1 | 1 |
| F3 | General ledger (double-entry) | F1, F2 | 1 |
| F4 | Client management | F1 | 1 |
| F5 | User auth (JWT + roles) | F1 | 1 |
| **Phase 2 — Transactions** | | | |
| T1 | Accounts Payable | F3, F4 | 2 |
| T2 | Accounts Receivable + invoicing | F3, F4 | 2 |
| T3 | Bank reconciliation | F3, T1, T2 | 2 |
| T4 | Transaction approval workflow | F3, F5 | 2 |
| **Phase 3 — Documents** | | | |
| D1 | Document upload | F4, F5 | 3 |
| D2 | Document viewer | D1 | 3 |
| D3 | Document search | D1 | 3 |
| **Phase 4 — Payroll** | | | |
| P1 | Employee records | F4 | 4 |
| P2 | GA income tax withholding | P1 | 4 |
| P3 | GA SUTA calculator | P1 | 4 |
| P4 | Federal withholding + FICA + FUTA | P1 | 4 |
| P5 | Pay stub generator (PDF) | P1, P2, P3, P4 | 4 |
| P6 | Payroll approval gate | P5, F5 | 4 |
| **Phase 5 — Tax Forms** | | | |
| X1 | GA Form G-7 | P6, F3 | 5 |
| X2 | GA Form 500 | F3, R1 | 5 |
| X3 | GA Form 600 | F3, R1 | 5 |
| X4 | GA Form ST-3 | F3, T2 | 5 |
| X5 | Federal Schedule C | F3, R1 | 5 |
| X6 | Federal Form 1120-S | F3, R1 | 5 |
| X7 | Federal Form 1120 | F3, R1 | 5 |
| X8 | Federal Form 1065 | F3, R1 | 5 |
| X9 | Tax document checklist | X1–X8 | 5 |
| **Phase 6 — Reporting** | | | |
| R1 | Profit & Loss | F3 | 6 |
| R2 | Balance Sheet | F3 | 6 |
| R3 | Cash Flow Statement | F3 | 6 |
| R4 | PDF export for reports | R1, R2, R3 | 6 |
| R5 | Firm-level dashboard | R1, R2, F4 | 6 |
| **Phase 7 — Operations** | | | |
| O1 | Audit trail viewer | F1 | 7 |
| O2 | Automated local backup | F1 | 7 |
| O3 | Backup restore tool | O2 | 7 |
| O4 | System health check | F1, O2 | 7 |

## Build Order (Critical Path)

```
F1 → F2 → F3 → F4 → F5 → T1/T2/T4 → T3 → P1 → P2/P3/P4 → P5 → P6
                                              ↓
                                         R1/R2/R3 → R4/R5
                                              ↓
                                    X1–X8 → X9 → D1 → D2/D3
                                              ↓
                                         O1/O2 → O3/O4
```

Migration modules (M1–M7) can be built in parallel with Phase 1 foundation, but cannot be **run** until F1–F3 are deployed.
