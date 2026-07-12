# Neuer Chat – Stempeluhr Professional 5.6.15

Diese Datei ist der Einstiegspunkt für jede neue ChatGPT-Unterhaltung zu diesem Projekt.

## Startanweisung

> Arbeite am GitHub-Projekt `Markus4771/Stempeluhr`. Lies zuerst `NEUER_CHAT.md`, danach `CHATGPT_PROJEKTKONTEXT.md`, `version.txt`, `README.md` und `changelog.md`. Prüfe anschließend den tatsächlichen aktuellen Quellcode. Bestätige zuerst die gefundene Version und den relevanten Ist-Stand. Arbeite ausschließlich auf Basis des Repository-Stands. Keine Rekonstruktion, keine erfundenen Dateien und keine behaupteten Builds oder Releases.

## Aktueller Schwerpunkt

Version **5.6.15** integriert das Hilfesystem mit Administrator-, Benutzer-, Installations- und API-Handbuch, Volltextsuche, Druckansicht und PDF-Ausgabe. Die Quellen liegen unter `docs/manuals/`. Der Router ist in `app/routes/help_docs.py` implementiert und muss über `app/routes/web.py` registriert bleiben.

## Verbindliche Arbeitsreihenfolge

1. Repository und Branch `main` prüfen.
2. Projektkontext vollständig lesen.
3. Versionen in `version.txt`, `app/version.py` und `debian/control` vergleichen.
4. README und Changelog prüfen.
5. Betroffene Quellcodedateien und echte Router-Registrierung analysieren.
6. Bestehende PostgreSQL-Daten und Kompatibilität erhalten.
7. Änderungen direkt im Repository umsetzen.
8. Syntax, Imports, Build und Healthcheck prüfen beziehungsweise auf der Test-VM testen lassen.
9. Dokumentation gemeinsam mit der Funktion aktualisieren.

## Wichtige Regeln

- PostgreSQL bleibt Standarddatenbank.
- Bestehende Daten dürfen nicht gelöscht werden.
- Keine Secrets oder Passwörter ins Repository schreiben.
- Debian 13 und Raspberry Pi OS berücksichtigen.
- Ein Paket oder Release erst nach tatsächlichem Build und Test als fertig bezeichnen.
- `docs/manuals/` muss im Debian-Paket enthalten sein, weil die integrierte Hilfe diese Dateien zur Laufzeit liest.

## Vor Freigabe von 5.6.15 testen

- `/help`
- alle vier Handbuchseiten
- Suche
- alle PDF-Downloads
- Druckansicht
- Anmeldungsschutz der Hilferouten
- Zusatz-Programme und Rollen aus 5.6.14
- `/health` und `/version`
- Mitarbeiter und Buchungen
