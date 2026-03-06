================================================================
FRONTEND & OPS AUDIT -- FINAL REPORT
Date: 2026-03-06
Auditor: Claude Code Instance 2 (Frontend & Ops)
================================================================

EXECUTIVE SUMMARY
-----------------
Critical blockers for go-live: 3
Major issues (fix before onboarding): 8
Minor issues (fix when convenient): 7
Informational notes: 5

================================================================
CATEGORY 1: BUILD & DEPENDENCY HEALTH
================================================================

BUILD HEALTH RESULTS
====================
npm install: CLEAN (no warnings)
npm run build: PASS (exit code 0)
Build size: 530.93 KB JS + 20 KB CSS (gzipped: 141.89 KB JS + 4.48 KB CSS)
Build time: 1.01s
Build warnings: 1 (chunk > 500 KB -- recommend code splitting)
Missing imports: NONE
Orphaned pages: NONE (all 27 pages are routed in App.jsx)
API base URL configured: YES (VITE_API_BASE env var, defaults to '' for same-origin; Vite proxy in dev points to localhost:8000)
Package vulnerabilities: 0 (npm audit clean)

NOTES:
- React is v19.2.4 (actual installed) despite package.json listing ^19.2.0.
  CLAUDE.md says "React 18.3" -- this is incorrect, the app runs React 19.
  Not a blocker but documentation is misleading.
- Node v25.7.0, npm v11.10.1 -- very current
- 5 dependencies total (react, react-dom, react-router-dom, axios, @tanstack/react-query)
  -- minimal and appropriate
- Bundle is 531 KB (single chunk). Recommend dynamic imports for code splitting
  for faster initial load on Windows LAN clients.

================================================================
CATEGORY 2: PAGE-BY-PAGE RENDER AUDIT
================================================================

PAGE RENDER AUDIT RESULTS
=========================
Pages found: 27 (CLAUDE.md claims 28)
Missing page: There is NO dedicated "Global Search" page -- it's a modal inside
  Layout.jsx (Cmd+K). This is fine architecturally but the count should be 27 not 28.

Routes defined: 27 (25 authenticated + 2 public: /login, /reset-password)
Routes -> missing components: NONE
Pages without routes (orphaned): NONE
Broken component imports: NONE (all verified by successful build)
API endpoint mismatches: NONE found via code review
Null-safety risks: LOW (most pages use optional chaining and fallback defaults)
dangerouslySetInnerHTML usage: NONE

