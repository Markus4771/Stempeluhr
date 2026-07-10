#!/bin/bash
set -e

echo "InitDB/Settings Reparatur"
echo "========================="

/opt/stempeluhr/.venv/bin/python /opt/stempeluhr/updates/migrations/404_v4_0_4_initdb_settings_fix.py

echo
echo "Dienst neu starten..."
systemctl restart stempeluhr

sleep 2

systemctl status stempeluhr --no-pager -l || true
journalctl -u stempeluhr -n 40 --no-pager || true
