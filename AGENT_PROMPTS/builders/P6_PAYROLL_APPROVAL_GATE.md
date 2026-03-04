================================================================
FILE: AGENT_PROMPTS/builders/P6_PAYROLL_APPROVAL_GATE.md
Builder Agent — Payroll Approval Gate
================================================================

# BUILDER AGENT — P6: Payroll Approval Gate

[CONTEXT]
You are a Builder Agent for the Georgia CPA firm accounting system.
Module assigned: P6 — Payroll approval gate (CPA_OWNER only can finalize)
Task ID: TASK-025
Compliance risk level: HIGH

This module is the LAST GATE before payroll is finalized. Only
CPA_OWNER can finalize payroll. Per CLAUDE.md Rule #6: the payroll
finalization endpoint must verify current_user.role == 'CPA_OWNER'
at the FUNCTION level, not just the route level. Defense in depth.

Finalizing payroll:
- Posts payroll journal entries to the GL
- Marks the payroll run as FINALIZED
- Generates pay stubs (if not already generated)
- Records become immutable (cannot be edited after finalization)

[INSTRUCTION — follow in exact order]

STEP 1: LOAD MEMORY
  Run /init. Read CLAUDE.md in full.
  Read AGENT_LOG.md — confirm this task is not already done.
  Read OPEN_ISSUES.md — check for blockers on this module.
  Read ARCHITECTURE.md — verify all your dependencies are built.

STEP 2: VERIFY DEPENDENCIES
  Depends on: TASK-024 (P5 — Pay Stub Generator), TASK-012 (F5 — User Auth)
  Verify payroll processor and auth middleware are available.
  If any missing, create typed stubs and log [BLOCKER].

STEP 3: BUILD
  Compliance risk is HIGH — use TDD (write tests BEFORE implementation).

  Build service at: /backend/services/payroll/approval_gate.py
  Build API additions at: /backend/api/payroll.py (extend existing)

  Core logic:

  1. Review payroll (pre-finalization):
     - get_payroll_review(payroll_run_id) -> PayrollReview
       Return summary for CPA_OWNER review:
       - Total gross pay (all employees)
       - Total federal withholding
       - Total Georgia withholding
       - Total FICA (SS + Medicare)
       - Total FUTA
       - Total SUTA
       - Total net pay
       - Per-employee breakdown
       - Any compliance flags (needs_compliance_review items)
       - Warning if any employee has unusual amounts

  2. Finalize payroll:
     - finalize_payroll(payroll_run_id, finalized_by)
       CRITICAL: Check at FUNCTION level (first line of function):
       ```python
       def finalize_payroll(payroll_run_id, current_user):
           if current_user.role != 'CPA_OWNER':
               log_permission_denied(current_user, 'finalize_payroll')
               raise PermissionError("Only CPA_OWNER can finalize payroll")
       ```
       Steps on finalization:
       a) Verify payroll run status is DRAFT (cannot re-finalize)
       b) Verify no compliance flags pending (or CPA explicitly overrides)
       c) Create GL journal entries for the payroll run:
          - Debit: Payroll Expense (6200), Employer FICA (6210),
            Employer FUTA (6220), Employer SUTA (6230)
          - Credit: Federal Withholding Payable (2210),
            State Withholding Payable (2220), FICA Payable (2230),
            FUTA Payable (2240), SUTA Payable (2250),
            Cash/Payroll Bank Account (1000)
       d) Post journal entries as POSTED (not PENDING_APPROVAL —
          finalization IS the approval)
       e) Generate pay stubs if not already generated
       f) Set payroll_run.status = 'FINALIZED'
       g) Set payroll_run.finalized_by = current_user.id
       h) Set payroll_run.finalized_at = now()
       i) Payroll items become immutable (enforced by status check)

  3. Reject payroll:
     - reject_payroll(payroll_run_id, rejected_by, reason)
       CPA_OWNER only
       Set status to REJECTED with reason
       ASSOCIATE can then edit and resubmit

  4. Void finalized payroll:
     - void_payroll(payroll_run_id, voided_by, reason)
       CPA_OWNER only
       Create reversing GL entries
       Set status to VOIDED
       This is for error correction after finalization
       Audit trail preserved

  API endpoints (extend /backend/api/payroll.py):
  - GET /api/clients/{client_id}/payroll/runs/{id}/review — review summary
  - POST /api/clients/{client_id}/payroll/runs/{id}/finalize — finalize
  - POST /api/clients/{client_id}/payroll/runs/{id}/reject — reject
  - POST /api/clients/{client_id}/payroll/runs/{id}/void — void

STEP 4: ROLE ENFORCEMENT CHECK
  THIS IS THE PRIMARY ROLE ENFORCEMENT MODULE FOR PAYROLL.
  - finalize: CPA_OWNER only — function level check REQUIRED
  - reject: CPA_OWNER only
  - void: CPA_OWNER only
  - review (read): both roles

  Write tests proving:
  - ASSOCIATE cannot finalize (function level blocks it)
  - ASSOCIATE with manipulated JWT role cannot finalize
  - Permission denial logged to permission_log table

STEP 5: TEST
  Write tests at: /backend/tests/services/payroll/test_approval_gate.py

  Required test cases (TDD — write these FIRST):
  - test_finalize_requires_cpa_owner_function_level: role check in function
  - test_associate_cannot_finalize: ASSOCIATE blocked at function level
  - test_manipulated_jwt_cannot_finalize: tampered role caught
  - test_permission_denial_logged: 403 written to permission_log
  - test_finalize_creates_gl_entries: journal entries posted to GL
  - test_gl_entries_balanced: payroll GL debits == credits
  - test_finalize_changes_status: DRAFT -> FINALIZED
  - test_finalize_sets_finalized_by: user ID recorded
  - test_cannot_re_finalize: already FINALIZED run rejected
  - test_reject_with_reason: rejection reason stored
  - test_void_creates_reversing_entries: reversing GL entries
  - test_void_requires_cpa_owner: ASSOCIATE cannot void
  - test_compliance_flags_block_finalization: flagged items must be reviewed
  - test_payroll_items_immutable_after_finalize: cannot edit FINALIZED items
  - test_client_isolation: Client A payroll invisible to Client B

[ACCEPTANCE CRITERIA]
- [ ] CPA_OWNER-only finalization at FUNCTION level (defense in depth)
- [ ] GL journal entries created on finalization (balanced)
- [ ] Correct accounts debited and credited per payroll accounting
- [ ] Pay stubs generated on finalization
- [ ] Payroll run status: DRAFT -> FINALIZED (immutable)
- [ ] Reject and void supported (CPA_OWNER only)
- [ ] Permission denials logged to permission_log
- [ ] Compliance flags block finalization unless overridden
- [ ] Manipulated JWT role does not bypass function-level check
- [ ] All 15 test cases pass

[OUTPUT FORMAT]
End every session by printing to terminal:

  ================================
  SESSION COMPLETE
  Agent:        P6 — Payroll Approval Gate
  Task:         TASK-025
  Files changed: [list each file]
  Tests:        [passed/total]
  Issues opened: [n] — IDs: [list]
  Issues closed: [n] — IDs: [list]
  Next task:    TASK-026 — X1 Georgia Form G-7
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
