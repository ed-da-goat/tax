#!/bin/bash
# Georgia CPA Accounting System - Deployment Setup (macOS)
#
# This script:
# 1. Installs nginx via Homebrew (if not installed)
# 2. Generates/regenerates TLS certificate (auto-detects LAN IP changes)
# 3. Builds the frontend for production
# 4. Creates log directories
# 5. Installs launchd services (backend + nightly backup)
# 6. Starts nginx
# 7. Configures macOS firewall for LAN access
#
# Usage: bash deploy/setup.sh
# To set an external backup drive: export BACKUP_REPLICA_DIR=/Volumes/MyDrive/backups

set -euo pipefail
cd "$(dirname "$0")/.."
PROJECT_ROOT="$(pwd)"

echo "========================================"
echo "  Georgia CPA - Deployment Setup"
echo "========================================"
echo "Project root: $PROJECT_ROOT"
echo ""

# -------------------------------------------------------
# 1. Prerequisites
# -------------------------------------------------------
echo "[1/7] Checking prerequisites..."

if ! command -v brew &>/dev/null; then
    echo "ERROR: Homebrew is required. Install from https://brew.sh"
    exit 1
fi

if ! brew list nginx &>/dev/null; then
    echo "  Installing nginx..."
    brew install nginx
else
    echo "  nginx: already installed"
fi

if ! command -v pg_dump &>/dev/null; then
    echo "  WARNING: pg_dump not found. Backups will not work."
fi

# -------------------------------------------------------
# 2. Self-signed TLS certificate
# -------------------------------------------------------
echo "[2/7] Generating self-signed TLS certificate..."

CERT_DIR="$PROJECT_ROOT/deploy/certs"
mkdir -p "$CERT_DIR"

# Detect current LAN IP
LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "127.0.0.1")
HOSTNAME=$(hostname -s 2>/dev/null || echo "localhost")

# Check if existing cert matches current IP
REGEN_CERT=false
if [ -f "$CERT_DIR/gacpa.crt" ] && [ -f "$CERT_DIR/gacpa.key" ]; then
    CERT_IPS=$(openssl x509 -in "$CERT_DIR/gacpa.crt" -noout -ext subjectAltName 2>/dev/null | grep -oE 'IP Address:[0-9.]+' | sed 's/IP Address://')
    if echo "$CERT_IPS" | grep -q "$LOCAL_IP"; then
        echo "  Certificate already exists and matches current IP ($LOCAL_IP), skipping."
    else
        echo "  IP changed ($LOCAL_IP not in cert SAN). Regenerating certificate..."
        REGEN_CERT=true
    fi
else
    REGEN_CERT=true
fi

if [ "$REGEN_CERT" = true ]; then
    openssl req -x509 -newkey rsa:2048 -nodes \
        -keyout "$CERT_DIR/gacpa.key" \
        -out "$CERT_DIR/gacpa.crt" \
        -days 3650 \
        -subj "/C=US/ST=Georgia/L=Atlanta/O=GA CPA Firm/CN=$HOSTNAME" \
        -addext "subjectAltName=DNS:$HOSTNAME,DNS:localhost,IP:$LOCAL_IP,IP:127.0.0.1" \
        2>/dev/null

    # Restrict key permissions
    chmod 600 "$CERT_DIR/gacpa.key"
    chmod 644 "$CERT_DIR/gacpa.crt"

    echo "  Created certificate for: $HOSTNAME ($LOCAL_IP)"
    echo "  Valid for 10 years."
    echo ""
    echo "  NOTE: Browsers will show a security warning for self-signed certs."
    echo "  To suppress this on macOS, run:"
    echo "    sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain $CERT_DIR/gacpa.crt"
fi

# Update CORS_ORIGINS in .env with current IP
ENV_FILE="$PROJECT_ROOT/backend/.env"
if [ -f "$ENV_FILE" ]; then
    if grep -q "CORS_ORIGINS" "$ENV_FILE"; then
        sed -i '' "s|CORS_ORIGINS=.*|CORS_ORIGINS=[\"https://localhost\",\"https://$LOCAL_IP\",\"http://localhost:5173\",\"http://localhost:3000\"]|" "$ENV_FILE"
    else
        echo "CORS_ORIGINS=[\"https://localhost\",\"https://$LOCAL_IP\",\"http://localhost:5173\",\"http://localhost:3000\"]" >> "$ENV_FILE"
    fi
    echo "  CORS_ORIGINS updated in .env for IP: $LOCAL_IP"
fi

# -------------------------------------------------------
# 3. Build frontend
# -------------------------------------------------------
echo "[3/7] Building frontend for production..."

cd "$PROJECT_ROOT/frontend"
if [ ! -d "node_modules" ]; then
    npm install
fi
npm run build
echo "  Frontend built to: $PROJECT_ROOT/frontend/dist"
cd "$PROJECT_ROOT"

# -------------------------------------------------------
# 4. Create directories
# -------------------------------------------------------
echo "[4/7] Creating directories..."

mkdir -p "$PROJECT_ROOT/deploy/logs"
mkdir -p "$PROJECT_ROOT/data/backups"
mkdir -p "$PROJECT_ROOT/data/documents"

# Restrict log directory and file permissions (owner-only read/write)
chmod 700 "$PROJECT_ROOT/deploy/logs"
find "$PROJECT_ROOT/deploy/logs" -type f -name "*.log" -exec chmod 600 {} \; 2>/dev/null || true

# Make backup script executable
chmod +x "$PROJECT_ROOT/deploy/backup.sh"

