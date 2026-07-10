#!/bin/bash
set -euo pipefail
URL="${1:-http://10.0.0.48:8000/raspberry}"
USER_NAME="${2:-pi}"
BROWSER="${3:-auto}"
DESKTOP="${4:-auto}"

if [ "$BROWSER" = "auto" ]; then
  if command -v chromium >/dev/null 2>&1; then
    BROWSER="chromium"
  elif command -v chromium-browser >/dev/null 2>&1; then
    BROWSER="chromium-browser"
  else
    BROWSER="chromium"
  fi
fi

if [ "$DESKTOP" = "auto" ]; then
  if [ -d /etc/xdg/labwc ] || [ -d /usr/share/wayland-sessions ]; then
    DESKTOP="labwc"
  else
    DESKTOP="lxde"
  fi
fi

if [ "$DESKTOP" = "labwc" ]; then
  AUTOSTART="/home/${USER_NAME}/.config/labwc/autostart"
  mkdir -p "$(dirname "$AUTOSTART")"
  cat > "$AUTOSTART" <<EOF
#!/bin/sh
xset s off 2>/dev/null || true
xset -dpms 2>/dev/null || true
xset s noblank 2>/dev/null || true
${BROWSER} --password-store=basic --use-mock-keychain --no-first-run --no-default-browser-check --noerrdialogs --disable-infobars --disable-session-crashed-bubble --kiosk ${URL} &
EOF
  chmod +x "$AUTOSTART"
else
  AUTOSTART="/home/${USER_NAME}/.config/lxsession/LXDE-pi/autostart"
  mkdir -p "$(dirname "$AUTOSTART")"
  cat > "$AUTOSTART" <<EOF
@xset s off
@xset -dpms
@xset s noblank
@${BROWSER} --password-store=basic --use-mock-keychain --no-first-run --no-default-browser-check --noerrdialogs --disable-infobars --disable-session-crashed-bubble --kiosk ${URL}
EOF
fi

chown -R "${USER_NAME}:${USER_NAME}" "/home/${USER_NAME}/.config" 2>/dev/null || true
echo "Kiosk-Autostart geschrieben: $AUTOSTART"
echo "URL: $URL"
echo "Browser: $BROWSER"
echo "Desktop: $DESKTOP"

# 5.2.29: zusaetzlich den robusten Raspberry-Agent installieren.
if [ -x /opt/stempeluhr/scripts/install_raspberry_agent.sh ]; then
  /opt/stempeluhr/scripts/install_raspberry_agent.sh "$USER_NAME" "$URL" || true
fi
