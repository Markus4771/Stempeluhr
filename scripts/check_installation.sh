#!/bin/bash
set +e
APP_DIR="/opt/stempeluhr"

echo "===================================="
echo " Stempeluhr Installationsprüfung"
echo "===================================="

echo "[Version]"
cat "$APP_DIR/version.txt" 2>/dev/null || echo "version.txt fehlt"

echo
echo "[PostgreSQL]"
systemctl status postgresql --no-pager -l | head -n 20

echo
echo "[Stempeluhr]"
systemctl status stempeluhr --no-pager -l | head -n 30

echo
echo "[.env]"
sudo grep DATABASE "$APP_DIR/.env" 2>/dev/null

echo
echo "[DB Login]"
if [ -f "$APP_DIR/.env" ]; then
    set -a
    . "$APP_DIR/.env"
    set +a
    PGPASSWORD="$DATABASE_PASSWORD" psql -h "$DATABASE_HOST" -U "$DATABASE_USER" -d "$DATABASE_NAME" -c "SELECT 1;" || true
fi

echo
echo "[Port 8000]"
ss -tulpn | grep 8000 || echo "Port 8000 nicht offen"

echo
echo "[Health]"
curl -sS http://127.0.0.1:8000/health || true
echo

echo
echo "[Startseite]"
curl -I http://127.0.0.1:8000/ || true

echo
echo "[Letzte Logs]"
journalctl -u stempeluhr -n 40 --no-pager || true
