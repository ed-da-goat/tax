# Georgia CPA Firm — Accounting System

A full-featured accounting system built to replace QuickBooks Online for a Georgia CPA firm with 26-50 clients. Runs entirely local — no cloud subscriptions, no third-party dependencies at runtime.

## Status: Backend Feature-Complete

All 34 backend modules across 7 phases are built and tested. **585 tests passing.**

| Phase | Modules | Status |
|-------|---------|--------|
| 0 - Migration | M1-M7: QBO CSV parser, client splitter, CoA mapper, transaction/invoice/payroll importers, audit report | Complete |
| 1 - Foundation | F1-F5: Database schema, chart of accounts, general ledger, client management, JWT auth | Complete |
| 2 - Transactions | T1-T4: Accounts payable, accounts receivable, bank reconciliation, approval workflow | Complete |
| 3 - Documents | D1-D3: Upload, viewer, search | Complete |
| 4 - Payroll | P1-P6: Employee records, GA withholding (G-4), GA SUTA, federal tax/FICA/FUTA, pay stubs, approval gate | Complete |
| 5 - Tax Exports | X1-X9: GA G-7, Form 500/600, ST-3, Schedule C, 1120-S, 1120, 1065, checklist generator | Complete |
| 6 - Reporting | R1-R5: P&L, balance sheet, cash flow, PDF export, firm dashboard | Complete |
| 7 - Operations | O1-O4: Audit trail, automated backup, restore, health check | Complete |

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Backend | Python 3.14 + FastAPI | Async API server |
| Database | PostgreSQL | 26 tables, ACID-compliant, audit triggers on all tables |
| Auth | JWT + RBAC | CPA_OWNER and ASSOCIATE roles with defense-in-depth |
| PDF | WeasyPrint | Pay stubs, tax forms, financial reports |
| Migration | Custom CSV parser | Imports QuickBooks Online exports |
| Frontend | React + Vite | *(not yet built)* |

## Project Structure

```
tax/
├── backend/
│   ├── app/
│   │   ├── auth/               # JWT auth, role dependencies (require_role, verify_role)
│   │   ├── models/             # SQLAlchemy ORM (26 models)
│   │   ├── schemas/            # Pydantic request/response schemas
│   │   ├── routers/            # FastAPI route handlers
│   │   ├── services/           # Business logic layer
│   │   │   ├── migration/      # QBO import pipeline (M1-M7)
│   │   │   └── payroll/        # Tax calculators, pay stubs, payroll runs (P2-P6)
│   │   ├── config.py           # Environment settings
│   │   ├── database.py         # Async SQLAlchemy engine
│   │   └── main.py             # FastAPI app entry point
│   └── tests/                  # 585 tests (pytest + pytest-asyncio)
├── frontend/                   # React + Vite (not yet built)
├── db/
│   ├── migrations/             # SQL schema (001_initial_schema.sql)
│   └── seeds/                  # Chart of accounts seed data
├── data/                       # Local file storage (documents, backups)
├── docs/                       # Compliance docs, migration reports
├── scripts/                    # Utility scripts
├── AGENT_PROMPTS/              # Claude Code agent instructions
├── .claude/CLAUDE.md           # Master context for all agents
├── ARCHITECTURE.md             # Module dependency map
├── OPEN_ISSUES.md              # 11 open compliance flags (rate verification)
└── AGENT_LOG.md                # Build session history
```

## Quick Start

### Prerequisites

- Python 3.14+
- PostgreSQL (local instance)
- pango (for PDF generation): `brew install pango`

### Setup

```bash
# Clone
git clone https://github.com/ed-da-goat/tax.git
cd tax

# Backend
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Database
psql -U postgres -c "CREATE DATABASE ga_cpa;"
psql -U postgres -d ga_cpa -f ../db/migrations/001_initial_schema.sql

# Run
uvicorn app.main:app --reload
```

### Run Tests

```bash
cd backend
source .venv/bin/activate
pytest tests/ -q
# 585 passed, 3 xfailed
```

## API Overview

All endpoints are prefixed with `/api/v1`. Authentication via `Authorization: Bearer <JWT>`.

| Group | Prefix | Key Endpoints |
|-------|--------|---------------|
| Auth | `/auth` | Login, token refresh |
| Clients | `/clients` | CRUD, archive, entity type |
| Chart of Accounts | `/clients/{id}/accounts` | CRUD, Georgia standard categories |
| Journal Entries | `/clients/{id}/journal-entries` | Double-entry GL, approval workflow |
| Vendors | `/clients/{id}/vendors` | CRUD |
| Bills (AP) | `/clients/{id}/bills` | Create, pay, void |
| Invoices (AR) | `/clients/{id}/invoices` | Create, record payment, void |
| Bank Reconciliation | `/clients/{id}/bank-accounts` | Import, match, reconcile |
| Documents | `/clients/{id}/documents` | Upload, view, search |
| Employees | `/clients/{id}/employees` | CRUD, terminate |
| Payroll | `/clients/{id}/payroll` | Create run, submit, finalize, pay stub PDF |
| Approvals | `/approvals` | Queue, batch approve/reject |
| Reports | `/reports` | P&L, balance sheet, cash flow, PDF export |
| Tax Exports | `/tax` | GA G-7, 500, 600, ST-3, federal forms |
| Operations | `/operations` | Backup, restore, health check |
| Audit Log | `/audit-log` | Immutable change history |

## Compliance

This system handles real financial data under Georgia tax law. Key enforcement:

- **Double-entry**: Every transaction balances debits and credits (DB-level CHECK constraint)
- **Audit trail**: No hard deletes anywhere. All changes logged with old/new values, user, timestamp
- **Client isolation**: Every table with client data has `client_id` as non-nullable FK; every query filters by it
- **Approval workflow**: Associates enter drafts; only CPA_OWNER can approve/post to GL
- **Payroll gate**: Finalization verified at both route level (`require_role`) and function level (`verify_role`) — defense in depth
- **Tax rate sourcing**: Every rate constant cites its Georgia DOR / IRS source document and review date

See `docs/GEORGIA_COMPLIANCE.md` and `OPEN_ISSUES.md` (11 open rate-verification flags for TY2026).

## Remaining Work

1. **Install pango** — `brew install pango` (unblocks 3 xfailed PDF tests)
2. **CPA_OWNER compliance review** — Verify 11 open tax rate flags in `OPEN_ISSUES.md`
3. **Frontend** — React + Vite dashboard (not yet started)
4. **E2E testing** — Integration test with real QuickBooks Online export data
