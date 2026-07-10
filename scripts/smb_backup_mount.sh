#!/bin/bash
set -euo pipefail

CONFIG_JSON="${1:-}"
if [ -z "$CONFIG_JSON" ] || [ ! -f "$CONFIG_JSON" ]; then
    echo "Fehler: Konfigurationsdatei fehlt."
    exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
    echo "Fehler: python3 fehlt."
    exit 1
fi

read_json() {
python3 - "$CONFIG_JSON" "$1" <<'PY'
import json, sys
path, key = sys.argv[1], sys.argv[2]
with open(path, "r", encoding="utf-8") as f:
    data = json.load(f)
print(data.get(key, ""))
PY
}

ACTION="$(read_json action)"
SERVER="$(read_json server)"
SHARE="$(read_json share)"
SUBPATH="$(read_json subpath)"
USERNAME="$(read_json username)"
PASSWORD="$(read_json password)"
DOMAIN="$(read_json domain)"
MOUNTPOINT="$(read_json mountpoint)"

if [ -z "$SERVER" ] || [ -z "$SHARE" ]; then
    echo "Fehler: SMB Server und Freigabe sind erforderlich."
    exit 1
fi

case "$MOUNTPOINT" in
    /mnt/*) ;;
    *) echo "Fehler: Mountpoint muss unter /mnt/ liegen."; exit 1 ;;
esac

if ! command -v mount.cifs >/dev/null 2>&1; then
    echo "Fehler: cifs-utils ist nicht installiert. Bitte ausführen: sudo apt install cifs-utils"
    exit 1
fi

mkdir -p "$MOUNTPOINT"
chown stempeluhr:stempeluhr "$MOUNTPOINT" || true
chmod 775 "$MOUNTPOINT" || true

mkdir -p /etc/stempeluhr
CRED="/etc/stempeluhr/smb_credentials"
{
    if [ -n "$USERNAME" ]; then
        echo "username=$USERNAME"
        echo "password=$PASSWORD"
    else
        echo "username=guest"
        echo "password="
    fi
    if [ -n "$DOMAIN" ]; then
        echo "domain=$DOMAIN"
    fi
} > "$CRED"
chmod 600 "$CRED"
chown root:root "$CRED"

FSTAB_LINE="//$SERVER/$SHARE $MOUNTPOINT cifs credentials=$CRED,uid=stempeluhr,gid=stempeluhr,file_mode=0664,dir_mode=0775,vers=3.0,iocharset=utf8,nofail,x-systemd.automount,_netdev 0 0"

touch /etc/fstab
cp /etc/fstab "/etc/fstab.stempeluhr.bak.$(date +%Y%m%d_%H%M%S)"
grep -v " $MOUNTPOINT cifs " /etc/fstab > /tmp/fstab.stempeluhr
echo "$FSTAB_LINE" >> /tmp/fstab.stempeluhr
cat /tmp/fstab.stempeluhr > /etc/fstab
rm -f /tmp/fstab.stempeluhr

systemctl daemon-reload || true

if mountpoint -q "$MOUNTPOINT"; then
    umount "$MOUNTPOINT" || true
fi

mount "$MOUNTPOINT"

DEST="$MOUNTPOINT"
if [ -n "$SUBPATH" ]; then
    DEST="$MOUNTPOINT/$SUBPATH"
fi
mkdir -p "$DEST"
chown stempeluhr:stempeluhr "$DEST" || true

TESTFILE="$DEST/.stempeluhr_smb_test_$(date +%s)"
echo "test" > "$TESTFILE"
rm -f "$TESTFILE"

echo "SMB erfolgreich eingerichtet und Schreibtest bestanden: //$SERVER/$SHARE -> $DEST"
exit 0
