# Stempeluhr Professional 5.6.00

Webbasierte Zeiterfassung für Debian-Server und Raspberry-Pi-Terminals mit PostgreSQL, FastAPI, Rollen und Rechten, Reporting, Onboarding und Raspberry-Kioskfunktionen.

## Aktueller Stand

- Version: **5.6.00**
- Standarddatenbank: PostgreSQL
- Zielplattform: Debian 13 / Raspberry Pi OS
- Standardbranch: `main`

Änderungen dieser Version:

- Einrichtungsassistent als achtstufiger Wizard vollständig neu aufgebaut
- Fortschrittsanzeige, Vor/Zurück-Navigation und automatische Zwischenspeicherung
- Unternehmensdaten, Zeitzone, Arbeitszeit und Funktionsmodule konfigurierbar
- Administrator-, PostgreSQL- und Raspberry-Status werden geprüft
- abschließende Systemdiagnose mit Betriebsbereitschaft und Warnungen
- Assistent unter **Systemeinstellungen → Wartung** eingeordnet
- bestehende Daten, Benutzer und PostgreSQL-Konfiguration werden nicht überschrieben
- keine neuen Datenbanktabellen erforderlich

## Debian-Paket bauen

```bash
bash scripts/build_release.sh
```

Ergebnis:

```text
releases/stempeluhr_5.6.00_all.deb
releases/stempeluhr_5.6.00_all.deb.sha256
releases/stempeluhr_5.6.00_build.log
releases/stempeluhr_5.6.00_BUILD_REPORT.md
```

Die vollständige Anleitung steht in `docs/DEBIAN_BUILD.md`.

## Sicherheit

Produktive Zugangsdaten, `.env`-Dateien, Datenbanken, Uploads und Sicherungen gehören nicht in Git. Der Einrichtungsassistent zeigt keine Datenbankpasswörter oder Tokens an. Bestehende PostgreSQL-Daten und `/etc/stempeluhr/stempeluhr.env` dürfen bei Updates nicht gelöscht oder überschrieben werden.
