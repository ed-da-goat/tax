# Backend -- Python + FastAPI

API server for the Georgia CPA accounting system. 900 tests passing, 34 routers, 257+ endpoints.

## Structure

```
app/
├── auth/                   # JWT auth, RBAC, 2FA (TOTP via pyotp)
├── models/                 # SQLAlchemy ORM (50+ models)
├── schemas/                # Pydantic request/response schemas
├── routers/                # 34 FastAPI route handlers
│   ├── auth.py             # Login, 2FA, password reset
│   ├── clients.py          # CRUD, archive, restore
│   ├── approvals.py        # Batch approve/reject workflow
│   ├── bills.py            # AP: create, pay, void, check printing
│   ├── invoices.py         # AR: create, approve, pay, void, PDF
│   ├── journal_entries.py  # Double-entry GL
│   ├── payroll.py          # Runs, finalize, pay stubs
│   ├── tax_exports.py      # GA/federal forms, W-2, 1099-NEC
│   ├── reports.py          # P&L, balance sheet, cash flow, aging
│   ├── search.py           # Global cross-entity search
│   ├── bulk_import.py      # CSV upload (5,000 row cap)
│   ├── recurring.py        # Recurring transaction templates
│   ├── statements.py       # Client account statements + email
│   ├── year_end.py         # Year-end close process
│   ├── operations.py       # Backup, health check
│   ├── restore.py          # Backup restoration
│   ├── time_tracking.py    # Billable hours
│   ├── service_billing.py  # Firm billing to clients
│   ├── engagements.py      # Engagement management
│   ├── contacts.py         # Client contacts
│   ├── workflows.py        # Task management
│   ├── portal.py           # Client portal messages
│   ├── fixed_assets.py     # Asset tracking, depreciation
│   ├── budgets.py          # Budget creation and tracking
│   ├── firm_analytics.py   # Cross-client metrics
│   └── ...                 # + bank_reconciliation, documents, employees, etc.
├── services/               # Business logic layer
│   ├── migration/          # QBO CSV import pipeline (M1-M7)
│   ├── payroll/            # Tax calculators, pay stubs, W-2, NACHA
│   ├── tax_filing/         # GA FSET XML, TaxBandits integration
│   ├── aging.py            # AR/AP aging report buckets
│   ├── check_printing.py   # Check PDF generation
│   ├── bulk_import.py      # CSV bill/invoice import
│   ├── email.py            # aiosmtplib templates (invoice, statement, reset)
│   ├── export.py           # CSV/Excel report export
│   ├── invoice_pdf.py      # Invoice PDF generation
│   ├── password_reset.py   # Token-based password reset
│   ├── recurring.py        # Recurring template execution
│   ├── search.py           # Cross-entity search
│   ├── statement.py        # Client account statements
│   ├── year_end.py         # Year-end close workflow
│   └── ...                 # + approval, client, document, reporting, etc.
├── middleware/             # Security headers, request size limits, audit
├── crypto.py               # Fernet PII encryption (encrypt_pii/decrypt_pii)
├── config.py               # pydantic-settings (no default secrets)
├── database.py             # Async SQLAlchemy engine + session
└── main.py                 # FastAPI app entry point
db/migrations/              # 004-006 (incremental SQL migrations)
scripts/
├── seed_test_data.py       # 4 clients, all entity types, all statuses
└── migrate_encrypt_pii.py  # Encrypt existing plaintext PII
tests/                      # 900 passing (pytest + pytest-asyncio)
```

## Running

```bash
source .venv/bin/activate
uvicorn app.main:app --reload
```

Required environment variables in `.env` (app crashes without them):
- `DATABASE_URL` -- asyncpg connection string
- `JWT_SECRET` -- signing key for JWT tokens
- `ENCRYPTION_KEY` -- Fernet key for PII encryption
- `DEBUG` -- `false` in production (disables docs endpoints)

## Testing

```bash
.venv/bin/python -m pytest --tb=short -q     # All 900 tests
.venv/bin/python -m pytest -x --tb=short     # Stop on first failure
.venv/bin/python -m pytest tests/test_payroll_service.py -v  # Single module
```

## Key Patterns

- **Async everywhere**: SQLAlchemy AsyncSession, asyncpg driver
- **Service layer**: Routers delegate to `services/` -- no business logic in routes
- **Role enforcement**: `require_role("CPA_OWNER")` at route level + `verify_role(user, "CPA_OWNER")` at function level
- **Client isolation**: Every client-scoped query filters by `client_id` + `deleted_at IS NULL`
- **Soft deletes**: No hard deletes. `SoftDeleteMixin` on all models
- **Audit triggers**: PostgreSQL triggers log every INSERT/UPDATE/DELETE to `audit_log`
- **PII encryption**: SSN and tax ID encrypted at rest via Fernet (`app/crypto.py`)
- **Rate limiting**: slowapi on login and 2FA endpoints
- **No default secrets**: `config.py` raises on missing env vars
