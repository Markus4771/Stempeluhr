#!/bin/bash
set +e
APP_DIR=/opt/stempeluhr
LOG=/var/log/stempeluhr/update.log

echo "Stempeluhr Diagnose"
echo "==================="
echo "Datum: $(date)"
echo ""
echo "Version:"
cat "$APP_DIR/version.txt" 2>/dev/null || true
PYTHONPATH="$APP_DIR" "$APP_DIR/.venv/bin/python" - <<'PY' 2>/dev/null
try:
    from app.version import APP_NAME, APP_VERSION
    print(f"{APP_NAME} {APP_VERSION}")
except Exception as exc:
    print(f"Versionsimport FEHLER: {exc}")
PY

echo ""
echo "Dienststatus:"
systemctl status stempeluhr --no-pager -l | sed -n '1,18p'

echo ""
echo "Health:"
curl -fsS http://127.0.0.1:8000/health || true
echo ""

echo ""
echo "PostgreSQL Rollen:"
sudo -u postgres psql -c "\du" 2>/dev/null || true

echo ""
echo "Pfade:"
ls -ld "$APP_DIR" "$APP_DIR/app" "$APP_DIR/.venv" "$APP_DIR/uploads" /var/log/stempeluhr /var/backups/stempeluhr 2>/dev/null

echo ""
echo "Letzte Update-Logs:"
tail -60 "$LOG" 2>/dev/null || true

echo ""
echo "Letzte Dienst-Logs:"
journalctl -u stempeluhr -n 60 --no-pager 2>/dev/null || true
