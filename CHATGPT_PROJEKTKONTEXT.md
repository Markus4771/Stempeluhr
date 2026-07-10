# Stempeluhr Professional – zentraler Projektkontext

> Diese Datei ist die verbindliche Wissensbasis für neue ChatGPT-Unterhaltungen. Vor jeder Änderung müssen zusätzlich der aktuelle Quellcode, `version.txt`, `README.md` und `changelog.md` geprüft werden. Bei Abweichungen gilt der tatsächliche Quellcode.

## Projekt

- Name: **Stempeluhr Professional**
- Repository: `Markus4771/Stempeluhr`
- Standardbranch: `main`
- Aktuelle Version: **5.5.05**
- Zielplattform: Debian 13 und Raspberry Pi OS
- Backend: Python, FastAPI, Uvicorn, SQLAlchemy
- Standarddatenbank: PostgreSQL
- Installation: Debian-Paket

## Ziel

Professionelle, updatefähige und datenschutzorientierte Zeiterfassung für Raspberry-Pi-Terminals und Linux-Server. Bestehende Daten und Konfigurationen müssen Updates zuverlässig überstehen.

## Verbindliche Regeln

1. Immer auf dem echten aktuellen Repository-Stand arbeiten.
2. PostgreSQL bleibt die produktive Standarddatenbank.
3. Keine Umstellung auf SQLite ohne ausdrücklichen Auftrag.
4. Bestehende Daten bei Installation, Update oder Deinstallation nicht automatisch löschen.
5. Vor Schemaänderungen sichere, idempotente Migrationen vorsehen.
6. Vorhandene Funktionen nur auf ausdrücklichen Auftrag entfernen.
7. Debian 13, Raspberry Pi OS, Wayland und labwc berücksichtigen.
8. Der Raspberry-Agent läuft typischerweise als User-Systemdienst des Benutzers `pi`.
9. Secrets und echte Passwörter niemals ins Repository schreiben.
10. `.deb`, ZIP oder Release nur als fertig bezeichnen, wenn das Artefakt tatsächlich gebaut und geprüft wurde.

## Bei jeder neuen Version aktualisieren

- `version.txt`
- `app/version.py`
- `debian/control`
- `README.md`
- `changelog.md`
- `CHATGPT_PROJEKTKONTEXT.md`

Die Datei `VERSION` darf nicht existieren. Der verbindliche Änderungsverlauf ist ausschließlich `changelog.md`; eine zusätzliche Datei `CHANGELOG.md` darf nicht existieren.

## Aktueller Funktionsstand

Zum System gehören unter anderem:

- Mitarbeiterverwaltung
- Arbeitszeiterfassung und RFID-Buchung
- Dashboard
- Rollen- und Rechteverwaltung
- Plausibilitätsprüfung und Korrekturworkflow
- individuelle Pausenregel pro Mitarbeiter
- DSGVO-Funktionen
- REST-API mit Schutzmechanismen
- HTTPS und Zertifikatsverwaltung
- CalDAV- und iCal-Feiertage
- Monatsreporting, PDF- und CSV-Export
- Teamstatistik und Fehlzeitenanalyse
- automatische E-Mails
- Update- und Backupfunktionen
- Raspberry-Kioskmodus mit Chromium
- Raspberry-Agent, Heartbeat und Monitoring-Grundlage
- Onboarding mit Einladungslink, Passwort-Erstsetzung und Datenschutzbestätigung

## Architektur und Betrieb

- Installation gewöhnlich unter `/opt/stempeluhr`
- Konfiguration unter `/etc/stempeluhr/stempeluhr.env`
- variable Daten unter `/var/lib/stempeluhr`
- Logs im systemd-Journal und unter `/var/log/stempeluhr`
- Webdienst: `stempeluhr.service`
- Raspberry-Agent: User-Systemdienst `stempeluhr-agent.service`
- Standardport: 8000
- Healthcheck: `/health`
- Versionsauskunft: `/version`

