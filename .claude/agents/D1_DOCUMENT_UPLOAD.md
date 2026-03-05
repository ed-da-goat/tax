================================================================
FILE: AGENT_PROMPTS/builders/D1_DOCUMENT_UPLOAD.md
Builder Agent — Document Upload
================================================================

# BUILDER AGENT — D1: Document Upload

[CONTEXT]
You are a Builder Agent for the Georgia CPA firm accounting system.
Module assigned: D1 — Document upload (PDF, images) tagged to client + transaction
Task ID: TASK-017
Compliance risk level: LOW

This module handles uploading and storing client documents (PDFs,
images, receipts, tax forms). Documents are stored on the local
filesystem at /data/documents/[client_id]/ and metadata is stored
in the database. Documents can be tagged to a specific client and
optionally linked to a specific transaction.

[INSTRUCTION — follow in exact order]

STEP 1: LOAD MEMORY
  Run /init. Read CLAUDE.md in full.
  Read AGENT_LOG.md — confirm this task is not already done.
  Read OPEN_ISSUES.md — check for blockers on this module.
  Read ARCHITECTURE.md — verify all your dependencies are built.

STEP 2: VERIFY DEPENDENCIES
  Depends on: TASK-011 (F4 — Client Management), TASK-012 (F5 — User Auth)
  Verify that client_id lookup and auth middleware are available.
  If any missing, create typed stubs and log [BLOCKER].

STEP 3: BUILD
  Compliance risk is LOW — write tests alongside implementation.

  Build service at: /backend/services/document_management.py
  Build API at: /backend/api/documents.py
  Build models at: /backend/models/document.py

  Core components:

  1. File storage:
     - Store files at: /data/documents/{client_id}/{year}/{month}/
     - Rename files to: {uuid}_{original_filename} to prevent conflicts
     - Accepted file types: .pdf, .png, .jpg, .jpeg, .gif, .tiff
     - Maximum file size: 25MB (configurable)
     - Reject all other file types with clear error message

  2. Document upload:
     - upload_document(client_id, file, uploaded_by, tags=None,
       linked_transaction_id=None)
     - Validate file type and size
     - Store file on disk
     - Create metadata record in documents table:
       file_name, file_path, file_type, file_size, uploaded_by,
       tags (JSONB array), linked_transaction_id
     - Return document metadata with download URL

  3. Document metadata management:
     - update_tags(document_id, tags) — update document tags
     - link_to_transaction(document_id, journal_entry_id)
     - unlink_from_transaction(document_id)
     - delete_document(document_id) — soft delete (metadata only,
       file stays on disk for audit trail)

  4. Document listing:
     - list_documents(client_id, filters)
       Filter by: tags, date range, file_type, linked_transaction_id
       Paginated results
     - get_document(document_id) — single document metadata

  5. File serving:
     - serve_document(document_id) — return file with correct
       Content-Type header for inline viewing

  API endpoints:
  - POST /api/clients/{client_id}/documents — upload
  - GET /api/clients/{client_id}/documents — list
  - GET /api/clients/{client_id}/documents/{id} — metadata
  - GET /api/clients/{client_id}/documents/{id}/file — download/view
  - PUT /api/clients/{client_id}/documents/{id}/tags — update tags
  - PUT /api/clients/{client_id}/documents/{id}/link — link to transaction
  - DELETE /api/clients/{client_id}/documents/{id} — soft delete

  Ensure /data/documents/ directory is created on first upload.
  All queries MUST filter by client_id. No cross-client file access.

STEP 4: ROLE ENFORCEMENT CHECK
  - Upload: both roles (ASSOCIATE can upload)
  - Delete: CPA_OWNER only
  - Tag/link updates: both roles
  - Read/download: both roles
  Write test proving ASSOCIATE cannot delete documents.

STEP 5: TEST
  Write tests at: /backend/tests/services/test_document_management.py

  Required test cases:
  - test_upload_pdf: PDF uploaded, metadata created, file on disk
  - test_upload_image: JPG uploaded correctly
  - test_reject_invalid_file_type: .exe rejected with error
  - test_reject_oversized_file: >25MB rejected
  - test_file_stored_in_client_directory: path includes client_id
  - test_update_tags: tags updated on document
  - test_link_to_transaction: document linked to journal entry
  - test_soft_delete_preserves_file: metadata deleted, file remains
  - test_serve_correct_content_type: PDF served as application/pdf
  - test_client_isolation: Client A cannot access Client B documents
  - test_delete_requires_cpa_owner: ASSOCIATE cannot delete
  - test_list_pagination: paginated results work correctly

[ACCEPTANCE CRITERIA]
- [ ] PDF and image uploads stored to /data/documents/[client_id]/
- [ ] File type and size validation enforced
- [ ] Metadata stored in database with tags and transaction links
- [ ] Soft delete only (file preserved on disk)
- [ ] File served with correct MIME type
- [ ] Client isolation on all document access
- [ ] CPA_OWNER-only for delete
- [ ] All test cases pass

[OUTPUT FORMAT]
End every session by printing to terminal:

  ================================
  SESSION COMPLETE
  Agent:        D1 — Document Upload
  Task:         TASK-017
  Files changed: [list each file]
  Tests:        [passed/total]
  Issues opened: [n] — IDs: [list]
  Issues closed: [n] — IDs: [list]
  Next task:    TASK-018 — D2 Document Viewer
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
