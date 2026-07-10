#!/bin/bash
set -e

cat >/etc/sudoers.d/stempeluhr-backup <<'EOF'
stempeluhr ALL=(root) NOPASSWD: /opt/stempeluhr/scripts/backup_root.sh
stempeluhr ALL=(root) NOPASSWD: /opt/stempeluhr/scripts/restore_root.sh
stempeluhr ALL=(root) NOPASSWD: /opt/stempeluhr/scripts/smb_backup_mount.sh *
EOF

chmod 440 /etc/sudoers.d/stempeluhr-backup
echo "sudoers-Regel installiert: stempeluhr darf Backup und Restore ohne Passwort starten."
