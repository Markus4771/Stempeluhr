# Stempeluhr Professional – zentraler Projektkontext

> Verbindliche Wissensbasis für neue ChatGPT-Unterhaltungen. Zusätzlich immer aktuellen Quellcode, `version.txt`, `README.md` und `changelog.md` prüfen. Bei Abweichungen gilt der tatsächliche Quellcode.

## Projekt

- Repository: `Markus4771/Stempeluhr`
- Standardbranch: `main`
- Aktuelle Entwicklungs- und Testversion: **5.6.23**
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
- Datenbank-Secret: `/etc/stempeluhr/secrets/database.conf`
- GitHub-Token: `/etc/stempeluhr/secrets/github_token`
- GitHub-main-Runner: `/usr/local/sbin/stempeluhr-github-main-update`
- variable Daten: `/var/lib/stempeluhr`
- Backups: `/var/backups/stempeluhr`
- Dienst: `stempeluhr.service`
- Healthcheck: `/health`
- Versionsauskunft: `/version`
- Kiosk-Zeiterfassung: `/raspberry`
- Auswertung & Reporting: `/reports`
- Plausibilitätsprüfung: `/plausibility`
- Überstundenverwaltung: `/overtime-adjustments`
- Zusatz-Programme: `/additional-programs`
- Zusatz-Programm-Verwaltung: `/system/settings/general/additional-programs`
- Updateverwaltung: `/system/settings/updates`
- öffentliche Datenschutzerklärung: `/datenschutz`

## Version 5.6.23

Umgesetzt:

- Zusatz-Programme besitzen pro Eintrag eine Liste freigegebener Rollen
- Administratoren verwalten die Rollenfreigaben in der Zusatz-Programm-Konfiguration
- die Übersicht liefert nur aktive und für die angemeldete Rolle freigegebene Programme
- der Hauptmenüpunkt `Zusatz-Programme` wird dynamisch nur bei mindestens einem sichtbaren Programm eingeblendet
- bestehende Programme ohne gespeicherte Rollenliste bleiben für die bisherigen Standardrollen kompatibel sichtbar
- direkte Zugriffe auf die Übersicht liefern für nicht berechtigte Benutzer keine fremden Programme
- Rollenfreigaben und Änderungen werden im Audit-Protokoll dokumentiert
- Webreport, CSV, PDF und E-Mail-Anhang verwenden dieselbe serverseitige Filterung
- zukünftige und unvollständige Tage werden aus Zeilen, Stempelzeiten, Summen und Teamstatistik ausgeschlossen

## Bereits enthalten

- Kommen-/Gehen-Uhrzeiten direkt in der Tagesübersicht von `Auswertung & Reporting`
- normale Mitarbeiter sehen ausschließlich eigene Zeiten
- Teamleiter sehen nur zugeordnete Mitarbeiter
- Plausibilitätsmeldungen zurücksetzen
- Überstundenänderungen mit Mitarbeitergenehmigung per E-Mail
- administrierbare Stempelgründe am Raspberry-Kiosk
- Abwesenheitskalender je Abteilung

## Offene Prüfungen vor Freigabe 5.6.23

- Python-Syntax und FastAPI-Formularverarbeitung prüfen
- Rollenlisten bei neuen und bestehenden Zusatz-Programmen testen
- Hauptmenü mit Administrator, Personal, Teamleiter und Mitarbeiter testen
- Verhalten ohne freigegebenes Programm prüfen
- direkten Aufruf `/additional-programs` mit verschiedenen Rollen prüfen
- Debian-Paket bauen und SHA256 validieren
- Upgrade auf Testsystem installieren
- `/health` und `/version` prüfen

## Build

```bash
bash scripts/build_release.sh
sha256sum -c releases/stempeluhr_5.6.23_all.deb.sha256
```

## Startanweisung für neue Chats

> Arbeite am GitHub-Projekt `Markus4771/Stempeluhr`. Lies zuerst `NEUER_CHAT.md`, danach `CHATGPT_PROJEKTKONTEXT.md`, `version.txt`, `README.md` und `changelog.md`. Prüfe anschließend den tatsächlichen Quellcode. Bestätige zuerst Version und Ist-Stand. Keine Rekonstruktion, keine erfundenen Dateien und keine behaupteten Builds oder Releases.