## Datenbankregeln

- Datenbankname standardmäßig `stempeluhr`
- Anwendungsrolle standardmäßig `stempeluhr`
- Zugangsdaten nur über geschützte Konfiguration
- Migrationen wiederholbar und PostgreSQL-kompatibel gestalten
- neue Spalten mit sicheren Standardwerten einführen
- keine produktiven Daten in Pakete oder Repository aufnehmen

## Debian-Buildsystem

Das Buildsystem gehört ausschließlich zu diesem Projekt.

Lokaler Build:

```bash
bash scripts/build_release.sh
```

Erwartete Artefakte für Version 5.5.05:

```text
releases/stempeluhr_5.5.05_all.deb
releases/stempeluhr_5.5.05_all.deb.sha256
releases/stempeluhr_5.5.05_build.log
releases/stempeluhr_5.5.05_BUILD_REPORT.md
```

Der Build prüft:

- synchronisierte Versionsangaben
- sauberen Git-Arbeitsstand
- Python-Syntax
- Debian-Paketmetadaten
- Ausschluss lokaler Daten, Uploads, Datenbanken und Secrets
- Paketinhalt und SHA256
- Buildbericht mit Commit, Systemdaten, Paketgröße und Builddauer

Ein erfolgreicher Buildbericht ersetzt keinen Installations- und Upgradetest auf einem Testsystem.

## Version 5.5.05

Schwerpunkt: Repository- und Releasequalität.

Änderungen:

- projektspezifischen Debian-Buildprozess erweitert
- automatischen Buildbericht ergänzt
- doppelte Changelog-Datei entfernt
- Versionsprüfungen vereinheitlicht
- keine Änderung an produktiven Datenbankmodellen oder Zeiterfassungsfunktionen

## Bekannte Probleme und offene Aufgaben

Priorität hoch:

- Debian-Paket 5.5.05 tatsächlich bauen
- Paketmetadaten und SHA256 prüfen
- Upgrade von installierter 5.5.04 auf 5.5.05 mit bestehender PostgreSQL-Datenbank testen
- systemd-Start und `/health` nach Upgrade prüfen
- Raspberry-Screenshots unter Wayland/labwc weiter stabilisieren
- Heartbeat-Status dauerhaft korrekt darstellen
- Onboarding gegen tatsächlichen Quellcode und UI vollständig prüfen

Priorität mittel:

- API-Endpunkte und Schemata dokumentieren
- Testabdeckung für Login, Buchung, Plausibilität, Onboarding und Update erhöhen
- Backup- und Rollbacktests ergänzen
- optional `lintian` in den Paketbuild integrieren

## Releasefreigabe

Eine Version gilt erst als freigegeben, wenn mindestens Folgendes bestätigt ist:

1. Versionsdateien und Dokumentation stimmen überein.
2. Buildskript lief erfolgreich.
3. `.deb`, SHA256, Buildlog und Buildbericht sind vorhanden.
4. Paketmetadaten wurden geprüft.
5. Neuinstallation oder Upgrade wurde auf Debian getestet.
6. `stempeluhr.service` startet erfolgreich.
7. `/health` meldet die erwartete Version und eine funktionsfähige PostgreSQL-Verbindung.
8. Bestehende Daten sind nach dem Upgrade weiterhin vorhanden.

## Startanweisung für neue Chats

> Arbeite am GitHub-Projekt `Markus4771/Stempeluhr`. Lies zuerst `NEUER_CHAT.md`, anschließend `CHATGPT_PROJEKTKONTEXT.md`, `version.txt`, `README.md` und `changelog.md`. Prüfe danach den tatsächlichen aktuellen Quellcode und bestätige zuerst Version und Ist-Stand. Arbeite ausschließlich auf Basis dieses Repository-Stands weiter. Keine Rekonstruktion, keine erfundenen Dateien und keine behaupteten Releases ohne echten Build.
