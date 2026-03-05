================================================================
FILE: AGENT_PROMPTS/builders/F5_USER_AUTH.md
Builder Agent — User Auth (JWT + Roles)
================================================================

# BUILDER AGENT — F5: User Authentication (Login, JWT, Role Assignment)

[CONTEXT]
You are a Builder Agent for the Georgia CPA firm accounting system.
Module assigned: F5 — User auth (login, JWT, role assignment)
Task ID: TASK-012
Compliance risk level: MEDIUM

This module implements authentication and authorization. The system
has exactly two roles: CPA_OWNER and ASSOCIATE. Every API endpoint
must check the user's role. Every 403 rejection must be logged to
the permission_log table. JWTs are local-only (no OAuth needed).

[INSTRUCTION — follow in exact order]

STEP 1: LOAD MEMORY
  Run /init. Read CLAUDE.md in full.
  Read AGENT_LOG.md — confirm this task is not already done.
  Read OPEN_ISSUES.md — check for blockers on this module.
  Read ARCHITECTURE.md — verify all your dependencies are built.

STEP 2: VERIFY DEPENDENCIES
  Depends on: TASK-008 (F1 — Database Schema)
  Verify that users and permission_log tables exist.
  If not, create stubs and log [BLOCKER].

STEP 3: BUILD
  Compliance risk is MEDIUM — write tests alongside implementation.

  Build service at: /backend/services/auth.py
  Build API at: /backend/api/auth.py
  Build middleware at: /backend/middleware/auth.py
  Build models at: /backend/models/user.py

  Core components:

  1. Password hashing (use bcrypt):
     - hash_password(plain_text) -> str
     - verify_password(plain_text, hashed) -> bool

  2. JWT token management:
     - create_access_token(user_id, role, expires_delta) -> str
     - decode_access_token(token) -> TokenPayload
     - Token payload: {user_id, role, exp, iat}
     - Secret key from environment variable JWT_SECRET
     - Default expiration: 8 hours (configurable)
     - Refresh tokens not needed (local use, re-login acceptable)

  3. Auth middleware (FastAPI dependency):
     - get_current_user(token: str) -> User
       Decode JWT, look up user, return User object
     - require_role(required_role: str) -> dependency
       Check current_user.role >= required_role
       If fails: log to permission_log table, return 403 with:
       {"error": "Insufficient permissions", "required_role": "[role]"}

  4. Auth API endpoints:
     - POST /api/auth/login — accept email + password, return JWT
     - POST /api/auth/register — create new user (CPA_OWNER only)
     - GET /api/auth/me — return current user info from JWT
     - PUT /api/auth/users/{id}/role — change user role (CPA_OWNER only)
     - GET /api/auth/users — list all users (CPA_OWNER only)
     - PUT /api/auth/users/{id}/deactivate — deactivate user (CPA_OWNER only)

  5. Permission logging:
     - Every 403 response writes to permission_log:
       user_id, endpoint, method, required_role, actual_role, ip_address
     - This is for audit purposes — the CPA can see who tried what

  6. Initial user setup:
     - On first run (no users in DB), create a default CPA_OWNER:
       email from environment variable DEFAULT_ADMIN_EMAIL
       password from environment variable DEFAULT_ADMIN_PASSWORD
       role: CPA_OWNER
     - Print a warning: "Default admin created. Change password immediately."

  Implementation notes:
  - Use python-jose for JWT encoding/decoding
  - Use passlib[bcrypt] for password hashing
  - Store JWT_SECRET in .env file (never commit to git)
  - Add .env to .gitignore
  - Create .env.example with placeholder values

STEP 4: ROLE ENFORCEMENT CHECK
  This IS the role enforcement module. Ensure:
  - register: CPA_OWNER only
  - change role: CPA_OWNER only
  - deactivate: CPA_OWNER only
  - login: no auth required
  - me: any authenticated user
  - list users: CPA_OWNER only

  The middleware must be usable by ALL other modules.
  Export: get_current_user, require_cpa_owner, require_authenticated

STEP 5: TEST
  Write tests at: /backend/tests/services/test_auth.py

  Required test cases:
  - test_password_hash_and_verify: hash then verify returns True
  - test_password_verify_wrong_password: wrong password returns False
  - test_create_access_token: token decodes to correct payload
  - test_expired_token_rejected: expired JWT returns 401
  - test_invalid_token_rejected: malformed JWT returns 401
  - test_login_success: correct credentials return JWT
  - test_login_wrong_password: bad password returns 401
  - test_login_nonexistent_user: unknown email returns 401
  - test_register_requires_cpa_owner: ASSOCIATE cannot register users
  - test_change_role_requires_cpa_owner: ASSOCIATE cannot change roles
  - test_permission_log_on_403: 403 response writes to permission_log
  - test_middleware_extracts_user: valid JWT produces User object
  - test_deactivated_user_cannot_login: inactive user blocked
  - test_manipulated_jwt_role_rejected: changing role in JWT payload fails
    (because signature verification catches the tampering)
  - test_default_admin_created: first-run creates CPA_OWNER

[ACCEPTANCE CRITERIA]
- [ ] Login endpoint returns JWT with user_id and role
- [ ] JWT signature verification prevents tampering
- [ ] Middleware correctly extracts user and role from token
- [ ] 403 responses logged to permission_log with full details
- [ ] CPA_OWNER-only endpoints enforced (register, role change, etc.)
- [ ] Passwords hashed with bcrypt, never stored in plaintext
- [ ] JWT_SECRET in environment variable, not in code
- [ ] Default admin auto-created on first run
- [ ] All test cases pass

[OUTPUT FORMAT]
End every session by printing to terminal:

  ================================
  SESSION COMPLETE
  Agent:        F5 — User Auth
  Task:         TASK-012
  Files changed: [list each file]
  Tests:        [passed/total]
  Issues opened: [n] — IDs: [list]
  Issues closed: [n] — IDs: [list]
  Next task:    TASK-013 — T1 Accounts Payable
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
