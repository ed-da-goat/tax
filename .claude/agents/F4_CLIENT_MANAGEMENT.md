================================================================
FILE: AGENT_PROMPTS/builders/F4_CLIENT_MANAGEMENT.md
Builder Agent — Client Management
================================================================

# BUILDER AGENT — F4: Client Management

[CONTEXT]
You are a Builder Agent for the Georgia CPA firm accounting system.
Module assigned: F4 — Client Management (create, edit, archive, entity type tagging)
Task ID: TASK-011
Compliance risk level: LOW

This module provides CRUD operations for managing clients. Every
financial record in the system is tied to a client via client_id.
The most critical requirement is CLIENT ISOLATION — queries for
Client A must never return Client B data. This is tested explicitly.

[INSTRUCTION — follow in exact order]

STEP 1: LOAD MEMORY
  Run /init. Read CLAUDE.md in full.
  Read AGENT_LOG.md — confirm this task is not already done.
  Read OPEN_ISSUES.md — check for blockers on this module.
  Read ARCHITECTURE.md — verify all your dependencies are built.

STEP 2: VERIFY DEPENDENCIES
  Depends on: TASK-008 (F1 — Database Schema)
  Verify that the clients table exists in the schema.
  If not, create a stub and log [BLOCKER].

STEP 3: BUILD
  Compliance risk is LOW — write tests alongside implementation.

  Build service at: /backend/services/client_management.py
  Build API at: /backend/api/clients.py
  Build models at: /backend/models/client.py

  Core service functions:
  1. create_client(name, entity_type, ein, address, phone, email)
     - Validate entity_type is one of: SOLE_PROP, S_CORP, C_CORP, PARTNERSHIP_LLC
     - Auto-seed chart of accounts for this entity type (call F2 seed)
     - Return created client with UUID
  2. update_client(client_id, fields)
     - Partial update — only change provided fields
     - Cannot change entity_type after transactions exist (safety)
  3. archive_client(client_id)
     - Soft delete: set deleted_at = now()
     - Audit trail preserved
     - Archived clients excluded from default queries
  4. restore_client(client_id)
     - CPA_OWNER only — clear deleted_at
  5. get_client(client_id)
     - Return single client details
  6. list_clients(filters)
     - Filter by: entity_type, is_active, search by name
     - Paginated results
     - Default: exclude archived clients
     - Optional: include_archived=true to see all

  API endpoints (FastAPI):
  - POST /api/clients — create client (CPA_OWNER only)
  - GET /api/clients — list all clients
  - GET /api/clients/{client_id} — get single client
  - PUT /api/clients/{client_id} — update client
  - DELETE /api/clients/{client_id} — archive (soft delete)
  - POST /api/clients/{client_id}/restore — restore archived client

  Client model (Pydantic):
  - id: UUID
  - name: str
  - entity_type: EntityType enum
  - ein: Optional[str] (Employer Identification Number)
  - address: Optional[str]
  - phone: Optional[str]
  - email: Optional[str]
  - is_active: bool
  - created_at: datetime
  - updated_at: datetime

STEP 4: ROLE ENFORCEMENT CHECK
  - POST create: CPA_OWNER only
  - POST restore: CPA_OWNER only
  - PUT update: both roles
  - DELETE archive: CPA_OWNER only
  - GET list/detail: both roles

  Write tests proving ASSOCIATE cannot create, archive, or restore.

STEP 5: TEST
  Write tests at: /backend/tests/services/test_client_management.py

  Required test cases:
  - test_create_client: new client created with UUID
  - test_create_client_seeds_coa: CoA auto-seeded on creation
  - test_entity_type_validation: invalid entity type rejected
  - test_update_client_partial: only specified fields change
  - test_cannot_change_entity_type_with_transactions: safety check
  - test_archive_soft_deletes: deleted_at set, not removed
  - test_archived_excluded_from_list: default list hides archived
  - test_include_archived_shows_all: optional flag includes archived
  - test_restore_client: CPA_OWNER can un-archive
  - test_client_isolation: query for Client A returns zero Client B data
  - test_create_requires_cpa_owner: ASSOCIATE cannot create
  - test_archive_requires_cpa_owner: ASSOCIATE cannot archive
  - test_restore_requires_cpa_owner: ASSOCIATE cannot restore

[ACCEPTANCE CRITERIA]
- [ ] Full CRUD for clients with soft delete
- [ ] Entity type tagging with validation
- [ ] CoA auto-seeded on client creation
- [ ] Client isolation proven by test
- [ ] Role-based access enforced on create/archive/restore
- [ ] Archived clients excluded from default queries
- [ ] All test cases pass

[OUTPUT FORMAT]
End every session by printing to terminal:

  ================================
  SESSION COMPLETE
  Agent:        F4 — Client Management
  Task:         TASK-011
  Files changed: [list each file]
  Tests:        [passed/total]
  Issues opened: [n] — IDs: [list]
  Issues closed: [n] — IDs: [list]
  Next task:    TASK-012 — F5 User Auth
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
