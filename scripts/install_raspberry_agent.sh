#!/bin/sh
set -e
USER_NAME="${1:-pi}"
URL="${2:-http://127.0.0.1:8000/raspberry}"
ENV_FILE=/etc/stempeluhr/raspberry-agent.env
mkdir -p /etc/stempeluhr /etc/systemd/user /etc/xdg/labwc/autostart.d /var/log
# Der Ordner darf nicht 750 root:stempeluhr sein, sonst kann der Kiosk-Benutzer die Agent-Env nicht lesen.
chown root:root /etc/stempeluhr 2>/dev/null || true
chmod 755 /etc/stempeluhr 2>/dev/null || true
if [ ! -f "$ENV_FILE" ]; then
  cat > "$ENV_FILE" <<ENV
STEMPELUHR_AGENT_ENABLED=1
STEMPELUHR_KIOSK_URL=$URL
STEMPELUHR_BROWSER=auto
STEMPELUHR_AGENT_INTERVAL=10
STEMPELUHR_START_DELAY=8
STEMPELUHR_LOG_FILE=/var/log/stempeluhr-agent.log
STEMPELUHR_CHROME_PROFILE=~/.config/stempeluhr-chromium-profile
STEMPELUHR_HEARTBEAT_ENABLED=1
STEMPELUHR_SERVER_BASE=${URL%/raspberry}
ENV
else
  grep -q '^STEMPELUHR_AGENT_ENABLED=' "$ENV_FILE" || echo 'STEMPELUHR_AGENT_ENABLED=1' >> "$ENV_FILE"
  grep -q '^STEMPELUHR_KIOSK_URL=' "$ENV_FILE" || echo "STEMPELUHR_KIOSK_URL=$URL" >> "$ENV_FILE"
  grep -q '^STEMPELUHR_BROWSER=' "$ENV_FILE" || echo 'STEMPELUHR_BROWSER=auto' >> "$ENV_FILE"
  grep -q '^STEMPELUHR_AGENT_INTERVAL=' "$ENV_FILE" || echo 'STEMPELUHR_AGENT_INTERVAL=10' >> "$ENV_FILE"
  grep -q '^STEMPELUHR_START_DELAY=' "$ENV_FILE" || echo 'STEMPELUHR_START_DELAY=8' >> "$ENV_FILE"
  grep -q '^STEMPELUHR_LOG_FILE=' "$ENV_FILE" || echo 'STEMPELUHR_LOG_FILE=/var/log/stempeluhr-agent.log' >> "$ENV_FILE"
  grep -q '^STEMPELUHR_CHROME_PROFILE=' "$ENV_FILE" || echo 'STEMPELUHR_CHROME_PROFILE=~/.config/stempeluhr-chromium-profile' >> "$ENV_FILE"
  grep -q '^STEMPELUHR_HEARTBEAT_ENABLED=' "$ENV_FILE" || echo 'STEMPELUHR_HEARTBEAT_ENABLED=1' >> "$ENV_FILE"
  grep -q '^STEMPELUHR_SERVER_BASE=' "$ENV_FILE" || echo "STEMPELUHR_SERVER_BASE=${URL%/raspberry}" >> "$ENV_FILE"
fi

# Rechte so setzen, dass der Kiosk-Benutzer die Agent-Konfiguration lesen kann.
if id "$USER_NAME" >/dev/null 2>&1; then
  USER_GROUP="$(id -gn "$USER_NAME" 2>/dev/null || echo "$USER_NAME")"
  chown root:"$USER_GROUP" "$ENV_FILE" 2>/dev/null || chown root:root "$ENV_FILE" 2>/dev/null || true
  chmod 640 "$ENV_FILE" 2>/dev/null || true
  chown root:root /etc/stempeluhr 2>/dev/null || true
  chmod 755 /etc/stempeluhr 2>/dev/null || true
  LOG_FILE_PATH="$(grep -E "^STEMPELUHR_LOG_FILE=" "$ENV_FILE" | tail -1 | cut -d= -f2-)"
  [ -n "$LOG_FILE_PATH" ] || LOG_FILE_PATH=/var/log/stempeluhr-agent.log
  touch "$LOG_FILE_PATH" 2>/dev/null || true
  chown "$USER_NAME":"$USER_GROUP" "$LOG_FILE_PATH" 2>/dev/null || true
  chmod 664 "$LOG_FILE_PATH" 2>/dev/null || true
else
  chown root:root "$ENV_FILE" 2>/dev/null || true
  chmod 644 "$ENV_FILE" 2>/dev/null || true
fi

cat > /etc/systemd/user/stempeluhr-agent.service <<'UNIT'
[Unit]
Description=Stempeluhr Raspberry Chromium Kiosk Agent
After=graphical-session.target
PartOf=graphical-session.target

[Service]
Type=simple
EnvironmentFile=-/etc/stempeluhr/raspberry-agent.env
ExecStart=/opt/stempeluhr/scripts/stempeluhr-raspberry-agent
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
UNIT
cat > /etc/xdg/labwc/autostart.d/stempeluhr-agent <<'AUTO'
#!/bin/sh
systemctl --user restart stempeluhr-agent.service >/tmp/stempeluhr-agent-autostart.log 2>&1 || /opt/stempeluhr/scripts/stempeluhr-raspberry-agent --once >>/tmp/stempeluhr-agent-autostart.log 2>&1 &
AUTO
chmod +x /etc/xdg/labwc/autostart.d/stempeluhr-agent
if id "$USER_NAME" >/dev/null 2>&1; then
  mkdir -p "/home/$USER_NAME/.config/labwc"
  cat > "/home/$USER_NAME/.config/labwc/autostart" <<'AUTOUSER'
#!/bin/sh
systemctl --user restart stempeluhr-agent.service >/tmp/stempeluhr-agent-autostart.log 2>&1 || /opt/stempeluhr/scripts/stempeluhr-raspberry-agent --once >>/tmp/stempeluhr-agent-autostart.log 2>&1 &
AUTOUSER
  chmod +x "/home/$USER_NAME/.config/labwc/autostart"
  chown -R "$USER_NAME:$USER_NAME" "/home/$USER_NAME/.config" 2>/dev/null || true
  loginctl enable-linger "$USER_NAME" 2>/dev/null || true
fi
systemctl daemon-reload >/dev/null 2>&1 || true
systemctl --global enable stempeluhr-agent.service >/dev/null 2>&1 || true
echo "Raspberry-Agent installiert. Benutzer=$USER_NAME URL=$URL"
