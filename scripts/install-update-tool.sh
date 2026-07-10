#!/bin/bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/stempeluhr}"
APP_USER="${APP_USER:-stempeluhr}"

if [ "$(id -u)" -ne 0 ]; then
    echo "Bitte mit sudo/root starten:"
    echo "sudo bash $APP_DIR/scripts/install-update-tool.sh"
    exit 1
fi

if [ ! -f "$APP_DIR/scripts/stempeluhr-update" ]; then
    echo "Fehler: $APP_DIR/scripts/stempeluhr-update nicht gefunden."
    echo "Bitte zuerst das Projekt nach $APP_DIR entpacken oder installieren."
    exit 1
fi

install -m 755 "$APP_DIR/scripts/stempeluhr-update" /usr/local/bin/stempeluhr-update
mkdir -p /var/backups/stempeluhr /var/log/stempeluhr /opt/stempeluhr/uploads/updates
chown -R "$APP_USER:$APP_USER" /opt/stempeluhr/uploads 2>/dev/null || true
touch /var/log/stempeluhr/update.log
chmod 664 /var/log/stempeluhr/update.log || true

cat >/etc/sudoers.d/stempeluhr-update <<'SUDOERS'
# Stempeluhr Web-Update: erlaubt nur den Update-Befehl ohne Passwort.
stempeluhr ALL=(root) NOPASSWD: /usr/local/bin/stempeluhr-update
SUDOERS
chmod 440 /etc/sudoers.d/stempeluhr-update

if command -v visudo >/dev/null 2>&1; then
    visudo -cf /etc/sudoers.d/stempeluhr-update >/dev/null
fi

echo "Update-Befehl installiert."
echo "Nutzung: sudo stempeluhr-update /pfad/zur/update.zip"
echo "Web-Update: Systemeinstellungen -> Updates"
