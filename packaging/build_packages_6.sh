#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
VERSION="${VERSION:-6.0.1}"
OUT="${OUT:-$ROOT/dist}"
WORK="${WORK:-$ROOT/.build-deb}"

command -v dpkg-deb >/dev/null 2>&1 || {
    echo "Fehler: dpkg-deb fehlt." >&2
    exit 1
}

prepare_control() {
    package="$1"
    stage="$2"

    mkdir -p "$stage/DEBIAN"
    cp "$ROOT/packaging/deb/$package/control" "$stage/DEBIAN/control"
    sed -i "s/^Version:.*/Version: $VERSION/" "$stage/DEBIAN/control"

    if [ "$package" = "stempeluhr-all-in-one" ]; then
        sed -i "s/^Depends:.*/Depends: stempeluhr-server (= $VERSION), stempeluhr-terminal (= $VERSION)/" \
            "$stage/DEBIAN/control"
    fi

    for script in postinst prerm; do
        if [ -f "$ROOT/packaging/deb/$package/$script" ]; then
            cp "$ROOT/packaging/deb/$package/$script" "$stage/DEBIAN/$script"
            chmod 0755 "$stage/DEBIAN/$script"
        fi
    done
}

finish_package() {
    package="$1"
    stage="$2"
    target="$OUT/${package}_${VERSION}_all.deb"
    contents="$WORK/${package}.contents"

    dpkg-deb --root-owner-group --build "$stage" "$target"
    dpkg-deb --info "$target" >/dev/null
    dpkg-deb --contents "$target" > "$contents"

    echo "OK: $target"
}

build_server() {
    package="stempeluhr-server"
    stage="$WORK/$package"

    rm -rf "$stage"
    mkdir -p "$stage/opt/stempeluhr" "$stage/etc/systemd/system"

    prepare_control "$package" "$stage"

    test -f "$ROOT/requirements.txt"
    cp "$ROOT/requirements.txt" "$stage/opt/stempeluhr/requirements.txt"

    for path in app scripts templates static; do
        if [ -e "$ROOT/$path" ]; then
            cp -a "$ROOT/$path" "$stage/opt/stempeluhr/"
        fi
    done

    install -m 0644 \
        "$ROOT/packaging/systemd/stempeluhr.service" \
        "$stage/etc/systemd/system/stempeluhr.service"

    finish_package "$package" "$stage"
}

build_terminal() {
    package="stempeluhr-terminal"
    stage="$WORK/$package"

    rm -rf "$stage"
    mkdir -p \
        "$stage/opt/stempeluhr-terminal" \
        "$stage/etc/systemd/system" \
        "$stage/etc/stempeluhr" \
        "$stage/var/lib/stempeluhr" \
        "$stage/var/log/stempeluhr"

    prepare_control "$package" "$stage"

    install -m 0755 \
        "$ROOT/packaging/terminal/terminal_agent.py" \
        "$stage/opt/stempeluhr-terminal/terminal_agent.py"

    install -m 0755 \
        "$ROOT/packaging/terminal/configure-terminal.sh" \
        "$stage/opt/stempeluhr-terminal/configure-terminal.sh"

    install -m 0644 \
        "$ROOT/packaging/systemd/stempeluhr-terminal.service" \
        "$stage/etc/systemd/system/stempeluhr-terminal.service"

    finish_package "$package" "$stage"
}

build_all_in_one() {
    package="stempeluhr-all-in-one"
    stage="$WORK/$package"

    rm -rf "$stage"
    mkdir -p "$stage"

    prepare_control "$package" "$stage"
    finish_package "$package" "$stage"
}

rm -rf "$WORK"
mkdir -p "$WORK" "$OUT"

build_server
build_terminal
build_all_in_one

printf 'Pakete erfolgreich erstellt in %s\n' "$OUT"
