# Frontend -- React + Vite

Internal dashboard for the Georgia CPA firm. 27 pages covering all workflows. Not client-facing.

## Tech

- React 18.3 + React Router 6
- Vite 6 (build + dev server)
- React Query 5 (`@tanstack/react-query`) for data fetching
- Axios for HTTP
- Vanilla CSS (single file: `src/styles/index.css`)
- Mobile responsive

## Pages (27)

| Page | File | Description |
|------|------|-------------|
| Login | `Login.jsx` | Email/password + TOTP 2FA support |
| Reset Password | `ResetPassword.jsx` | Token-based password reset |
| Dashboard | `Dashboard.jsx` | Firm metrics, revenue chart, due dates, activity feed |
| Clients | `Clients.jsx` | List with filters, pagination, add/edit/archive |
| Client Detail | `ClientDetail.jsx` | Tabs: overview, chart of accounts, journal entries |
| Journal Entry | `JournalEntryForm.jsx` | Dynamic line items, balance validation |
| Approval Queue | `ApprovalQueue.jsx` | Batch approve/reject with rejection notes |
| Accounts Payable | `AccountsPayable.jsx` | Vendors + bills CRUD, payment recording |
| Accounts Receivable | `AccountsReceivable.jsx` | Invoices, approve/pay workflow |
| Bank Reconciliation | `BankReconciliation.jsx` | Import, match, reconcile |
| Documents | `Documents.jsx` | Upload, tag, search, in-browser viewer |
| Employees | `Employees.jsx` | Per-client employee records |
| Payroll | `Payroll.jsx` | Create runs, submit, finalize, pay stub PDF |
| Reports | `Reports.jsx` | P&L, balance sheet, cash flow, CSV/Excel/PDF export |
| Tax Exports | `TaxExports.jsx` | GA/federal forms, W-2, 1099-NEC |
| Audit Trail | `AuditTrail.jsx` | Immutable change history viewer |
| System Admin | `SystemAdmin.jsx` | Health check, backup, user management |
| Time Tracking | `TimeTracking.jsx` | Billable hours entry |
| Service Billing | `ServiceBilling.jsx` | Firm invoices to clients |
| Engagements | `Engagements.jsx` | Engagement management |
| Contacts | `Contacts.jsx` | Client contact records |
| Workflows | `Workflows.jsx` | Task/workflow Kanban |
| Client Portal | `ClientPortal.jsx` | Portal message management |
| Fixed Assets | `FixedAssets.jsx` | Asset tracking, depreciation |
| Budgets | `Budgets.jsx` | Budget creation and tracking |
| Firm Analytics | `FirmAnalytics.jsx` | Cross-client metrics and trends |
| Due Dates | `DueDates.jsx` | Upcoming deadlines |

## Components (11 shared)

| Component | Purpose |
|-----------|---------|
| `Layout.jsx` | App shell: sidebar nav, header, global search (Cmd+K), hamburger menu |
| `DataTable.jsx` | Sortable, filterable table with pagination |
| `Modal.jsx` | Dialog overlay |
| `FormField.jsx` | Labeled input with validation |
| `Tabs.jsx` | Tab container |
| `Toast.jsx` | Notification toasts |
| `StatusBadge.jsx` | Colored status pill |
| `ConfirmDialog.jsx` | Confirmation modal |
| `ProtectedRoute.jsx` | Auth gate (redirects to login) |
| `RoleGate.jsx` | Role-based UI visibility |
| `ClientSelector.jsx` | Client dropdown picker |

## Hooks

| Hook | Purpose |
|------|---------|
| `useAuth.js` | AuthContext: login, logout, current user, role checks |
| `useApiQuery.js` | React Query wrapper with auth error handling |
| `useApi.js` | Axios instance with cookie auth + mutation helpers |
| `useToast.js` | Toast notification state |
| `useUnsavedChanges.js` | Warns before navigating away from dirty forms |

## Commands

```bash
npm install          # Install dependencies
npm run dev          # Dev server (http://localhost:5173, proxies to backend)
npm run build        # Production build (output: dist/)
npm run preview      # Preview production build locally
```

## Environment

| File | `VITE_API_BASE` | Notes |
|------|-----------------|-------|
| `.env.development` | *(empty)* | Vite proxy forwards `/api` to `localhost:8000` |
| `.env.production` | *(empty)* | nginx reverse proxy serves API on same origin |

## Key Patterns

- **Auth**: `AuthContext` provides `user`, `login()`, `logout()`, `isOwner`. Set synchronously on login (no race condition).
- **Data fetching**: All API calls go through `useApiQuery` (GET) and `useApiMutation` (POST/PUT/DELETE), which wrap React Query with automatic error handling and toast notifications.
- **Formatting**: `src/utils/format.js` has `formatCurrency`, `formatDate`, `formatEntityType` used across all pages.
- **Routing**: React Router 6 with `ProtectedRoute` wrapper. All routes defined in `App.jsx`.
- **Styles**: Single CSS file (`src/styles/index.css`). No CSS modules or styled-components. Mobile breakpoints at 768px and 480px.
- **Role gating**: `RoleGate` component hides UI elements from ASSOCIATE users. Backend enforces the same rules independently.
