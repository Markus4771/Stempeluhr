# Neuer Chat – Stempeluhr Professional

Diese Datei ist der Einstiegspunkt für jede neue ChatGPT-Unterhaltung zu diesem Projekt.

## Startanweisung für einen neuen Chat

Kopiere folgenden Text in einen neuen Chat:

> Arbeite am GitHub-Projekt `Markus4771/Stempeluhr`. Lies zuerst `NEUER_CHAT.md`, anschließend `CHATGPT_PROJEKTKONTEXT.md`, `version.txt`, `README.md` und `changelog.md`. Prüfe danach den tatsächlichen aktuellen Quellcode und bestätige mir zuerst die gefundene Version sowie den relevanten Ist-Stand. Arbeite ausschließlich auf Basis dieses Repository-Stands weiter. Keine Rekonstruktion, keine erfundenen Dateien und keine behaupteten Releases ohne echten Build.

## Verbindliche Arbeitsreihenfolge

1. Repository und Standardbranch prüfen.
2. `CHATGPT_PROJEKTKONTEXT.md` vollständig lesen.
3. Version aus `version.txt` lesen.
4. `README.md` und `changelog.md` gegen die Versionsnummer prüfen.
5. Die betroffenen Quellcodedateien suchen und analysieren.
6. Vorhandene Datenbankmodelle und Migrationen berücksichtigen.
7. Bestehende API-, UI- und systemd-Kompatibilität erhalten.
8. Änderungen direkt im echten Repository umsetzen.
9. Syntax-, Import-, Start- und Healthchecks durchführen beziehungsweise deren Durchführung vorbereiten.
10. Bei einer neuen Version alle Versions- und Dokumentationsdateien aktualisieren.

## Wichtige Regeln

- PostgreSQL bleibt die Standarddatenbank.
- Bestehende Daten dürfen durch Updates nicht gelöscht werden.
- Keine Umstellung auf SQLite ohne ausdrücklichen Auftrag.
- Keine vorhandenen Funktionen entfernen, außer der Benutzer verlangt es ausdrücklich.
- Raspberry Pi OS / Debian 13, Wayland und labwc berücksichtigen.
- Der Raspberry-Agent läuft typischerweise als User-Systemdienst des Benutzers `pi`.
- Secrets und echte Passwörter niemals ins Repository schreiben.
- Nicht geprüfte Annahmen deutlich kennzeichnen.
- Ein `.deb`, ZIP oder Release darf erst als fertig bezeichnet werden, wenn die Datei tatsächlich gebaut und vorhanden ist.

## Bei jeder neuen Version aktualisieren

- `version.txt`
- `README.md`
- `changelog.md`
- `CHATGPT_PROJEKTKONTEXT.md`

## Aktuelles Hauptziel

Die jeweils aktuellen Ziele, offenen Aufgaben und bekannten Probleme stehen verbindlich in `CHATGPT_PROJEKTKONTEXT.md`.
