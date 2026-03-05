================================================================
FILE: AGENT_PROMPTS/builders/D2_DOCUMENT_VIEWER.md
Builder Agent — Document Viewer
================================================================

# BUILDER AGENT — D2: Document Viewer

[CONTEXT]
You are a Builder Agent for the Georgia CPA firm accounting system.
Module assigned: D2 — Document viewer (in-browser, no external app)
Task ID: TASK-018
Compliance risk level: LOW

This module provides an in-browser viewer for documents stored in
the system. Users should be able to view PDFs and images inline
without downloading or opening external applications. This is a
React frontend component.

[INSTRUCTION — follow in exact order]

STEP 1: LOAD MEMORY
  Run /init. Read CLAUDE.md in full.
  Read AGENT_LOG.md — confirm this task is not already done.
  Read OPEN_ISSUES.md — check for blockers on this module.
  Read ARCHITECTURE.md — verify all your dependencies are built.

STEP 2: VERIFY DEPENDENCIES
  Depends on: TASK-017 (D1 — Document Upload)
  Verify that D1's file serving endpoint exists.
  If not, create a stub API and log [BLOCKER].

STEP 3: BUILD
  Compliance risk is LOW — write tests alongside implementation.

  Build React component at: /frontend/src/components/DocumentViewer.jsx
  Build supporting components at: /frontend/src/components/documents/

  Core components:

  1. DocumentViewer (main component):
     - Accept document_id as prop
     - Fetch document metadata from API
     - Based on file_type, render appropriate viewer:
       - PDF: use react-pdf or embed with <iframe>/<object>
       - Images (JPG, PNG, GIF): use <img> tag with zoom controls
       - TIFF: convert to displayable format or show download link
     - Navigation controls: zoom in/out, rotate, fit to width/height
     - Download button (always available as fallback)
     - Display metadata: file name, upload date, tags, linked transaction

  2. DocumentListPanel (sidebar/list):
     - Show list of documents for current client
     - Filter controls: by type, date, tags
     - Click a document to open in DocumentViewer
     - Thumbnail previews where possible

  3. DocumentUploadModal:
     - Drag-and-drop file upload
     - Tag assignment during upload
     - Transaction linking during upload
     - Progress indicator for large files
     - Validation feedback (file type, size)

  Implementation notes:
  - Use React + Vite (per CLAUDE.md tech stack)
  - No external desktop app dependencies — everything in browser
  - Handle loading states and error states gracefully
  - Responsive design for different screen sizes
  - Keyboard shortcuts: Escape to close, arrow keys for navigation

STEP 4: ROLE ENFORCEMENT CHECK
  All document viewing is available to both roles.
  No special role enforcement needed for this module.
  (Delete is handled in D1, not here.)

STEP 5: TEST
  Write tests at: /frontend/src/components/__tests__/DocumentViewer.test.jsx

  Required test cases:
  - test_render_pdf_viewer: PDF document displays embedded viewer
  - test_render_image_viewer: image document displays <img>
  - test_zoom_controls: zoom in/out changes display size
  - test_download_button: download button present and functional
  - test_metadata_display: file name, date, tags shown
  - test_loading_state: loading spinner shown while fetching
  - test_error_state: error message shown on fetch failure
  - test_document_list_filtering: filter by type/date works
  - test_upload_modal_validation: invalid file type shows error

[ACCEPTANCE CRITERIA]
- [ ] PDF documents render inline in browser
- [ ] Image documents (JPG, PNG, GIF) render inline
- [ ] Zoom and navigation controls functional
- [ ] Download fallback always available
- [ ] Document metadata displayed alongside viewer
- [ ] Document list with filtering
- [ ] Upload modal with drag-and-drop
- [ ] Loading and error states handled
- [ ] All test cases pass

[OUTPUT FORMAT]
End every session by printing to terminal:

  ================================
  SESSION COMPLETE
  Agent:        D2 — Document Viewer
  Task:         TASK-018
  Files changed: [list each file]
  Tests:        [passed/total]
  Issues opened: [n] — IDs: [list]
  Issues closed: [n] — IDs: [list]
  Next task:    TASK-019 — D3 Document Search
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
