#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
VERSION="${VERSION:-6.0.0}"
OUT="${OUT:-$ROOT/dist}"
WORK="${WORK:-$ROOT/.build-deb}"

build_package() {
    package="$1"
    stage="$WORK/$package"
    rm -rf "$stage"
    mkdir -p "$stage/DEBIAN" "$stage/opt/stempeluhr/scripts" "$stage/etc/systemd/system"
    cp "$ROOT/packaging/deb/$package/control" "$stage/DEBIAN/control"
    sed -i "s/^Version:.*/Version: $VERSION/" "$stage/DEBIAN/control"
    cp "$ROOT/packaging/deb/$package/postinst" "$stage/DEBIAN/postinst"
    cp "$ROOT/packaging/deb/$package/prerm" "$stage/DEBIAN/prerm"
    chmod 0755 "$stage/DEBIAN/postinst" "$stage/DEBIAN/prerm"
    install -m 0755 "$ROOT/scripts/raspberry_hce_agent.py" "$stage/opt/stempeluhr/scripts/raspberry_hce_agent.py"
    install -m 0644 "$ROOT/packaging/systemd/stempeluhr-hce-agent.service" "$stage/etc/systemd/system/stempeluhr-hce-agent.service"

    # Keep the existing application tree in the package where available.
    for path in app scripts templates static; do
        if [ -e "$ROOT/$path" ]; then
            mkdir -p "$stage/opt/stempeluhr"
            cp -a "$ROOT/$path" "$stage/opt/stempeluhr/"
        fi
    done
    mkdir -p "$OUT"
    dpkg-deb --root-owner-group --build "$stage" "$OUT/${package}_${VERSION}_all.deb"
}

rm -rf "$WORK"
mkdir -p "$WORK" "$OUT"
build_package stempeluhr-terminal
build_package stempeluhr-all-in-one
printf 'Pakete erstellt in %s\n' "$OUT"
