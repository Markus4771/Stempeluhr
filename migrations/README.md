# Datenbankmigrationen

Ab Version 4.7.07 führt die Stempeluhr Schemaänderungen versioniert aus.

Die Tabelle `schema_migrations` speichert, welche Migrationen bereits angewendet wurden.

Manueller Lauf:

```bash
cd /opt/stempeluhr
./.venv/bin/python scripts/db_migrate.py
sudo systemctl restart stempeluhr
```

Die Migrationen sind idempotent: vorhandene Spalten werden erkannt und nicht erneut angelegt.
