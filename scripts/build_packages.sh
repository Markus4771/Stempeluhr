#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

VERSION="$(tr -d '[:space:]' < version.txt)"
ARCH="all"
BUILD_ROOT="$ROOT_DIR/build/packages"
RELEASE_DIR="$ROOT_DIR/releases"
SERVER_ROOT="$BUILD_ROOT/stempeluhr-server_${VERSION}_${ARCH}"
TERMINAL_ROOT="$BUILD_ROOT/stempeluhr-terminal_${VERSION}_${ARCH}"
ALL_ROOT="$BUILD_ROOT/stempeluhr-all-in-one_${VERSION}_${ARCH}"

fail(){ echo "FEHLER: $*" >&2; exit 1; }
for cmd in dpkg-deb rsync sha256sum python3; do command -v "$cmd" >/dev/null || fail "Befehl fehlt: $cmd"; done
[[ "$VERSION" == "6.0.0" ]] || fail "Für diesen Paketbau wird version.txt=6.0.0 erwartet, aktuell: $VERSION"
python3 -m compileall -q app scripts/raspberry_rfid_agent.py

rm -rf "$BUILD_ROOT"
mkdir -p "$RELEASE_DIR" "$SERVER_ROOT/DEBIAN" "$TERMINAL_ROOT/DEBIAN" "$ALL_ROOT/DEBIAN"

# ---------------- Server ----------------
mkdir -p "$SERVER_ROOT/opt/stempeluhr" "$SERVER_ROOT/etc/systemd/system" "$SERVER_ROOT/etc/stempeluhr" "$SERVER_ROOT/var/lib/stempeluhr" "$SERVER_ROOT/var/log/stempeluhr"
rsync -a \
  --exclude '.git' --exclude '.github' --exclude '.venv' --exclude 'build' --exclude 'releases' \
  --exclude '__pycache__' --exclude '*.pyc' --exclude 'data' --exclude 'uploads' \
  --exclude 'scripts/raspberry_rfid_agent.py' --exclude 'scripts/install_rfid_agent.sh' \
  --exclude 'stempeluhr-rfid-agent.service' \
  ./ "$SERVER_ROOT/opt/stempeluhr/"
install -m 0644 stempeluhr.service "$SERVER_ROOT/etc/systemd/system/stempeluhr.service"
install -m 0755 debian/postinst "$SERVER_ROOT/DEBIAN/postinst"
install -m 0755 debian/prerm "$SERVER_ROOT/DEBIAN/prerm"
cat > "$SERVER_ROOT/DEBIAN/control" <<EOF
Package: stempeluhr-server
Version: $VERSION
Section: web
Priority: optional
Architecture: $ARCH
Maintainer: Markus <admin@example.local>
Depends: python3, python3-venv, python3-pip, adduser, systemd, postgresql-client, ca-certificates, openssl, sudo
Recommends: postgresql, postgresql-contrib, nginx, curl, wget, git, build-essential, python3-dev, libpq-dev
Replaces: stempeluhr (<< 6.0.0), stempeluhr-professional
Breaks: stempeluhr (<< 6.0.0), stempeluhr-professional
Provides: stempeluhr-backend
Description: Stempeluhr Professional Server
 Zentrale Webanwendung, PostgreSQL-Datenhaltung, Verwaltung, Berichte,
 APIs, Terminalverwaltung und Authentifizierungsdienste.
EOF

# ---------------- Terminal ----------------
mkdir -p "$TERMINAL_ROOT/opt/stempeluhr-terminal" "$TERMINAL_ROOT/etc/systemd/system" "$TERMINAL_ROOT/etc/stempeluhr" "$TERMINAL_ROOT/var/log/stempeluhr" "$TERMINAL_ROOT/var/lib/stempeluhr"
install -m 0755 scripts/raspberry_rfid_agent.py "$TERMINAL_ROOT/opt/stempeluhr-terminal/terminal_agent.py"
install -m 0755 scripts/install_rfid_agent.sh "$TERMINAL_ROOT/opt/stempeluhr-terminal/configure-terminal.sh"
sed 's#/opt/stempeluhr/scripts/raspberry_rfid_agent.py#/opt/stempeluhr-terminal/terminal_agent.py#' stempeluhr-rfid-agent.service \
  | sed 's#/usr/bin/python3 /opt/stempeluhr-terminal#/usr/bin/python3 /opt/stempeluhr-terminal#' \
  > "$TERMINAL_ROOT/etc/systemd/system/stempeluhr-terminal.service"
cat > "$TERMINAL_ROOT/DEBIAN/control" <<EOF
Package: stempeluhr-terminal
Version: $VERSION
Section: web
Priority: optional
Architecture: $ARCH
Maintainer: Markus <admin@example.local>
Depends: python3, python3-evdev, python3-requests, systemd, chromium | chromium-browser
Replaces: stempeluhr-rfid-agent
Breaks: stempeluhr-rfid-agent
Provides: stempeluhr-hardware-terminal
Description: Stempeluhr Professional Terminal
 Schlanker Hardware-Client für Raspberry Pi und Debian-Terminals mit Display,
 RFID/NFC-Leser, Terminal-Heartbeat und entferntem Anlernmodus.
