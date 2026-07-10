#!/bin/bash
set -e

APP_DIR="/opt/stempeluhr"

echo "Migration-Pfad Reparatur"
echo "========================"

cd "$APP_DIR"
export PYTHONPATH="$APP_DIR:${PYTHONPATH:-}"

if [ -d "$APP_DIR/updates/migrations" ]; then
    chmod +x "$APP_DIR/updates/migrations/"*.py 2>/dev/null || true
    for migration in "$APP_DIR"/updates/migrations/*.py; do
        [ -e "$migration" ] || continue
        echo "Migration: $migration"
        (
            cd "$APP_DIR"
            PYTHONPATH="$APP_DIR" "$APP_DIR/.venv/bin/python" "$migration"
        )
    done
fi

echo
echo "Dienst neu starten..."
systemctl restart stempeluhr
systemctl status stempeluhr --no-pager -l || true
journalctl -u stempeluhr -n 40 --no-pager || true
