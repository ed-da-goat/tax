#!/bin/bash
# Database maintenance for Georgia CPA Accounting System
# Runs VACUUM ANALYZE weekly to reclaim dead tuples and update statistics
# Called by launchd: com.gacpa.dbmaint.plist

set -eu

DEPLOY_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$DEPLOY_DIR")"
ENV_FILE="$PROJECT_DIR/backend/.env"

# Parse DATABASE_URL from .env to get connection params
if [ -f "$ENV_FILE" ]; then
    DB_URL=$(grep "^DATABASE_URL_SYNC=" "$ENV_FILE" | cut -d'=' -f2- | tr -d '\r')
    # Extract parts: postgresql+psycopg2://user:pass@host:port/dbname
    DB_USER=$(echo "$DB_URL" | sed -E 's|.*://([^:]+):.*|\1|')
    DB_PASS=$(echo "$DB_URL" | sed -E 's|.*://[^:]+:([^@]+)@.*|\1|')
    DB_HOST=$(echo "$DB_URL" | sed -E 's|.*@([^:]+):.*|\1|')
    DB_PORT=$(echo "$DB_URL" | sed -E 's|.*:([0-9]+)/.*|\1|')
    DB_NAME=$(echo "$DB_URL" | sed -E 's|.*/([^?]+).*|\1|')
else
    echo "ERROR: .env file not found at $ENV_FILE"
    exit 1
fi

echo "[$(date)] Database maintenance starting..."
echo "  Database: $DB_NAME on $DB_HOST:$DB_PORT"

export PGPASSWORD="$DB_PASS"

# VACUUM ANALYZE — reclaims space and updates planner statistics
psql -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" -d "$DB_NAME" -c "VACUUM ANALYZE;" 2>&1

echo "  VACUUM ANALYZE complete."

# Report table sizes for monitoring
echo "  Table sizes:"
psql -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" -d "$DB_NAME" -c "
SELECT schemaname || '.' || relname AS table,
       pg_size_pretty(pg_total_relation_size(relid)) AS total_size,
       n_live_tup AS live_rows,
       n_dead_tup AS dead_rows
FROM pg_stat_user_tables
ORDER BY pg_total_relation_size(relid) DESC
LIMIT 15;
" 2>&1

unset PGPASSWORD

echo "[$(date)] Database maintenance complete."
