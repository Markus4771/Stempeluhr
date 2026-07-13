#!/usr/bin/env bash
set -Eeuo pipefail

APP_NAME="Stempeluhr"
REPO_URL="${STEMPELUHR_REPO_URL:-https://github.com/Markus4771/Stempeluhr.git}"
REPO_USER="${STEMPELUHR_REPO_USER:-${SUDO_USER:-pi}}"
REPO_HOME="${STEMPELUHR_REPO_HOME:-$(getent passwd "$REPO_USER" 2>/dev/null | cut -d: -f6)}"
REPO_HOME="${REPO_HOME:-/home/$REPO_USER}"
REPO_DIR="${STEMPELUHR_REPO_DIR:-$REPO_HOME/Stempeluhr}"
SERVICE_NAME="${STEMPELUHR_SERVICE_NAME:-stempeluhr}"
PACKAGE_NAME="stempeluhr"
CONFIG_DIR="${STEMPELUHR_CONFIG_DIR:-/etc/stempeluhr}"
ENV_FILE="$CONFIG_DIR/stempeluhr.env"
SECRET_FILE="$CONFIG_DIR/secrets/database.conf"
BACKUP_DIR="${STEMPELUHR_BACKUP_DIR:-/var/backups/stempeluhr}"
MODE="${1:-help}"
ARGUMENT="${2:-}"

log() { printf '\n[%s] %s\n' "$APP_NAME" "$*"; }
warn() { printf '\n[%s] WARNUNG: %s\n' "$APP_NAME" "$*" >&2; }
fatal() { printf '\n[%s] FEHLER: %s\n' "$APP_NAME" "$*" >&2; exit 1; }
command_exists() { command -v "$1" >/dev/null 2>&1; }

require_root() {
    [[ ${EUID:-$(id -u)} -eq 0 ]] || fatal "Dieses Skript muss als root oder mit sudo ausgeführt werden."
}

ensure_repo_user() {
    id "$REPO_USER" >/dev/null 2>&1 || fatal "Der Repository-Benutzer '$REPO_USER' existiert nicht. Setze STEMPELUHR_REPO_USER bei Bedarf."
    REPO_HOME="$(getent passwd "$REPO_USER" | cut -d: -f6)"
    [[ -n "$REPO_HOME" ]] || fatal "Home-Verzeichnis für $REPO_USER konnte nicht ermittelt werden."
}

run_as_repo_user() {
    runuser -u "$REPO_USER" -- "$@"
}

install_system_packages() {
    log "System- und Buildpakete werden installiert"
    export DEBIAN_FRONTEND=noninteractive
    apt-get update
    apt-get install -y \
        ca-certificates curl git rsync openssl util-linux \
        python3 python3-venv python3-pip python3-dev \
        dpkg-dev build-essential libpq-dev \
        postgresql postgresql-client postgresql-contrib
    systemctl enable --now postgresql
}

