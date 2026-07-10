#!/bin/bash
set -e

APP_DIR="/opt/stempeluhr"

echo "Backup-Seite Reparatur: Rechte/Ordner/Defaults"

mkdir -p "$APP_DIR/backups/daily" "$APP_DIR/backups/weekly" "$APP_DIR/backups/monthly" "$APP_DIR/backups/yearly"
chown -R stempeluhr:stempeluhr "$APP_DIR/backups"

if [ -f "$APP_DIR/updates/migrations/317_v3_1_7_backup_page_fix.py" ]; then
    "$APP_DIR/.venv/bin/python" "$APP_DIR/updates/migrations/317_v3_1_7_backup_page_fix.py"
fi

systemctl restart stempeluhr
systemctl status stempeluhr --no-pager -l
