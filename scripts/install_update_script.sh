#!/bin/bash
set -e
SRC_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_DIR="/opt/stempeluhr"

echo "Installiere Update-Skript..."
mkdir -p "$APP_DIR/scripts"
cp "$SRC_DIR/update.sh" "$APP_DIR/scripts/update.sh"
chmod +x "$APP_DIR/scripts/update.sh"
chown stempeluhr:stempeluhr "$APP_DIR/scripts/update.sh" 2>/dev/null || true
echo "Fertig: $APP_DIR/scripts/update.sh"
