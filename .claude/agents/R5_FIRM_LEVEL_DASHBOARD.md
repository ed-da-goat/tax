================================================================
FILE: AGENT_PROMPTS/builders/R5_FIRM_LEVEL_DASHBOARD.md
Builder Agent — Firm-Level Dashboard
================================================================

# BUILDER AGENT — R5: Firm-Level Dashboard

[CONTEXT]
You are a Builder Agent for the Georgia CPA firm accounting system.
Module assigned: R5 — Firm-level dashboard (all clients, key metrics)
Task ID: TASK-039
Compliance risk level: LOW

This is the main landing page for the application. It shows a
summary view of all clients with key financial metrics, upcoming
deadlines, and system status. This is a React frontend component
backed by an API endpoint that aggregates data across all clients.

[INSTRUCTION — follow in exact order]

STEP 1: LOAD MEMORY
  Run /init. Read CLAUDE.md in full.
  Read AGENT_LOG.md — confirm this task is not already done.
  Read OPEN_ISSUES.md — check for blockers on this module.
  Read ARCHITECTURE.md — verify all your dependencies are built.

STEP 2: VERIFY DEPENDENCIES
  Depends on: TASK-035 (R1 — P&L), TASK-036 (R2 — Balance Sheet),
              TASK-011 (F4 — Client Management)
  Verify report services and client list are available.
  If any missing, create typed stubs and log [BLOCKER].

STEP 3: BUILD
  Compliance risk is LOW — write tests alongside implementation.

  Build service at: /backend/services/reports/dashboard.py
  Build API at: /backend/api/dashboard.py
  Build React components at:
  - /frontend/src/components/Dashboard.jsx (main)
  - /frontend/src/components/dashboard/ClientSummaryCard.jsx
  - /frontend/src/components/dashboard/MetricCard.jsx
  - /frontend/src/components/dashboard/DeadlineWidget.jsx

  Core logic:

  1. Firm-wide metrics:
     - get_firm_dashboard() -> FirmDashboard
       Aggregate across all active clients:
       a) Total clients (active count)
       b) Total revenue (all clients, current month/quarter/year)
       c) Total expenses (all clients, current period)
       d) Total outstanding AR (all clients)
       e) Total outstanding AP (all clients)
       f) Clients by entity type (count per type)

  2. Per-client summary:
     - get_client_summaries() -> list[ClientSummary]
       For each active client:
       - client_name, entity_type
       - Current month revenue
       - Current month expenses
       - Outstanding AR balance
       - Outstanding AP balance
       - Last payroll date (if applicable)
       - Next tax deadline

  3. Upcoming deadlines:
     - get_upcoming_deadlines(days_ahead=30) -> list[Deadline]
       Pull from tax checklist (X9) and payroll schedule:
       - Form type and description
       - Client name
       - Due date
       - Status (not started, in progress, filed)
       - Days until due (color: red if < 7, yellow if < 14, green)

  4. System alerts:
     - Payroll runs pending approval
     - Transactions pending approval
     - Documents pending review
     - Tax forms overdue or approaching deadline
     - Backup status (last backup age)

  5. React dashboard layout:
     - Top row: MetricCards (total revenue, expenses, AR, AP)
     - Client list: sortable/filterable table with ClientSummaryCards
     - Right sidebar: DeadlineWidget showing upcoming deadlines
     - Bottom: system alerts and pending items
     - Responsive design for different screen sizes

  API endpoints:
  - GET /api/dashboard — firm-wide dashboard data
  - GET /api/dashboard/clients — per-client summaries
  - GET /api/dashboard/deadlines — upcoming deadlines
  - GET /api/dashboard/alerts — system alerts

  Both roles can view the dashboard.

STEP 4: ROLE ENFORCEMENT CHECK
  Dashboard viewing: both roles.
  No special role enforcement needed.

STEP 5: TEST
  Write tests at: /backend/tests/services/reports/test_dashboard.py

  Required test cases:
  - test_total_client_count: correct active client count
  - test_total_revenue_aggregation: all clients' revenue summed
  - test_total_ar_balance: outstanding AR across clients
  - test_per_client_summary: individual client metrics correct
  - test_upcoming_deadlines: deadlines within window returned
  - test_overdue_deadlines_flagged: past-due items highlighted
  - test_system_alerts: pending approvals counted
  - test_entity_type_breakdown: correct count per type
  - test_archived_clients_excluded: archived not in dashboard
  - test_empty_dashboard: no clients produces empty metrics, not error

  React component tests at:
  /frontend/src/components/__tests__/Dashboard.test.jsx
  - test_metric_cards_render: four metric cards displayed
  - test_client_table_sortable: can sort by revenue, name, etc.
  - test_deadline_color_coding: red/yellow/green applied correctly

[ACCEPTANCE CRITERIA]
- [ ] Firm-wide metrics aggregated across all clients
- [ ] Per-client summary with key financial metrics
- [ ] Upcoming deadlines with color-coded urgency
- [ ] System alerts for pending items
- [ ] Both roles can view
- [ ] Archived clients excluded
- [ ] React components with responsive layout
- [ ] All test cases pass

[OUTPUT FORMAT]
End every session by printing to terminal:

  ================================
  SESSION COMPLETE
  Agent:        R5 — Firm-Level Dashboard
  Task:         TASK-039
  Files changed: [list each file]
  Tests:        [passed/total]
  Issues opened: [n] — IDs: [list]
  Issues closed: [n] — IDs: [list]
  Next task:    TASK-040 — O1 Audit Trail Viewer
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
