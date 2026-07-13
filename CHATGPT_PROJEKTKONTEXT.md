# Stempeluhr Professional – zentraler Projektkontext

> Verbindliche Wissensbasis für neue ChatGPT-Unterhaltungen. Zusätzlich immer aktuellen Quellcode, `version.txt`, `README.md` und `changelog.md` prüfen. Bei Abweichungen gilt der tatsächliche Quellcode.

## Projekt

- Repository: `Markus4771/Stempeluhr`
- Standardbranch: `main`
- Aktuelle Entwicklungs- und Testversion: **5.6.21**
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
- GitHub-Token: `/etc/stempeluhr/secrets/github_token`
- variable Daten: `/var/lib/stempeluhr`
- Backups: `/var/backups/stempeluhr`
- Dienst: `stempeluhr.service`
- Healthcheck: `/health`
- Versionsauskunft: `/version`
- Kiosk-Zeiterfassung: `/raspberry`
- Persönlicher Report: `/reports`
- Plausibilitätsprüfung: `/plausibility`
- Überstundenverwaltung: `/overtime-adjustments`
- Updateverwaltung: `/system/settings/updates`
- öffentliche Datenschutzerklärung: `/datenschutz`

## Version 5.6.21

Umgesetzt:

- Kommen- und Gehen-Uhrzeiten werden direkt im Template von `Mein Report` angezeigt
- die Datenbankabfrage filtert nach zulässigen Mitarbeitern sowie exakt nach Von-/Bis-Datum
- normale Mitarbeiter sehen ausschließlich eigene Buchungen
- Teamleiter sehen ausschließlich zugeordnete Mitarbeiter
- Menüeinträge für Überstunden und Plausibilität sind für Teamleiter, Personal und Administratoren sichtbar
- Updateverwaltung fragt bei fehlendem GitHub-Token per Eingabefenster nach
- Token kann in der Updateverwaltung ersetzt werden
- Speicherung unter `/etc/stempeluhr/secrets/github_token` mit restriktiven Dateirechten
- Report-E-Mail und automatischer Monatsversand bleiben erhalten

## Enthalten aus Version 5.6.20

- Plausibilitätsmeldungen zurücksetzen
- Überstundenänderungen mit Zielwert und Wirksamkeitszeitpunkt
- verpflichtende Mitarbeitergenehmigung per E-Mail

## Offene Prüfungen vor Freigabe 5.6.21

- Python-Syntax und Imports prüfen
- Debian-Paket bauen und SHA256 validieren
- Upgrade auf Testsystem installieren
- Kommen-/Gehen-Zeiten im persönlichen Report prüfen
- Mitarbeiter- und Teamleiterrechte prüfen
- Plausibilitäts-Reset prüfen
- Überstundenantrag, Genehmigung, Ablehnung und geplante Ausführung prüfen
- Token-Popup und geschützte Speicherung prüfen
- GitHub-Release-Abfrage mit privatem Repository prüfen
- `/health` und `/version` prüfen

## Build

```bash
bash scripts/build_release.sh
sha256sum -c releases/stempeluhr_5.6.21_all.deb.sha256
```

## Startanweisung für neue Chats

> Arbeite am GitHub-Projekt `Markus4771/Stempeluhr`. Lies zuerst `NEUER_CHAT.md`, danach `CHATGPT_PROJEKTKONTEXT.md`, `version.txt`, `README.md` und `changelog.md`. Prüfe anschließend den tatsächlichen Quellcode. Bestätige zuerst Version und Ist-Stand. Keine Rekonstruktion, keine erfundenen Dateien und keine behaupteten Builds oder Releases.
