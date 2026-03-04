# Data Directory (Local Only)

This directory stores client documents and backups locally. Contents are NOT committed to git.

## Structure
- `documents/[client_id]/` — Uploaded client documents (PDFs, images)
- `backups/` — Automated daily database backups

## Important
- This directory is in .gitignore — data stays on the local machine only
- Backups are managed by the O2 automated backup module
