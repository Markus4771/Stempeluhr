# Stempeluhr Professional – zentraler Projektkontext

> Verbindliche Wissensbasis für neue ChatGPT-Unterhaltungen. Zusätzlich immer aktuellen Quellcode, `version.txt`, `README.md` und `changelog.md` prüfen. Bei Abweichungen gilt der tatsächliche Quellcode.

## Projekt

- Repository: `Markus4771/Stempeluhr`
- Standardbranch: `main`
- Aktuelle Entwicklungs- und Testversion: **5.6.18**
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
- Persönlicher Report: `/reports`
- Plausibilitätsprüfung: `/plausibility`
- öffentliche Datenschutzerklärung: `/datenschutz`

## Version 5.6.18

Umgesetzt:

- Plausibilitätsfilter bleiben nach dem Speichern erhalten
- Status und Kommentar werden im Bearbeitungsformular wieder angezeigt
- Stempelzeiten werden im gewählten Reportzeitraum aufgeführt
- normale Mitarbeiter werden serverseitig immer auf die eigene Mitarbeiter-ID eingeschränkt
- Teamleiter sehen nur die ihnen zugeordneten Mitarbeiter
- Personal und Administratoren behalten den vorgesehenen erweiterten Zugriff
- öffentliche Datenschutzerklärung und Link bei der Kontoeinrichtung

## Offene Prüfungen vor Freigabe 5.6.18

- Python-Syntax und Imports prüfen
- Debian-Paket bauen und SHA256 validieren
- Upgrade auf Testsystem installieren
- Plausibilitätsfilter nach Statusänderung prüfen
- Mitarbeiterreport ausschließlich mit eigenen Daten prüfen
- Teamleiterreport mit zugeordneten Mitarbeitern prüfen
- Stempelzeiten im Report prüfen
- Kontoeinrichtung und `/datenschutz` prüfen
- `/health` und `/version` prüfen

## Build

```bash
bash scripts/build_release.sh
sha256sum -c releases/stempeluhr_5.6.18_all.deb.sha256
```

## Startanweisung für neue Chats

> Arbeite am GitHub-Projekt `Markus4771/Stempeluhr`. Lies zuerst `NEUER_CHAT.md`, danach `CHATGPT_PROJEKTKONTEXT.md`, `version.txt`, `README.md` und `changelog.md`. Prüfe anschließend den tatsächlichen Quellcode. Bestätige zuerst Version und Ist-Stand. Keine Rekonstruktion, keine erfundenen Dateien und keine behaupteten Builds oder Releases.
