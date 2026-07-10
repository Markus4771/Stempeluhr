#!/bin/bash
set -e
/opt/stempeluhr/.venv/bin/python /opt/stempeluhr/scripts/restore_backup.py "$@"

echo "Restore erfolgreich abgeschlossen."
exit 0
