# Stempeluhr Professional – zentraler Projektkontext

> Verbindliche Wissensbasis für neue ChatGPT-Unterhaltungen. Zusätzlich immer aktuellen Quellcode, `version.txt`, `README.md` und `changelog.md` prüfen. Bei Abweichungen gilt der tatsächliche Quellcode.

## Projekt

- Repository: `Markus4771/Stempeluhr`
- Standardbranch: `main`
- Aktuelle Entwicklungs- und Testversion: **5.6.16**
- Letzte vor Beginn von 5.6.16 bestätigte Version: **5.6.13**
- Versionen 5.6.14 bis 5.6.16 müssen noch vollständig auf der Proxmox-Test-VM abgenommen werden
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
- Abwesenheiten: `/vacation`
- Abwesenheitsarten: `/system/settings/absence-types`
- Rollen & Rechte: `/system/settings/roles`
- Zusatz-Programme: `/additional-programs`
- Hilfe und Dokumentation: `/help`

## Version 5.6.16 – Abwesenheiten und Installation

Umgesetzt:

- Hauptnavigation auf einen Eintrag **Abwesenheiten** reduziert
- separaten Hauptmenüpunkt **Meine Abwesenheiten** entfernt
- Abwesenheitsübersicht mit Kacheln für Antrag, eigene Abwesenheiten, Genehmigungen, Kalender und Resturlaub
- Administrator-Kachel für Abwesenheitsarten
- gespeicherte Einstellung `requires_approval` wird beim Erstellen eines Antrags ausgewertet
- genehmigungsfreie Arten wie `Krank` erhalten sofort den Status `genehmigt`
- genehmigungsfreie Arten erscheinen nicht in offenen Genehmigungen
- Formularstruktur der Abwesenheitsarten korrigiert
- `install.sh` für Installation, Update, Build, Backup, Restore, Status, Logs, Version und Diagnose
- keine destruktive Datenbankmigration

## Stand aus Version 5.6.15

- integrierter Hilfebereich mit Administrator-, Benutzer-, Installations- und API-Handbuch
- Volltextsuche, HTML-, Druck- und PDF-Ansichten
- Handbuchquellen unter `docs/manuals/`
- Hilfebereich nur für angemeldete Benutzer

## Bekannter offener Punkt

Der GitHub-Actions-Workflow **„Debian-Paket bauen und veröffentlichen“** war zuletzt fehlgeschlagen. Der konkrete Fehler muss vor einer automatischen Veröffentlichung anhand des Joblogs geprüft werden. Ein lokal gebautes Paket darf nur nach erfolgreichem Build und Test als fertig bezeichnet werden.

## Offene Prüfungen vor Freigabe 5.6.16

- Python-Syntax und Imports prüfen
- Debian-Paket bauen und SHA256 validieren
- Upgrade auf der Proxmox-Test-VM installieren
- Abwesenheitsart `Krank` ohne Genehmigung anlegen und Status prüfen
- genehmigungspflichtige Abwesenheitsart mit offenem Antrag prüfen
- Hauptnavigation auf nur einen Eintrag `Abwesenheiten` prüfen
- Rollenabhängigkeit der Kacheln prüfen
- Backup und Update mit `sudo bash install.sh update` prüfen
- `/help`, PDF-Erzeugung, Rollen und Zusatz-Programme erneut testen
- `/health`, `/version`, Mitarbeiter und Buchungen prüfen
- erst danach Tag und GitHub Release veröffentlichen

## Build

```bash
bash scripts/build_release.sh
sha256sum -c releases/stempeluhr_5.6.16_all.deb.sha256
```

Erwartete Artefakte:

```text
releases/stempeluhr_5.6.16_all.deb
releases/stempeluhr_5.6.16_all.deb.sha256
releases/stempeluhr_5.6.16_build.log
releases/stempeluhr_5.6.16_BUILD_REPORT.md
```

## Startanweisung für neue Chats

> Arbeite am GitHub-Projekt `Markus4771/Stempeluhr`. Lies zuerst `NEUER_CHAT.md`, danach `CHATGPT_PROJEKTKONTEXT.md`, `version.txt`, `README.md` und `changelog.md`. Prüfe anschließend den tatsächlichen Quellcode. Bestätige zuerst Version und Ist-Stand. Keine Rekonstruktion, keine erfundenen Dateien und keine behaupteten Builds oder Releases.
