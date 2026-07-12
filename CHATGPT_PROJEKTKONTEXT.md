# Stempeluhr Professional – zentraler Projektkontext

> Verbindliche Wissensbasis für neue ChatGPT-Unterhaltungen. Zusätzlich immer aktuellen Quellcode, `version.txt`, `README.md` und `changelog.md` prüfen. Bei Abweichungen gilt der tatsächliche Quellcode.

## Projekt

- Repository: `Markus4771/Stempeluhr`
- Standardbranch: `main`
- Aktuelle Entwicklungs- und Testversion: **5.6.15**
- Letzte vor Beginn von 5.6.15 bestätigte Version: **5.6.13**
- Versionen 5.6.14 und 5.6.15 müssen noch vollständig auf der Proxmox-Test-VM abgenommen werden
- Zielplattform: Debian 13 und Raspberry Pi OS
- Backend: Python, FastAPI, Uvicorn, SQLAlchemy
- Standarddatenbank: PostgreSQL
- Installation und Update: Debian-Paket

## Verbindliche Regeln

Bestehende Daten und Konfigurationen dürfen bei Updates nicht gelöscht werden. PostgreSQL bleibt Standarddatenbank. Secrets gehören niemals in Repository, Logs, URLs oder Diagnoseberichte. `.deb`, Prüfsumme und Release dürfen erst nach tatsächlichem Build und Test als fertig bezeichnet werden.

Bei jeder neuen Version synchron aktualisieren: `version.txt`, `app/version.py`, `debian/control`, `README.md`, `changelog.md`, `CHATGPT_PROJEKTKONTEXT.md` und bei Bedarf `NEUER_CHAT.md`.

## Wichtige Pfade und Funktionen

- Anwendung: `/opt/stempeluhr`
- Konfiguration: `/etc/stempeluhr/stempeluhr.env`
- Datenbank-Secret: `/etc/stempeluhr/secrets/database.conf`
- variable Daten: `/var/lib/stempeluhr`
- Dienst: `stempeluhr.service`
- Healthcheck: `/health`
- Versionsauskunft: `/version`
- Rollen & Rechte: `/system/settings/roles`
- Zusatz-Programme: `/additional-programs`
- Konfiguration Zusatz-Programme: `/system/settings/general/additional-programs`
- Hilfe und Dokumentation: `/help`

## Version 5.6.15 – Dokumentation und Hilfesystem

Umgesetzt:

- neuer Hauptmenüpunkt **Hilfe & Dokumentation**
- Handbuchquellen unter `docs/manuals/`
- Administratorhandbuch
- Benutzerhandbuch
- Installations- und Einrichterhandbuch
- API-Handbuch
- gemeinsame Volltextsuche über alle Handbücher
- HTML-Leseansicht und browserbasierte Druckansicht
- PDF-Erzeugung direkt in der Anwendung mit ReportLab
- PDF-Routen `/help/{slug}/pdf`
- Hilfebereich nur für angemeldete Benutzer
- feste Kapitelnavigation mit Sprunglinks
- lokale Suche innerhalb eines geöffneten Handbuchs
- helle, kontrastreiche Codeblöcke mit automatischem Umbruch
- Kopierfunktion für Befehle, URLs und API-Beispiele
- responsive Darstellung für kleinere Bildschirme
- Druckansicht ohne Navigation und Bedienelemente
- keine Datenbankmigration und keine Änderung produktiver Daten

Zentrale Dateien:

- `app/routes/help_docs.py`
- `app/templates/help_index.html`
- `app/templates/help_manual.html`
- `app/static/help.css`
- `docs/manuals/administrator.md`
- `docs/manuals/benutzer.md`
- `docs/manuals/installation.md`
- `docs/manuals/api.md`

## Stand aus Version 5.6.14

- Rollen und Berechtigungen werden im vorhandenen Feld `roles.permissions` als JSON gespeichert
- Administrator behält immer Vollzugriff
- Standardrollen sind geschützt
- gruppierte Systemeinstellungs-Untermenüs mit Alle-aktivieren/Alle-deaktivieren
- Zusatz-Programme über HTTP/HTTPS, IP oder Hostname, Port und optionalen Pfad
- Zusatz-Programme sind bearbeitbar, aktivierbar und rollenabhängig sichtbar
- tatsächliche Router-Registrierung erfolgt über `app/routes/web.py`

## Bekannter offener Punkt

Der GitHub-Actions-Workflow **„Debian-Paket bauen und veröffentlichen“** ist zuletzt fehlgeschlagen. Der konkrete rote Fehler aus dem Joblog wurde noch nicht ausgewertet und muss vor einer automatischen Veröffentlichung behoben werden. Ein lokal gebautes Paket darf nur nach erfolgreichem Build und Test als fertig bezeichnet werden.

## Offene Prüfungen vor Freigabe 5.6.15

- Python-Syntax und Imports prüfen
- Debian-Paket bauen und SHA256 validieren
- Upgrade auf der Proxmox-Test-VM installieren
- `/help` und alle vier Handbücher öffnen
- feste Kapitelnavigation und Sprunglinks testen
- helle Codeblöcke und Kopierfunktion testen
- Suche nach `Backup`, `RFID`, `Passwort` und `API` testen
- alle vier PDF-Dateien erzeugen und öffnen
- Druckansicht testen
- prüfen, dass nicht angemeldete Aufrufe auf `/login` umleiten
- Zusatz-Programme und Rollen aus 5.6.14 erneut testen
- `/health`, `/version`, Mitarbeiter und Buchungen prüfen
- GitHub-Actions-Fehler anhand des Joblogs beheben
- erst danach Tag und GitHub Release veröffentlichen

## Build

```bash
bash scripts/build_release.sh
sha256sum -c releases/stempeluhr_5.6.15_all.deb.sha256
```

Erwartete Artefakte:

```text
releases/stempeluhr_5.6.15_all.deb
releases/stempeluhr_5.6.15_all.deb.sha256
releases/stempeluhr_5.6.15_build.log
releases/stempeluhr_5.6.15_BUILD_REPORT.md
```

## Startanweisung für neue Chats

> Arbeite am GitHub-Projekt `Markus4771/Stempeluhr`. Lies zuerst `NEUER_CHAT.md`, danach `CHATGPT_PROJEKTKONTEXT.md`, `version.txt`, `README.md` und `changelog.md`. Prüfe anschließend den tatsächlichen Quellcode. Bestätige zuerst Version und Ist-Stand. Keine Rekonstruktion, keine erfundenen Dateien und keine behaupteten Builds oder Releases.