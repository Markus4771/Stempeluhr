## 5.6.17

- Menüpunkt `Zeiterfassung` aus der normalen Hauptnavigation entfernt
- Kiosk-Seite `/raspberry` bleibt direkt erreichbar
- Raspberry-Kiosk kann die Zeiterfassung weiterhin automatisch öffnen
- keine Änderung an Buchungslogik, RFID-Funktion oder produktiven Daten

## 5.6.16

- Hauptnavigation im Bereich `Abwesenheiten` zusammengefasst
- doppelten Menüpunkt `Meine Abwesenheiten` aus der Hauptnavigation entfernt
- Abwesenheitsübersicht um rollenabhängige Kacheln ergänzt
- Administrator-Kachel für `Abwesenheitsarten` ergänzt
- Einstellung `Genehmigung nötig` wird beim Anlegen neuer Abwesenheiten ausgewertet
- genehmigungsfreie Arten wie `Krank` werden direkt mit Status `genehmigt` gespeichert
- genehmigungsfreie Anträge erscheinen nicht in der offenen Genehmigungsliste
- Formularzuordnung bei der Bearbeitung von Abwesenheitsarten korrigiert
- `install.sh` für Installation, Update, Paketbau, Backup, Restore, Status, Logs und Diagnose ergänzt
- keine destruktive Datenbankmigration und keine Änderung bestehender produktiver Daten

## 5.6.15

- Hauptmenüpunkt `Hilfe & Dokumentation` ergänzt
- Administratorhandbuch, Benutzerhandbuch, Installations- und Einrichterhandbuch sowie API-Handbuch integriert
- Handbuchquellen unter `docs/manuals/` versioniert
- HTML-Leseansicht und browserbasierte Druckansicht ergänzt
- PDF-Erzeugung und Download direkt aus der Anwendung mit ReportLab ergänzt
- gemeinsame Volltextsuche über alle Handbücher ergänzt
- Hilfebereich nur für angemeldete Benutzer erreichbar
- Dokumentationsquellen werden zusammen mit dem Debian-Paket ausgeliefert
- keine produktiven Mitarbeiter-, Buchungs- oder Datenbankdaten verändert

## 5.6.14

- Rollenverwaltung und gruppierte Systemeinstellungen ergänzt
- Zusatz-Programme konfigurierbar und rollenabhängig sichtbar
- keine destruktive Migration erforderlich

## 5.6.13

- Schutz gegen wiederholte Fehlanmeldungen und Passwortrichtlinien ergänzt

## 5.6.12

- Datenbankpasswort in geschützte Secret-Datei ausgelagert

## 5.6.11

- Updateverwaltung um stabile GitHub Releases erweitert

## 5.6.10

- automatisches GitHub-Release-System für Debian-Pakete ergänzt

## 5.6.00

- Einrichtungsassistent als achtstufigen Wizard neu aufgebaut

## 5.5.09

- Offboarding unter Systemeinstellungen eingeordnet

## 5.5.08

- Systemdiagnose unter Wartung integriert

## 5.5.07

- Systemdiagnose und PostgreSQL-Prüfung ergänzt

## 5.5.06

- PostgreSQL-Verbindungsaufbau und Passwortbehandlung gehärtet

## 5.5.05

- Debian-Buildprozess und Buildbericht erweitert

## 5.5.04

- Onboarding aus dem Hauptmenü entfernt

## 5.5.0

- Onboarding, Datenschutzbestätigung und Benutzer-REST-API erweitert
