#!/bin/bash
set -e
APP_DIR="/opt/stempeluhr"
APP_USER="stempeluhr"

chown -R "$APP_USER:$APP_USER" "$APP_DIR"
chmod +x "$APP_DIR/scripts/"*.sh 2>/dev/null || true
chmod +x "$APP_DIR/updates/migrations/"*.py 2>/dev/null || true
chmod 640 "$APP_DIR/.env" 2>/dev/null || true

systemctl restart stempeluhr
systemctl status stempeluhr --no-pager -l || true
