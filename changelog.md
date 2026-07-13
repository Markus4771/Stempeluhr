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
