#!/bin/bash
# Nightly database backup for Georgia CPA Accounting System.
# Called by launchd (com.gacpa.backup.plist) at 2:00 AM daily.
#
# - Creates a compressed pg_dump in /data/backups/
# - Encrypts with GPG (AES-256) using passphrase from .env or macOS Keychain
# - Retains last 30 backups (deletes older ones)
# - Optionally copies to BACKUP_REPLICA_DIR if set

set -euo pipefail

BACKUP_DIR="/Users/edwardahrens/tax/data/backups"
LOG_FILE="/Users/edwardahrens/tax/deploy/logs/backup.log"
RETAIN_DAYS=30

# Load .env for DATABASE_URL and BACKUP_PASSPHRASE
ENV_FILE="/Users/edwardahrens/tax/backend/.env"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

mkdir -p "$BACKUP_DIR"
mkdir -p "$(dirname "$LOG_FILE")"

log "=== Backup started ==="

# Parse DATABASE_URL from .env
DB_URL=$(grep '^DATABASE_URL=' "$ENV_FILE" | head -1 | cut -d'=' -f2-)
# Convert asyncpg URL to standard postgresql URL for pg_dump
CLEAN_URL=$(echo "$DB_URL" | sed 's/postgresql+asyncpg/postgresql/')

# Get backup encryption passphrase:
# 1. From BACKUP_PASSPHRASE in .env
# 2. From macOS Keychain (service: gacpa-backup)
# 3. Fail if neither is set
BACKUP_PASSPHRASE=$(grep '^BACKUP_PASSPHRASE=' "$ENV_FILE" 2>/dev/null | head -1 | cut -d'=' -f2- || true)
if [ -z "$BACKUP_PASSPHRASE" ]; then
    BACKUP_PASSPHRASE=$(security find-generic-password -s gacpa-backup -w 2>/dev/null || true)
fi
if [ -z "$BACKUP_PASSPHRASE" ]; then
    log "ERROR: No BACKUP_PASSPHRASE in .env or macOS Keychain (service: gacpa-backup). Backup NOT encrypted."
    log "Set BACKUP_PASSPHRASE in .env or run: security add-generic-password -s gacpa-backup -a backup -w 'YOUR_PASSPHRASE'"
    exit 1
fi

TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
FILENAME="ga_cpa_${TIMESTAMP}.dump.gpg"
FILEPATH="${BACKUP_DIR}/${FILENAME}"
TMPFILE="${BACKUP_DIR}/.ga_cpa_${TIMESTAMP}.dump.tmp"

# Create backup, encrypt with GPG AES-256, then remove unencrypted temp file
if /opt/homebrew/opt/postgresql@16/bin/pg_dump \
    --format=custom \
    --compress=6 \
    "--file=${TMPFILE}" \
    "${CLEAN_URL}" 2>> "$LOG_FILE"; then

    # Encrypt with GPG symmetric AES-256
    if echo "$BACKUP_PASSPHRASE" | gpg --batch --yes --symmetric --cipher-algo AES256 \
        --passphrase-fd 0 \
        --output "$FILEPATH" \
        "$TMPFILE" 2>> "$LOG_FILE"; then
        rm -f "$TMPFILE"
        SIZE=$(stat -f%z "$FILEPATH" 2>/dev/null || echo "unknown")
        log "Encrypted backup created: ${FILENAME} (${SIZE} bytes)"
    else
        rm -f "$TMPFILE"
        log "ERROR: GPG encryption failed"
        exit 1
    fi
else
    rm -f "$TMPFILE"
    log "ERROR: pg_dump failed"
    exit 1
fi

# Prune old backups (keep last RETAIN_DAYS days) — both encrypted and legacy unencrypted
find "$BACKUP_DIR" -name "ga_cpa_*.dump.gpg" -mtime +${RETAIN_DAYS} -delete 2>/dev/null
find "$BACKUP_DIR" -name "ga_cpa_*.dump" -not -name "*.gpg" -mtime +${RETAIN_DAYS} -delete 2>/dev/null
REMAINING=$(find "$BACKUP_DIR" \( -name "ga_cpa_*.dump" -o -name "ga_cpa_*.dump.gpg" \) | wc -l | tr -d ' ')
log "Backup retention: ${REMAINING} backups on disk (max age: ${RETAIN_DAYS} days)"

# Replicate to external drive if configured
REPLICA_DIR="${BACKUP_REPLICA_DIR:-}"
if [ -n "$REPLICA_DIR" ] && [ -d "$REPLICA_DIR" ]; then
    if cp "$FILEPATH" "$REPLICA_DIR/"; then
        log "Replicated to: ${REPLICA_DIR}/${FILENAME}"
        # Prune old replicas too
        find "$REPLICA_DIR" -name "ga_cpa_*.dump.gpg" -mtime +${RETAIN_DAYS} -delete 2>/dev/null
        find "$REPLICA_DIR" -name "ga_cpa_*.dump" -not -name "*.gpg" -mtime +${RETAIN_DAYS} -delete 2>/dev/null
    else
        log "WARNING: Failed to replicate to ${REPLICA_DIR}"
    fi
elif [ -n "$REPLICA_DIR" ]; then
    log "WARNING: BACKUP_REPLICA_DIR set but directory not found: ${REPLICA_DIR}"
fi

log "=== Backup complete ==="
