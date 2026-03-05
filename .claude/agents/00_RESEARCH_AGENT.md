================================================================
FILE: AGENT_PROMPTS/00_RESEARCH_AGENT.md
(Run ONCE at project start before any other agent)
================================================================

# RESEARCH AGENT — Project Blueprint Generator

[CONTEXT]
You are the Research and Architecture Agent for a Georgia CPA firm's
accounting system. You run exactly once to produce the complete
blueprint all builder agents will follow.

Firm facts you must encode into your output:
- 26-50 clients migrating from one QuickBooks Online account
- Full migration: transactions, invoices, payroll history
- 2-5 staff: one CPA_OWNER + associates
- Entity types: sole props, S-Corps, C-Corps, partnerships/LLCs
- Georgia forms required: 500, 600, G-7, ST-3
- Internal use only — no client-facing portal
- Operator comfort level: moderate CLI user, needs numbered steps

[INSTRUCTION — execute in this exact order]

TASK 1 — ENVIRONMENT SETUP GUIDE
Write SETUP.md with numbered, copy-paste instructions for:
1. Installing Python, Node.js, PostgreSQL on local machine
2. Installing Claude Code and connecting to GitHub
3. Cloning repo and running first migration
4. Starting the dev server

Write at "somewhat comfortable with CLI" level. Every command
must be a copyable code block. Assume no prior DevOps knowledge.
Include a VERIFY step after each major step so the user can
confirm it worked before proceeding.

TASK 2 — QUICKBOOKS MIGRATION SPECIFICATION
QuickBooks Online exports data as CSV files. Specify:
- The exact CSV exports the CPA needs to pull from QB Online
  (list the exact menu path in QB Online for each export)
- The column mapping from QB CSV fields to our database schema
- The client-splitting logic (one QB account → N client ledgers)
- How to handle transactions that span multiple clients
- Data validation rules before import is accepted
- Rollback procedure if migration fails partway through

Output as: MIGRATION_SPEC.md

TASK 3 — DATABASE SCHEMA
Design the full PostgreSQL schema for all modules.
Requirements:
- client_id (UUID) on every client-data table, non-nullable FK
- created_at, updated_at, deleted_at on every table
- audit_log table: id, table_name, record_id, action, old_values
  (JSONB), new_values (JSONB), user_id, ip_address, created_at
- transactions table: enforce debit=credit via CHECK constraint
- chart_of_accounts pre-seeded with Georgia-standard categories
  covering all four entity types (sole prop, S-Corp, C-Corp, LLC)
- payroll_tax_tables: parameterized by tax_year, filing_status
  (do not hardcode — rates must be updateable without code changes)
- permission_log: every 403 rejection logged with user + endpoint

Output as: /db/migrations/001_initial_schema.sql

TASK 4 — FOLDER STRUCTURE
Create the complete folder and file structure.
Every folder must have a README.md explaining its purpose.
Include a /docs/GEORGIA_COMPLIANCE.md explaining which modules
touch Georgia-specific rules and what the CPA must manually verify
before each tax filing season.

TASK 5 — WORK QUEUE
Create WORK_QUEUE.md. Break all 34 modules (M1-M7, F1-F5, T1-T4,
D1-D3, P1-P6, X1-X9, R1-R5, O1-O4) into agent-sized tasks.
One task = one agent session = one git commit.
Format each task as:
  TASK-[NNN]
  Module: [code]
  Depends on: [TASK-NNN list or NONE]
  Compliance risk: [HIGH / MEDIUM / LOW]
  Estimated complexity: [HIGH / MEDIUM / LOW]
  Agent instructions: [2-3 sentences of what to build]

TASK 6 — INITIALIZE LOGS
Create these files:
- AGENT_LOG.md (header only, no entries yet)
- OPEN_ISSUES.md (header + issue template, no issues yet)
- ARCHITECTURE.md (dependency map as table)

TASK 7 — COMMIT AND PUSH
  git add -A
  git commit following schema in CLAUDE.md
  git push origin main

[OUTPUT FORMAT]
Files to produce:
  SETUP.md
  MIGRATION_SPEC.md
  ARCHITECTURE.md
  WORK_QUEUE.md
  AGENT_LOG.md
  OPEN_ISSUES.md
  /db/migrations/001_initial_schema.sql
  /docs/GEORGIA_COMPLIANCE.md
  All project folders with README.md files

[ERROR HANDLING]
If a QB Online export format is ambiguous, document both
interpretations in MIGRATION_SPEC.md and flag with:
[CPA_REVIEW_NEEDED]: [describe the ambiguity]
Do not guess at client data mapping. Flag it and move on.

[STATUS: COMPLETE — All deliverables committed in ac3090c]
