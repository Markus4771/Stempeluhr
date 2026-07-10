#!/bin/bash
set +e
APP_DIR="/opt/stempeluhr"
ERRORS=0
OUT="/tmp/stempeluhr_selftest.out"
ERR="/tmp/stempeluhr_selftest.err"

check_cmd() {
    NAME="$1"
    CMD="$2"
    echo -n "$NAME ... "
    if bash -c "$CMD" >"$OUT" 2>"$ERR"; then
        echo "OK"
    else
        echo "FEHLER"
        cat "$ERR"
        ERRORS=$((ERRORS+1))
    fi
}

check_func() {
    NAME="$1"
    shift
    echo -n "$NAME ... "
    if "$@" >"$OUT" 2>"$ERR"; then
        echo "OK"
    else
        echo "FEHLER"
        cat "$ERR"
        ERRORS=$((ERRORS+1))
    fi
}

wait_for_http() {
    URL="$1"
    SECONDS_MAX="${2:-30}"
    i=0
    while [ "$i" -lt "$SECONDS_MAX" ]; do
        if curl -fsS "$URL" >/dev/null 2>"$ERR"; then
            return 0
        fi
        sleep 1
        i=$((i+1))
    done
    curl -fsS "$URL" >/dev/null 2>"$ERR"
    return 1
}

wait_for_port() {
    SECONDS_MAX="${1:-30}"
    i=0
    while [ "$i" -lt "$SECONDS_MAX" ]; do
        if command -v ss >/dev/null 2>&1; then
            ss -tuln | grep -q ':8000' && return 0
        else
            curl -fsS http://127.0.0.1:8000/health >/dev/null 2>"$ERR" && return 0
        fi
        sleep 1
        i=$((i+1))
    done
    if command -v ss >/dev/null 2>&1; then
        ss -tuln | grep ':8000' >/dev/null 2>"$ERR"
    else
        curl -fsS http://127.0.0.1:8000/health >/dev/null 2>"$ERR"
    fi
    return 1
}

echo "Stempeluhr Selftest"
[ -f "$APP_DIR/version.txt" ] && echo "Version: $(cat "$APP_DIR/version.txt")"
check_cmd "Python venv vorhanden" "test -x $APP_DIR/.venv/bin/python"
check_cmd "PostgreSQL aktiv" "systemctl is-active --quiet postgresql"
check_cmd "Stempeluhr aktiv" "systemctl is-active --quiet stempeluhr"
check_func "Port 8000 offen" wait_for_port 30
check_func "Health Endpoint" wait_for_http http://127.0.0.1:8000/health 30
check_func "API Health Endpoint" wait_for_http http://127.0.0.1:8000/api/v1/health 30
check_func "Startseite erreichbar" wait_for_http http://127.0.0.1:8000/ 30
check_cmd "Versionsmodul importierbar" "cd $APP_DIR && PYTHONPATH=$APP_DIR $APP_DIR/.venv/bin/python -c 'from app.version import APP_NAME, APP_VERSION; print(APP_NAME, APP_VERSION)'"
check_cmd "Version Datei passt" "cd $APP_DIR && PYTHONPATH=$APP_DIR $APP_DIR/.venv/bin/python - <<'PYTEST'
from app.version import APP_VERSION
from pathlib import Path
file_version = Path('version.txt').read_text().strip()
assert file_version == APP_VERSION, f'version.txt={file_version} app.version={APP_VERSION}'
PYTEST"

check_cmd "Webupdate-Starter vorhanden" "test -x /usr/local/sbin/stempeluhr-web-update-run || test -x $APP_DIR/scripts/stempeluhr-web-update-run"
check_cmd "Update-Log beschreibbar" "touch /var/log/stempeluhr/update.log && test -w /var/log/stempeluhr/update.log"
check_cmd "App importierbar" "cd $APP_DIR && PYTHONPATH=$APP_DIR $APP_DIR/.venv/bin/python -c 'import app.main; print(app.main.APP_VERSION)'"

if [ "$ERRORS" -eq 0 ]; then
    echo "SELFTEST OK"
    exit 0
else
    echo "SELFTEST FEHLER: $ERRORS"
    echo ""
    echo "Letzte Dienst-Logs:"
    journalctl -u stempeluhr -n 40 --no-pager 2>/dev/null || true
    exit 1
fi
