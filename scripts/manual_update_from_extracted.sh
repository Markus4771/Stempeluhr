#!/bin/bash
set -euo pipefail

SRC_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP_DIR="/opt/stempeluhr"

echo "Manuelles Update aus entpacktem Ordner:"
echo "$SRC_ROOT"

systemctl stop stempeluhr || true

rsync -a --delete \
  --exclude ".env" \
  --exclude ".venv" \
  --exclude "backups" \
  --exclude "data" \
  "$SRC_ROOT/" "$APP_DIR/"

chown -R stempeluhr:stempeluhr "$APP_DIR" || true
chmod +x "$APP_DIR/scripts/"*.sh 2>/dev/null || true
chmod +x "$APP_DIR/updates/migrations/"*.py 2>/dev/null || true

cd "$APP_DIR"
export PYTHONPATH="$APP_DIR"

"$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"

for migration in "$APP_DIR"/updates/migrations/*.py; do
    [ -e "$migration" ] || continue
    base="$(basename "$migration")"
    if [[ "$base" == "001_create_or_update_v2.py" ]]; then
        echo "Überspringe alte Migration: $base"
        continue
    fi
    echo "Migration: $base"
    PYTHONPATH="$APP_DIR" "$APP_DIR/.venv/bin/python" "$migration"
done

systemctl daemon-reload
systemctl start stempeluhr
systemctl status stempeluhr --no-pager -l || true
