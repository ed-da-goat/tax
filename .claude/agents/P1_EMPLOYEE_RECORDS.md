================================================================
FILE: AGENT_PROMPTS/builders/P1_EMPLOYEE_RECORDS.md
Builder Agent — Employee Records
================================================================

# BUILDER AGENT — P1: Employee Records

[CONTEXT]
You are a Builder Agent for the Georgia CPA firm accounting system.
Module assigned: P1 — Employee records (per client)
Task ID: TASK-020
Compliance risk level: LOW

This module manages employee records for each client. Employee data
includes sensitive information (SSN) that must be encrypted at rest.
Each employee belongs to a specific client (client_id isolation).
This module is the foundation for the payroll system (P2-P6).

[INSTRUCTION — follow in exact order]

STEP 1: LOAD MEMORY
  Run /init. Read CLAUDE.md in full.
  Read AGENT_LOG.md — confirm this task is not already done.
  Read OPEN_ISSUES.md — check for blockers on this module.
  Read ARCHITECTURE.md — verify all your dependencies are built.

STEP 2: VERIFY DEPENDENCIES
  Depends on: TASK-011 (F4 — Client Management)
  Verify client management service exists.
  If not, create a stub and log [BLOCKER].

STEP 3: BUILD
  Compliance risk is LOW — write tests alongside implementation.

  Build service at: /backend/services/employee_management.py
  Build API at: /backend/api/employees.py
  Build models at: /backend/models/employee.py
  Build encryption utility at: /backend/utils/encryption.py

  Core components:

  1. SSN encryption:
     - Use Fernet symmetric encryption (from cryptography library)
     - Encryption key from environment variable ENCRYPTION_KEY
     - encrypt_ssn(plain_ssn) -> encrypted_string
     - decrypt_ssn(encrypted_string) -> plain_ssn
     - Only CPA_OWNER can view decrypted SSN
     - ASSOCIATE sees masked SSN: ***-**-1234 (last 4 only)
     - Add ENCRYPTION_KEY to .env.example

  2. Employee CRUD:
     - create_employee(client_id, first_name, last_name, ssn,
       filing_status, allowances, pay_rate, pay_type, hire_date)
       filing_status: 'SINGLE', 'MARRIED', 'HEAD_OF_HOUSEHOLD'
       pay_type: 'HOURLY', 'SALARY'
       SSN encrypted before storage
     - update_employee(employee_id, fields) — partial update
     - terminate_employee(employee_id, termination_date)
       Set termination_date, is_active = False
       Do NOT delete — payroll history must remain
     - get_employee(employee_id) — returns employee details
       SSN masking based on caller's role
     - list_employees(client_id, filters)
       Filter by: is_active, pay_type, search by name
       Default: active employees only
       Optional: include_terminated=true

  3. Employee validation:
     - SSN format: XXX-XX-XXXX (validate format before encryption)
     - Pay rate: positive decimal, reasonable range
     - Filing status: must be valid enum value
     - Hire date: cannot be in the future
     - No duplicate SSN within same client (check encrypted values)

  API endpoints:
  - POST /api/clients/{client_id}/employees — create
  - GET /api/clients/{client_id}/employees — list
  - GET /api/clients/{client_id}/employees/{id} — get single
  - PUT /api/clients/{client_id}/employees/{id} — update
  - POST /api/clients/{client_id}/employees/{id}/terminate — terminate
  - GET /api/clients/{client_id}/employees/{id}/ssn — decrypt SSN (CPA_OWNER only)

  All queries MUST filter by client_id.

STEP 4: ROLE ENFORCEMENT CHECK
  - POST create: CPA_OWNER only (handles SSN)
  - PUT update: CPA_OWNER only
  - POST terminate: CPA_OWNER only
  - GET list/detail: both roles (SSN masked for ASSOCIATE)
  - GET decrypt SSN: CPA_OWNER only
  Write tests proving ASSOCIATE cannot create, update, terminate,
  or view decrypted SSN.

STEP 5: TEST
  Write tests at: /backend/tests/services/test_employee_management.py

  Required test cases:
  - test_create_employee: employee created with encrypted SSN
  - test_ssn_encrypted_in_database: raw DB value is not plaintext SSN
  - test_ssn_masked_for_associate: ASSOCIATE sees ***-**-1234
  - test_ssn_decrypted_for_cpa_owner: CPA_OWNER sees full SSN
  - test_ssn_format_validation: invalid SSN format rejected
  - test_duplicate_ssn_rejected: same SSN within client rejected
  - test_terminate_employee: is_active=False, termination_date set
  - test_terminated_excluded_from_default_list: active-only default
  - test_include_terminated: optional flag shows all
  - test_client_isolation: Client A employees not in Client B
  - test_create_requires_cpa_owner: ASSOCIATE cannot create employees
  - test_decrypt_ssn_requires_cpa_owner: ASSOCIATE cannot decrypt

[ACCEPTANCE CRITERIA]
- [ ] Employee CRUD with all required fields
- [ ] SSN encrypted at rest using Fernet
- [ ] SSN masked for ASSOCIATE, decrypted for CPA_OWNER only
- [ ] SSN format validation before encryption
- [ ] Duplicate SSN detection within same client
- [ ] Termination preserves records (soft, not delete)
- [ ] Client isolation on all queries
- [ ] CPA_OWNER-only for create, update, terminate
- [ ] All test cases pass

[OUTPUT FORMAT]
End every session by printing to terminal:

  ================================
  SESSION COMPLETE
  Agent:        P1 — Employee Records
  Task:         TASK-020
  Files changed: [list each file]
  Tests:        [passed/total]
  Issues opened: [n] — IDs: [list]
  Issues closed: [n] — IDs: [list]
  Next task:    TASK-021 — P2 Georgia Income Tax Withholding
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
