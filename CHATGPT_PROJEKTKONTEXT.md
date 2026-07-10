# Stempeluhr Professional – zentraler Projektkontext

> Diese Datei ist die verbindliche Wissensbasis für neue ChatGPT-Unterhaltungen. Vor jeder Änderung müssen zusätzlich der aktuelle Quellcode, `version.txt`, `README.md` und `changelog.md` geprüft werden. Bei Abweichungen gilt der tatsächliche Quellcode.

## Projekt

- Name: **Stempeluhr Professional**
- Repository: `Markus4771/Stempeluhr`
- Standardbranch: `main`
- Aktuelle Version: **5.5.09**
- Zielplattform: Debian 13 und Raspberry Pi OS
- Backend: Python, FastAPI, Uvicorn, SQLAlchemy
- Standarddatenbank: PostgreSQL
- Installation: Debian-Paket

## Ziel und verbindliche Regeln

Professionelle, updatefähige und datenschutzorientierte Zeiterfassung für Raspberry-Pi-Terminals und Linux-Server. PostgreSQL bleibt Standarddatenbank. Bestehende Daten und Konfigurationen dürfen bei Updates nicht gelöscht werden. Secrets gehören niemals ins Repository oder in Diagnoseberichte. Debian 13, Raspberry Pi OS, Wayland und labwc sind zu berücksichtigen.

Bei jeder neuen Version synchron aktualisieren:

- `version.txt`
- `app/version.py`
- `debian/control`
- `README.md`
- `changelog.md`
- `CHATGPT_PROJEKTKONTEXT.md`

Die Dateien `VERSION` und `CHANGELOG.md` dürfen nicht existieren.

## Aktueller Funktionsstand

Zum System gehören Mitarbeiterverwaltung, Arbeitszeiterfassung, RFID, Dashboard, Rollen und Rechte, Plausibilitätsprüfung, Korrekturworkflow, DSGVO, REST-API, HTTPS, CalDAV/iCal, Reporting, PDF/CSV-Export, E-Mail-Funktionen, Update/Backup, Raspberry-Kiosk, Agent, Heartbeat, Monitoring, Onboarding, Offboarding und Systemdiagnose.

## Architektur und Betrieb

- Anwendung: `/opt/stempeluhr`
- Konfiguration: `/etc/stempeluhr/stempeluhr.env`
- variable Daten: `/var/lib/stempeluhr`
- Logs: systemd-Journal und `/var/log/stempeluhr`
- Dienst: `stempeluhr.service`
- Standardport: 8000
- Healthcheck: `/health`
- Versionsauskunft: `/version`
- Onboarding und Offboarding: unter **Systemeinstellungen → Personal & Arbeitszeit**
- Systemdiagnose: über **Systemeinstellungen → Wartung → Systemdiagnose**
- Diagnose-Seite: `/system/diagnostics`
- Diagnose-API: `/diagnostics` und `/api/v1/diagnostics` (Administrator)
- Diagnosebericht: `/system/diagnostics/report` (Administrator)

## Datenbankregeln

- Standarddatenbank und Rolle: `stempeluhr`
- Zugangsdaten ausschließlich aus geschützter Konfiguration
- SQLAlchemy-Verbindungen müssen Sonderzeichen sicher verarbeiten
- lokale Verbindungen dürfen keine Root-Zertifikatsumgebung erben
- Rollenpasswörter bei normalen Updates nicht verändern
- Migrationen wiederholbar und PostgreSQL-kompatibel ausführen
- keine produktiven Daten in Pakete oder Repository aufnehmen

## Version 5.5.09

Schwerpunkt: logischere Einordnung von Onboarding und Offboarding.

Umgesetzt:

- Offboarding aus dem Wartungsbereich entfernt
- Offboarding direkt neben Onboarding unter `Personal & Arbeitszeit` eingeordnet
- Beschreibung der Systemeinstellungsübersicht angepasst
- bestehende Berechtigungs- und Modulsteuerung für Offboarding erhalten
- keine Datenbankmodelle geändert; keine Schema-Migration erforderlich

## Debian-Buildsystem

Lokaler Build:

```bash
bash scripts/build_release.sh
```

Erwartete Artefakte:

```text
releases/stempeluhr_5.5.09_all.deb
releases/stempeluhr_5.5.09_all.deb.sha256
releases/stempeluhr_5.5.09_build.log
releases/stempeluhr_5.5.09_BUILD_REPORT.md
```

Ein Buildbericht ersetzt keinen Installations- und Upgradetest.

## Offene Aufgaben

Priorität hoch:

- 5.5.09 bauen und Paketmetadaten prüfen
- Upgrade von produktiver 5.5.08 auf 5.5.09 testen
- Position von Onboarding und Offboarding in den Systemeinstellungen prüfen
- `/health` und `/version` prüfen
- Erhalt von Mitarbeitern und Buchungen bestätigen
- Raspberry-Screenshots unter Wayland/labwc stabilisieren
- Heartbeat-Status dauerhaft korrekt darstellen

Priorität mittel:

- API-Dokumentation vervollständigen
- Testabdeckung für Login, Buchung, Plausibilität, Onboarding und Update erhöhen
- Backup- und Rollbacktests ergänzen
- optional `lintian` integrieren

## Releasefreigabe

Eine Version gilt erst als freigegeben, wenn Versionen und Dokumentation übereinstimmen, `.deb`/SHA256/Buildlog/Buildbericht vorhanden sind, das Upgrade getestet wurde, der Dienst läuft, `/health` die erwartete Version meldet und bestehende Daten erhalten sind.

## Startanweisung für neue Chats

> Arbeite am GitHub-Projekt `Markus4771/Stempeluhr`. Lies zuerst `NEUER_CHAT.md`, anschließend `CHATGPT_PROJEKTKONTEXT.md`, `version.txt`, `README.md` und `changelog.md`. Prüfe danach den tatsächlichen aktuellen Quellcode und bestätige zuerst Version und Ist-Stand. Arbeite ausschließlich auf Basis dieses Repository-Stands weiter. Keine Rekonstruktion, keine erfundenen Dateien und keine behaupteten Releases ohne echten Build.
