#!/bin/bash
set +e
APP_DIR="/opt/stempeluhr"
echo "===================================="
echo " Stempeluhr Diagnose"
echo "===================================="
echo "[Version]"; cat "$APP_DIR/version.txt" 2>/dev/null || true
echo; echo "[Dienst]"; systemctl status stempeluhr --no-pager -l || true
echo; echo "[Port 8000]"; ss -tulpn | grep ':8000' || echo "Port 8000 nicht offen"
echo; echo "[Python Importtest]"
cd "$APP_DIR" || exit 1
PYTHONPATH="$APP_DIR" "$APP_DIR/.venv/bin/python" - <<'PY'
try:
    import app.main
    print("OK: app.main importierbar")
except Exception as e:
    import traceback
    print("FEHLER beim Import von app.main:")
    traceback.print_exc()
PY
echo; echo "[DB init Test]"
PYTHONPATH="$APP_DIR" "$APP_DIR/.venv/bin/python" - <<'PY'
try:
    from app.init_db import init_db
    init_db()
    print("OK: init_db erfolgreich")
except Exception:
    import traceback
    print("FEHLER bei init_db:")
    traceback.print_exc()
PY
echo; echo "[Letzte Logs]"; journalctl -u stempeluhr -n 120 --no-pager || true
