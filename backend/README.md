# Backend — Python + FastAPI

API server for the Georgia CPA accounting system. Feature-complete with 585 tests.

## Structure

```
app/
├── auth/                   # JWT auth, RBAC dependencies
├── models/                 # SQLAlchemy ORM (26 models)
├── schemas/                # Pydantic request/response schemas
├── routers/                # FastAPI route handlers
├── services/               # Business logic
│   ├── migration/          # QBO CSV import pipeline (M1-M7)
│   │   ├── qbo_parser.py        # CSV parser + validator
│   │   ├── client_splitter.py   # Multi-client QBO split
│   │   ├── coa_mapper.py        # QB -> GA chart of accounts
│   │   ├── transaction_importer.py  # GL journal entries
│   │   ├── invoice_importer.py      # AR history
│   │   ├── payroll_importer.py      # Payroll history
│   │   └── audit_report.py         # Migration quality report
│   └── payroll/            # Payroll calculators (P2-P6)
│       ├── ga_withholding.py     # Georgia G-4 income tax
│       ├── ga_suta.py            # Georgia SUTA (employer)
│       ├── federal_tax.py        # Federal withholding + FICA + FUTA
│       ├── pay_stub.py           # WeasyPrint PDF generator
│       └── payroll_service.py    # Payroll runs + approval gate
├── config.py               # pydantic-settings configuration
├── database.py             # Async SQLAlchemy engine + session
└── main.py                 # FastAPI app entry point
tests/                      # 585 passing, 3 xfailed
```

## Running

```bash
source .venv/bin/activate
uvicorn app.main:app --reload
```

## Testing

```bash
pytest tests/ -q              # All tests
pytest tests/ -x --tb=short   # Stop on first failure
pytest tests/test_payroll_service.py -v  # Single module
```

## Key Patterns

- **Async everywhere**: SQLAlchemy AsyncSession, asyncpg driver
- **Service layer**: Routers delegate to `services/` — no business logic in routes
- **Role enforcement**: `require_role("CPA_OWNER")` at route level + `verify_role(user, "CPA_OWNER")` at function level
- **Client isolation**: Every client-scoped query filters by `client_id` + `deleted_at IS NULL`
- **Soft deletes**: No hard deletes. `SoftDeleteMixin` on all models
- **Audit triggers**: PostgreSQL triggers log every INSERT/UPDATE/DELETE to `audit_log`
