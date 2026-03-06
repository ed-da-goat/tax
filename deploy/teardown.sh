#!/bin/bash
# Georgia CPA Accounting System - Stop and uninstall all services
#
# Usage: bash deploy/teardown.sh

set -euo pipefail

echo "Stopping Georgia CPA services..."

# Stop backend
launchctl bootout "gui/$(id -u)/com.gacpa.backend" 2>/dev/null && echo "  Backend stopped" || echo "  Backend not running"

# Stop backup scheduler
launchctl bootout "gui/$(id -u)/com.gacpa.backup" 2>/dev/null && echo "  Backup scheduler stopped" || echo "  Backup scheduler not running"

# Stop DB maintenance
launchctl bootout "gui/$(id -u)/com.gacpa.dbmaint" 2>/dev/null && echo "  DB maintenance stopped" || echo "  DB maintenance not running"

# Stop log rotation
launchctl bootout "gui/$(id -u)/com.gacpa.logrotate" 2>/dev/null && echo "  Log rotation stopped" || echo "  Log rotation not running"

# Stop nginx
brew services stop nginx 2>/dev/null && echo "  nginx stopped" || echo "  nginx not running"

# Restore original nginx config if backed up
NGINX_PREFIX=$(brew --prefix)/etc/nginx
if [ -f "$NGINX_PREFIX/nginx.conf.bak" ]; then
    mv "$NGINX_PREFIX/nginx.conf.bak" "$NGINX_PREFIX/nginx.conf"
    echo "  nginx config restored from backup"
fi

# Remove launchd plists
rm -f "$HOME/Library/LaunchAgents/com.gacpa.backend.plist"
rm -f "$HOME/Library/LaunchAgents/com.gacpa.backup.plist"
rm -f "$HOME/Library/LaunchAgents/com.gacpa.dbmaint.plist"
rm -f "$HOME/Library/LaunchAgents/com.gacpa.logrotate.plist"
echo "  LaunchAgent plists removed"

echo ""
echo "All services stopped and removed."
echo "Database and backup files are preserved."
