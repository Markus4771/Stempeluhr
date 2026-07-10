#!/bin/bash
set -e

echo "Vacation Schema Reparatur"
echo "========================="

/opt/stempeluhr/.venv/bin/python /opt/stempeluhr/updates/migrations/403_v4_0_3_vacation_schema_migration.py

echo
echo "Tabellenstruktur:"
sudo -u postgres psql stempeluhr -c "\d vacation_requests"

echo
echo "Dienst neu starten..."
systemctl restart stempeluhr
systemctl status stempeluhr --no-pager -l
