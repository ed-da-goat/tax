================================================================
FILE: AGENT_PROMPTS/builders/T4_TRANSACTION_APPROVAL_WORKFLOW.md
Builder Agent — Transaction Approval Workflow
================================================================

# BUILDER AGENT — T4: Transaction Approval Workflow

[CONTEXT]
You are a Builder Agent for the Georgia CPA firm accounting system.
Module assigned: T4 — Transaction Approval Workflow
Task ID: TASK-016
Compliance risk level: HIGH

This module enforces the ASSOCIATE-enters, CPA_OWNER-approves
workflow. It is a core compliance requirement: transactions entered
by ASSOCIATE must have status = PENDING_APPROVAL and MUST NOT
affect GL balances until CPA_OWNER posts them. This is Rule #5
in CLAUDE.md. Never auto-post on entry.

[INSTRUCTION — follow in exact order]

STEP 1: LOAD MEMORY
  Run /init. Read CLAUDE.md in full.
  Read AGENT_LOG.md — confirm this task is not already done.
  Read OPEN_ISSUES.md — check for blockers on this module.
  Read ARCHITECTURE.md — verify all your dependencies are built.

STEP 2: VERIFY DEPENDENCIES
  Depends on: TASK-010 (F3 — General Ledger), TASK-012 (F5 — User Auth)
  Verify that:
  - GL service supports status transitions
  - Auth middleware provides role checking
  If any missing, create typed stubs and log [BLOCKER].

STEP 3: BUILD
  Compliance risk is HIGH — use TDD (write tests BEFORE implementation).

  Build service at: /backend/services/approval_workflow.py
  Build API at: /backend/api/approval_workflow.py

  Core logic:

  1. Entry rules (enforced at service level):
     - When ASSOCIATE creates a journal entry:
       status MUST be DRAFT (never POSTED, never PENDING)
     - When ASSOCIATE submits:
       status changes to PENDING_APPROVAL
     - When CPA_OWNER creates:
       status can be DRAFT or PENDING_APPROVAL
       CPA_OWNER can also directly post their own entries
     - PENDING_APPROVAL entries DO NOT affect GL balances
       (This must be enforced in the GL balance calculation queries)

  2. Approval queue:
     - get_pending_approvals(client_id) — list all PENDING entries
       Ordered by entry_date (oldest first)
       Show: entry details, who created it, when submitted
     - approve(entry_id, approved_by)
       CPA_OWNER only — verify at function level
       Changes status to POSTED
       Sets approved_by, posted_at
       Entry now affects GL balances
     - reject(entry_id, rejected_by, reason)
       CPA_OWNER only — verify at function level
       Changes status to REJECTED
       Stores rejection reason
       Notifies creator (future: in-app notification)
     - bulk_approve(entry_ids, approved_by)
       CPA_OWNER only
       Approve multiple entries at once
       Atomic: all succeed or all fail

  3. Status flow enforcement:
     Valid transitions only:
     - DRAFT -> PENDING_APPROVAL (submit)
     - PENDING_APPROVAL -> POSTED (approve)
     - PENDING_APPROVAL -> REJECTED (reject)
     - POSTED -> VOIDED (void, with reversing entry)
     - REJECTED -> DRAFT (re-edit by creator)
     Invalid transitions raise an error (e.g., DRAFT -> POSTED
     for ASSOCIATE, REJECTED -> POSTED without re-submit).

  4. Approval audit trail:
     Every approval/rejection writes to audit_log with:
     - Who approved/rejected
     - When
     - Previous status
     - New status
     - Rejection reason (if applicable)

  API endpoints:
  - GET /api/clients/{client_id}/pending-approvals — list queue
  - POST /api/clients/{client_id}/journal-entries/{id}/approve — approve
  - POST /api/clients/{client_id}/journal-entries/{id}/reject — reject
  - POST /api/clients/{client_id}/journal-entries/bulk-approve — bulk
  - GET /api/clients/{client_id}/approval-history — audit trail

STEP 4: ROLE ENFORCEMENT CHECK
  This is THE role enforcement module for transactions.
  CRITICAL TESTS:
  - ASSOCIATE cannot call approve endpoint (even with manipulated JWT)
  - ASSOCIATE cannot call reject endpoint
  - ASSOCIATE cannot call bulk-approve endpoint
  - ASSOCIATE-created entries ALWAYS start as DRAFT
  - PENDING entries never appear in GL balance calculations
  - Role check at FUNCTION level, not just route level

STEP 5: TEST
  Write tests at: /backend/tests/services/test_approval_workflow.py

  Required test cases:
  - test_associate_entry_starts_draft: ASSOCIATE always creates DRAFT
  - test_associate_submit_changes_to_pending: submit works for ASSOCIATE
  - test_pending_not_in_gl_balance: PENDING entry excluded from balance
  - test_approve_changes_to_posted: CPA_OWNER approval works
  - test_posted_in_gl_balance: POSTED entry included in balance
  - test_reject_with_reason: rejection stores reason
  - test_rejected_can_return_to_draft: re-edit allowed
  - test_invalid_transition_rejected: DRAFT -> POSTED for ASSOCIATE fails
  - test_bulk_approve_all_or_nothing: atomic bulk approval
  - test_approve_requires_cpa_owner_function_level: role check in service
  - test_reject_requires_cpa_owner: ASSOCIATE cannot reject
  - test_cpa_owner_can_direct_post: CPA_OWNER can skip approval
  - test_approval_audit_trail: approve/reject logged in audit_log
  - test_manipulated_jwt_rejected: tampered role in JWT caught
  - test_client_isolation: Client A pending queue invisible to Client B

[ACCEPTANCE CRITERIA]
- [ ] ASSOCIATE entries always start as DRAFT
- [ ] PENDING_APPROVAL entries never affect GL balances
- [ ] Only CPA_OWNER can approve, reject, or bulk-approve
- [ ] Role checked at function level (not just route)
- [ ] Valid status transitions enforced, invalid ones rejected
- [ ] Bulk approve is atomic (all or nothing)
- [ ] Approval/rejection audit trail recorded
- [ ] CPA_OWNER can direct-post their own entries
- [ ] Client isolation on approval queue
- [ ] All 15 test cases pass

[OUTPUT FORMAT]
End every session by printing to terminal:

  ================================
  SESSION COMPLETE
  Agent:        T4 — Transaction Approval Workflow
  Task:         TASK-016
  Files changed: [list each file]
  Tests:        [passed/total]
  Issues opened: [n] — IDs: [list]
  Issues closed: [n] — IDs: [list]
  Next task:    TASK-017 — D1 Document Upload
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
