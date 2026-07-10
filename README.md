# Stempeluhr Professional

Webbasierte Zeiterfassung für Debian-Server und Raspberry-Pi-Terminals.

## Aktueller Stand

- Version: **5.5.06**
- Backend: Python, FastAPI, Uvicorn
- Datenbank: PostgreSQL
- Plattform: Debian 13 / Raspberry Pi
- Paketname: `stempeluhr`

## Installation

```bash
sudo apt install ./releases/stempeluhr_5.5.06_all.deb
sudo systemctl status stempeluhr --no-pager
```

Das Debian-Paket richtet bei einer Neuinstallation PostgreSQL, den Datenbankbenutzer, die Datenbankverbindung und den Systemdienst ein.

## Repository-Struktur

- `source/` – Anwendungsquellcode
- `debian/` – Debian-Paketsteuerdateien und Installationsskripte
- `releases/` – installierbare Debian-Pakete
- `docs/` – Projekt-, Administrator- und Onboarding-Dokumentation

## Sicherheit

Produktive Zugangsdaten, `.env`-Dateien, Datenbanken, Uploads und Sicherungen gehören nicht in Git.
