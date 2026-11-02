#!/bin/sh
set -eu

APP_ROOT="${STEMPELUHR_ROOT:-/opt/stempeluhr}"
SERVICE_SRC="$APP_ROOT/packaging/systemd/stempeluhr-hce-agent.service"

if [ "$(id -u)" -ne 0 ]; then
  echo "Bitte als root ausführen." >&2
  exit 1
fi

apt-get update
apt-get install -y pcscd python3-pyscard python3-requests
install -m 0644 "$SERVICE_SRC" /etc/systemd/system/stempeluhr-hce-agent.service
systemctl daemon-reload
systemctl enable pcscd.service
systemctl enable stempeluhr-hce-agent.service
systemctl restart pcscd.service
systemctl restart stempeluhr-hce-agent.service

echo "HCE-Agent installiert. Diagnose: systemctl status stempeluhr-hce-agent --no-pager"
