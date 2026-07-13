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
- Handbuchansicht mit festem Inhaltsverzeichnis und direkten Kapitelsprüngen überarbeitet
- helle, kontrastreiche und umbrechende Codeblöcke für bessere Lesbarkeit ergänzt
- Kopierfunktion für Befehle, URLs und API-Beispiele ergänzt
- lokale Suche innerhalb des geöffneten Handbuchs ergänzt
- Typografie, Zeilenbreite und mobile Darstellung der Dokumentation verbessert
- Druckansicht blendet Navigation und Bedienelemente automatisch aus
- Hilfebereich nur für angemeldete Benutzer erreichbar
- neue Routen `/help`, `/help/{handbuch}` und `/help/{handbuch}/pdf`
- Dokumentationsquellen werden zusammen mit dem Debian-Paket ausgeliefert
- keine produktiven Mitarbeiter-, Buchungs- oder Datenbankdaten verändert

## 5.6.14

- Rollenverwaltung unter `Systemeinstellungen → Personal & Arbeitszeit → Rollen & Rechte` ergänzt
- eigene Rollen mit Name, Beschreibung und auswählbaren Berechtigungen anlegbar
- Rollenberechtigungen werden als JSON im vorhandenen Feld `roles.permissions` gespeichert
- vorhandene Rollen können bearbeitet werden
- eigene Rollen können nur ohne zugeordnete Benutzer gelöscht werden
- Standardrollen sind gegen Löschen geschützt
- Rolle `Administrator` behält immer Vollzugriff und kann nicht umbenannt werden
- Navigation wird anhand der Rollenberechtigungen aufgebaut
- neue Rollenberechtigung `Zusatz-Programme anzeigen` ergänzt
- Systemeinstellungs-Untermenüs in den Allgemeinen Einstellungen nach Allgemein, Personal & Arbeitszeit, Integrationen, Sicherheit und Wartung gruppiert
- Schaltflächen `Alle aktivieren` und `Alle deaktivieren` für optionale Systemeinstellungs-Untermenüs ergänzt
- wichtige Bereiche wie Allgemeine Einstellungen, Rollen & Rechte, Updates, Datenbankzugang und Systemdiagnose bleiben immer erreichbar
- Zusatz-Programme mit Name, Beschreibung, HTTP/HTTPS, IP-Adresse oder Hostname, Port und optionalem Pfad konfigurierbar
- Zusatz-Programme können aktiviert, deaktiviert, bearbeitet, geöffnet und gelöscht werden
- freigeschaltete Zusatz-Programme erscheinen in einer eigenen WebGUI-Übersicht und in der Hauptnavigation
- Zugangsdaten fremder Programme werden nicht in der Stempeluhr gespeichert
- rückwärtskompatible Standardrechte für bestehende Rollen ohne gespeicherte Rechte
- keine neue Datenbanktabelle und keine destruktive Migration erforderlich
- keine produktiven Mitarbeiter- oder Buchungsdaten verändert

## 5.6.13

- konfigurierbaren Schutz gegen wiederholte Fehlanmeldungen ergänzt
- Anzahl der Fehlversuche und gemeinsame Sperrdauer konfigurierbar
- optionale IP-Sperre ergänzt
- bestehende Testsperren werden beim Speichern neuer Richtlinien aufgehoben
- konfigurierbare Passwortrichtlinien für neue und geänderte Passwörter ergänzt
- einmalige Ausnahme und dauerhafte Warnung für das initiale Admin-Standardpasswort
- fehlgeschlagene und blockierte Anmeldungen werden ohne Passwortdaten protokolliert
- keine produktiven Mitarbeiter- oder Buchungsdaten verändert

## 5.6.12

- Datenbankpasswort aus der allgemeinen Konfiguration in eine geschützte Secret-Datei ausgelagert
- bestehende Installationen werden ohne Änderung der PostgreSQL-Rolle migriert
- neue Seite für Datenbankzugang und sicheren Passwortwechsel ergänzt
- SCRAM-SHA-256, Verbindungstest, Sicherung und Rollback ergänzt
- enger Root-Helfer statt allgemeiner sudo-Rechte
- keine Datenbankmodelle oder produktiven Daten geändert

## 5.6.11

- bestehende Updateverwaltung um stabile GitHub Releases erweitert
- manueller DEB-Upload unverändert erhalten
- Paket und SHA256 werden gemeinsam geprüft
- GitHub-Paket wird an denselben bestehenden Update-Runner übergeben

## 5.6.10

- automatisches GitHub-Release-System für Debian-Pakete ergänzt
- Release wird durch einen passenden Versions-Tag ausgelöst
- DEB, SHA256, Buildbericht und Changelog werden veröffentlicht

## 5.6.00

- Einrichtungsassistent als achtstufigen Wizard neu aufgebaut
- Fortschrittsanzeige, Navigation und Wiederaufnahme ergänzt
- Unternehmensdaten, Zeitzone, Datenbank, E-Mail, API, HTTPS und Backup zusammengeführt
- bestehende Daten und Konfigurationen werden nicht überschrieben

## 5.5.09

- Offboarding unter `Systemeinstellungen → Personal & Arbeitszeit` eingeordnet

## 5.5.08

- Systemdiagnose unter `Systemeinstellungen → Wartung` integriert

## 5.5.07

- Systemdiagnose, PostgreSQL-Prüfung und Diagnosebericht ergänzt

## 5.5.06

- PostgreSQL-Verbindungsaufbau und Passwortbehandlung gehärtet
- bestehende Datenbank und Konfiguration bleiben erhalten

## 5.5.05

- Debian-Buildprozess und Buildbericht erweitert
- verbindlicher Änderungsverlauf auf `changelog.md` vereinheitlicht

## 5.5.04

- Onboarding aus dem Hauptmenü entfernt
- Einladungsbutton in der Mitarbeiterverwaltung verfügbar

## 5.5.0

- Onboarding, Datenschutzbestätigung und Benutzer-REST-API erweitert
