## 5.6.23

- Zusatz-Programme erhalten pro Eintrag konfigurierbare Rollenfreigaben
- aktive Programme werden nur den freigegebenen Rollen angezeigt
- Hauptmenüpunkt `Zusatz-Programme` erscheint nur, wenn für die angemeldete Rolle mindestens ein aktives Programm vorhanden ist
- bestehende Einträge ohne Rollenliste bleiben kompatibel für Administrator, Personal, Teamleiter und Mitarbeiter sichtbar
- Rollenänderungen werden im Audit-Protokoll dokumentiert
- Report-Webansicht, CSV, PDF und E-Mail-Anhang filtern zukünftige und unvollständige Tage einheitlich
- Summen und Teamstatistik werden ausschließlich aus vollständigen, nicht zukünftigen Tagen berechnet

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
