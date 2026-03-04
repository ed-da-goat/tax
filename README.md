# Georgia CPA Firm — Accounting System

A full-featured accounting system built to replace QuickBooks Online for a Georgia CPA firm with 26-50 clients.

## Status

**Current Phase: Phase 1 — Foundation (starting)**

| Phase | Description | Progress |
|-------|------------|----------|
| 0 | QB Online Migration | Not started |
| 1 | Foundation (DB, Auth, GL, Clients) | **Starting next** |
| 2 | Transactions (AP, AR, Bank Rec) | Not started |
| 3 | Document Management | Not started |
| 4 | Payroll (Georgia-specific) | Not started |
| 5 | Tax Form Exports (GA + Federal) | Not started |
| 6 | Reporting (P&L, Balance Sheet, etc.) | Not started |
| 7 | Operations (Backup, Audit, Health) | Not started |

## What's Built So Far

### Research Agent Output (Complete)
- [x] `SETUP.md` — Environment setup guide (Python, Node, PostgreSQL)
- [x] `MIGRATION_SPEC.md` — QuickBooks Online import specification
- [x] `db/migrations/001_initial_schema.sql` — Full PostgreSQL schema (27 tables)
- [x] `ARCHITECTURE.md` — Module dependency map
- [x] `WORK_QUEUE.md` — 43 tasks covering all 34 modules
- [x] `docs/GEORGIA_COMPLIANCE.md` — Georgia tax compliance guide
- [x] `AGENT_LOG.md` — Session tracking
- [x] `OPEN_ISSUES.md` — Issue tracker
- [x] Agent prompts for all agent types (`AGENT_PROMPTS/`)

### Next Up: TASK-008 (F1 — Database Schema)
Apply the schema to PostgreSQL, verify constraints and triggers work.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React + Vite |
| Backend | Python + FastAPI |
| Database | PostgreSQL (local) |
| Auth | JWT with role-based access (CPA_OWNER / ASSOCIATE) |
| PDF Export | WeasyPrint |
| Migration | Custom CSV parser for QB Online exports |

## Project Structure

```
tax/
├── AGENT_PROMPTS/       # Claude Code agent instructions
├── backend/             # Python FastAPI server
│   ├── app/
│   │   ├── api/routes/  # API endpoints
│   │   ├── core/        # Config, security, DB connection
│   │   ├── models/      # SQLAlchemy ORM models
│   │   ├── schemas/     # Pydantic schemas
│   │   ├── services/    # Business logic
│   │   └── utils/       # Shared utilities
│   └── tests/           # pytest suite
├── frontend/            # React + Vite dashboard
│   └── src/
│       ├── components/  # Reusable UI components
│       ├── pages/       # Page-level components
│       ├── hooks/       # Custom React hooks
│       └── utils/       # Helper functions
├── db/
│   ├── migrations/      # SQL migration files
│   └── seeds/           # Seed data
├── docs/                # Compliance docs, migration reports
├── data/                # Local-only: client docs + backups
├── scripts/             # Utility scripts
├── SETUP.md             # Environment setup guide
├── MIGRATION_SPEC.md    # QB Online import spec
├── ARCHITECTURE.md      # Module dependency map
├── WORK_QUEUE.md        # Task queue (43 tasks)
└── CLAUDE.md            # Master context for all agents
```

## Quick Start

See `SETUP.md` for full instructions. Summary:

```bash
# Clone
git clone https://github.com/ed-da-goat/tax.git
cd tax

# Backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt

# Frontend
cd frontend && npm install && cd ..

# Database
psql -U cpa_admin -d cpa_accounting -f db/migrations/001_initial_schema.sql

# Run
uvicorn backend.app.main:app --reload  # Terminal 1
cd frontend && npm run dev              # Terminal 2
```

## Module List (34 modules, 43 tasks)

See `WORK_QUEUE.md` for the full task queue with dependencies and complexity ratings.

## Compliance

This system handles real financial data under Georgia tax law. See `docs/GEORGIA_COMPLIANCE.md` for:
- Which modules touch Georgia-specific rules
- Annual pre-filing verification checklist
- Source citation requirements for all tax rates

## Contributing (Agent Protocol)

Each module is built by a Claude Code agent session following `AGENT_PROMPTS/02_BUILDER_AGENT_TEMPLATE.md`. Every agent must:
1. Read `CLAUDE.md` first
2. Check `AGENT_LOG.md` and `OPEN_ISSUES.md`
3. Verify dependencies in `ARCHITECTURE.md`
4. Build, test, commit per the schema in `CLAUDE.md`
5. Update all log files before ending session
