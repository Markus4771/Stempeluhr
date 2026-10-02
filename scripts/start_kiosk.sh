#!/bin/bash
set -euo pipefail

URL="${1:-${KIOSK_URL:-http://10.0.0.48:8000/raspberry}}"
TERMINAL_CODE="${TERMINAL_CODE:-${RASPBERRY_HOSTNAME:-$(hostname)}}"

# Die bestehende Kiosk-Seite identifiziert sich damit eindeutig beim Server.
# So kann sie pluginbasierte Anlernaufträge selbst übernehmen, ohne einen
# zweiten Chromium-Prozess aus dem systemd-Agenten starten zu müssen.
if [[ "$URL" != *"terminal_code="* ]]; then
    if [[ "$URL" == *"?"* ]]; then
        URL="${URL}&terminal_code=${TERMINAL_CODE}"
    else
        URL="${URL}?terminal_code=${TERMINAL_CODE}"
    fi
fi

xset s off 2>/dev/null || true
xset -dpms 2>/dev/null || true
xset s noblank 2>/dev/null || true

if command -v chromium-browser >/dev/null 2>&1; then
    exec chromium-browser --kiosk --password-store=basic --use-mock-keychain --no-first-run --no-default-browser-check --noerrdialogs --disable-infobars --disable-session-crashed-bubble "$URL"
elif command -v chromium >/dev/null 2>&1; then
    exec chromium --kiosk --password-store=basic --use-mock-keychain --no-first-run --no-default-browser-check --noerrdialogs --disable-infobars --disable-session-crashed-bubble "$URL"
else
    echo "Kein Chromium gefunden. Bitte chromium oder chromium-browser installieren." >&2
    exit 1
fi
