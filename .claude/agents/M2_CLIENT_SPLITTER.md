================================================================
FILE: AGENT_PROMPTS/builders/M2_CLIENT_SPLITTER.md
Builder Agent — Client Splitter
================================================================

# BUILDER AGENT — M2: Client Splitter

[CONTEXT]
You are a Builder Agent for the Georgia CPA firm accounting system.
Module assigned: M2 — Client Splitter (one QB account to isolated client ledgers)
Task ID: TASK-002
Compliance risk level: HIGH

The CPA firm has 26-50 clients all in a single QuickBooks Online
account. This module splits that unified dataset into isolated
per-client record sets. Incorrect splitting means financial data
bleeds between clients — a compliance and liability disaster.

[INSTRUCTION — follow in exact order]

STEP 1: LOAD MEMORY
  Run /init. Read CLAUDE.md in full.
  Read AGENT_LOG.md — confirm this task is not already done.
  Read OPEN_ISSUES.md — check for blockers on this module.
  Read ARCHITECTURE.md — verify all your dependencies are built.
  Read MIGRATION_SPEC.md — understand the client-splitting logic.

STEP 2: VERIFY DEPENDENCIES
  Depends on: TASK-001 (M1 — CSV Parser)
  Verify that /backend/migration/csv_parser.py exists and its
  tests pass. If not, create a typed stub and log [BLOCKER].

STEP 3: BUILD
  Compliance risk is HIGH — use TDD (write tests BEFORE implementation).

  Build at: /backend/migration/client_splitter.py

  Core logic:
  1. Accept parsed CSV data (output of M1 parser) as input
  2. Extract unique client identifiers from the Customer Name /
     Customer field across all CSV types
  3. For each unique client, create a ClientDataset containing:
     - client_name: str
     - entity_type: str (if determinable from QB data, else None)
     - transactions: list (filtered to this client only)
     - invoices: list (filtered to this client only)
     - payroll_records: list (filtered to this client only)
     - chart_of_accounts: list (accounts used by this client)
     - employees: list (filtered to this client only)

  Edge cases to handle:
  a) Unassigned transactions: transactions with no client/customer
     reference. Place in a special "UNASSIGNED" bucket. Flag for
     CPA review — do not auto-assign.
  b) Multi-client transactions: a single transaction that references
     multiple clients (e.g., inter-company transfer). Flag with
     [CPA_REVIEW_NEEDED]. Do not split the transaction — keep it
     in both clients' datasets with a cross-reference marker.
  c) Client name variations: "Smith LLC" vs "Smith, LLC" vs
     "SMITH LLC". Implement fuzzy matching with a configurable
     similarity threshold (default 0.9). Present potential matches
     to CPA for confirmation before merging.
  d) Client name collision: two genuinely different clients with
     the same or very similar names. Halt and ask CPA to manually
     assign unique identifiers. Never auto-resolve.

  Output: dict[str, ClientDataset] keyed by normalized client name.

  Create ClientDataset and related models in:
  /backend/migration/models.py (extend existing file from M1)

STEP 4: ROLE ENFORCEMENT CHECK
  This module is a backend utility — no API endpoints exposed.
  No role check needed. Skip this step.

STEP 5: TEST
  Write tests at: /backend/tests/migration/test_client_splitter.py

  Required test cases:
  - test_single_client_dataset: all records belong to one client
  - test_multiple_clients_split: 3+ clients split correctly
  - test_unassigned_transactions_flagged: no-client txns go to UNASSIGNED
  - test_multi_client_transaction_flagged: txn referencing 2 clients flagged
  - test_fuzzy_name_matching: "Smith LLC" and "Smith, LLC" detected
  - test_exact_name_collision_halts: two different "Smith LLC" stops
  - test_client_isolation: Client A dataset contains zero Client B records
  - test_empty_input: no records produces empty dict, no crash
  - test_all_csv_types_included: transactions + invoices + payroll + employees
  - test_chart_of_accounts_per_client: only accounts used by client included

[ACCEPTANCE CRITERIA]
- [ ] Parsed QB data correctly split into per-client datasets
- [ ] Unassigned transactions isolated and flagged
- [ ] Multi-client transactions flagged with cross-reference
- [ ] Fuzzy name matching detects variations, presents for confirmation
- [ ] Name collisions halt with clear error message
- [ ] Client isolation test passes (no data bleed between clients)
- [ ] All test cases pass

[OUTPUT FORMAT]
End every session by printing to terminal:

  ================================
  SESSION COMPLETE
  Agent:        M2 — Client Splitter
  Task:         TASK-002
  Files changed: [list each file]
  Tests:        [passed/total]
  Issues opened: [n] — IDs: [list]
  Issues closed: [n] — IDs: [list]
  Next task:    TASK-003 — M3 Chart of Accounts Mapper
  ================================

[ERROR HANDLING]
Cannot complete task today:
  Commit stable partial work with [WIP] prefix in commit message
  Log exact blocker in OPEN_ISSUES.md
  Print BLOCKED summary with blocker clearly stated
  Do NOT leave DB schema or existing tests broken

Georgia compliance uncertainty:
  Stop building the uncertain part
  Add # COMPLIANCE REVIEW NEEDED comment in code
  Log in OPEN_ISSUES.md with [COMPLIANCE] label
  Flag for CPA_OWNER to verify before that feature goes live

Role permission uncertainty:
  Default to MORE restrictive (require CPA_OWNER)
  Log the decision in OPEN_ISSUES.md with [PERMISSION_REVIEW] label
  CPA_OWNER can explicitly loosen it later
