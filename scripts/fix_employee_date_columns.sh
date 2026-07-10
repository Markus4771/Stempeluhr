#!/bin/bash
set -e

APP_DIR="/opt/stempeluhr"

echo "===================================="
echo " Reparatur: Mitarbeiter-Datumsspalten"
echo "===================================="

if [ -f "$APP_DIR/.env" ]; then
    set -a
    . "$APP_DIR/.env"
    set +a
fi

DB_NAME=${DATABASE_NAME:-stempeluhr}

sudo -u postgres psql -d "$DB_NAME" -c "ALTER TABLE employees ADD COLUMN IF NOT EXISTS birth_date DATE;"
sudo -u postgres psql -d "$DB_NAME" -c "ALTER TABLE employees ADD COLUMN IF NOT EXISTS entry_date DATE;"

sudo systemctl restart stempeluhr
sudo systemctl status stempeluhr --no-pager -l
