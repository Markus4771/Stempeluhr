#!/bin/bash
set -e
APP_DIR="/opt/stempeluhr"

echo "Employee/init_db Reparatur"
echo "=========================="

cd "$APP_DIR"
export PYTHONPATH="$APP_DIR"

"$APP_DIR/.venv/bin/python" - <<'PY'
from app.init_db import init_db
init_db()
print("init_db erfolgreich")
PY

systemctl restart stempeluhr
sleep 2
systemctl status stempeluhr --no-pager -l || true
journalctl -u stempeluhr -n 40 --no-pager || true
