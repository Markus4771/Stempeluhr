# Stempeluhr Professional – zentraler Projektkontext

> Diese Datei ist die verbindliche Wissensbasis für neue ChatGPT-Unterhaltungen. Vor jeder Änderung müssen zusätzlich der aktuelle Quellcode, `version.txt`, `app/version.py`, `debian/control`, `README.md` und `changelog.md` geprüft werden. Bei Abweichungen gilt immer der tatsächliche Quellcode im Repository.

## Projekt

- Name: **Stempeluhr Professional**
- Repository: `Markus4771/Stempeluhr`
- Standardbranch: `main`
- Aktuelle Entwicklungs- und Testversion: **5.6.14**
- Letzte freigegebene Version: **5.6.13**
- Zielplattform: Debian 13 und Raspberry Pi OS
- Backend: Python, FastAPI, Uvicorn, SQLAlchemy
- Standarddatenbank: PostgreSQL
- Installation und Update: Debian-Paket
- Projektstrategie: eine gemeinsame **Stempeluhr Professional**, keine unterschiedlichen Editionen

## Verbindliche Regeln

PostgreSQL bleibt Standarddatenbank. Bestehende Mitarbeiter, Buchungen, Einstellungen und Konfigurationen dürfen bei Updates nicht gelöscht werden. Secrets und Passwörter gehören niemals ins Repository, in Logs, Auditdetails oder Diagnoseberichte.

Ein Paket, Tag oder GitHub Release darf erst als fertig oder freigegeben bezeichnet werden, wenn die Dateien tatsächlich gebaut, geprüft und auf der Proxmox-Test-VM getestet wurden.

Bei jeder neuen Version synchron aktualisieren:

- `version.txt`
- `app/version.py`
- `debian/control`
- `README.md`
- `changelog.md`
- `CHATGPT_PROJEKTKONTEXT.md`
- bei wesentlichen Änderungen auch `NEUER_CHAT.md`

Die Dateien `VERSION` und `CHANGELOG.md` dürfen nicht parallel zu den verbindlichen Dateien verwendet werden.

## Architektur und Betrieb

- Anwendung: `/opt/stempeluhr`
- allgemeine Konfiguration: `/etc/stempeluhr/stempeluhr.env`
- Datenbank-Secret: `/etc/stempeluhr/secrets/database.conf`
- variable Daten: `/var/lib/stempeluhr`
- Logs: systemd-Journal und `/var/log/stempeluhr`
- Dienst: `stempeluhr.service`
- Healthcheck: `/health`
- Versionsauskunft: `/version`
- Rollenverwaltung: **Systemeinstellungen → Personal & Arbeitszeit → Rollen & Rechte**
- Sicherheitsrichtlinien: **Systemeinstellungen → Allgemeine Einstellungen → Sicherheit**
- Zusatz-Programme konfigurieren: **Systemeinstellungen → Allgemeine Einstellungen → Zusatz-Programme**
- Updates: **Systemeinstellungen → Wartung → Updates**
- Systemdiagnose: **Systemeinstellungen → Wartung → Systemdiagnose**

## Freigegebene Sicherheitsbasis

### Version 5.6.12

- Datenbankpasswort aus `stempeluhr.env` nach `/etc/stempeluhr/secrets/database.conf` ausgelagert
- Secret-Verzeichnis `root:stempeluhr`, Modus `0750`
- Secret-Datei `root:stempeluhr`, Modus `0640`
- Datenbankpasswort über die Weboberfläche änderbar
- Verbindungstest, Sicherung und Rollback vorhanden
- Backup enthält `stempeluhr.env` und `config/secrets/database.conf`
- Healthcheck berücksichtigt die getrennte Secret-Datei

### Version 5.6.13

- konfigurierbarer Schutz gegen Fehlanmeldungen
- Fehlversuche bis Sperre und gemeinsame Sperrdauer konfigurierbar
- optionale IP-Sperre
- konfigurierbare Passwortrichtlinien
- einmalige Ausnahme für das initiale Passwort `admin123` des festen Benutzers `admin`
- dauerhafte Warnung, solange das Standardpasswort aktiv ist
- erneutes Setzen von `admin123` nach der Änderung gesperrt
- Passwortänderung, Sperre und Entsperrung auf der Test-VM erfolgreich geprüft

## Version 5.6.14

Schwerpunkte:

1. konfigurierbare Rollen und Berechtigungen
2. übersichtlich gruppierte Systemeinstellungs-Untermenüs
3. konfigurierbare Verknüpfungen zu externen Zusatz-Programmen

### Rollen und Rechte

- Verwaltung unter `/system/settings/roles`
- neue Rollen mit Name, Beschreibung und Berechtigungen anlegbar
- vorhandene Rollen bearbeitbar
- eigene Rollen nur löschbar, wenn ihnen keine Benutzer zugeordnet sind
- Standardrollen `Administrator`, `Personal`, `Teamleiter` und `Mitarbeiter` sind gegen Löschen geschützt
- Rolle `Administrator` behält immer Vollzugriff und kann nicht umbenannt werden
- Berechtigungen werden als JSON im vorhandenen Feld `roles.permissions` gespeichert
- keine neue Tabelle und keine destruktive Datenbankmigration erforderlich
- bestehende Standardrollen ohne gespeicherte Rechte erhalten rückwärtskompatible Standardrechte
- Rollen werden weiterhin in der vorhandenen Mitarbeiterverwaltung zugeordnet
- Navigation liest die Rollenberechtigungen aus der Sitzung
- Änderungen werden im Audit-Protokoll erfasst

