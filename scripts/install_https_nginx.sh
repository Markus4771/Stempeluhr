#!/bin/bash
set -euo pipefail
CONF_SRC="/opt/stempeluhr/nginx/stempeluhr_https.conf"
CONF_DST="/etc/nginx/sites-available/stempeluhr_https.conf"
LINK_DST="/etc/nginx/sites-enabled/stempeluhr_https.conf"
if [ "$(id -u)" -ne 0 ]; then
  echo "Bitte mit sudo/root starten."
  exit 1
fi
if [ ! -f "$CONF_SRC" ]; then
  echo "Nginx-Konfiguration fehlt: $CONF_SRC"
  echo "Bitte zuerst in Systemeinstellungen → HTTPS erzeugen."
  exit 1
fi
apt install -y nginx >/dev/null 2>&1 || true
cp "$CONF_SRC" "$CONF_DST"
ln -sf "$CONF_DST" "$LINK_DST"
nginx -t
systemctl enable nginx
systemctl reload nginx || systemctl restart nginx
echo "HTTPS-Nginx-Konfiguration aktiviert."
