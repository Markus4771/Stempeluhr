# Stempeluhr Professional 5.6.34

Webbasierte Zeiterfassung für Debian-Server und Raspberry-Pi-Terminals.

## Aktueller Stand

- Version: **5.6.34**
- Standarddatenbank: PostgreSQL
- Zielplattform: Debian / Raspberry Pi OS
- Standardbranch: `main`

## Änderungen in 5.6.34

- Mehrere RFID-/NFC-Medien können einem Mitarbeiter zugeordnet werden.
- Handy, Smartwatch, Karte, Ring und weitere Medien werden getrennt verwaltet.
- RFID-/NFC-UIDs werden vor dem Vergleich vereinheitlicht.
- Bestehende Werte aus `employees.rfid_code` werden automatisch übernommen.
- Das Backupformat enthält ein Manifest und SHA256-Prüfsummen.
- PostgreSQL-Dumps und Archive werden vor der Veröffentlichung geprüft.
- Backup-Dateien werden atomar erstellt und Prüfsummen auch auf SMB/NAS kopiert.

## Installation

```bash
cd ~/Stempeluhr
git pull --ff-only
bash scripts/build_release.sh
sudo apt install ./releases/stempeluhr_5.6.34_all.deb
```
