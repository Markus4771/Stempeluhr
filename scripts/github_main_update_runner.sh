#!/usr/bin/env bash
set -Eeuo pipefail

REPOSITORY="${STEMPELUHR_GITHUB_REPOSITORY:-Markus4771/Stempeluhr}"
BRANCH="${STEMPELUHR_GITHUB_BRANCH:-main}"
TOKEN_FILE="${STEMPELUHR_GITHUB_TOKEN_FILE:-/etc/stempeluhr/secrets/github_token}"
UPLOAD_DIR="${STEMPELUHR_UPDATE_UPLOAD_DIR:-/var/lib/stempeluhr/uploads/updates}"
WEB_UPDATE_RUNNER="/usr/local/sbin/stempeluhr-web-update-run"
LOG_FILE="/opt/stempeluhr/logs/update.log"
STATUS_FILE="/opt/stempeluhr/logs/update-status.json"

log(){ printf '[%s] main-update: %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" | tee -a "$LOG_FILE"; }
status(){
  local state="$1" message="$2" progress="$3" step="$4" version="${5:-}"
  python3 - "$STATUS_FILE" "$state" "$message" "$progress" "$step" "$version" <<'PY'
import json, os, sys
from datetime import datetime
path, state, message, progress, step, version = sys.argv[1:]
os.makedirs(os.path.dirname(path), exist_ok=True)
with open(path, 'w', encoding='utf-8') as f:
    json.dump({"state": state, "message": message, "progress": int(progress), "step": step, "version": version, "package": "stempeluhr", "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')}, f, ensure_ascii=False, indent=2)
os.chmod(path, 0o664)
PY
}
fail(){ status failed "$*" 0 "main-Update"; log "FEHLER: $*"; exit 1; }

[[ "$(id -u)" == "0" ]] || fail "Runner muss als root ausgeführt werden."
[[ -s "$TOKEN_FILE" ]] || fail "GitHub-Token fehlt: $TOKEN_FILE"
command -v curl >/dev/null || fail "curl fehlt."
command -v tar >/dev/null || fail "tar fehlt."
command -v python3 >/dev/null || fail "python3 fehlt."
[[ -x "$WEB_UPDATE_RUNNER" ]] || fail "Web-Update-Runner fehlt: $WEB_UPDATE_RUNNER"

TOKEN="$(tr -d '\r\n' < "$TOKEN_FILE")"
[[ -n "$TOKEN" ]] || fail "GitHub-Token ist leer."
TMP_DIR="$(mktemp -d /var/tmp/stempeluhr-main-update.XXXXXX)"
trap 'rm -rf "$TMP_DIR"' EXIT
ARCHIVE="$TMP_DIR/source.tar.gz"
EXTRACT="$TMP_DIR/source"
mkdir -p "$EXTRACT" "$UPLOAD_DIR" "$(dirname "$LOG_FILE")"

status starting "GitHub-main wird geladen" 5 "Quellcode herunterladen"
log "Lade $REPOSITORY Branch $BRANCH"
curl --fail --silent --show-error --location \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  -H "User-Agent: Stempeluhr-Professional-Updater" \
  "https://api.github.com/repos/$REPOSITORY/tarball/$BRANCH" \
  -o "$ARCHIVE" || fail "GitHub-Quellcode konnte nicht geladen werden."

tar -xzf "$ARCHIVE" -C "$EXTRACT" --strip-components=1 || fail "GitHub-Archiv konnte nicht entpackt werden."
[[ -f "$EXTRACT/version.txt" && -x "$EXTRACT/scripts/build_release.sh" ]] || fail "Geladener Quellcode ist unvollständig."
VERSION="$(tr -d '[:space:]' < "$EXTRACT/version.txt")"
[[ -n "$VERSION" ]] || fail "Version im GitHub-Stand fehlt."
CURRENT="$(dpkg-query -W -f='${Version}' stempeluhr 2>/dev/null || echo 0)"
if ! dpkg --compare-versions "$VERSION" gt "$CURRENT"; then
  fail "GitHub-main Version $VERSION ist nicht neuer als installiert $CURRENT."
fi

status running "Debian-Paket wird aus GitHub-main gebaut" 25 "Paketbau" "$VERSION"
log "Baue Version $VERSION"
cd "$EXTRACT"
ALLOW_DIRTY=1 bash scripts/build_release.sh || fail "Paketbau für Version $VERSION fehlgeschlagen."
DEB="$EXTRACT/releases/stempeluhr_${VERSION}_all.deb"
[[ -f "$DEB" ]] || fail "Gebautes Paket fehlt: $DEB"
TARGET="$UPLOAD_DIR/$(basename "$DEB")"
install -m 0644 "$DEB" "$TARGET"

status uploaded "GitHub-main Paket gebaut und geprüft" 35 "Installation wird gestartet" "$VERSION"
log "Starte bestehenden Update-Assistenten mit $TARGET"
exec "$WEB_UPDATE_RUNNER" "$TARGET"
