#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

VERSION="$(tr -d '[:space:]' < version.txt)"
PACKAGE="stempeluhr"
ARCH="all"
BUILD_ROOT="$ROOT_DIR/build/debian-package"
PKG_ROOT="$BUILD_ROOT/${PACKAGE}_${VERSION}_${ARCH}"
RELEASE_DIR="$ROOT_DIR/releases"
DEB_FILE="$RELEASE_DIR/${PACKAGE}_${VERSION}_${ARCH}.deb"
LOG_FILE="$RELEASE_DIR/${PACKAGE}_${VERSION}_build.log"

mkdir -p "$RELEASE_DIR"
exec > >(tee "$LOG_FILE") 2>&1

fail() {
  echo "FEHLER: $*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "Erforderlicher Befehl fehlt: $1"
}

require_command python3
require_command dpkg-deb
require_command sha256sum
require_command rsync

[[ -n "$VERSION" ]] || fail "version.txt ist leer"
[[ -f app/version.py ]] || fail "app/version.py fehlt"
[[ -f debian/control ]] || fail "debian/control fehlt"
[[ -f debian/postinst ]] || fail "debian/postinst fehlt"
[[ -f debian/prerm ]] || fail "debian/prerm fehlt"
[[ -f stempeluhr.service ]] || fail "stempeluhr.service fehlt"
[[ -f requirements.txt ]] || fail "requirements.txt fehlt"

APP_VERSION="$(python3 - <<'PY'
import re
from pathlib import Path
text = Path('app/version.py').read_text(encoding='utf-8')
match = re.search(r'^APP_VERSION\s*=\s*["\x27]([^"\x27]+)["\x27]', text, re.MULTILINE)
if not match:
    raise SystemExit(1)
print(match.group(1))
PY
)" || fail "APP_VERSION konnte nicht gelesen werden"

CONTROL_VERSION="$(awk -F': *' '/^Version:/ {print $2; exit}' debian/control | tr -d '[:space:]')"
[[ "$APP_VERSION" == "$VERSION" ]] || fail "app/version.py=$APP_VERSION, version.txt=$VERSION"
[[ "$CONTROL_VERSION" == "$VERSION" ]] || fail "debian/control=$CONTROL_VERSION, version.txt=$VERSION"
grep -Fq "$VERSION" README.md || fail "README.md enthält Version $VERSION nicht"
grep -Fq "$VERSION" changelog.md || fail "changelog.md enthält Version $VERSION nicht"
grep -Fq "$VERSION" CHATGPT_PROJEKTKONTEXT.md || fail "CHATGPT_PROJEKTKONTEXT.md enthält Version $VERSION nicht"
[[ ! -e VERSION ]] || fail "Veraltete zweite Versionsdatei VERSION existiert"

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  if [[ -n "$(git status --porcelain)" && "${ALLOW_DIRTY:-0}" != "1" ]]; then
    fail "Git-Arbeitsverzeichnis ist nicht sauber. Mit ALLOW_DIRTY=1 nur für lokale Tests übergehen."
  fi
fi

echo "Prüfe Python-Syntax ..."
python3 -m compileall -q app

echo "Bereite Paketstruktur vor ..."
rm -rf "$BUILD_ROOT"
mkdir -p \
  "$PKG_ROOT/DEBIAN" \
  "$PKG_ROOT/opt/stempeluhr" \
  "$PKG_ROOT/etc/systemd/system" \
  "$PKG_ROOT/etc/stempeluhr" \
  "$PKG_ROOT/var/lib/stempeluhr" \
  "$PKG_ROOT/var/log/stempeluhr"

rsync -a \
  --exclude '.git' \
  --exclude '.github' \
  --exclude '.venv' \
  --exclude 'build' \
  --exclude 'releases' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude 'data' \
  --exclude 'data.moved.*' \
  --exclude 'uploads' \
  ./ "$PKG_ROOT/opt/stempeluhr/"

install -m 0644 debian/control "$PKG_ROOT/DEBIAN/control"
install -m 0755 debian/postinst "$PKG_ROOT/DEBIAN/postinst"
install -m 0755 debian/prerm "$PKG_ROOT/DEBIAN/prerm"
install -m 0644 stempeluhr.service "$PKG_ROOT/etc/systemd/system/stempeluhr.service"

cat > "$PKG_ROOT/etc/stempeluhr/stempeluhr.env.example" <<'EOF'
DATABASE_TYPE=postgresql
DATABASE_HOST=127.0.0.1
DATABASE_PORT=5432
DATABASE_NAME=stempeluhr
DATABASE_USER=stempeluhr
DATABASE_PASSWORD=BITTE_SICHER_SETZEN
HOST=0.0.0.0
PORT=8000
EOF
chmod 0640 "$PKG_ROOT/etc/stempeluhr/stempeluhr.env.example"

find "$PKG_ROOT" -type d -exec chmod 0755 {} +
chmod 0750 "$PKG_ROOT/etc/stempeluhr" "$PKG_ROOT/var/lib/stempeluhr" "$PKG_ROOT/var/log/stempeluhr"

if find "$PKG_ROOT/opt/stempeluhr" -type f \( -name '*.env' -o -name '*.db' -o -name '*.sqlite*' \) -print -quit | grep -q .; then
  fail "Paket enthält lokale .env- oder Datenbankdateien"
fi

echo "Baue $DEB_FILE ..."
rm -f "$DEB_FILE" "$DEB_FILE.sha256"
dpkg-deb --root-owner-group --build "$PKG_ROOT" "$DEB_FILE"

dpkg-deb --info "$DEB_FILE"
dpkg-deb --contents "$DEB_FILE" >/dev/null
sha256sum "$DEB_FILE" > "$DEB_FILE.sha256"

echo
echo "Build erfolgreich:"
echo "  Paket:     $DEB_FILE"
echo "  Prüfsumme: $DEB_FILE.sha256"
echo "  Protokoll: $LOG_FILE"
