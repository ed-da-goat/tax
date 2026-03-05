#!/bin/bash
# Nightly database backup for Georgia CPA Accounting System.
# Called by launchd (com.gacpa.backup.plist) at 2:00 AM daily.
#
# - Creates a compressed pg_dump in /data/backups/
# - Retains last 30 backups (deletes older ones)
# - Optionally copies to BACKUP_REPLICA_DIR if set

set -euo pipefail

BACKUP_DIR="/Users/edwardahrens/tax/data/backups"
LOG_FILE="/Users/edwardahrens/tax/deploy/logs/backup.log"
RETAIN_DAYS=30

# Load .env for DATABASE_URL
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

TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
FILENAME="ga_cpa_${TIMESTAMP}.dump"
FILEPATH="${BACKUP_DIR}/${FILENAME}"

# Create backup
if /opt/homebrew/opt/postgresql@16/bin/pg_dump \
    --format=custom \
    --compress=6 \
    "--file=${FILEPATH}" \
    "${CLEAN_URL}" 2>> "$LOG_FILE"; then
    SIZE=$(stat -f%z "$FILEPATH" 2>/dev/null || echo "unknown")
    log "Backup created: ${FILENAME} (${SIZE} bytes)"
else
    log "ERROR: pg_dump failed"
    exit 1
fi

# Prune old backups (keep last RETAIN_DAYS days)
find "$BACKUP_DIR" -name "ga_cpa_*.dump" -mtime +${RETAIN_DAYS} -delete 2>/dev/null
REMAINING=$(find "$BACKUP_DIR" -name "ga_cpa_*.dump" | wc -l | tr -d ' ')
log "Backup retention: ${REMAINING} backups on disk (max age: ${RETAIN_DAYS} days)"

# Replicate to external drive if configured
REPLICA_DIR="${BACKUP_REPLICA_DIR:-}"
if [ -n "$REPLICA_DIR" ] && [ -d "$REPLICA_DIR" ]; then
    if cp "$FILEPATH" "$REPLICA_DIR/"; then
        log "Replicated to: ${REPLICA_DIR}/${FILENAME}"
        # Prune old replicas too
        find "$REPLICA_DIR" -name "ga_cpa_*.dump" -mtime +${RETAIN_DAYS} -delete 2>/dev/null
    else
        log "WARNING: Failed to replicate to ${REPLICA_DIR}"
    fi
elif [ -n "$REPLICA_DIR" ]; then
    log "WARNING: BACKUP_REPLICA_DIR set but directory not found: ${REPLICA_DIR}"
fi

log "=== Backup complete ==="
