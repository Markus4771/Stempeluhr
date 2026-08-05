#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="/opt/stempeluhr"
CONFIG_DIR="/etc/stempeluhr"
ENV_FILE="$CONFIG_DIR/rfid-agent.env"
UNIT_FILE="/etc/systemd/system/stempeluhr-rfid-agent.service"

[[ $EUID -eq 0 ]] || { echo "Bitte mit sudo ausführen." >&2; exit 1; }
[[ -f "$APP_DIR/scripts/raspberry_rfid_agent.py" ]] || { echo "Agent fehlt unter $APP_DIR/scripts/raspberry_rfid_agent.py" >&2; exit 1; }

apt-get update
apt-get install -y python3-evdev

install -d -m 0750 "$CONFIG_DIR"
if [[ ! -f "$ENV_FILE" ]]; then
  DEVICE="$(find /dev/input -maxdepth 1 -name 'event*' 2>/dev/null | head -n1 || true)"
  cat > "$ENV_FILE" <<EOF
STEMPELUHR_SERVER=http://127.0.0.1:8000
RASPBERRY_HOSTNAME=$(hostname)
RFID_INPUT_DEVICE=${DEVICE}
RFID_SCAN_TIMEOUT=35
HEARTBEAT_SECONDS=5
EOF
  chmod 0640 "$ENV_FILE"
  echo "Konfiguration angelegt: $ENV_FILE"
  echo "Bitte RFID_INPUT_DEVICE kontrollieren."
fi

install -m 0644 "$APP_DIR/stempeluhr-rfid-agent.service" "$UNIT_FILE"
systemctl daemon-reload
systemctl enable --now stempeluhr-rfid-agent.service
systemctl status stempeluhr-rfid-agent.service --no-pager -l || true
