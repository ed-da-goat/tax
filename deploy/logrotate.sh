#!/bin/bash
# Log rotation for Georgia CPA Accounting System
# Rotates backend, nginx, and backup logs weekly, keeps 10 rotations
# Called by launchd: com.gacpa.logrotate.plist

set -eu

DEPLOY_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$DEPLOY_DIR/logs"
MAX_ROTATIONS=10

rotate_log() {
    local logfile="$1"
    if [ ! -f "$logfile" ]; then
        return
    fi

    # Don't rotate empty files
    local size
    size=$(stat -f%z "$logfile" 2>/dev/null || echo "0")
    if [ "$size" -eq 0 ]; then
        return
    fi

    # Rotate: move .9 -> .10, .8 -> .9, ..., .1 -> .2, current -> .1
    for i in $(seq $((MAX_ROTATIONS - 1)) -1 1); do
        if [ -f "${logfile}.${i}" ]; then
            mv "${logfile}.${i}" "${logfile}.$((i + 1))"
        fi
        if [ -f "${logfile}.${i}.gz" ]; then
            mv "${logfile}.${i}.gz" "${logfile}.$((i + 1)).gz"
        fi
    done

    # Current -> .1 (compress)
    cp "$logfile" "${logfile}.1"
    gzip -f "${logfile}.1"
    : > "$logfile"  # Truncate current log

    # Remove old rotations beyond MAX_ROTATIONS
    for i in $(seq $((MAX_ROTATIONS + 1)) $((MAX_ROTATIONS + 5))); do
        rm -f "${logfile}.${i}" "${logfile}.${i}.gz"
    done
}

echo "[$(date)] Log rotation starting..."

# Rotate each log file
for logfile in "$LOG_DIR"/backend.log "$LOG_DIR"/nginx-access.log "$LOG_DIR"/nginx-error.log "$LOG_DIR"/backup.log; do
    if [ -f "$logfile" ]; then
        rotate_log "$logfile"
        echo "  Rotated: $(basename "$logfile")"
    fi
done

echo "[$(date)] Log rotation complete."
