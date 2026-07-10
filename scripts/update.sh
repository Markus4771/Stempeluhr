#!/bin/bash
set -euo pipefail

APP_DIR="/opt/stempeluhr"
APP_USER="stempeluhr"
SERVICE="stempeluhr"
UPDATE_ZIP="${1:-}"

fail(){
    echo "FEHLER: $*"
    journalctl -u "$SERVICE" -n 120 --no-pager || true
    exit 1
}

echo "===================================="
echo " Stempeluhr Update 5.2.11"
echo "===================================="

if [ "$(id -u)" -ne 0 ]; then
    echo "Bitte mit sudo/root starten."
    exit 1
fi
if [ -z "$UPDATE_ZIP" ]; then
    echo "Fehler: Bitte ZIP-Datei angeben."
    echo "Beispiel: sudo /opt/stempeluhr/scripts/update.sh /home/pi/update.zip"
    exit 1
fi
if [ ! -f "$UPDATE_ZIP" ]; then
    echo "Fehler: Update-Datei nicht gefunden: $UPDATE_ZIP"
    exit 1
fi

command -v unzip >/dev/null || apt install -y unzip
command -v rsync >/dev/null || apt install -y rsync
command -v curl >/dev/null || apt install -y curl
command -v openssl >/dev/null || apt install -y openssl
command -v nginx >/dev/null || apt install -y nginx || true

TMP_DIR="/tmp/stempeluhr_update_$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="/opt/stempeluhr_update_backups"
mkdir -p "$TMP_DIR" "$BACKUP_DIR"
trap 'rm -rf "$TMP_DIR"' EXIT

echo "[1/11] Dienst stoppen..."
systemctl stop "$SERVICE" || true

echo "[2/11] Sicherheitskopie erstellen..."
if [ -d "$APP_DIR" ]; then
    tar -czf "$BACKUP_DIR/stempeluhr_before_update_$(date +%Y%m%d_%H%M%S).tar.gz" -C /opt stempeluhr || true
fi

echo "[3/11] ZIP entpacken..."
unzip -q "$UPDATE_ZIP" -d "$TMP_DIR"
NEW_ROOT="$(find "$TMP_DIR" -type d -name app -printf '%h\n' | head -n 1)"
[ -n "$NEW_ROOT" ] || { echo "Fehler: Kein app-Verzeichnis im Update gefunden."; exit 1; }

echo "[4/11] Dateien kopieren..."
rsync -a --delete \
    --exclude ".env" \
    --exclude ".venv" \
    --exclude "backups" \
    --exclude "data" \
    "$NEW_ROOT/" "$APP_DIR/"

echo "[5/13] Version prüfen..."
if [ -f "$APP_DIR/app/version.py" ]; then
    VERSION="$(grep -E '^APP_VERSION' "$APP_DIR/app/version.py" | sed -E "s/.*=[[:space:]]*['\"]([^'\"]+)['\"].*/\1/" || true)"
    [ -n "$VERSION" ] || VERSION="unbekannt"
    echo "$VERSION" > "$APP_DIR/version.txt"
fi

echo "[6/13] Rechte setzen..."
chown -R "$APP_USER:$APP_USER" "$APP_DIR" || true
chmod +x "$APP_DIR/scripts/"*.sh 2>/dev/null || true
chmod +x "$APP_DIR/updates/migrations/"*.py 2>/dev/null || true
chmod 640 "$APP_DIR/.env" 2>/dev/null || true

echo "[7/13] Virtuelle Umgebung prüfen..."
if [ ! -d "$APP_DIR/.venv" ]; then
    python3 -m venv "$APP_DIR/.venv"
fi

echo "[8/13] Python-Pakete installieren..."
"$APP_DIR/.venv/bin/python" -m pip install --upgrade pip
"$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"

echo "[9/13] Projektprüfung vor Dienststart..."
cd "$APP_DIR"
export PYTHONPATH="$APP_DIR"
PYTHONPATH="$APP_DIR" "$APP_DIR/.venv/bin/python" -m compileall -q "$APP_DIR/app" || fail "Python-Compile-Prüfung fehlgeschlagen"
PYTHONPATH="$APP_DIR" "$APP_DIR/.venv/bin/python" -c 'from app.version import APP_NAME, APP_VERSION; import app.main; print(f"Import OK: {APP_NAME} {APP_VERSION}")' || fail "App-Import fehlgeschlagen"

