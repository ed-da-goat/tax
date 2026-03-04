# Database — PostgreSQL

All database migrations and seed data.

## Structure
- `migrations/` — Sequential SQL migration files (001_, 002_, etc.)
- `seeds/` — Seed data (chart of accounts, tax tables, etc.)

## Rules
- Every migration is numbered and runs in order
- Never modify a migration after it has been applied — create a new one
- All client-data tables must have `client_id` as non-nullable FK
