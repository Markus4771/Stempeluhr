## 5.6.22

- GitHub-Updater kann bei fehlendem veröffentlichtem Release auf den aktuellen Branch `main` zurückgreifen
- privater Quellcode wird mit dem lokal gespeicherten Lesetoken geladen
- Quellcode wird temporär entpackt und lokal als Debian-Paket gebaut
- gebautes Paket wird an den bestehenden Update-Assistenten übergeben
- Backup, Installation, Dienstneustart und Healthcheck bleiben Bestandteil des bestehenden Updateablaufs
- main-Update ist ausschließlich für Administratoren verfügbar
- privilegierter Runner `/usr/local/sbin/stempeluhr-github-main-update` mit begrenzter sudoers-Regel ergänzt
- Token-Popup verwendet ein Passwortfeld

## 5.6.21

- Kommen- und Gehen-Uhrzeiten werden direkt in `Mein Report` geladen
- Stempelzeiten werden serverseitig nach Berechtigung, Mitarbeiter und Zeitraum gefiltert
- iframe-/JavaScript-Zwischenlösung entfernt
- Menüeinträge `Überstunden` und `Plausibilität` für Teamleiter, Personal und Administratoren sichtbar
- fehlender GitHub-Lesetoken wird in der Updateverwaltung über ein Eingabefenster abgefragt
- Token kann dort auch ersetzt werden
- Speicherung unter `/etc/stempeluhr/secrets/github_token` mit restriktiven Dateirechten

## 5.6.20

- Plausibilitätsmeldungen können von Administrator, Personal und zuständigen Teamleitern zurückgesetzt werden
- Zurücksetzen stellt den Status auf `offen` und entfernt Kommentar, Erledigungszeit und Bearbeiter
- Überstundenverwaltung mit Zielwert, sofortigem oder geplantem Wirksamkeitszeitpunkt ergänzt
- Zielwert kann `0`, positiv oder negativ sein
- Mitarbeiterfreigabe per E-Mail ist vor der Änderung verpflichtend
- genehmigte zukünftige Änderungen werden automatisch zum geplanten Zeitpunkt angewendet
- Änderungsverlauf mit Altwert, Zielwert, Begründung und Status ergänzt

## 5.6.19

- Stempelzeiten in `Mein Report` werden serverseitig nach gewähltem Mitarbeiter und Zeitraum geladen
- Begrenzung auf die letzten 300 allgemeinen Buchungen entfernt
- Buchungsarten werden als `Kommen` und `Gehen` dargestellt
- Mitarbeiter bleiben strikt auf den eigenen Report beschränkt
- Teamleiter sehen ausschließlich ihre zugeordneten Mitarbeiter
- GitHub-Updater unterstützt private Repositorys über `/etc/stempeluhr/secrets/github_token` oder `STEMPELUHR_GITHUB_TOKEN`

## 5.6.18

- aktive Filter der Plausibilitätsprüfung bleiben nach Statusänderungen erhalten
- aktueller Status und Kommentar werden im Bearbeitungsformular angezeigt
- Mitarbeiter werden serverseitig immer auf den eigenen Report beschränkt
- Teamleiter sehen nur die ihnen zugeordneten Mitarbeiter
- öffentliche Datenschutzerklärung unter `/datenschutz` ergänzt
- Link zur Datenschutzerklärung bei der Kontoeinrichtung ergänzt

## 5.6.17

- Menüpunkt `Zeiterfassung` aus der normalen Hauptnavigation entfernt
- Kiosk-Seite `/raspberry` bleibt direkt erreichbar

## 5.6.16

- Hauptnavigation im Bereich `Abwesenheiten` zusammengefasst
- doppelten Menüpunkt `Meine Abwesenheiten` entfernt
- genehmigungsfreie Arten wie `Krank` werden direkt mit Status `genehmigt` gespeichert
- `install.sh` für Installation, Update, Paketbau, Backup, Restore, Status, Logs und Diagnose ergänzt

## 5.6.15

- Hauptmenüpunkt `Hilfe & Dokumentation` ergänzt
- Handbücher und Hilfebereich integriert

## 5.6.14

- Rollenverwaltung und Zusatz-Programme ergänzt

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