echo "[10/13] systemd-Dateien aktualisieren..."
if [ -f "$APP_DIR/systemd/stempeluhr.service" ]; then
    cp "$APP_DIR/systemd/stempeluhr.service" /etc/systemd/system/stempeluhr.service
fi
if [ -f "$APP_DIR/systemd/stempeluhr-backup.service" ]; then
    cp "$APP_DIR/systemd/stempeluhr-backup.service" /etc/systemd/system/stempeluhr-backup.service || true
fi
if [ -f "$APP_DIR/systemd/stempeluhr-backup.timer" ]; then
    cp "$APP_DIR/systemd/stempeluhr-backup.timer" /etc/systemd/system/stempeluhr-backup.timer || true
fi
if [ -f "$APP_DIR/systemd/stempeluhr-plausibility.service" ]; then
    cp "$APP_DIR/systemd/stempeluhr-plausibility.service" /etc/systemd/system/stempeluhr-plausibility.service || true
fi
if [ -f "$APP_DIR/systemd/stempeluhr-plausibility.timer" ]; then
    cp "$APP_DIR/systemd/stempeluhr-plausibility.timer" /etc/systemd/system/stempeluhr-plausibility.timer || true
fi
systemctl daemon-reload

echo "[11/13] Datenbank-Migrationen ausführen..."
cd "$APP_DIR"
export PYTHONPATH="$APP_DIR"
if [ -d "$APP_DIR/updates/migrations" ]; then
    for migration in "$APP_DIR"/updates/migrations/*.py; do
        [ -e "$migration" ] || continue
        base="$(basename "$migration")"
        if [[ "$base" == "001_create_or_update_v2.py" ]]; then
            echo "Überspringe alte Migration: $base"
            continue
        fi
        echo "Migration: $base"
        PYTHONPATH="$APP_DIR" "$APP_DIR/.venv/bin/python" "$migration" || fail "Migration fehlgeschlagen: $base"
    done
fi

echo "[12/13] Import-Check vor Neustart..."
cd "$APP_DIR"
export PYTHONPATH="$APP_DIR"
PYTHONPATH="$APP_DIR" "$APP_DIR/.venv/bin/python" -c 'from app.version import APP_NAME, APP_VERSION; import app.main; print(f"Import OK: {APP_NAME} {APP_VERSION}")' || fail "App-Import fehlgeschlagen. Update wurde kopiert, Dienst wird nicht gestartet."

echo "[13/13] Dienste starten und prüfen..."
systemctl enable "$SERVICE"
systemctl restart "$SERVICE"
if [ -f /etc/systemd/system/stempeluhr-backup.timer ]; then
    systemctl enable --now stempeluhr-backup.timer || true
fi
if [ -f /etc/systemd/system/stempeluhr-plausibility.timer ]; then
    systemctl enable --now stempeluhr-plausibility.timer || true
fi

READY=0
for i in $(seq 1 45); do
    if curl -fsS http://127.0.0.1:8000/health >/tmp/stempeluhr_health.out 2>/tmp/stempeluhr_health.err; then
        READY=1
        break
    fi
    if ! systemctl is-active --quiet "$SERVICE"; then
        fail "Dienst ist nach dem Start beendet."
    fi
    sleep 1
done

systemctl status "$SERVICE" --no-pager -l || true
if [ "$READY" -eq 1 ]; then
    echo "Healthcheck OK: $(cat /tmp/stempeluhr_health.out)"
else
    echo "WARNUNG: Dienst läuft, aber /health war nach 45 Sekunden nicht erreichbar."
    ss -tulpn | grep ':8000' || true
    journalctl -u "$SERVICE" -n 120 --no-pager || true
fi

if [ -x "$APP_DIR/scripts/selftest.sh" ]; then
    "$APP_DIR/scripts/selftest.sh" || true
fi

echo "===================================="
echo " Update abgeschlossen"
echo "===================================="
