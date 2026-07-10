#!/bin/bash
set -e

echo "Version:"
cat /opt/stempeluhr/version.txt || true

echo "Prüfe Urlaubsrouten:"
grep -n "def vacation_home" /opt/stempeluhr/app/routes/web.py
grep -n "@router.get(\"/vacation\"" /opt/stempeluhr/app/routes/web.py

echo "Migration prüfen:"
/opt/stempeluhr/.venv/bin/python /opt/stempeluhr/updates/migrations/322_v3_2_2_vacation_route_fix.py

echo "Dienst neu starten:"
systemctl restart stempeluhr
systemctl status stempeluhr --no-pager -l
