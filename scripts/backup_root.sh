#!/bin/bash
set -e
/opt/stempeluhr/.venv/bin/python /opt/stempeluhr/scripts/backup_gfs.py "${1:-daily}"
