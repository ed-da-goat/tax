================================================================
FILE: AGENT_PROMPTS/builders/D3_DOCUMENT_SEARCH.md
Builder Agent — Document Search
================================================================

# BUILDER AGENT — D3: Document Search

[CONTEXT]
You are a Builder Agent for the Georgia CPA firm accounting system.
Module assigned: D3 — Document search by client, date, type
Task ID: TASK-019
Compliance risk level: LOW

This module provides search and filtering capabilities for
documents stored in the system. Users should be able to find
documents quickly by client, date range, document type, and tags.

[INSTRUCTION — follow in exact order]

STEP 1: LOAD MEMORY
  Run /init. Read CLAUDE.md in full.
  Read AGENT_LOG.md — confirm this task is not already done.
  Read OPEN_ISSUES.md — check for blockers on this module.
  Read ARCHITECTURE.md — verify all your dependencies are built.

STEP 2: VERIFY DEPENDENCIES
  Depends on: TASK-017 (D1 — Document Upload)
  Verify D1's document metadata and listing services exist.
  If not, create stubs and log [BLOCKER].

STEP 3: BUILD
  Compliance risk is LOW — write tests alongside implementation.

  Build service at: /backend/services/document_search.py
  Build API at: /backend/api/document_search.py
  Build React component at: /frontend/src/components/DocumentSearch.jsx

  Core components:

  1. Backend search service:
     - search_documents(client_id, query_params)
       Query parameters:
       - q: text search on file_name and tags
       - file_type: filter by type (pdf, image, etc.)
       - date_from, date_to: date range filter on upload date
       - tags: filter by tag(s), supports multiple
       - linked_transaction_id: find docs linked to a specific txn
       - sort_by: date_asc, date_desc, name_asc, name_desc
       - page, page_size: pagination (default 20 per page)
     - Return: paginated list with total count
     - All searches MUST filter by client_id (mandatory, not optional)

  2. Tag management:
     - get_all_tags(client_id) — list unique tags for a client
       Useful for populating filter dropdowns
     - get_tag_counts(client_id) — tags with document count each

  3. React search component:
     - Search bar with text input
     - Filter dropdowns: file type, tags, date range
     - Results grid with thumbnails and metadata
     - Click result to open in DocumentViewer (D2)
     - Real-time search (debounced, 300ms)
     - Empty state: helpful message when no results

  API endpoints:
  - GET /api/clients/{client_id}/documents/search — search
  - GET /api/clients/{client_id}/documents/tags — list tags
  - GET /api/clients/{client_id}/documents/tags/counts — tag counts

STEP 4: ROLE ENFORCEMENT CHECK
  All search operations available to both roles.
  No special role enforcement needed.

STEP 5: TEST
  Write tests at: /backend/tests/services/test_document_search.py

  Required test cases:
  - test_search_by_filename: text search matches file name
  - test_search_by_tag: tag filter returns tagged documents
  - test_search_by_date_range: date filter works correctly
  - test_search_by_file_type: type filter works correctly
  - test_search_combined_filters: multiple filters applied together
  - test_search_pagination: page/page_size returns correct subset
  - test_search_empty_results: no matches returns empty list, not error
  - test_client_isolation: search for Client A returns zero Client B docs
  - test_get_all_tags: unique tags returned for client
  - test_tag_counts_accurate: tag count matches actual document count
  - test_sort_by_date: results sorted correctly

[ACCEPTANCE CRITERIA]
- [ ] Text search across file names and tags
- [ ] Filter by file type, date range, tags
- [ ] Combined filters work together
- [ ] Pagination with total count
- [ ] Tag listing and counting
- [ ] Client isolation on all searches
- [ ] React search component with real-time filtering
- [ ] All test cases pass

[OUTPUT FORMAT]
End every session by printing to terminal:

  ================================
  SESSION COMPLETE
  Agent:        D3 — Document Search
  Task:         TASK-019
  Files changed: [list each file]
  Tests:        [passed/total]
  Issues opened: [n] — IDs: [list]
  Issues closed: [n] — IDs: [list]
  Next task:    TASK-020 — P1 Employee Records
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