EOF
cat > "$TERMINAL_ROOT/DEBIAN/postinst" <<'EOF'
#!/usr/bin/env bash
set -Eeuo pipefail
install -d -m 0750 /etc/stempeluhr /var/log/stempeluhr /var/lib/stempeluhr
if [[ ! -f /etc/stempeluhr/terminal.env ]]; then
  DEVICE="$(find /dev/input/by-id /dev/input -maxdepth 1 \( -type l -o -name 'event*' \) 2>/dev/null | head -n1 || true)"
  cat > /etc/stempeluhr/terminal.env <<ENV
STEMPELUHR_SERVER=http://127.0.0.1:8000
RASPBERRY_HOSTNAME=$(hostname)
RFID_INPUT_DEVICE=$DEVICE
RFID_SCAN_TIMEOUT=35
HEARTBEAT_SECONDS=5
RFID_DISPLAY_ENABLED=true
RFID_DISPLAY_USER=pi
RFID_DISPLAY=:0
RFID_WAYLAND_DISPLAY=wayland-0
RFID_XDG_RUNTIME_DIR=/run/user/1000
RFID_SUCCESS_SECONDS=3
ENV
  chmod 0640 /etc/stempeluhr/terminal.env
fi
# Kompatibilität mit der bisherigen Agent-Konfiguration.
if [[ -f /etc/stempeluhr/rfid-agent.env && ! -s /etc/stempeluhr/terminal.env ]]; then
  cp /etc/stempeluhr/rfid-agent.env /etc/stempeluhr/terminal.env
fi
sed -i 's#EnvironmentFile=-/etc/stempeluhr/rfid-agent.env#EnvironmentFile=-/etc/stempeluhr/terminal.env#' /etc/systemd/system/stempeluhr-terminal.service
/usr/bin/python3 -c 'import evdev, requests'
systemctl daemon-reload
systemctl enable --now stempeluhr-terminal.service
EOF
chmod 0755 "$TERMINAL_ROOT/DEBIAN/postinst"
cat > "$TERMINAL_ROOT/DEBIAN/prerm" <<'EOF'
#!/usr/bin/env bash
set -e
systemctl disable --now stempeluhr-terminal.service >/dev/null 2>&1 || true
EOF
chmod 0755 "$TERMINAL_ROOT/DEBIAN/prerm"

# ---------------- All-in-One-Metapaket ----------------
cat > "$ALL_ROOT/DEBIAN/control" <<EOF
Package: stempeluhr-all-in-one
Version: $VERSION
Section: web
Priority: optional
Architecture: $ARCH
Maintainer: Markus <admin@example.local>
Depends: stempeluhr-server (= $VERSION), stempeluhr-terminal (= $VERSION)
Replaces: stempeluhr (<< 6.0.0), stempeluhr-professional
Breaks: stempeluhr (<< 6.0.0), stempeluhr-professional
Provides: stempeluhr
Description: Stempeluhr Professional All-in-One
 Installiert Server und Hardware-Terminal gemeinsam. Empfohlen für eine einzelne
 Raspberry-Pi-Installation, die zugleich Server und Stempelterminal ist.
EOF

find "$BUILD_ROOT" -type d -exec chmod 0755 {} +
for root in "$SERVER_ROOT" "$TERMINAL_ROOT" "$ALL_ROOT"; do
  package="$(awk -F': ' '/^Package:/ {print $2}' "$root/DEBIAN/control")"
  target="$RELEASE_DIR/${package}_${VERSION}_${ARCH}.deb"
  rm -f "$target" "$target.sha256"
  dpkg-deb --root-owner-group --build "$root" "$target"
  dpkg-deb --info "$target" >/dev/null
  sha256sum "$target" > "$target.sha256"
done

cat > "$RELEASE_DIR/stempeluhr_${VERSION}_INSTALLATION.txt" <<EOF
Stempeluhr Professional $VERSION

All-in-One auf einem Raspberry:
  sudo apt install ./stempeluhr-server_${VERSION}_${ARCH}.deb ./stempeluhr-terminal_${VERSION}_${ARCH}.deb ./stempeluhr-all-in-one_${VERSION}_${ARCH}.deb

Nur Server:
  sudo apt install ./stempeluhr-server_${VERSION}_${ARCH}.deb

Nur Terminal:
  sudo apt install ./stempeluhr-terminal_${VERSION}_${ARCH}.deb
  sudo nano /etc/stempeluhr/terminal.env
  sudo systemctl restart stempeluhr-terminal
EOF

echo "Paketbau erfolgreich:"
ls -lh "$RELEASE_DIR"/*"_${VERSION}_${ARCH}.deb"
