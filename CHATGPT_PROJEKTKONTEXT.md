# Stempeluhr Professional – zentraler Projektkontext

> Verbindliche Wissensbasis für neue ChatGPT-Unterhaltungen. Zusätzlich immer aktuellen Quellcode, `version.txt`, `README.md` und `changelog.md` prüfen. Bei Abweichungen gilt der tatsächliche Quellcode.

## Projekt

- Repository: `Markus4771/Stempeluhr`
- Standardbranch: `main`
- Aktuelle Entwicklungs- und Testversion: **5.6.17**
- Zielplattform: Debian 13 und Raspberry Pi OS
- Backend: Python, FastAPI, Uvicorn, SQLAlchemy
- Standarddatenbank: PostgreSQL
- Installation und Update: Debian-Paket über `install.sh`

## Verbindliche Regeln

Bestehende Daten und Konfigurationen dürfen bei Updates nicht gelöscht werden. PostgreSQL bleibt Standarddatenbank. Secrets gehören niemals in Repository, Logs, URLs oder Diagnoseberichte. `.deb`, Prüfsumme und Release dürfen erst nach tatsächlichem Build und Test als fertig bezeichnet werden.

Bei jeder neuen Version synchron aktualisieren: `version.txt`, `app/version.py`, `debian/control`, `README.md`, `changelog.md`, `CHATGPT_PROJEKTKONTEXT.md` und bei Bedarf `NEUER_CHAT.md`.

## Wichtige Pfade und Funktionen

- Anwendung: `/opt/stempeluhr`
- Konfiguration: `/etc/stempeluhr/stempeluhr.env`
- Datenbank-Secret: `/etc/stempeluhr/secrets/database.conf`
- variable Daten: `/var/lib/stempeluhr`
- Backups: `/var/backups/stempeluhr`
- Dienst: `stempeluhr.service`
- Healthcheck: `/health`
- Versionsauskunft: `/version`
- Kiosk-Zeiterfassung: `/raspberry`
- Abwesenheiten: `/vacation`
- Abwesenheitsarten: `/system/settings/absence-types`
- Rollen & Rechte: `/system/settings/roles`
- Zusatz-Programme: `/additional-programs`
- Hilfe und Dokumentation: `/help`

## Version 5.6.17 – Kiosk-Navigation

Umgesetzt:

- Menüpunkt **Zeiterfassung** aus der normalen Hauptnavigation entfernt
- Route `/raspberry` bleibt unverändert verfügbar
- Raspberry-Kiosk kann die Zeiterfassung weiterhin direkt und automatisch öffnen
- keine Änderung an RFID, Buchungslogik oder produktiven Daten

## Stand aus Version 5.6.16

- Hauptnavigation auf einen Eintrag **Abwesenheiten** reduziert
- separaten Hauptmenüpunkt **Meine Abwesenheiten** entfernt
- Abwesenheitsübersicht mit rollenabhängigen Kacheln
- genehmigungsfreie Arten wie `Krank` erhalten sofort den Status `genehmigt`
- `install.sh` für Installation, Update, Build, Backup, Restore, Status, Logs, Version und Diagnose

## Offene Prüfungen vor Freigabe 5.6.17

- Python-Syntax und Imports prüfen
- Debian-Paket bauen und SHA256 validieren
- Upgrade auf der Proxmox-Test-VM installieren
- normale Hauptnavigation ohne `Zeiterfassung` prüfen
- direkten Aufruf `/raspberry` und Kiosk-Autostart prüfen
- Abwesenheitsnavigation und Genehmigungslogik erneut testen
- `/health` und `/version` prüfen
- erst danach Tag und GitHub Release veröffentlichen

## Build

```bash
bash scripts/build_release.sh
sha256sum -c releases/stempeluhr_5.6.17_all.deb.sha256
```

Erwartete Artefakte:

```text
releases/stempeluhr_5.6.17_all.deb
releases/stempeluhr_5.6.17_all.deb.sha256
releases/stempeluhr_5.6.17_build.log
releases/stempeluhr_5.6.17_BUILD_REPORT.md
```

## Startanweisung für neue Chats

> Arbeite am GitHub-Projekt `Markus4771/Stempeluhr`. Lies zuerst `NEUER_CHAT.md`, danach `CHATGPT_PROJEKTKONTEXT.md`, `version.txt`, `README.md` und `changelog.md`. Prüfe anschließend den tatsächlichen Quellcode. Bestätige zuerst Version und Ist-Stand. Keine Rekonstruktion, keine erfundenen Dateien und keine behaupteten Builds oder Releases.