### Berechtigungsgruppen

- Navigation: Dashboard, Zeiterfassung, Abwesenheiten, Mitarbeiterverwaltung, Korrekturen, Auswertungen, Plausibilität, Systemeinstellungen, Audit, Monitoring und Zusatz-Programme
- Mitarbeiter: ansehen, verwalten und Onboarding-Einladungen versenden
- Arbeitszeit: Korrekturen verwalten, Gesamtauswertungen, Abwesenheiten genehmigen und Plausibilitätsfälle bearbeiten
- System: Einstellungen, Backup, Updates, Diagnose, Audit und Monitoring

### Systemeinstellungs-Untermenüs

Unter **Allgemeine Einstellungen → Systemeinstellungs-Untermenüs** sind die optionalen Kacheln gruppiert nach:

- Allgemein
- Personal & Arbeitszeit
- Integrationen
- Sicherheit
- Wartung

Zusätzlich vorhanden:

- Schaltfläche **Alle aktivieren**
- Schaltfläche **Alle deaktivieren**
- Hinweis auf wichtige Menüs, die dauerhaft erreichbar bleiben

Die vorhandenen Einstellungswerte `module_settings_*_enabled` bleiben erhalten und werden weiterverwendet.

### Zusatz-Programme

- Konfiguration unter `/system/settings/general/additional-programs`
- Benutzerübersicht unter `/additional-programs`
- Angaben: Name, Beschreibung, HTTP/HTTPS, IP-Adresse oder Hostname, Port, optionaler Pfad und Aktivstatus
- Programme können angelegt, bearbeitet, aktiviert, deaktiviert, geöffnet und gelöscht werden
- aktivierte Programme erscheinen als Kacheln im Menü **Zusatz-Programme**
- Öffnen erfolgt in einem neuen Browser-Tab
- die Stempeluhr speichert keine Zugangsdaten fremder Programme
- Adressen werden als direkte Verknüpfung aufgebaut, zum Beispiel `http://10.0.0.20:8069/web`
- Rollenrecht `nav.additional_programs` steuert die Sichtbarkeit
- Programme werden im bestehenden PostgreSQL-Setting `additional_programs` als JSON gespeichert

## Sicherheits- und Kompatibilitätsregeln

- Administrator-Vollzugriff darf nicht entfernbar sein
- Standardrollen dürfen nicht versehentlich gelöscht werden
- Rollen mit zugeordneten Benutzern dürfen nicht gelöscht werden
- unbekannte Berechtigungswerte werden beim Speichern verworfen
- bestehende Installationen ohne gespeicherte JSON-Rechte müssen weiterhin funktionieren
- Zusatz-Programme dürfen nur `http` oder `https` verwenden
- Hostname/IP und Port müssen serverseitig validiert werden
- keine Kennwörter, Tokens oder eingebetteten Zugangsdaten in Zusatz-Programm-URLs speichern
- externe Programme werden nicht als Reverse Proxy eingebettet, sondern sicher verlinkt
- produktive Mitarbeiter- und Buchungsdaten dürfen durch 5.6.14 nicht verändert werden

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

## Offene Prüfungen vor Freigabe von 5.6.14

- Repository auf sauberen Stand bringen
- Python-Syntax und Imports der neuen Module prüfen
- Debian-Paket bauen und SHA256 prüfen
- Upgrade von 5.6.13 auf 5.6.14 auf der Proxmox-Test-VM durchführen
- `/health` muss `status: ok` melden
- `/version` muss 5.6.14 melden
- bestehende Mitarbeiter und Buchungen prüfen
- neue Rolle anlegen, bearbeiten und einem Testbenutzer zuordnen
- Navigation und Rechte des Testbenutzers prüfen
- verwendete Rolle darf nicht löschbar sein
- eigene unbenutzte Rolle muss löschbar sein
- Administrator- und Standardrollenschutz prüfen
- Gruppierung der Systemeinstellungs-Untermenüs prüfen
- Alle-aktivieren- und Alle-deaktivieren-Funktion prüfen
- Zusatz-Programm anlegen, bearbeiten, deaktivieren, aktivieren, öffnen und löschen
- ungültige IP-/Hostname-/Port-Eingaben müssen abgelehnt werden
- Rollenrecht für Zusatz-Programme prüfen
- erst danach Tag `v5.6.14` und GitHub Release veröffentlichen

## Releasefreigabe

Version 5.6.14 ist derzeit **umgesetzt, aber noch nicht freigegeben**. Sie gilt erst als freigegeben, wenn `.deb`, SHA256, Buildlog und Buildbericht tatsächlich vorhanden sind und Rollenverwaltung, Berechtigungen, Untermenü-Gruppierung, Zusatz-Programme, Healthcheck und Datenbestand auf der Test-VM erfolgreich geprüft wurden.

## Startanweisung für neue Chats

> Arbeite am GitHub-Projekt `Markus4771/Stempeluhr`. Lies zuerst `NEUER_CHAT.md`, anschließend `CHATGPT_PROJEKTKONTEXT.md`, `version.txt`, `app/version.py`, `debian/control`, `README.md` und `changelog.md`. Prüfe danach den tatsächlichen aktuellen Quellcode und bestätige zuerst Version, Freigabestatus und relevanten Ist-Stand. Arbeite ausschließlich auf Basis dieses Repository-Stands weiter. Keine Rekonstruktion, keine erfundenen Dateien und keine behaupteten Builds oder Releases ohne tatsächlich vorhandene Artefakte.