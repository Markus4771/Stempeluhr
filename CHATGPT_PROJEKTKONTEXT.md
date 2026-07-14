# Stempeluhr Professional – zentraler Projektkontext

> Verbindliche Wissensbasis für neue ChatGPT-Unterhaltungen. Zusätzlich immer aktuellen Quellcode, `version.txt`, `README.md` und `changelog.md` prüfen. Bei Abweichungen gilt der tatsächliche Quellcode.

## Projekt

- Repository: `Markus4771/Stempeluhr`
- Standardbranch: `main`
- Aktuelle Entwicklungs- und Testversion: **5.6.24**
- Zielplattform: Debian 13 und Raspberry Pi OS
- Backend: Python, FastAPI, Uvicorn, SQLAlchemy
- Standarddatenbank: PostgreSQL
- Installation und Update: Debian-Paket über `install.sh` oder Web-Updater

## Verbindliche Regeln

Bestehende Daten und Konfigurationen dürfen bei Updates nicht gelöscht werden. PostgreSQL bleibt Standarddatenbank. Secrets gehören niemals in Repository, Logs, URLs oder Diagnoseberichte. `.deb`, Prüfsumme und Release dürfen erst nach tatsächlichem Build und Test als fertig bezeichnet werden.

Bei jeder neuen Version synchron aktualisieren: `version.txt`, `app/version.py`, `debian/control`, `README.md`, `changelog.md`, `CHATGPT_PROJEKTKONTEXT.md` und bei Bedarf `NEUER_CHAT.md`.

## Wichtige Pfade und Funktionen

- Anwendung: `/opt/stempeluhr`
- Konfiguration: `/etc/stempeluhr/stempeluhr.env`
- GitHub-Token: `/etc/stempeluhr/secrets/github_token`
- Dienst: `stempeluhr.service`
- Healthcheck: `/health`
- Versionsauskunft: `/version`
- Kiosk-Zeiterfassung: `/raspberry`
- Auswertung & Reporting: `/reports`
- Zusatz-Programme: `/additional-programs`
- Zusatz-Programm-Verwaltung: `/system/settings/general/additional-programs`
- Stempelgründe: `/system/settings/stamp-reasons`

## Version 5.6.24

Umgesetzt:

- Hauptmenüpunkt `Zusatz-Programme` bleibt ausgeblendet, wenn keine Programme hinterlegt sind
- Programme werden zusätzlich nach Aktivstatus und Rollenfreigabe gefiltert
- Stempelgründe unterstützen `status` für reine Personenstatus ohne Arbeitszeitbuchung
- Stempelgründe unterstützen `status_clear` zum Zurücksetzen des Personenstatus
- Personenstatus werden als getrennte Systemeinstellung je Mitarbeiter gespeichert
- Statusänderungen werden im Audit-Protokoll dokumentiert
- ohne Auswahl bleibt die automatische Kommen-/Gehen-Buchung unverändert

## Bereits enthalten

- Kommen-/Gehen-Uhrzeiten in `Auswertung & Reporting`
- Rollenabhängige Zusatz-Programme
- Plausibilitätsmeldungen zurücksetzen
- Überstundenänderungen mit Mitarbeitergenehmigung per E-Mail
- Abwesenheitskalender je Abteilung

## Offene Prüfungen vor Freigabe 5.6.24

- Python-Syntax und Dienststart prüfen
- Menü ohne Zusatz-Programme testen
- Statusgründe `Außer Haus` und `Bitte nicht stören` testen
- Statusrücksetzung testen
- prüfen, dass Statusgründe keine TimeEntry-Buchung erzeugen
- Debian-Paket bauen und installieren
- `/health` und `/version` prüfen

## Build

```bash
bash scripts/build_release.sh
sha256sum -c releases/stempeluhr_5.6.24_all.deb.sha256
```

## Startanweisung für neue Chats

> Arbeite am GitHub-Projekt `Markus4771/Stempeluhr`. Lies zuerst `NEUER_CHAT.md`, danach `CHATGPT_PROJEKTKONTEXT.md`, `version.txt`, `README.md` und `changelog.md`. Prüfe anschließend den tatsächlichen Quellcode. Bestätige zuerst Version und Ist-Stand. Keine Rekonstruktion, keine erfundenen Dateien und keine behaupteten Builds oder Releases.
