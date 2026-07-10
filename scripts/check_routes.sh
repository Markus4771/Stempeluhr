#!/bin/bash
set -e

echo "Version:"
cat /opt/stempeluhr/version.txt || true

echo
echo "Main Router:"
grep -n "include_router(web.router)" /opt/stempeluhr/app/main.py || true
grep -n "routes_modular" /opt/stempeluhr/app/main.py || true

echo
echo "Admin Route:"
grep -n "@router.get(\"/admin" /opt/stempeluhr/app/routes/web.py || true

echo
echo "Vacation Route:"
grep -n "def vacation_home" /opt/stempeluhr/app/routes/web.py || true
grep -n "@router.get(\"/vacation\"" /opt/stempeluhr/app/routes/web.py || true

echo
echo "HTTP Tests:"
curl -I http://127.0.0.1:8000/admin || true
curl -I http://127.0.0.1:8000/vacation || true