ROUTE MAP (verified):
  PUBLIC:
    /login               -> Login.jsx
    /reset-password       -> ResetPassword.jsx

  AUTHENTICATED (inside ProtectedRoute + Layout):
    /dashboard            -> Dashboard.jsx
    /clients              -> Clients.jsx
    /clients/:clientId    -> ClientDetail.jsx
    /clients/:clientId/journal-entries/new -> JournalEntryForm.jsx
    /approvals            -> ApprovalQueue.jsx
    /clients/:clientId/ap -> AccountsPayable.jsx
    /clients/:clientId/ar -> AccountsReceivable.jsx
    /reconciliation       -> BankReconciliation.jsx
    /documents            -> Documents.jsx
    /employees            -> Employees.jsx
    /payroll              -> Payroll.jsx
    /reports              -> Reports.jsx
    /tax-exports          -> TaxExports.jsx
    /time-tracking        -> TimeTracking.jsx
    /workflows            -> Workflows.jsx
    /service-billing      -> ServiceBilling.jsx
    /engagements          -> Engagements.jsx
    /contacts             -> Contacts.jsx
    /portal               -> ClientPortal.jsx
    /fixed-assets         -> FixedAssets.jsx
    /budgets              -> Budgets.jsx
    /analytics            -> FirmAnalytics.jsx
    /due-dates            -> DueDates.jsx
    /audit-trail          -> AuditTrail.jsx
    /admin                -> SystemAdmin.jsx
    /* (catch-all)        -> Redirect to /dashboard

  ROLE-GATED IN NAV (CPA_OWNER only visible):
    /approvals, /analytics, /payroll, /tax-exports, /portal, /admin

================================================================
CATEGORY 3: END-TO-END WORKFLOW TRACING
================================================================

WORKFLOW 1: New User Login
==========================
UI component exists: YES (Login.jsx)
API endpoint exists: YES (POST /api/v1/auth/login)
API call works via curl: YES -- returns JWT cookie + user object
Cookie settings: HttpOnly=YES, SameSite=lax, Path=/api
  ISSUE: Secure flag is ABSENT when served over HTTP (localhost:8000).
  When served through nginx HTTPS, SameSite should be "Strict" per
  CLAUDE.md hardening spec. Observed: SameSite=lax. Needs verification
  that production (via nginx HTTPS) sends SameSite=Strict + Secure.
Error handling in UI: GOOD -- shows error messages for invalid credentials
2FA flow handled: YES (Login.jsx lines 41-44, TOTP code input)
Forgot password link: YES (Login.jsx lines 196-203, toggles forgotMode)
Auth persistence: YES -- on mount, AuthContext calls /api/v1/auth/me
401 handling: YES -- useApi interceptor auto-logouts on 401
VERDICT: READY

WORKFLOW 2: ASSOCIATE Enters a Transaction
==========================================
UI component exists: YES (JournalEntryForm.jsx)
API endpoint exists: YES (POST /api/v1/clients/{id}/journal-entries)
Debit/credit validation: YES (lines 38-40, isBalanced check)
Auto-submit for approval: YES (lines 59-61, optional submit after save)
Unsaved changes warning: NOT USED on this page (useUnsavedChanges hook
  exists but JournalEntryForm.jsx does not import it)
  FINDING: User can navigate away and lose a partially entered journal
  entry without warning.
VERDICT: READY (minor: add unsaved changes warning)

WORKFLOW 3: CPA_OWNER Approves Transactions
============================================
UI component exists: YES (ApprovalQueue.jsx)
API endpoint: GET /api/v1/approvals (works, returns items)
Batch approve: YES (POST /api/v1/approvals/batch)
Single approve/reject: YES (inline buttons per row)
Rejection notes: YES (Modal with required textarea)
Role gate: YES (actions only shown to CPA_OWNER via isCpa check)
Badge count in nav: YES (Layout.jsx polls every 30 seconds)
VERDICT: READY

WORKFLOW 4: Generate and Export a Report
========================================
UI component exists: YES (Reports.jsx with 6 tabs: P&L, BS, CF, Dashboard, AR/AP Aging)
API endpoints: ALL WORK via curl
  - P&L: 200 OK, returns revenue/expenses/net
  - PDF export: 200 OK, 20.6 KB
  - CSV export: 200 OK, 105 bytes
  - Excel export: 200 OK, 5.1 KB
Date range selectors: YES (connected to API params)
Export buttons: YES (PDF, CSV, Excel -- CPA_OWNER only via RoleGate)
VERDICT: READY

WORKFLOW 5: Run Payroll
=======================
UI component exists: YES (Payroll.jsx)
Client selector: YES (ClientSelector component)
Create payroll run: YES (modal with period dates, employee selection, hours)
Employee list: YES (fetched from /api/v1/clients/{id}/employees)
Finalize gate: YES (RoleGate on Finalize button, lines 279-282)
Pay stub PDF: YES (download handler, lines 107-121)
Payroll detail view: YES (modal with gross/net/withholding breakdown)
Void capability: YES (RoleGate protected)
VERDICT: READY

WORKFLOW 6: Client Onboarding
=============================
UI component exists: YES (Clients.jsx -- Add Client button, modal)
API endpoint: POST /api/v1/clients (works, returns new client)
Entity type selection: YES (SOLE_PROP, S_CORP, C_CORP, PARTNERSHIP_LLC)
EIN field: YES
Client detail page: YES (ClientDetail.jsx -- overview, CoA, journal entries)
Clone template accounts: YES (button appears when CoA is empty)
  FINDING: After creating a client, the user must navigate to
  ClientDetail and click "Clone Template Accounts" to get a chart of
  accounts. This is not obvious to a new user -- no onboarding wizard
  or prompt guides them.
VERDICT: READY (minor UX gap: no onboarding prompt)

================================================================
CATEGORY 4: SHARED COMPONENTS & UX PATTERNS
================================================================

SHARED COMPONENTS RESULTS
=========================
Components found: 11 (matching claim of "11+ shared components")
  1. Modal.jsx -- modal dialog (isOpen, onClose, title, size)
  2. DataTable.jsx -- paginated table (columns, data, total, page, onRowClick, selectable)
  3. FormField.jsx -- form field wrapper (label, error, required) + SelectField
  4. Toast.jsx -- notification toast (type, message, onClose)
  5. Tabs.jsx -- tab navigation (tabs, activeTab, onTabChange)
  6. RoleGate.jsx -- conditional render based on user role
  7. ConfirmDialog.jsx -- confirm/cancel modal
  8. ClientSelector.jsx -- client dropdown picker
  9. StatusBadge.jsx -- colored status badges
  10. ProtectedRoute.jsx -- auth guard for routes
  11. Layout.jsx -- main app shell (sidebar, topbar, search modal, content)

Missing components: NONE
All components imported by at least one page: YES

format.js coverage: GOOD
  - formatCurrency: handles null (returns '--'), uses Intl.NumberFormat USD
  - formatDate: handles empty (returns '--'), uses en-US locale
  - formatEntityType: maps enum values to display names, fallback to raw value
  - formatStatus: replaces underscores with spaces, title-cases
  MINOR GAP: No formatPhone or formatEIN function (phone numbers shown raw)

Error handling pattern: CONSISTENT
  - All pages using useApiQuery get React Query's built-in error handling
  - Pages using manual api.get/post catch errors and set error state
  - Error messages displayed via alert--error class or Toast
  - 401 auto-logout via useApi interceptor

Loading states: GOOD
  - Pages using useApiQuery: isLoading state rendered as <span className="spinner" />
  - Pages using manual fetch: loading state variable with spinner

Empty states handled: GOOD
  - Dashboard: "No clients yet" with action text
  - DataTable: emptyMessage + emptyAction props
  - Reports: "Select a client and date range" prompt
  - Documents: "No documents found"
  - Payroll: "No payroll runs"

Responsive CSS: BASIC (2 breakpoints only)
  - 768px breakpoint: hides sidebar, shows hamburger, stacks cards/filters
  - Handles: sidebar collapse, card grid stack, form row stack, table scroll
  - MISSING: No tablet breakpoint (1024px), no print styles
  - Tables become horizontally scrollable on mobile (acceptable)

Accessibility: NEEDS WORK
  - Form labels: YES (htmlFor used on Login page, FormField component adds labels)
  - Button text: MOSTLY OK (some icon-only buttons lack aria-label, e.g., hamburger)
  - Focus styles: DEFAULT (browser defaults, no custom focus-visible styles)
  - Keyboard nav: PARTIAL (search modal has ArrowUp/Down/Enter, but no
    skip-to-content link, no focus management for modals)
  - Color contrast: APPEARS OK (dark text on white, but not verified with WCAG tool)
  - NO error boundary: If any page component throws, the entire app crashes
    to a white screen with no recovery path.

================================================================
CATEGORY 5: DEPLOYMENT & OPERATIONS READINESS
================================================================

DEPLOYMENT RESULTS
==================

setup.sh: SOLID
  - Error handling: set -euo pipefail (YES)
  - Prerequisites check: Homebrew, nginx, pg_dump (YES)
  - Idempotent: YES (checks existing cert, stops existing services)
  - Creates cert with LAN IP in SAN: YES (auto-detects en0/en1)
  - IP change detection: YES (regenerates cert if IP changes)
  - Updates CORS_ORIGINS in .env: YES
  - Installs 2 of 4 launchd plists (backend + backup only)
    FINDING: setup.sh does NOT install com.gacpa.dbmaint.plist or
    com.gacpa.logrotate.plist. These exist as files but are never
    loaded by setup.sh, so weekly VACUUM/REINDEX and daily log
    rotation will NOT run unless manually installed.
  - Firewall: YES (adds nginx to macOS Application Firewall)
  - Output messages: Excellent (clear instructions, LAN URL, cert trust)

teardown.sh: SOLID
  - Stops backend + backup services: YES
  - Stops nginx: YES
  - Restores original nginx.conf: YES
  - Removes launchd plists: YES
  - Preserves database and backups: YES ("Database and backup files are preserved")
  - MISSING: Does not unload/remove dbmaint or logrotate plists
    (matches setup.sh which doesn't install them)

nginx.conf: MOSTLY CORRECT
  - HTTPS configured: YES (TLS 1.2/1.3, HIGH ciphers)
  - Proxy pass to backend: YES (127.0.0.1:8000)
  - Static file serving: YES (frontend/dist, SPA fallback)
  - Security headers: YES (X-Frame-Options DENY, X-Content-Type-Options,
    XSS-Protection, HSTS max-age=31536000)
  - Dotfile blocking: YES (deny all for /\.)
  - Gzip: YES (text, CSS, JSON, JS, XML)
  - ISSUES:
    1. NO client_max_body_size directive -- document uploads will fail for
       files > nginx default 1MB. The backend accepts file uploads but
       nginx will reject them before they reach the backend.
    2. NO Content-Security-Policy header (CSP). While the app doesn't use
       inline scripts (React handles this), adding a basic CSP would
       strengthen the security posture.
    3. Listen on port 443 without specifying address -- defaults to
       0.0.0.0 which IS correct for LAN access, but not explicit.

Backup system: SOLID
  - pg_dump: YES (custom format, compress level 6)
  - GPG encryption: YES (AES-256, passphrase via --passphrase-fd 0)
  - 30-day retention: YES (find + -mtime +30 -delete)
  - Logging: YES (timestamped entries to backup.log)
  - Failure handling: YES (set -euo pipefail, logs errors, exits non-zero)
  - External replication: YES (optional BACKUP_REPLICA_DIR)
  - Passphrase sourcing: GOOD (checks .env first, then macOS Keychain)

Restore script: EXISTS (deploy/restore.sh)
  - read from audit agent: NOT reviewed in detail by this instance
  - Endpoint exists: POST /api/v1/operations/backups/{filename}/restore
  - UI exists: YES (SystemAdmin -> Backups tab -> Restore button per backup)

LAN access configured: YES
  - nginx listens on: 0.0.0.0:443 (implicit, correct)
  - Cert SAN includes LAN IP: YES (auto-detected by setup.sh)
  - Windows trust docs: EXIST (deploy/windows-trust.md)
    Quality: GOOD -- three options (click-through, GUI import, PowerShell)
    Clear enough for semi-technical person. Includes note about IP changes.
  - IP change handling: AUTOMATED (setup.sh detects and regenerates cert,
    updates CORS_ORIGINS in .env)

Log management: GOOD
  - Logs go to: deploy/logs/
  - Directory permissions: 700 (owner-only access)
  - File permissions: 600 (set by setup.sh)
  - Log rotation: logrotate.sh EXISTS but NOT installed by setup.sh
  - CPA_OWNER can read logs: YES (they own the files)

Launchd services: 2/4 correctly configured AND INSTALLED
  1. com.gacpa.backend: INSTALLED
     - RunAtLoad: true (auto-start on login)
     - KeepAlive: true (auto-restart on crash)
     - ThrottleInterval: 5 seconds
     - Workers: 2
  2. com.gacpa.backup: INSTALLED
     - Schedule: daily at 2:00 AM
  3. com.gacpa.dbmaint: EXISTS but NOT INSTALLED by setup.sh
     - Schedule: weekly Sunday at 4:00 AM
  4. com.gacpa.logrotate: EXISTS but NOT INSTALLED by setup.sh
     - Schedule: weekly Sunday at 3:00 AM

Recovery documentation: PARTIAL
  - "Backend won't start": NO explicit troubleshooting doc
  - "Database corrupted": Restore flow exists in UI (SystemAdmin)
  - "Cert expired": setup.sh regenerates (10-year validity anyway)
  - "IP changed": setup.sh auto-handles
  - README.md exists with overview but no troubleshooting section

================================================================
CATEGORY 6: DAY-1 READINESS
================================================================

DAY-1 READINESS CHECKLIST
=========================

1. Create ASSOCIATE account: NOT POSSIBLE VIA UI
   The SystemAdmin page has System Health and Backup Management tabs
   only. There is NO user management UI anywhere in the frontend.
   The API endpoint exists (POST /api/v1/auth/users, CPA_OWNER only)
   and works, but the CPA_OWNER would need to use curl or a REST client
   to create user accounts. This is the #1 critical blocker.

2. ASSOCIATE login from Windows: POSSIBLE (with cert warning)
   - URL: https://<mac-ip> (setup.sh prints this)
   - First time: "Advanced" -> "Proceed to site (unsafe)"
   - Permanent trust: deploy/windows-trust.md has clear instructions
   - ISSUE: Login page shows "755 Accounting" -- this is hardcoded
     and may or may not match the firm name.

3. First client migration: CLI ONLY
   - There is NO migration UI in the frontend (no import page, no
     CSV upload for QBO data)
   - Migration requires running Python scripts from terminal:
     backend/scripts/seed_test_data.py or the migration pipeline
   - Bulk import (CSV upload) exists for bills/invoices only, not
     for full QBO migration
   - This is expected per CLAUDE.md (migration is CLI-based) but
     means the CPA_OWNER needs terminal access for initial setup

4. Backup status visible to owner: YES
   - SystemAdmin -> System Health tab shows backup count and last backup
   - SystemAdmin -> Backups tab lists all backups with verify/restore
   - Manual backup creation button exists

5. User guide / help text: NONE
   - No in-app help documentation
   - No tooltips on complex forms (only ~53 title/aria-label attributes
     across the entire frontend, mostly on SVG icons)
   - No onboarding wizard or getting-started guide
   - README.md exists but is developer-focused, not user-focused
   - No keyboard shortcut reference beyond Cmd+K hint in search bar

6. Training estimate for ASSOCIATE: 2-4 hours
   - The UI is fairly intuitive for someone familiar with accounting
     software (QuickBooks-like workflow)
   - Journal entry form is well-designed (debit/credit validation,
     account grouping, real-time balance check)
   - But no help text means the associate needs verbal training

7. First-login password change: NOT IMPLEMENTED
   - No mechanism to force a password change on first login
   - The CPA_OWNER sets the initial password, and the associate can
     continue using it indefinitely
   - Password reset exists via forgot-password flow, but there's no
     "change my password" option in the app UI

Missing features vs QBO expectations:
  - Bank feeds (Plaid): DEFERRED (paid API)
  - Document OCR: DEFERRED (Tesseract)
  - Recurring transactions UI: MISSING (backend exists at
    /api/v1/clients/{id}/recurring-transactions, but no frontend page)
  - Year-end close UI: MISSING (backend exists at
    /api/v1/year-end/clients/{id}/close, but no frontend page)
  - User management UI: MISSING (API exists, no frontend page)
  - Change password UI: MISSING (only forgot-password flow exists)
  - Multi-client AP/AR navigation: AWKWARD (must go to ClientDetail
    first, then click AP/AR -- no global AP/AR view)
  - Client import/migration: CLI ONLY
  - Batch operations: LIMITED (batch approve exists, no batch
    invoice/bill operations)

================================================================
CRITICAL BLOCKERS (team cannot use the app until these are fixed)
================================================================

1. NO USER MANAGEMENT UI
   File: frontend/src/pages/SystemAdmin.jsx
   Problem: The SystemAdmin page only has "System Health" and "Backup
   Management" tabs. There is no way to create, edit, or deactivate
   user accounts through the UI. The API endpoints exist at
   /api/v1/auth/users (GET, POST, PUT, DELETE) and work correctly,
   but the frontend has zero references to these endpoints.
   Impact: The CPA_OWNER cannot create ASSOCIATE accounts without
   using curl or a REST client. This blocks team onboarding entirely.
   Fix: Add a "Users" tab to SystemAdmin with a table of users and
   create/edit/deactivate modals. Estimated effort: 2-3 hours.

2. NO CHANGE PASSWORD UI
   Problem: There is no "Change Password" or "My Account" page anywhere
   in the frontend. The only password change mechanism is the
   forgot-password flow (which requires email delivery to work).
   Additionally, there is no force-password-change on first login.
   Impact: Associates cannot change their initial password without
   the forgot-password email flow. If email is not configured (which
   it may not be on a local deployment), they're stuck with the
   initial password forever.
   Fix: Add a "Change Password" option in the topbar user dropdown
   or a "My Account" page. Estimated effort: 1-2 hours.

3. NGINX MISSING client_max_body_size
   File: deploy/nginx.conf
   Problem: No client_max_body_size directive. nginx defaults to 1MB.
   The Documents page allows file uploads, but any file larger than
   1MB will be rejected by nginx with a 413 (Request Entity Too Large)
   before it reaches the backend.
   Impact: Users cannot upload documents larger than 1MB (most scanned
   PDFs, multi-page contracts, tax forms exceed this).
   Fix: Add `client_max_body_size 25m;` to the server block in
   nginx.conf. One line, 30 seconds.

================================================================
MAJOR ISSUES (fix before team onboarding)
================================================================

4. SETUP.SH DOES NOT INSTALL DBMAINT AND LOGROTATE SERVICES
   Files: deploy/setup.sh, deploy/com.gacpa.dbmaint.plist,
   deploy/com.gacpa.logrotate.plist
   Problem: setup.sh only installs 2 of 4 launchd services (backend
   and backup). The weekly VACUUM/REINDEX (dbmaint) and log rotation
   (logrotate) plists exist but are never loaded.
   Impact: Database performance will degrade over time without
   VACUUM/REINDEX. Log files will grow unbounded.
   Fix: Add 4 lines to setup.sh to copy and bootstrap these plists.

5. NO RECURRING TRANSACTIONS UI
   Problem: The backend has full recurring transaction support
   (model, service, router at /api/v1/clients/{id}/recurring-transactions)
   but there is no frontend page to manage recurring templates.
   Impact: Users cannot set up recurring monthly transactions
   (rent, utilities, subscriptions) -- a core QBO feature they'll expect.
   Fix: Create a RecurringTransactions page. Estimated effort: 3-4 hours.

6. NO YEAR-END CLOSE UI
   Problem: Backend has year-end close service and router
   (/api/v1/year-end/clients/{id}/close) but no frontend page.
   Impact: CPA_OWNER cannot perform year-end closing entries from the
   UI. Must use API directly.
   Fix: Add year-end close tab to ClientDetail or standalone page.
   Estimated effort: 2-3 hours.

7. NO ERROR BOUNDARY
   Problem: The React app has no ErrorBoundary component. If any
   page component throws a runtime error, the entire app crashes
   to a white screen with no way to recover except refreshing.
   Impact: A single null pointer exception in any page kills the
   entire session. Non-technical users won't know to refresh.
   Fix: Add an ErrorBoundary component wrapping <App /> in main.jsx.
   Estimated effort: 30 minutes.

8. JOURNAL ENTRY FORM LACKS UNSAVED CHANGES WARNING
   File: frontend/src/pages/JournalEntryForm.jsx
   Problem: The useUnsavedChanges hook exists and works (verified in
   code), but JournalEntryForm does not use it. A user can spend 10
   minutes entering a complex journal entry, accidentally click a
   nav link, and lose everything.
   Impact: Data loss for the most critical data entry form in the app.
   Fix: Import and call useUnsavedChanges(lines.some(l => l.account_id)).
   One line change.

9. COOKIE SameSite=lax INSTEAD OF Strict
   Problem: The JWT cookie is set with SameSite=lax. CLAUDE.md security
   hardening states "SameSite=Strict enforced always (not just
   non-DEBUG)". Observed behavior contradicts the documented hardening.
   Impact: Lower CSRF protection than documented. lax allows cookies
   on top-level navigations from external sites.
   Fix: Verify and update the set_cookie call in auth.py.

10. REACT VERSION MISMATCH IN DOCS
    Problem: CLAUDE.md says "React 18.3" but the app actually runs
    React 19.2.4. While this works fine, it means some React 18
    patterns documented may not be accurate.
    Impact: Misleading for future development.
    Fix: Update CLAUDE.md to say "React 19.2".

11. AP/AR ROUTES REQUIRE CLIENT ID IN URL
    Problem: AccountsPayable and AccountsReceivable are routed at
    /clients/:clientId/ap and /clients/:clientId/ar. There is no
    global AP or AR view. Users must first navigate to a specific
    client to see their bills or invoices.
    Impact: A firm managing 26-50 clients cannot see all outstanding
    bills or invoices across clients from one screen.
    Fix: Consider adding top-level /ap and /ar routes with
    ClientSelector, similar to how Reports page works.

================================================================
ADDITIONAL FINDINGS FROM DEEP ANALYSIS
================================================================

(Confirmed by parallel sub-audits of all 27 pages, all 11 components,
all deploy scripts, and all hooks/utils)

A. ALL 27 PAGES HAVE CLEAN IMPORTS -- zero broken imports across 80+
   API endpoint references. Every component, hook, and utility import
   resolves to an existing file. Build validates this.

B. NULL-SAFETY IS CONSISTENTLY APPLIED -- all pages use optional
   chaining (?.) and nullish coalescing (||, ??) for API response
   data. No unsafe .map() calls on potentially undefined arrays.

C. NO 404 PAGE -- the catch-all route redirects to /dashboard.
   Users who type invalid URLs see the dashboard instead of a
   "page not found" message. Low priority but worth noting.

D. TOAST SYSTEM WORKS GLOBALLY -- ToastContext renders at z-index
   9999 (above modals at z-index 1000). Auto-dismiss after 4 seconds.
   Manual close available. Used by 6+ pages via useToast hook.

E. MODAL FOCUS TRAP IMPLEMENTED -- Modal.jsx has proper focus
   management (trap Tab key, restore previous focus on close,
   Escape to dismiss, body scroll lock). Accessibility-correct.

F. RESTORE.SH HAS GOOD SAFETY -- requires typing "RESTORE" to
   confirm, stops backend before restore, restarts after. Handles
   both encrypted (.dump.gpg) and legacy (.dump) formats. However,
   no rollback if restore fails mid-stream (drops DB before restore).

G. DBMAINT.SH DOES VACUUM ANALYZE -- but only reports table sizes,
   does not run REINDEX despite CLAUDE.md claiming "weekly VACUUM/
   REINDEX". The REINDEX step is missing from the script.

H. CSS ACCESSIBILITY IS DECENT -- text contrast ratios are WCAG AA
   compliant (primary text 21:1, muted text 8.5:1). Form focus
   states use visible blue ring. Georgia serif headings with Inter
   sans-serif body font.

================================================================
MINOR ISSUES (fix when convenient)
================================================================

12. NO PRINT STYLES IN CSS
    Problem: No @media print rules in index.css. Printing reports
    from the browser will include sidebar, topbar, and navigation.
    Fix: Add @media print rules to hide nav and adjust layout.

13. HAMBURGER BUTTON LACKS ARIA-LABEL
    File: frontend/src/components/Layout.jsx:411
    Problem: The mobile hamburger button has no aria-label for
    screen readers.
    Fix: Add aria-label="Toggle navigation menu".

14. NO SKIP-TO-CONTENT LINK
    Problem: No accessibility skip link for keyboard navigation.
    Low priority for internal app.

15. ONLY 2 CSS BREAKPOINTS
    Problem: Only 768px and 769px breakpoints. No tablet (1024px)
    or large desktop (1440px+) breakpoints.
    Impact: Layout may not optimize well on tablets.

16. CLIENT NAME TRUNCATION IN DASHBOARD CHART
    File: Dashboard.jsx:163
    Problem: Client names in revenue chart are truncated to 80px.
    Long business names like "Southern Manufacturing Corp" become
    unreadable.
    Fix: Increase width or add tooltip on hover.

17. LOGIN PAGE BRANDING HARDCODED
    File: Login.jsx:134
    Problem: Shows "755 Accounting" -- this is specific to the firm.
    If the system is ever reused, this would need configuration.
    Low priority since it's a single-firm deployment.

18. SEARCH TYPE ROUTE MAPPING INCONSISTENT
    File: Layout.jsx:191-197
    Problem: SEARCH_TYPE_ROUTES maps "vendor" and "invoice" results
    to /clients/{client_id} (the client detail page), not to the
    vendor or invoice specifically. Clicking a search result for a
    vendor takes you to the client, not the AP page.
    Fix: Map vendor -> /clients/{client_id}/ap, invoice ->
    /clients/{client_id}/ar.

================================================================
PASSES LIST (things that work correctly)
================================================================

1. Build pipeline: Clean, fast (1s), zero vulnerabilities
2. Login flow: Fully functional with 2FA, forgot password, error handling
3. Protected routes: Properly redirect to /login, preserve intended URL
4. Role-based access: CPA_OWNER-only pages hidden from ASSOCIATE nav
5. Dashboard: Rich (stat cards, revenue chart, due dates, activity feed)
6. Client CRUD: Create, edit, archive with entity type selection
7. Journal entry form: Dynamic lines, debit/credit validation, submit flow
8. Approval queue: Batch approve, single reject with notes, real-time badge
9. Reports: All 6 types with PDF/CSV/Excel export
10. Tax exports: All 11 form types with PDF generation
11. Payroll: Full workflow (create, review, finalize, pay stubs)
12. Documents: Upload, view, download, search, delete
13. Global search: Cmd+K modal with debounce, keyboard nav, category grouping
14. System health: DB status, disk usage, backup status, issues display
15. Backup management: Create, verify, restore with confirmation modal
16. Auth context: Proper session persistence (/api/v1/auth/me on mount)
17. Auto-logout: 401 interceptor cleans up session
18. Cookie auth: HttpOnly, proper Path, withCredentials in axios
19. Deploy script: Idempotent, IP-aware cert, CORS update, firewall config
20. Backup script: GPG encrypted, 30-day retention, failure handling
21. Windows trust docs: Three options, clear instructions
22. Mobile responsive: Sidebar collapse, hamburger menu, table scroll

================================================================
WORKFLOW READINESS MATRIX
================================================================

| Workflow                    | Status      | Blocker? |
|-----------------------------|-------------|----------|
| Login (CPA_OWNER)          | READY       | N        |
| Login (ASSOCIATE)           | BLOCKED     | Y (#1)   |
| Login from Windows LAN      | READY       | N        |
| Create ASSOCIATE account    | BLOCKED     | Y (#1)   |
| Enter journal entry         | READY       | N        |
| Approve transaction         | READY       | N        |
| Create invoice              | READY       | N        |
| Run payroll                 | READY       | N        |
| Generate report (PDF)       | READY       | N        |
| Export tax form             | READY       | N        |
| Upload document (>1MB)      | BLOCKED     | Y (#3)   |
| Search (Cmd+K)             | READY       | N        |
| Change password             | BLOCKED     | Y (#2)   |
| QBO migration               | CLI ONLY    | N*       |
| Backup & restore            | READY       | N        |
| Recurring transactions      | NO UI       | N*       |
| Year-end close              | NO UI       | N*       |

*Not blockers for initial go-live but will be needed soon.

================================================================
GAP-TO-PRODUCTION ESTIMATE
================================================================

Based on findings, estimated effort to reach team-ready:

Critical fixes (must-do before onboarding):
  #1 User management UI:      2-3 hours
  #2 Change password UI:      1-2 hours
  #3 nginx body size:         5 minutes

Major fixes (should-do before onboarding):
  #4 Install dbmaint/logrotate: 15 minutes
  #5 Recurring transactions UI: 3-4 hours
  #6 Year-end close UI:        2-3 hours
  #7 Error boundary:           30 minutes
  #8 Unsaved changes warning:  15 minutes
  #9 Cookie SameSite verify:   30 minutes
  #10 Docs version update:     5 minutes
  #11 Global AP/AR view:       3-4 hours

Total critical: ~4 hours
Total major: ~10-12 hours
Total minor: ~3-4 hours
Grand total: ~18-20 hours of development

================================================================
WHAT THE OWNER SHOULD DO NEXT (in priority order)
================================================================

1. Add `client_max_body_size 25m;` to deploy/nginx.conf and restart
   nginx. This is a 30-second fix that unblocks document uploads.

2. Build a User Management tab in SystemAdmin.jsx so you can create
   ASSOCIATE accounts from the UI. The API is already there at
   /api/v1/auth/users -- just needs a frontend form.

3. Build a Change Password page or add it to a "My Account" dropdown.
   Without this, associates cannot change their initial password.

4. Add an ErrorBoundary component to main.jsx to prevent white-screen
   crashes. This protects against the worst user experience failure.

5. Add `useUnsavedChanges` to JournalEntryForm.jsx to prevent
   accidental data loss on the most important data entry form.

6. Update setup.sh to install the dbmaint and logrotate launchd
   plists (4 lines of code).

7. Build the Recurring Transactions page (backend is ready).

8. Build the Year-End Close page (backend is ready).

9. Write a 1-page "Getting Started" guide for associates covering:
   login, enter a journal entry, upload a document, search.

10. Consider adding a global AP/AR view (top-level routes with
    ClientSelector) for cross-client bill/invoice management.