fix_repository() {
    [[ -d "$REPO_DIR/.git" ]] || return
    rm -f "$REPO_DIR/.git/index.lock"
    chown -R "$REPO_USER:$(id -gn "$REPO_USER")" "$REPO_DIR"
    run_as_repo_user git -C "$REPO_DIR" config --local safe.directory "$REPO_DIR" 2>/dev/null || true

    local remote
    remote="$(run_as_repo_user git -C "$REPO_DIR" remote get-url origin 2>/dev/null || true)"
    if [[ "$remote" == git@github.com:* || "$remote" == ssh://git@github.com/* ]]; then
        log "Git-Remote wird für schlüssellose Updates auf HTTPS umgestellt"
        run_as_repo_user git -C "$REPO_DIR" remote set-url origin "$REPO_URL"
    fi
}

clone_or_update_repository() {
    if [[ -d "$REPO_DIR/.git" ]]; then
        log "Repository wird aktualisiert"
        fix_repository
        if [[ -n "$(run_as_repo_user git -C "$REPO_DIR" status --porcelain)" ]]; then
            fatal "Das Git-Arbeitsverzeichnis enthält lokale Änderungen. Bitte zuerst sichern oder committen: $REPO_DIR"
        fi
        run_as_repo_user git -C "$REPO_DIR" fetch origin main
        run_as_repo_user git -C "$REPO_DIR" checkout main
        run_as_repo_user git -C "$REPO_DIR" pull --ff-only origin main
    elif [[ -e "$REPO_DIR" ]]; then
        fatal "$REPO_DIR existiert, ist aber kein Git-Repository."
    else
        log "Repository wird nach $REPO_DIR geklont"
        install -d -o "$REPO_USER" -g "$(id -gn "$REPO_USER")" "$(dirname "$REPO_DIR")"
        run_as_repo_user git clone --branch main "$REPO_URL" "$REPO_DIR"
    fi
}

load_database_config() {
    DATABASE_HOST="127.0.0.1"
    DATABASE_PORT="5432"
    DATABASE_NAME="stempeluhr"
    DATABASE_USER="stempeluhr"
    DATABASE_PASSWORD=""

    set -a
    [[ ! -f "$ENV_FILE" ]] || . "$ENV_FILE"
    [[ ! -f "$SECRET_FILE" ]] || . "$SECRET_FILE"
    set +a
}

create_backup() {
    if ! dpkg-query -W -f='${Status}' "$PACKAGE_NAME" 2>/dev/null | grep -q 'install ok installed'; then
        warn "Noch keine installierte Stempeluhr gefunden; Backup wird übersprungen."
        return 0
    fi

    load_database_config
    install -d -m 0700 "$BACKUP_DIR"

    local stamp target archive
    stamp="$(date +%Y%m%d_%H%M%S)"
    target="$BACKUP_DIR/stempeluhr_${stamp}"
    archive="${target}.tar.gz"
    install -d -m 0700 "$target"

    log "Datenbank und Konfiguration werden gesichert"
    if [[ -n "${DATABASE_PASSWORD:-}" ]]; then
        PGPASSWORD="$DATABASE_PASSWORD" pg_dump \
            --host="$DATABASE_HOST" --port="$DATABASE_PORT" \
            --username="$DATABASE_USER" --format=custom \
            --file="$target/database.dump" "$DATABASE_NAME"
    elif [[ "$DATABASE_HOST" == "127.0.0.1" || "$DATABASE_HOST" == "localhost" ]] && id postgres >/dev/null 2>&1; then
        runuser -u postgres -- pg_dump --format=custom --file="$target/database.dump" "$DATABASE_NAME"
    else
        fatal "Datenbankpasswort fehlt; Datenbanksicherung ist nicht möglich."
    fi

    [[ ! -d "$CONFIG_DIR" ]] || cp -a "$CONFIG_DIR" "$target/config"
    [[ ! -f /opt/stempeluhr/version.txt ]] || cp -a /opt/stempeluhr/version.txt "$target/version.txt"
    dpkg-query -W "$PACKAGE_NAME" > "$target/package-version.txt" 2>/dev/null || true

    tar -C "$BACKUP_DIR" -czf "$archive" "$(basename "$target")"
    rm -rf "$target"
    chmod 0600 "$archive"
    log "Backup erstellt: $archive"
}

build_package() {
    [[ -x "$REPO_DIR/scripts/build_release.sh" || -f "$REPO_DIR/scripts/build_release.sh" ]] || fatal "Buildskript fehlt: $REPO_DIR/scripts/build_release.sh"
    log "Debian-Paket wird gebaut"
    run_as_repo_user bash -c "cd '$REPO_DIR' && bash scripts/build_release.sh"

    VERSION="$(tr -d '[:space:]' < "$REPO_DIR/version.txt")"
    DEB_FILE="$REPO_DIR/releases/${PACKAGE_NAME}_${VERSION}_all.deb"
    [[ -f "$DEB_FILE" ]] || fatal "Paket wurde nicht erzeugt: $DEB_FILE"
    log "Paket erfolgreich gebaut: $DEB_FILE"
}

install_package() {
    VERSION="$(tr -d '[:space:]' < "$REPO_DIR/version.txt")"
    DEB_FILE="$REPO_DIR/releases/${PACKAGE_NAME}_${VERSION}_all.deb"
    [[ -f "$DEB_FILE" ]] || fatal "Paket fehlt: $DEB_FILE"

    log "Debian-Paket $VERSION wird installiert"
    apt-get install -y "$DEB_FILE"
}

health_check() {
    local port="8000"
    if [[ -f "$ENV_FILE" ]]; then
        port="$(sed -n 's/^PORT=//p' "$ENV_FILE" | tail -n1)"
        port="${port:-8000}"
    fi

    local attempt
    for attempt in {1..20}; do
        if curl --fail --silent --show-error "http://127.0.0.1:${port}/health" >/dev/null; then
            printf '[OK] HTTP-Health-Test auf Port %s\n' "$port"
            curl --fail --silent --show-error "http://127.0.0.1:${port}/version" 2>/dev/null || true
            printf '\n'
            return 0
        fi
        sleep 1
    done

    journalctl -u "$SERVICE_NAME" -n 100 --no-pager >&2 || true
    fatal "Health-Test auf Port $port fehlgeschlagen."
}

install_or_update() {
    install_system_packages
    clone_or_update_repository
    create_backup
    build_package
    install_package
    health_check
}

restore_backup() {
    [[ -n "$ARGUMENT" ]] || fatal "Verwendung: $0 restore /pfad/zum/backup.tar.gz"
    [[ -f "$ARGUMENT" ]] || fatal "Backup nicht gefunden: $ARGUMENT"
    command_exists pg_restore || fatal "pg_restore fehlt."

    local tmp source_dir
    tmp="$(mktemp -d)"
    trap 'rm -rf "$tmp"' RETURN
    tar -xzf "$ARGUMENT" -C "$tmp"
    source_dir="$(find "$tmp" -mindepth 1 -maxdepth 1 -type d | head -n1)"
    [[ -n "$source_dir" && -f "$source_dir/database.dump" ]] || fatal "Ungültiges Backup: database.dump fehlt."

    log "Stempeluhr wird für die Wiederherstellung gestoppt"
    systemctl stop "$SERVICE_NAME" || true

    if [[ -d "$source_dir/config" ]]; then
        rm -rf "$CONFIG_DIR"
        cp -a "$source_dir/config" "$CONFIG_DIR"
    fi

    load_database_config
    log "PostgreSQL-Datenbank wird wiederhergestellt"
    if [[ -n "${DATABASE_PASSWORD:-}" ]]; then
        PGPASSWORD="$DATABASE_PASSWORD" pg_restore \
            --clean --if-exists --no-owner \
            --host="$DATABASE_HOST" --port="$DATABASE_PORT" \
            --username="$DATABASE_USER" --dbname="$DATABASE_NAME" \
            "$source_dir/database.dump"
    else
        runuser -u postgres -- pg_restore --clean --if-exists --no-owner \
            --dbname="$DATABASE_NAME" "$source_dir/database.dump"
    fi

    systemctl restart "$SERVICE_NAME"
    health_check
    log "Wiederherstellung abgeschlossen"
}

show_status() {
    systemctl --no-pager --full status "$SERVICE_NAME" || true
    printf '\nInstalliertes Paket:\n'
    dpkg-query -W -f='${Package} ${Version} ${Status}\n' "$PACKAGE_NAME" 2>/dev/null || true
    printf '\nAnwendung:\n'
    health_check || true
}

show_version() {
    printf 'Installierte Paketversion: '
    dpkg-query -W -f='${Version}\n' "$PACKAGE_NAME" 2>/dev/null || printf 'nicht installiert\n'
    if [[ -f "$REPO_DIR/version.txt" ]]; then
        printf 'Repository-Version:       '
        cat "$REPO_DIR/version.txt"
    fi
    if [[ -f /opt/stempeluhr/version.txt ]]; then
        printf 'Dateiversion unter /opt:  '
        cat /opt/stempeluhr/version.txt
    fi
}

show_logs() {
    journalctl -u "$SERVICE_NAME" -n "${STEMPELUHR_LOG_LINES:-100}" --no-pager
}

doctor() {
    local failures=0
    check() {
        local label="$1"
        shift
        if "$@"; then
            printf '[OK]     %s\n' "$label"
        else
            printf '[FEHLER] %s\n' "$label"
            failures=$((failures + 1))
        fi
    }

    log "Systemdiagnose"
    check "Git verfügbar" command_exists git
    check "Python verfügbar" command_exists python3
    check "dpkg-deb verfügbar" command_exists dpkg-deb
    check "rsync verfügbar" command_exists rsync
    check "PostgreSQL-Client verfügbar" command_exists psql
    check "Repository vorhanden" test -d "$REPO_DIR/.git"
    check "Konfiguration vorhanden" test -s "$ENV_FILE"
    check "Paket installiert" dpkg-query -W "$PACKAGE_NAME"
    check "PostgreSQL aktiv" systemctl is-active --quiet postgresql
    check "Stempeluhr aktiviert" systemctl is-enabled --quiet "$SERVICE_NAME"
    check "Stempeluhr aktiv" systemctl is-active --quiet "$SERVICE_NAME"

    if curl --fail --silent http://127.0.0.1:8000/health >/dev/null 2>&1; then
        printf '[OK]     HTTP-Health-Test\n'
    else
        printf '[FEHLER] HTTP-Health-Test\n'
        failures=$((failures + 1))
    fi

    (( failures == 0 )) || fatal "$failures Diagnoseprüfung(en) fehlgeschlagen."
    log "Alle Diagnoseprüfungen erfolgreich"
}

uninstall_app() {
    if [[ "$ARGUMENT" == "--purge" ]]; then
        warn "Purge entfernt Paket, Konfiguration und lokale Anwendungsdaten."
        create_backup
        apt-get purge -y "$PACKAGE_NAME"
        rm -rf "$CONFIG_DIR" /var/lib/stempeluhr /var/log/stempeluhr
        log "Vollständige Deinstallation abgeschlossen. Das Backup bleibt unter $BACKUP_DIR erhalten."
    else
        apt-get remove -y "$PACKAGE_NAME"
        log "Paket entfernt. Konfiguration und Daten bleiben erhalten."
    fi
}

usage() {
    cat <<EOF
Verwendung (als root oder mit sudo):
  $0 install              Erstinstallation: Repository holen, Paket bauen und installieren
  $0 update               Backup erstellen, Repository aktualisieren, Paket bauen und installieren
  $0 upgrade              Alias für update
  $0 build                nur das Debian-Paket bauen
  $0 backup               PostgreSQL und Konfiguration sichern
  $0 restore DATEI        Backup wiederherstellen
  $0 start|stop|restart   Dienst steuern
  $0 status               Dienst, Paketversion und Health anzeigen
  $0 logs                 letzte Dienstprotokolle anzeigen
  $0 version              installierte und vorhandene Versionen anzeigen
  $0 doctor               vollständige Systemdiagnose
  $0 uninstall            Paket entfernen, Daten behalten
  $0 uninstall --purge    Backup erstellen und Paket, Konfiguration und Daten löschen

Repository: $REPO_DIR
Backups:    $BACKUP_DIR
EOF
}

require_root
ensure_repo_user

case "$MODE" in
    install) install_or_update ;;
    update|upgrade) install_or_update ;;
    build)
        install_system_packages
        clone_or_update_repository
        build_package
        ;;
    backup) create_backup ;;
    restore) restore_backup ;;
    start) systemctl start "$SERVICE_NAME"; health_check ;;
    stop) systemctl stop "$SERVICE_NAME" ;;
    restart) systemctl restart "$SERVICE_NAME"; health_check ;;
    status) show_status ;;
    logs) show_logs ;;
    version) show_version ;;
    doctor) doctor ;;
    uninstall) uninstall_app ;;
    -h|--help|help) usage ;;
    *) usage; fatal "Unbekannter Modus: $MODE" ;;
esac

log "$MODE erfolgreich abgeschlossen"
