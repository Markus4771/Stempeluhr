#!/bin/bash
set -e

echo "Version:"
cat /opt/stempeluhr/version.txt || true

echo
echo "Prüfe falsche Department-Abfrage:"
if grep -n "db.query(Department, VacationRequest)" /opt/stempeluhr/app/routes/web.py; then
  echo "FEHLER: falsche Department-Abfrage noch vorhanden"
  exit 1
else
  echo "OK: keine falsche Department-Abfrage"
fi

echo
echo "Prüfe VacationRequest.requested_at im Modell:"
grep -n "requested_at" /opt/stempeluhr/app/models.py

echo
echo "Migration ausführen:"
/opt/stempeluhr/.venv/bin/python /opt/stempeluhr/updates/migrations/402_v4_0_2_admin_vacation_fix.py

echo
echo "Dienst neu starten:"
systemctl restart stempeluhr
systemctl status stempeluhr --no-pager -l
