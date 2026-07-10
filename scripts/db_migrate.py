#!/usr/bin/env python3
"""Datenbankmigrationen manuell ausführen.

Auf dem Raspberry Pi aus dem Projektordner starten:
    /opt/stempeluhr/.venv/bin/python scripts/db_migrate.py
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db_migrations import migration_status, run_migrations  # noqa: E402

if __name__ == "__main__":
    before = migration_status()
    print("Offene Migrationen vor Start:", before["pending"])
    executed = run_migrations()
    print("Ausgeführt:", executed if executed else "keine")
    after = migration_status()
    print("Aktueller Stand:", after)