# -------------------------------------------------------
# 5. Install launchd services
# -------------------------------------------------------
echo "[5/7] Installing launchd services..."

LAUNCH_AGENTS="$HOME/Library/LaunchAgents"
mkdir -p "$LAUNCH_AGENTS"

# Stop existing services if running
launchctl bootout "gui/$(id -u)/com.gacpa.backend" 2>/dev/null || true
launchctl bootout "gui/$(id -u)/com.gacpa.backup" 2>/dev/null || true
launchctl bootout "gui/$(id -u)/com.gacpa.dbmaint" 2>/dev/null || true
launchctl bootout "gui/$(id -u)/com.gacpa.logrotate" 2>/dev/null || true

# Copy plists
cp "$PROJECT_ROOT/deploy/com.gacpa.backend.plist" "$LAUNCH_AGENTS/"
cp "$PROJECT_ROOT/deploy/com.gacpa.backup.plist" "$LAUNCH_AGENTS/"
cp "$PROJECT_ROOT/deploy/com.gacpa.dbmaint.plist" "$LAUNCH_AGENTS/"
cp "$PROJECT_ROOT/deploy/com.gacpa.logrotate.plist" "$LAUNCH_AGENTS/"

# Load services
launchctl bootstrap "gui/$(id -u)" "$LAUNCH_AGENTS/com.gacpa.backend.plist"
launchctl bootstrap "gui/$(id -u)" "$LAUNCH_AGENTS/com.gacpa.backup.plist"
launchctl bootstrap "gui/$(id -u)" "$LAUNCH_AGENTS/com.gacpa.dbmaint.plist"
launchctl bootstrap "gui/$(id -u)" "$LAUNCH_AGENTS/com.gacpa.logrotate.plist"

echo "  Backend service:    installed (auto-starts on login)"
echo "  Backup service:     installed (runs daily at 2:00 AM)"
echo "  DB maintenance:     installed (weekly VACUUM/REINDEX)"
echo "  Log rotation:       installed (daily rotation)"

# -------------------------------------------------------
# 6. Start nginx
# -------------------------------------------------------
echo "[6/7] Configuring and starting nginx..."

# Stop any existing nginx
brew services stop nginx 2>/dev/null || true

# Point nginx at our config
NGINX_PREFIX=$(brew --prefix)/etc/nginx
if [ -f "$NGINX_PREFIX/nginx.conf" ]; then
    cp "$NGINX_PREFIX/nginx.conf" "$NGINX_PREFIX/nginx.conf.bak"
fi
cp "$PROJECT_ROOT/deploy/nginx.conf" "$NGINX_PREFIX/nginx.conf"

# Start nginx via brew services (manages its own launchd plist)
brew services start nginx

# -------------------------------------------------------
# 7. macOS Firewall — allow nginx for LAN access
# -------------------------------------------------------
echo "[7/7] Checking macOS firewall..."

if /usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate 2>/dev/null | grep -q "enabled"; then
    echo "  macOS Firewall is ON. Adding nginx to allowed apps..."
    NGINX_BIN=$(which nginx 2>/dev/null || echo "$(brew --prefix)/bin/nginx")
    sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add "$NGINX_BIN" 2>/dev/null || true
    sudo /usr/libexec/ApplicationFirewall/socketfilterfw --unblockapp "$NGINX_BIN" 2>/dev/null || true
    echo "  nginx allowed through firewall."
else
    echo "  macOS Firewall is OFF — no changes needed."
fi

echo ""
echo "========================================"
echo "  Deployment Complete!"
echo "========================================"
echo ""
echo "Services running:"
echo "  Backend:  http://127.0.0.1:8000 (direct)"
echo "  Frontend: https://localhost (via nginx)"
echo "  Backup:   daily at 2:00 AM → $PROJECT_ROOT/data/backups/"
echo ""
echo "Access the app at: https://localhost"
if [ -n "$LOCAL_IP" ] && [ "$LOCAL_IP" != "127.0.0.1" ]; then
    echo ""
    echo "----------------------------------------"
    echo "  LAN Access (Windows/other machines)"
    echo "----------------------------------------"
    echo "  URL: https://$LOCAL_IP"
    echo ""
    echo "  First time from Windows:"
    echo "    1. Open browser to https://$LOCAL_IP"
    echo "    2. Click 'Advanced' -> 'Proceed to site (unsafe)'"
    echo "    3. Log in with your credentials"
    echo ""
    echo "  To permanently trust the certificate on Windows:"
    echo "    Copy this file to the Windows machine and import it:"
    echo "    $CERT_DIR/gacpa.crt"
    echo "    See deploy/windows-trust.md for detailed instructions."
fi
echo ""
echo "Default login:"
echo "  Email:    edward@755mortgage.com"
echo "  Password: admin123"
echo ""
echo "To set up external backup replication:"
echo "  1. Edit deploy/com.gacpa.backup.plist"
echo "  2. Add EnvironmentVariables → BACKUP_REPLICA_DIR=/Volumes/YourDrive/backups"
echo "  3. launchctl bootout gui/$(id -u)/com.gacpa.backup"
echo "  4. launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.gacpa.backup.plist"
echo ""
echo "To stop everything:"
echo "  brew services stop nginx"
echo "  launchctl bootout gui/$(id -u)/com.gacpa.backend"
echo ""
echo "Logs:"
echo "  Backend: $PROJECT_ROOT/deploy/logs/backend.stderr.log"
echo "  nginx:   $PROJECT_ROOT/deploy/logs/nginx.error.log"
echo "  Backup:  $PROJECT_ROOT/deploy/logs/backup.log"
