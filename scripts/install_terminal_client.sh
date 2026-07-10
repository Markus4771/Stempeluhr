#!/usr/bin/env bash
set -euo pipefail

# Stempeluhr Terminal-Client Installer
# Nutzung:
# sudo bash install_terminal_client.sh http://10.0.0.48:8000 tk_stempeluhr_...

SERVER_URL="${1:-}"
TERMINAL_KEY="${2:-}"
INSTALL_DIR="/opt/stempeluhr-terminal"

if [ -z "$SERVER_URL" ] || [ -z "$TERMINAL_KEY" ]; then
  echo "Nutzung: sudo bash install_terminal_client.sh http://SERVER:8000 TERMINAL_KEY"
  exit 1
fi

mkdir -p "$INSTALL_DIR"
cat > "$INSTALL_DIR/config.env" <<CFG
SERVER_URL=$SERVER_URL
TERMINAL_KEY=$TERMINAL_KEY
TERMINAL_VERSION=4.6.1
CFG

cat > "$INSTALL_DIR/heartbeat.sh" <<'SH2'
#!/usr/bin/env bash
set -euo pipefail
source /opt/stempeluhr-terminal/config.env
curl -fsS -X POST "$SERVER_URL/api/v1/terminals/heartbeat" \
  -H "Authorization: Bearer $TERMINAL_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"app_version\":\"$TERMINAL_VERSION\"}" >/dev/null
SH2
chmod +x "$INSTALL_DIR/heartbeat.sh"

cat > "$INSTALL_DIR/time_sync.py" <<'PY'
#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import time
import urllib.request

CONFIG = "/opt/stempeluhr-terminal/config.env"

def load_env(path):
    data = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            data[k] = v
    return data

def request_json(method, url, key, payload=None, timeout=10):
    body = None
    headers = {"Authorization": f"Bearer {key}"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))

def main():
    env = load_env(CONFIG)
    server = env["SERVER_URL"].rstrip("/")
    key = env["TERMINAL_KEY"]
    try:
        info = request_json("GET", f"{server}/api/v1/terminals/time", key)
        server_unix = int(info["server_unix"])
        offset = float(server_unix - time.time())
        status = "ok"
        message = "Zeit geprüft"
        if info.get("sync_enabled"):
            # Setzt die Zeit nur, wenn die Abweichung relevant ist. Dafür braucht der Client sudo/root.
            if abs(offset) >= 1.0:
                result = subprocess.run(["timedatectl", "set-time", f"@{server_unix}"], capture_output=True, text=True, timeout=15)
                if result.returncode == 0:
                    status = "synced"
                    message = f"Systemzeit gesetzt, Offset vorher {offset:+.3f}s"
                else:
                    status = "set_failed"
                    message = (result.stderr or result.stdout or "timedatectl fehlgeschlagen")[:300]
            else:
                status = "in_sync"
                message = f"Offset {offset:+.3f}s"
        else:
            status = "disabled"
            message = "Server-Zeitsynchronisation deaktiviert"
        request_json("POST", f"{server}/api/v1/terminals/time/report", key, {"offset_seconds": offset, "status": status, "message": message})
        print(message)
    except Exception as exc:
        try:
            request_json("POST", f"{server}/api/v1/terminals/time/report", key, {"status": "error", "message": str(exc)})
        except Exception:
            pass
        print(f"Terminal-Zeitsync Fehler: {exc}", file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
PY
chmod +x "$INSTALL_DIR/time_sync.py"

cat > /etc/systemd/system/stempeluhr-terminal-heartbeat.service <<'UNIT'
[Unit]
Description=Stempeluhr Terminal Heartbeat
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/opt/stempeluhr-terminal/heartbeat.sh
UNIT

cat > /etc/systemd/system/stempeluhr-terminal-heartbeat.timer <<'UNIT'
[Unit]
Description=Stempeluhr Terminal Heartbeat Timer

[Timer]
OnBootSec=30
OnUnitActiveSec=60
Unit=stempeluhr-terminal-heartbeat.service

[Install]
WantedBy=timers.target
UNIT

cat > /etc/systemd/system/stempeluhr-terminal-timesync.service <<'UNIT'
[Unit]
Description=Stempeluhr Terminal Zeitsynchronisation
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/opt/stempeluhr-terminal/time_sync.py
UNIT

cat > /etc/systemd/system/stempeluhr-terminal-timesync.timer <<'UNIT'
[Unit]
Description=Stempeluhr Terminal Zeitsynchronisation Timer

[Timer]
OnBootSec=45
OnUnitActiveSec=300
Unit=stempeluhr-terminal-timesync.service

[Install]
WantedBy=timers.target
UNIT

systemctl daemon-reload
systemctl enable --now stempeluhr-terminal-heartbeat.timer
systemctl enable --now stempeluhr-terminal-timesync.timer

echo "Terminal-Client eingerichtet. Tests:"
"$INSTALL_DIR/heartbeat.sh" && echo "Heartbeat OK"
"$INSTALL_DIR/time_sync.py" || true
