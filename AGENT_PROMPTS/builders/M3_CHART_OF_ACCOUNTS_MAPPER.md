================================================================
FILE: AGENT_PROMPTS/builders/M3_CHART_OF_ACCOUNTS_MAPPER.md
Builder Agent — Chart of Accounts Mapper
================================================================

# BUILDER AGENT — M3: Chart of Accounts Mapper

[CONTEXT]
You are a Builder Agent for the Georgia CPA firm accounting system.
Module assigned: M3 — Chart of Accounts Mapper (QB categories to Georgia standard)
Task ID: TASK-003
Compliance risk level: MEDIUM

This module maps QuickBooks Online chart of accounts categories to the
Georgia-standard chart of accounts that was pre-seeded by module F2.
Incorrect mapping means transactions post to wrong accounts, producing
incorrect financial statements and tax returns.

[INSTRUCTION — follow in exact order]

STEP 1: LOAD MEMORY
  Run /init. Read CLAUDE.md in full.
  Read AGENT_LOG.md — confirm this task is not already done.
  Read OPEN_ISSUES.md — check for blockers on this module.
  Read ARCHITECTURE.md — verify all your dependencies are built.
  Read MIGRATION_SPEC.md — understand the column mappings.

STEP 2: VERIFY DEPENDENCIES
  Depends on: TASK-001 (M1 — CSV Parser), TASK-008 (F1 — Database Schema)
  Verify that:
  - /backend/migration/csv_parser.py exists and passes tests
  - F2 (Chart of Accounts seed data) is available or schema exists
  If either missing, create typed stubs and log [BLOCKER].

STEP 3: BUILD
  Compliance risk is MEDIUM — write tests alongside implementation.

  Build at: /backend/migration/coa_mapper.py

  Core logic:
  1. Load the Georgia-standard chart of accounts (from F2 seed data
     or a local JSON/YAML mapping file if F2 not yet built)
  2. Accept QB Online Chart of Accounts parsed data (from M1)
  3. For each QB account, attempt automatic mapping:
     - Exact name match (case-insensitive)
     - Category/type match (QB "Expense" → Georgia expense accounts)
     - Common synonym matching (e.g., "Automobile Expense" →
       "Vehicle Expense", "Telephone" → "Communications")
  4. Build a mapping table: dict[str, MappedAccount] where key is
     QB account name and value contains:
     - qb_account_name: str
     - qb_account_type: str
     - ga_account_id: UUID (matched Georgia standard account)
     - ga_account_name: str
     - ga_account_number: str
     - confidence: float (1.0 = exact match, 0.0 = no match)
     - needs_review: bool (True if confidence < 0.8)

  5. For unmappable accounts (confidence < 0.5):
     - Flag with [CPA_REVIEW_NEEDED]
     - Include in output with ga_account_id = None
     - Do NOT create new accounts automatically

  6. Support manual override:
     - Accept a JSON override file that maps specific QB account
       names to specific Georgia account IDs
     - Overrides take precedence over automatic mapping
     - Override file path: /data/migration/coa_overrides.json

  Create a MappingReport that summarizes:
  - Total QB accounts
  - Auto-mapped (high confidence)
  - Auto-mapped (needs review)
  - Unmapped (requires CPA action)

  Common QB-to-Georgia mappings to pre-build:
  - QB "Accounts Receivable" → 1200 Accounts Receivable
  - QB "Accounts Payable" → 2000 Accounts Payable
  - QB "Checking" → 1000 Cash and Cash Equivalents
  - QB "Savings" → 1010 Savings
  - QB "Sales" / "Revenue" → 4000 Revenue
  - QB "Cost of Goods Sold" → 5000 Cost of Goods Sold
  - QB "Payroll Expenses" → 6200 Payroll Expenses
  - Expand to cover all standard QB default accounts

STEP 4: ROLE ENFORCEMENT CHECK
  This module is a backend utility — no API endpoints exposed.
  No role check needed. Skip this step.

STEP 5: TEST
  Write tests at: /backend/tests/migration/test_coa_mapper.py

  Required test cases:
  - test_exact_name_match: QB "Cash" maps to Georgia "Cash"
  - test_case_insensitive_match: "ACCOUNTS RECEIVABLE" matches
  - test_synonym_match: "Automobile Expense" → "Vehicle Expense"
  - test_type_based_match: QB Expense type maps to Georgia expense
  - test_unmappable_account_flagged: unknown account flagged for review
  - test_manual_override_applied: override file takes precedence
  - test_mapping_report_counts: report counts match actual mappings
  - test_all_entity_types_covered: sole prop, S-Corp, C-Corp, LLC
  - test_confidence_scores_correct: exact=1.0, synonym=0.8-0.9, none=0.0
  - test_no_duplicate_mappings: one QB account maps to exactly one GA account

[ACCEPTANCE CRITERIA]
- [ ] Automatic mapping handles exact, case-insensitive, and synonym matches
- [ ] Confidence scoring applied to every mapping
- [ ] Unmappable accounts flagged, not silently dropped
- [ ] Manual override file supported and takes precedence
- [ ] MappingReport generated with accurate counts
- [ ] All four entity types' account needs covered
- [ ] All test cases pass

[OUTPUT FORMAT]
End every session by printing to terminal:

  ================================
  SESSION COMPLETE
  Agent:        M3 — Chart of Accounts Mapper
  Task:         TASK-003
  Files changed: [list each file]
  Tests:        [passed/total]
  Issues opened: [n] — IDs: [list]
  Issues closed: [n] — IDs: [list]
  Next task:    TASK-004 — M4 Transaction History Importer
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
