#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
VERSION="${VERSION:-6.0.1}"
OUT="${OUT:-$ROOT/dist}"
WORK="${WORK:-$ROOT/.build-deb}"

command -v dpkg-deb >/dev/null 2>&1 || {
    echo "Fehler: dpkg-deb fehlt. Debian/Ubuntu: apt install dpkg-dev" >&2
    exit 1
}

build_package() {
    package="$1"
    stage="$WORK/$package"
    rm -rf "$stage"
    mkdir -p "$stage/DEBIAN" "$stage/opt/stempeluhr" "$stage/etc/systemd/system"

    cp "$ROOT/packaging/deb/$package/control" "$stage/DEBIAN/control"
    sed -i "s/^Version:.*/Version: $VERSION/" "$stage/DEBIAN/control"
    cp "$ROOT/packaging/deb/$package/postinst" "$stage/DEBIAN/postinst"
    cp "$ROOT/packaging/deb/$package/prerm" "$stage/DEBIAN/prerm"
    chmod 0755 "$stage/DEBIAN/postinst" "$stage/DEBIAN/prerm"

    if [ "$package" = "stempeluhr-server" ] || [ "$package" = "stempeluhr-all-in-one" ]; then
        test -f "$ROOT/requirements.txt" || {
            echo "Fehler: requirements.txt fehlt im Quellbaum." >&2
            exit 1
        }
        cp "$ROOT/requirements.txt" "$stage/opt/stempeluhr/requirements.txt"
        install -m 0644 "$ROOT/packaging/systemd/stempeluhr.service"             "$stage/etc/systemd/system/stempeluhr.service"
    fi

    # Application files. Do not copy the scripts tree twice: cp -a preserves
    # all terminal helper scripts including raspberry_hce_agent.py.
    for path in app scripts templates static; do
        if [ -e "$ROOT/$path" ]; then
            cp -a "$ROOT/$path" "$stage/opt/stempeluhr/"
        fi
    done

    if [ "$package" = "stempeluhr-terminal" ] || [ "$package" = "stempeluhr-all-in-one" ]; then
        test -f "$stage/opt/stempeluhr/scripts/raspberry_hce_agent.py" || {
            echo "Fehler: scripts/raspberry_hce_agent.py fehlt im Quellbaum." >&2
            exit 1
        }
        chmod 0755 "$stage/opt/stempeluhr/scripts/raspberry_hce_agent.py"
        install -m 0644 "$ROOT/packaging/systemd/stempeluhr-hce-agent.service" \
            "$stage/etc/systemd/system/stempeluhr-hce-agent.service"
    fi

    mkdir -p "$OUT"
    target="$OUT/${package}_${VERSION}_all.deb"
    dpkg-deb --root-owner-group --build "$stage" "$target"
    dpkg-deb --info "$target" >/dev/null
    if [ "$package" = "stempeluhr-server" ] || [ "$package" = "stempeluhr-all-in-one" ]; then
        dpkg-deb --contents "$target" | grep -q 'opt/stempeluhr/requirements.txt'
        dpkg-deb --contents "$target" | grep -q 'etc/systemd/system/stempeluhr.service'
    fi
    if [ "$package" = "stempeluhr-terminal" ] || [ "$package" = "stempeluhr-all-in-one" ]; then
        dpkg-deb --contents "$target" | grep -q 'opt/stempeluhr/scripts/raspberry_hce_agent.py'
        dpkg-deb --contents "$target" | grep -q 'etc/systemd/system/stempeluhr-hce-agent.service'
    fi
    echo "OK: $target"
}

rm -rf "$WORK"
mkdir -p "$WORK" "$OUT"
build_package stempeluhr-server
build_package stempeluhr-terminal
build_package stempeluhr-all-in-one
printf 'Pakete erfolgreich geprüft und erstellt in %s\n' "$OUT"
