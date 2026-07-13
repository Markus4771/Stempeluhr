## 5.6.20

- Plausibilitätsmeldungen können von Administrator, Personal und zuständigen Teamleitern zurückgesetzt werden
- Zurücksetzen stellt den Status auf `offen` und entfernt Kommentar, Erledigungszeit und Bearbeiter
- Überstundenverwaltung mit Zielwert, sofortigem oder geplantem Wirksamkeitszeitpunkt ergänzt
- Zielwert kann `0`, positiv oder negativ sein
- Mitarbeiterfreigabe per E-Mail ist vor der Änderung verpflichtend
- genehmigte zukünftige Änderungen werden automatisch zum geplanten Zeitpunkt angewendet
- Änderungsverlauf mit Altwert, Zielwert, Begründung und Status ergänzt
- Einbindung der Kommen-/Gehen-Zeiten in `Mein Report` robuster gemacht

## 5.6.19

- Stempelzeiten in `Mein Report` werden serverseitig nach gewähltem Mitarbeiter und Zeitraum geladen
- Begrenzung auf die letzten 300 allgemeinen Buchungen entfernt
- Buchungsarten werden als `Kommen` und `Gehen` dargestellt
- Mitarbeiter bleiben strikt auf den eigenen Report beschränkt
- Teamleiter sehen ausschließlich ihre zugeordneten Mitarbeiter
- GitHub-Updater unterstützt private Repositorys über `/etc/stempeluhr/secrets/github_token` oder `STEMPELUHR_GITHUB_TOKEN`
- HTTP-404-Meldung bei privatem Repository oder fehlendem Release präzisiert

## 5.6.18

- aktive Filter der Plausibilitätsprüfung bleiben nach Statusänderungen erhalten
- aktueller Status und Kommentar werden im Bearbeitungsformular angezeigt
- Stempelzeiten werden in `Mein Report` für den gewählten Zeitraum aufgeführt
- Mitarbeiter werden serverseitig immer auf den eigenen Report beschränkt
- Teamleiter sehen nur die ihnen zugeordneten Mitarbeiter
- Personal und Administratoren behalten den vorgesehenen erweiterten Zugriff
- öffentliche Datenschutzerklärung unter `/datenschutz` ergänzt
- Link zur Datenschutzerklärung bei der Kontoeinrichtung ergänzt

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
