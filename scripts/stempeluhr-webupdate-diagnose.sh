#!/bin/bash
set -u
echo "== Stempeluhr Webupdate Diagnose =="
echo "Version: $(cat /opt/stempeluhr/version.txt 2>/dev/null || echo unbekannt)"
echo "Health: $(curl -fsS http://127.0.0.1:8000/health 2>/dev/null || echo FEHLER)"
echo "Runner: $(ls -la /usr/local/sbin/stempeluhr-web-update-run 2>&1)"
echo "Runner Ziel: $(readlink -f /usr/local/sbin/stempeluhr-web-update-run 2>/dev/null || true)"
echo "Sudoers:"; cat /etc/sudoers.d/stempeluhr-update 2>/dev/null || true
echo "Uploads:"; ls -lah /opt/stempeluhr/uploads/updates 2>/dev/null || true
echo "Log tail:"; tail -80 /var/log/stempeluhr/update.log 2>/dev/null || true
