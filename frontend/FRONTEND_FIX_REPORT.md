# Frontend Fix Report

Executed 2026-03-06. All 11 audit findings addressed.

## Fixes Applied

### CRITICAL

| # | Fix | File(s) | Status |
|---|-----|---------|--------|
| 1 | nginx body size limit | `deploy/nginx.conf` | DONE — `client_max_body_size 25m` added |
| 2 | Missing launchd plists in setup/teardown | `deploy/setup.sh`, `deploy/teardown.sh` | DONE — dbmaint + logrotate added |
| 3 | ErrorBoundary | `frontend/src/components/ErrorBoundary.jsx`, `main.jsx` | DONE — wraps entire app |

### MAJOR

| # | Fix | File(s) | Status |
|---|-----|---------|--------|
| 4 | useUnsavedChanges on JournalEntryForm | `pages/JournalEntryForm.jsx` | DONE — tracks form+line dirty state |
| 5 | User Management tab on SystemAdmin | `pages/SystemAdmin.jsx` | DONE — full CRUD (create, edit, activate/deactivate) |
| 6 | Change Password modal | `components/Layout.jsx` | DONE — modal in topbar, calls POST /auth/change-password |
| 7 | RecurringTransactions page | `pages/RecurringTransactions.jsx`, `App.jsx`, `Layout.jsx` | DONE — client selector, CRUD, generate due |
| 8 | YearEndClose page | `pages/YearEndClose.jsx`, `App.jsx`, `Layout.jsx` | DONE — status, preview, close, reopen |
| 9 | Cookie SameSite verification | N/A | VERIFIED — code correct at auth.py:157, curl shows lax over HTTP (expected) |
| 10 | Search result routing | `components/Layout.jsx` | DONE — vendor/bill -> /ap, invoice -> /ar |
| 11 | CLAUDE.md React version | `.claude/CLAUDE.md` | DONE — 18.3 -> 19.2 |

## Build Verification

```
vite v7.3.1 building client environment for production...
178 modules transformed
dist/assets/index-QRFirLUt.js   548.91 kB
Built in 818ms — zero errors
```

## Summary

- 3 critical fixes (nginx, launchd, ErrorBoundary)
- 8 major fixes (UX, missing pages, routing)
- 2 new pages created (RecurringTransactions, YearEndClose)
- 1 new component created (ErrorBoundary)
- 0 backend files modified
- Frontend compiles clean (178 modules, 0 errors)
