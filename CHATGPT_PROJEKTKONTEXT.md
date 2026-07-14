# Stempeluhr Professional – zentraler Projektkontext

> Verbindliche Wissensbasis für neue ChatGPT-Unterhaltungen. Zusätzlich immer aktuellen Quellcode, `version.txt`, `README.md` und `changelog.md` prüfen. Bei Abweichungen gilt der tatsächliche Quellcode.

## Projekt

- Repository: `Markus4771/Stempeluhr`
- Standardbranch: `main`
- Aktuelle Entwicklungs- und Testversion: **5.6.25**
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

## Version 5.6.25

Umgesetzt:

- Hauptmenüpunkt `Zusatz-Programme` wird bei leerer oder für die Rolle nicht sichtbarer Programmliste vollständig aus dem DOM entfernt
- die API-Sichtbarkeitsprüfung bleibt serverseitig nach Aktivstatus und Rollenfreigabe gefiltert
- Fehler beim Abruf der Sichtbarkeit führen zum sicheren Entfernen des Menüpunktes
- reine Personenstatus und Statusrücksetzung aus 5.6.24 bleiben enthalten
- ohne Auswahl bleibt die automatische Kommen-/Gehen-Buchung unverändert

## Bereits enthalten

- Kommen-/Gehen-Uhrzeiten in `Auswertung & Reporting`
- rollenabhängige Zusatz-Programme
- Plausibilitätsmeldungen zurücksetzen
- Überstundenänderungen mit Mitarbeitergenehmigung per E-Mail
- Abwesenheitskalender je Abteilung
- reine Personenstatus als Stempelgrund ohne Arbeitszeitbuchung

## Offene Prüfungen vor Freigabe 5.6.25

- Python-Syntax und Dienststart prüfen
- Menü ohne Zusatz-Programme mit mehreren Rollen testen
- prüfen, dass der Link auch bei API-Fehlern nicht sichtbar bleibt
- Statusgründe `Außer Haus` und `Bitte nicht stören` testen
- prüfen, dass Statusgründe keine TimeEntry-Buchung erzeugen
- Debian-Paket bauen und installieren
- `/health` und `/version` prüfen

## Build

```bash
bash scripts/build_release.sh
sha256sum -c releases/stempeluhr_5.6.25_all.deb.sha256
```

## Startanweisung für neue Chats

> Arbeite am GitHub-Projekt `Markus4771/Stempeluhr`. Lies zuerst `NEUER_CHAT.md`, danach `CHATGPT_PROJEKTKONTEXT.md`, `version.txt`, `README.md` und `changelog.md`. Prüfe anschließend den tatsächlichen Quellcode. Bestätige zuerst Version und Ist-Stand. Keine Rekonstruktion, keine erfundenen Dateien und keine behaupteten Builds oder Releases.
