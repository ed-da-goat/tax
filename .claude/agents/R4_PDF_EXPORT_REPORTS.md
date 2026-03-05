================================================================
FILE: AGENT_PROMPTS/builders/R4_PDF_EXPORT_REPORTS.md
Builder Agent — PDF Export for All Reports
================================================================

# BUILDER AGENT — R4: PDF Export for All Reports

[CONTEXT]
You are a Builder Agent for the Georgia CPA firm accounting system.
Module assigned: R4 — PDF export for all reports (CPA_OWNER only)
Task ID: TASK-038
Compliance risk level: LOW

This module adds PDF export capability to all three financial
reports (P&L, Balance Sheet, Cash Flow) using WeasyPrint. The PDFs
must be professionally formatted, suitable for delivering to clients.
Only CPA_OWNER can export reports to PDF.

[INSTRUCTION — follow in exact order]

STEP 1: LOAD MEMORY
  Run /init. Read CLAUDE.md in full.
  Read AGENT_LOG.md — confirm this task is not already done.
  Read OPEN_ISSUES.md — check for blockers on this module.
  Read ARCHITECTURE.md — verify all your dependencies are built.

STEP 2: VERIFY DEPENDENCIES
  Depends on: TASK-035 (R1 — P&L), TASK-036 (R2 — Balance Sheet),
              TASK-037 (R3 — Cash Flow)
  Verify all three report services are available.
  If any missing, create typed stubs and log [BLOCKER].

STEP 3: BUILD
  Compliance risk is LOW — write tests alongside implementation.

  Build service at: /backend/services/reports/pdf_export.py
  Build templates at:
  - /backend/templates/reports/profit_loss.html
  - /backend/templates/reports/balance_sheet.html
  - /backend/templates/reports/cash_flow.html
  - /backend/templates/reports/base_report.html (shared layout)
  - /backend/templates/reports/report_styles.css

  Core logic:

  1. Shared report template:
     - Professional header with:
       - Firm name and logo (if configured)
       - Client name
       - Report title
       - Date range or as-of date
       - "Prepared by [firm name]" and date generated
     - Clean table styling with borders and alternating rows
     - Section headers and subtotals
     - Footer with page numbers
     - CSS print media queries for clean PDF output

  2. P&L PDF:
     - export_profit_loss_pdf(client_id, date_from, date_to) -> bytes
     - Call R1 service to get data
     - Render through WeasyPrint template
     - Revenue, COGS, gross profit, expenses, net income sections
     - Optional: comparison layout if two periods specified

  3. Balance Sheet PDF:
     - export_balance_sheet_pdf(client_id, as_of_date) -> bytes
     - Call R2 service to get data
     - Assets, liabilities, equity sections
     - Balance verification note at bottom

  4. Cash Flow PDF:
     - export_cash_flow_pdf(client_id, date_from, date_to) -> bytes
     - Call R3 service to get data
     - Operating, investing, financing sections
     - Net change and cash reconciliation

  5. Save generated PDFs:
     /data/documents/{client_id}/reports/{report_type}_{date_range}.pdf

  API endpoints (extend /backend/api/reports.py):
  - GET /api/clients/{client_id}/reports/profit-loss/pdf
  - GET /api/clients/{client_id}/reports/balance-sheet/pdf
  - GET /api/clients/{client_id}/reports/cash-flow/pdf

  ALL PDF export endpoints: CPA_OWNER only.

STEP 4: ROLE ENFORCEMENT CHECK
  - ALL PDF exports: CPA_OWNER only
  - Write tests proving ASSOCIATE cannot download PDF reports

STEP 5: TEST
  Write tests at: /backend/tests/services/reports/test_pdf_export.py

  Required test cases:
  - test_profit_loss_pdf: valid PDF generated
  - test_balance_sheet_pdf: valid PDF generated
  - test_cash_flow_pdf: valid PDF generated
  - test_pdf_contains_client_name: client name in header
  - test_pdf_contains_date_range: dates in header
  - test_pdf_contains_firm_name: firm name in header
  - test_requires_cpa_owner_pl: ASSOCIATE blocked from P&L PDF
  - test_requires_cpa_owner_bs: ASSOCIATE blocked from BS PDF
  - test_requires_cpa_owner_cf: ASSOCIATE blocked from CF PDF
  - test_pdf_saved_to_disk: file created at expected path
  - test_client_isolation: Client A PDF has only Client A data

[ACCEPTANCE CRITERIA]
- [ ] P&L, Balance Sheet, Cash Flow all export to PDF
- [ ] Professional formatting suitable for client delivery
- [ ] Shared template with firm branding
- [ ] WeasyPrint renders clean, print-quality PDFs
- [ ] PDFs saved to /data/documents/{client_id}/reports/
- [ ] CPA_OWNER only for all PDF exports
- [ ] Client isolation
- [ ] All test cases pass

[OUTPUT FORMAT]
End every session by printing to terminal:

  ================================
  SESSION COMPLETE
  Agent:        R4 — PDF Export for Reports
  Task:         TASK-038
  Files changed: [list each file]
  Tests:        [passed/total]
  Issues opened: [n] — IDs: [list]
  Issues closed: [n] — IDs: [list]
  Next task:    TASK-039 — R5 Firm-Level Dashboard
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
