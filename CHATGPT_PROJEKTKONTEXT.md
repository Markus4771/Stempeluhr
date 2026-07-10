# Stempeluhr Professional – zentraler Projektkontext

> Diese Datei ist die verbindliche Wissensbasis für neue ChatGPT-Unterhaltungen. Vor jeder Änderung müssen zusätzlich der aktuelle Quellcode, `version.txt`, `README.md` und `changelog.md` geprüft werden. Bei Abweichungen gilt der tatsächliche Quellcode.

## Projekt

- Name: **Stempeluhr Professional**
- Repository: `Markus4771/Stempeluhr`
- Standardbranch: `main`
- Aktuelle Version: **5.6.00**
- Zielplattform: Debian 13 und Raspberry Pi OS
- Backend: Python, FastAPI, Uvicorn, SQLAlchemy
- Standarddatenbank: PostgreSQL
- Installation: Debian-Paket

## Verbindliche Regeln

PostgreSQL bleibt Standarddatenbank. Bestehende Daten und Konfigurationen dürfen bei Updates nicht gelöscht werden. Secrets gehören niemals ins Repository, in Logs oder Diagnoseberichte. Debian 13, Raspberry Pi OS, Wayland und labwc sind zu berücksichtigen. Paketartefakte gelten erst nach tatsächlichem Build und Prüfung als fertig.

Bei jeder neuen Version synchron aktualisieren:

- `version.txt`
- `app/version.py`
- `debian/control`
- `README.md`
- `changelog.md`
- `CHATGPT_PROJEKTKONTEXT.md`

Die Dateien `VERSION` und `CHANGELOG.md` dürfen nicht existieren.

## Aktueller Funktionsstand

Zum System gehören Mitarbeiterverwaltung, Arbeitszeiterfassung, RFID, Dashboard, Rollen und Rechte, Plausibilitätsprüfung, Korrekturworkflow, DSGVO, REST-API, HTTPS, CalDAV/iCal, Reporting, PDF/CSV-Export, E-Mail-Funktionen, Update/Backup, Raspberry-Kiosk, Agent, Heartbeat, Monitoring, Onboarding, Offboarding, Systemdiagnose und ein mehrstufiger Einrichtungsassistent.

## Architektur und Betrieb

- Anwendung: `/opt/stempeluhr`
- Konfiguration: `/etc/stempeluhr/stempeluhr.env`
- variable Daten: `/var/lib/stempeluhr`
- Logs: systemd-Journal und `/var/log/stempeluhr`
- Dienst: `stempeluhr.service`
- Standardport: 8000
- Healthcheck: `/health`
- Versionsauskunft: `/version`
- Onboarding und Offboarding: **Systemeinstellungen → Personal & Arbeitszeit**
- Einrichtungsassistent: **Systemeinstellungen → Wartung → Einrichtungsassistent** beziehungsweise `/setup`
- Systemdiagnose: **Systemeinstellungen → Wartung → Systemdiagnose** beziehungsweise `/system/diagnostics`

## Version 5.6.00

Schwerpunkt: professioneller Einrichtungsassistent.

Umgesetzt:

- acht Schritte: Willkommen, Unternehmen, Administrator, PostgreSQL, Arbeitszeit, Kommunikation, Raspberry und Abschluss
- Fortschrittsanzeige, Vor/Zurück-Navigation und Wiederaufnahme nach Abbruch
- Speicherung über bestehende `settings`-Tabelle; keine neue Datenbanktabelle erforderlich
- Unternehmensdaten, Sprache, Zeitzone, Sollstunden und Pausenaktivierung konfigurierbar
- Administratorbestand wird geprüft, aber nicht automatisch verändert
- PostgreSQL-Verbindung und Serverversion werden geprüft; Passwörter werden nicht angezeigt
- E-Mail, API, HTTPS und Backup können aktiviert und über bestehende Detailseiten konfiguriert werden
- registrierte und online gemeldete Raspberry-Terminals werden zusammengefasst
- Abschluss nutzt die bestehende Systemdiagnose und zeigt Betriebsbereitschaft sowie Warnungen
- Assistent aus der Hauptnavigation entfernt und unter Wartung eingeordnet
- bestehende Daten, Benutzer und Konfigurationen werden nicht überschrieben

Keine Datenbankmodelle wurden geändert; eine Schema-Migration ist für 5.6.00 nicht erforderlich.

## Datenbankregeln

- Standarddatenbank und Rolle: `stempeluhr`
- Zugangsdaten ausschließlich aus geschützter Konfiguration
- SQLAlchemy-Verbindungen müssen Sonderzeichen sicher verarbeiten
- lokale Verbindungen dürfen keine Root-Zertifikatsumgebung erben
- Rollenpasswörter bei normalen Updates nicht verändern
- Migrationen wiederholbar und PostgreSQL-kompatibel ausführen
- keine produktiven Daten in Pakete oder Repository aufnehmen

## Debian-Buildsystem

```bash
bash scripts/build_release.sh
```

Erwartete Artefakte:

```text
releases/stempeluhr_5.6.00_all.deb
releases/stempeluhr_5.6.00_all.deb.sha256
releases/stempeluhr_5.6.00_build.log
releases/stempeluhr_5.6.00_BUILD_REPORT.md
```

## Offene Prüfungen

- Python-Syntax und Import des neuen `setup_wizard` prüfen
- 5.6.00 bauen und Paketmetadaten kontrollieren
- Upgrade von produktiver 5.5.09 auf 5.6.00 testen
- alle acht Assistentenschritte und Wiederaufnahme testen
- Speicherung von Unternehmens-, Arbeitszeit- und Modulwerten prüfen
- Abschlussdiagnose, `/health` und `/version` prüfen
- Erhalt von Mitarbeitern und Buchungen bestätigen

## Releasefreigabe

Eine Version gilt erst als freigegeben, wenn Versionsdateien und Dokumentation übereinstimmen, `.deb`/SHA256/Buildlog/Buildbericht vorhanden sind, das Upgrade getestet wurde, der Dienst läuft, `/health` die erwartete Version meldet und bestehende Daten erhalten sind.

## Startanweisung für neue Chats

> Arbeite am GitHub-Projekt `Markus4771/Stempeluhr`. Lies zuerst `NEUER_CHAT.md`, anschließend `CHATGPT_PROJEKTKONTEXT.md`, `version.txt`, `README.md` und `changelog.md`. Prüfe danach den tatsächlichen aktuellen Quellcode und bestätige zuerst Version und Ist-Stand. Arbeite ausschließlich auf Basis dieses Repository-Stands weiter. Keine Rekonstruktion, keine erfundenen Dateien und keine behaupteten Releases ohne echten Build.
