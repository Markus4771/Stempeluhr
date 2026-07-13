# Stempeluhr Professional – zentraler Projektkontext

> Verbindliche Wissensbasis für neue ChatGPT-Unterhaltungen. Zusätzlich immer aktuellen Quellcode, `version.txt`, `README.md` und `changelog.md` prüfen. Bei Abweichungen gilt der tatsächliche Quellcode.

## Projekt

- Repository: `Markus4771/Stempeluhr`
- Standardbranch: `main`
- Aktuelle Entwicklungs- und Testversion: **5.6.19**
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
- GitHub-Token für privaten Release-Zugriff: `/etc/stempeluhr/secrets/github_token`
- variable Daten: `/var/lib/stempeluhr`
- Backups: `/var/backups/stempeluhr`
- Dienst: `stempeluhr.service`
- Healthcheck: `/health`
- Versionsauskunft: `/version`
- Kiosk-Zeiterfassung: `/raspberry`
- Persönlicher Report: `/reports`
- Report-Stempelzeiten: `/reports/stamp-entries`
- Plausibilitätsprüfung: `/plausibility`
- öffentliche Datenschutzerklärung: `/datenschutz`

## Version 5.6.19

Umgesetzt:

- Stempelzeiten werden serverseitig exakt nach Mitarbeiter und Zeitraum geladen
- allgemeine Begrenzung auf die letzten 300 Buchungen entfernt
- Kommen-/Gehen-Bezeichnungen im Report vereinheitlicht
- Mitarbeiter bleiben auf die eigenen Zeiten beschränkt
- Teamleiter sehen ausschließlich zugeordnete Mitarbeiter
- privater GitHub-Release-Zugriff über Secret-Datei oder Umgebungsvariable
- präzisere Meldung bei HTTP 404 oder fehlendem Release

## Offene Prüfungen vor Freigabe 5.6.19

- Python-Syntax und Imports prüfen
- Debian-Paket bauen und SHA256 validieren
- Upgrade auf Testsystem installieren
- persönlichen Report mit Kommen-/Gehen-Buchungen prüfen
- Zeitraumfilter mit älteren Buchungen prüfen
- Mitarbeiter- und Teamleiterrechte prüfen
- GitHub-Release-Abfrage mit privatem Repository und Token prüfen
- `/health` und `/version` prüfen

## Build

```bash
bash scripts/build_release.sh
sha256sum -c releases/stempeluhr_5.6.19_all.deb.sha256
```

## Startanweisung für neue Chats

> Arbeite am GitHub-Projekt `Markus4771/Stempeluhr`. Lies zuerst `NEUER_CHAT.md`, danach `CHATGPT_PROJEKTKONTEXT.md`, `version.txt`, `README.md` und `changelog.md`. Prüfe anschließend den tatsächlichen Quellcode. Bestätige zuerst Version und Ist-Stand. Keine Rekonstruktion, keine erfundenen Dateien und keine behaupteten Builds oder Releases.
