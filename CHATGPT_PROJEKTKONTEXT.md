# Stempeluhr Professional – zentraler Projektkontext

> Diese Datei ist die verbindliche Wissensbasis für neue ChatGPT-Unterhaltungen. Vor jeder Änderung müssen zusätzlich der aktuelle Quellcode, `version.txt`, `README.md` und `changelog.md` geprüft werden. Bei Abweichungen gilt der tatsächliche Quellcode.

## Projekt

- Name: **Stempeluhr Professional**
- Repository: `Markus4771/Stempeluhr`
- Standardbranch: `main`
- Aktuelle Version: **5.6.14**
- Zielplattform: Debian 13 und Raspberry Pi OS
- Backend: Python, FastAPI, Uvicorn, SQLAlchemy
- Standarddatenbank: PostgreSQL
- Installation: Debian-Paket

## Verbindliche Regeln

PostgreSQL bleibt Standarddatenbank. Bestehende Daten und Konfigurationen dürfen bei Updates nicht gelöscht werden. Secrets und Passwörter gehören niemals ins Repository, in Logs oder Diagnoseberichte. Paketartefakte gelten erst nach tatsächlichem Build und Prüfung als fertig.

Bei jeder neuen Version synchron aktualisieren: `version.txt`, `app/version.py`, `debian/control`, `README.md`, `changelog.md` und `CHATGPT_PROJEKTKONTEXT.md`. Die Dateien `VERSION` und `CHANGELOG.md` dürfen nicht existieren.

## Architektur und Betrieb

- Anwendung: `/opt/stempeluhr`
- allgemeine Konfiguration: `/etc/stempeluhr/stempeluhr.env`
- Datenbank-Secret: `/etc/stempeluhr/secrets/database.conf`
- variable Daten: `/var/lib/stempeluhr`
- Logs: systemd-Journal und `/var/log/stempeluhr`
- Dienst: `stempeluhr.service`
- Rollenverwaltung: **Systemeinstellungen → Personal & Arbeitszeit → Rollen & Rechte**
- Sicherheitsrichtlinien: **Systemeinstellungen → Allgemeine Einstellungen → Sicherheit**
- Updates: **Systemeinstellungen → Wartung → Updates**
- Healthcheck: `/health`
- Versionsauskunft: `/version`

## Version 5.6.14

Schwerpunkt: konfigurierbare Rollen und Berechtigungen.

Umgesetzt:

- Rollenverwaltung unter `/system/settings/roles`
- neue Rollen mit Name, Beschreibung und Berechtigungsauswahl anlegbar
- vorhandene Rollen bearbeitbar
- eigene Rollen nur löschbar, wenn ihnen keine Benutzer zugeordnet sind
- Standardrollen `Administrator`, `Personal`, `Teamleiter` und `Mitarbeiter` sind gegen Löschen geschützt
- Rolle `Administrator` behält immer Vollzugriff und kann nicht umbenannt werden
- Berechtigungen werden als JSON im bereits vorhandenen Feld `roles.permissions` gespeichert
- keine neue Tabelle und keine destruktive Migration erforderlich
- vorhandene Standardrollen erhalten rückwärtskompatible Standardrechte, solange keine individuellen Rechte gespeichert wurden
- Navigation liest die Rollenberechtigungen aus der Sitzung
- Rollen werden weiterhin über die vorhandene Mitarbeiterverwaltung zugeordnet
- Änderungen an Rollen werden im Audit-Protokoll erfasst

## Berechtigungsgruppen

- Navigation: Dashboard, Zeiterfassung, Abwesenheit, Mitarbeiter, Korrektur, Auswertung, Plausibilität, Systemeinstellungen, Audit und Monitoring
- Mitarbeiter: ansehen, verwalten und Onboarding-Einladungen
- Arbeitszeit: Korrekturen, Gesamtauswertungen, Abwesenheitsfreigabe und Plausibilitätsbearbeitung
- System: Einstellungen, Backup, Updates, Diagnose, Audit und Monitoring

## Sicherheitsregeln

- Administrator-Vollzugriff darf nicht entfernbar sein
- Standardrollen dürfen nicht versehentlich gelöscht werden
- Rollen mit zugeordneten Benutzern dürfen nicht gelöscht werden
- unbekannte Berechtigungswerte werden beim Speichern verworfen
- bestehende Installationen ohne gespeicherte JSON-Rechte müssen weiterhin funktionieren
- keine Passwörter oder Secrets in Rollen- oder Auditdaten speichern

## Debian-Buildsystem

```bash
bash scripts/build_release.sh
```

Erwartete Artefakte:

```text
releases/stempeluhr_5.6.14_all.deb
releases/stempeluhr_5.6.14_all.deb.sha256
releases/stempeluhr_5.6.14_build.log
releases/stempeluhr_5.6.14_BUILD_REPORT.md
```

## Offene Prüfungen vor Freigabe

- Python-Syntax und Imports der neuen Module prüfen
- Upgrade von 5.6.13 auf 5.6.14 auf der Proxmox-Test-VM durchführen
- Rollenverwaltung öffnen
- neue Testrolle anlegen und speichern
- Testrolle einem Testbenutzer zuweisen
- Navigation und Zugriffe mit der Testrolle prüfen
- Rolle mit zugeordnetem Benutzer darf nicht löschbar sein
- Rolle nach Entfernung der Zuordnung löschen
- Standardrollen und Administrator-Vollzugriff prüfen
- `/health`, `/version`, Mitarbeiter und Buchungen prüfen
- erst danach Tag `v5.6.14` und GitHub Release veröffentlichen

## Releasefreigabe

5.6.14 ist erst freigegeben, wenn `.deb`, SHA256, Buildlog und Buildbericht tatsächlich vorhanden sind und Rollenanlage, Bearbeitung, Zuordnung, Navigation, Schutzregeln und bestehende Daten auf der Test-VM geprüft wurden.

## Startanweisung für neue Chats

> Arbeite am GitHub-Projekt `Markus4771/Stempeluhr`. Lies zuerst `NEUER_CHAT.md`, anschließend `CHATGPT_PROJEKTKONTEXT.md`, `version.txt`, `README.md` und `changelog.md`. Prüfe danach den tatsächlichen aktuellen Quellcode und bestätige zuerst Version und Ist-Stand. Arbeite ausschließlich auf Basis dieses Repository-Stands weiter. Keine Rekonstruktion, keine erfundenen Dateien und keine behaupteten Releases ohne echten Build.
