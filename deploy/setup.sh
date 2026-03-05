#!/bin/bash
# Georgia CPA Accounting System - Deployment Setup (macOS)
#
# This script:
# 1. Installs nginx via Homebrew (if not installed)
# 2. Generates a self-signed TLS certificate for LAN HTTPS
# 3. Builds the frontend for production
# 4. Creates log directories
# 5. Installs launchd services (backend + nightly backup)
# 6. Starts everything
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
echo "[1/6] Checking prerequisites..."

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
echo "[2/6] Generating self-signed TLS certificate..."

CERT_DIR="$PROJECT_ROOT/deploy/certs"
mkdir -p "$CERT_DIR"

if [ -f "$CERT_DIR/gacpa.crt" ] && [ -f "$CERT_DIR/gacpa.key" ]; then
    echo "  Certificate already exists, skipping."
else
    # Get the local machine's hostname and IP for the certificate
    LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || echo "127.0.0.1")
    HOSTNAME=$(hostname -s 2>/dev/null || echo "localhost")

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

# -------------------------------------------------------
# 3. Build frontend
# -------------------------------------------------------
echo "[3/6] Building frontend for production..."

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
echo "[4/6] Creating directories..."

mkdir -p "$PROJECT_ROOT/deploy/logs"
mkdir -p "$PROJECT_ROOT/data/backups"
mkdir -p "$PROJECT_ROOT/data/documents"

# Make backup script executable
chmod +x "$PROJECT_ROOT/deploy/backup.sh"

# -------------------------------------------------------
# 5. Install launchd services
# -------------------------------------------------------
echo "[5/6] Installing launchd services..."

LAUNCH_AGENTS="$HOME/Library/LaunchAgents"
mkdir -p "$LAUNCH_AGENTS"

# Stop existing services if running
launchctl bootout "gui/$(id -u)/com.gacpa.backend" 2>/dev/null || true
launchctl bootout "gui/$(id -u)/com.gacpa.backup" 2>/dev/null || true

# Copy plists
cp "$PROJECT_ROOT/deploy/com.gacpa.backend.plist" "$LAUNCH_AGENTS/"
cp "$PROJECT_ROOT/deploy/com.gacpa.backup.plist" "$LAUNCH_AGENTS/"

# Load services
launchctl bootstrap "gui/$(id -u)" "$LAUNCH_AGENTS/com.gacpa.backend.plist"
launchctl bootstrap "gui/$(id -u)" "$LAUNCH_AGENTS/com.gacpa.backup.plist"

echo "  Backend service: installed (auto-starts on login)"
echo "  Backup service:  installed (runs daily at 2:00 AM)"

# -------------------------------------------------------
# 6. Start nginx
# -------------------------------------------------------
echo "[6/6] Configuring and starting nginx..."

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
LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || echo "")
if [ -n "$LOCAL_IP" ]; then
    echo "From other machines on LAN: https://$LOCAL_IP"
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
