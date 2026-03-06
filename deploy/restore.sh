#!/bin/bash
# Restore a database backup for Georgia CPA Accounting System.
#
# Usage:
#   ./deploy/restore.sh <backup_file>
#   ./deploy/restore.sh                  (restores latest backup)
#
# Supports both encrypted (.dump.gpg) and legacy unencrypted (.dump) backups.
# Prompts for confirmation before overwriting the database.

set -euo pipefail

BACKUP_DIR="/Users/edwardahrens/tax/data/backups"
ENV_FILE="/Users/edwardahrens/tax/backend/.env"
PG_DUMP="/opt/homebrew/opt/postgresql@16/bin/pg_restore"

# Parse DATABASE_URL from .env
DB_URL=$(grep '^DATABASE_URL=' "$ENV_FILE" | head -1 | cut -d'=' -f2-)
CLEAN_URL=$(echo "$DB_URL" | sed 's/postgresql+asyncpg/postgresql/')

# Determine backup file
if [ $# -ge 1 ]; then
    BACKUP_FILE="$1"
else
    # Find the most recent backup (prefer .gpg, fall back to .dump)
    BACKUP_FILE=$(find "$BACKUP_DIR" \( -name "ga_cpa_*.dump.gpg" -o -name "ga_cpa_*.dump" \) -print0 \
        | xargs -0 ls -t 2>/dev/null | head -1 || true)
    if [ -z "$BACKUP_FILE" ]; then
        echo "ERROR: No backup files found in ${BACKUP_DIR}"
        exit 1
    fi
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "ERROR: Backup file not found: ${BACKUP_FILE}"
    exit 1
fi

echo "=================================================="
echo "  Georgia CPA Accounting System — Database Restore"
echo "=================================================="
echo ""
echo "  Backup file: $(basename "$BACKUP_FILE")"
echo "  File size:    $(stat -f%z "$BACKUP_FILE" 2>/dev/null || echo 'unknown') bytes"
echo "  File date:    $(stat -f '%Sm' -t '%Y-%m-%d %H:%M:%S' "$BACKUP_FILE" 2>/dev/null || echo 'unknown')"
echo "  Target DB:    ga_cpa"
echo ""
echo "  WARNING: This will DROP and recreate the ga_cpa database."
echo "  All current data will be replaced with the backup contents."
echo ""
read -r -p "  Type 'RESTORE' to confirm: " CONFIRM

if [ "$CONFIRM" != "RESTORE" ]; then
    echo "Restore cancelled."
    exit 0
fi

# Determine if encrypted
RESTORE_FILE="$BACKUP_FILE"
TMPFILE=""

if [[ "$BACKUP_FILE" == *.gpg ]]; then
    echo ""
    echo "Decrypting backup..."

    # Get passphrase
    BACKUP_PASSPHRASE=$(grep '^BACKUP_PASSPHRASE=' "$ENV_FILE" 2>/dev/null | head -1 | cut -d'=' -f2- || true)
    if [ -z "$BACKUP_PASSPHRASE" ]; then
        BACKUP_PASSPHRASE=$(security find-generic-password -s gacpa-backup -w 2>/dev/null || true)
    fi
    if [ -z "$BACKUP_PASSPHRASE" ]; then
        echo "ERROR: No BACKUP_PASSPHRASE in .env or macOS Keychain."
        echo "Set BACKUP_PASSPHRASE in .env or run:"
        echo "  security add-generic-password -s gacpa-backup -a backup -w 'YOUR_PASSPHRASE'"
        exit 1
    fi

    TMPFILE=$(mktemp /tmp/ga_cpa_restore.XXXXXX.dump)
    if ! echo "$BACKUP_PASSPHRASE" | gpg --batch --yes --decrypt \
        --passphrase-fd 0 \
        --output "$TMPFILE" \
        "$BACKUP_FILE" 2>/dev/null; then
        rm -f "$TMPFILE"
        echo "ERROR: Decryption failed. Check your passphrase."
        exit 1
    fi
    RESTORE_FILE="$TMPFILE"
    echo "Decryption successful."
fi

echo ""
echo "Restoring database..."

# Stop the backend service during restore
launchctl bootout gui/$(id -u) /Users/edwardahrens/tax/deploy/com.gacpa.backend.plist 2>/dev/null || true

# Drop and recreate the database, then restore
/opt/homebrew/opt/postgresql@16/bin/dropdb --if-exists ga_cpa 2>/dev/null || true
/opt/homebrew/opt/postgresql@16/bin/createdb ga_cpa 2>/dev/null

if $PG_DUMP --dbname="${CLEAN_URL}" "$RESTORE_FILE" 2>/dev/null; then
    echo "Database restored successfully."
else
    echo "ERROR: pg_restore encountered errors (some may be non-fatal)."
fi

# Clean up temp file
if [ -n "$TMPFILE" ]; then
    rm -f "$TMPFILE"
fi

# Restart the backend service
launchctl bootstrap gui/$(id -u) /Users/edwardahrens/tax/deploy/com.gacpa.backend.plist 2>/dev/null || true

echo ""
echo "Restore complete. Backend service restarted."
echo "Verify at: https://localhost/health"
