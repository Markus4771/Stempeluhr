# Stempeluhr Professional 5.5.07

Webbasierte Zeiterfassung für Debian-Server und Raspberry-Pi-Terminals mit PostgreSQL, FastAPI, Rollen und Rechten, Reporting, Onboarding und Raspberry-Kioskfunktionen.

## Aktueller Stand

- Version: **5.5.07**
- Standarddatenbank: PostgreSQL
- Zielplattform: Debian 13 / Raspberry Pi OS
- Standardbranch: `main`

Änderungen dieser Version:

- neue Admin-Seite **Systemdiagnose**
- geschützte Diagnose-API unter `/diagnostics` und `/api/v1/diagnostics`
- Prüfung von PostgreSQL, Konfiguration, Speicherplatz, Verzeichnissen und Schreibrechten
- Anzeige von Version, Python, Laufzeit, PostgreSQL-Version, Mitarbeiter- und Buchungsanzahl
- Diagnosebericht als ZIP ohne Passwörter, Tokens oder Secrets
- erweiterte Startup-Prüfungen mit verständlichen Warnungen

## Debian-Paket bauen

```bash
bash scripts/build_release.sh
```

Ergebnis:

```text
releases/stempeluhr_5.5.07_all.deb
releases/stempeluhr_5.5.07_all.deb.sha256
releases/stempeluhr_5.5.07_build.log
releases/stempeluhr_5.5.07_BUILD_REPORT.md
```

Die vollständige Anleitung steht in `docs/DEBIAN_BUILD.md`.

## Sicherheit

Produktive Zugangsdaten, `.env`-Dateien, Datenbanken, Uploads und Sicherungen gehören nicht in Git. Diagnoseberichte enthalten keine Passwörter oder Tokens. Bestehende PostgreSQL-Daten und `/etc/stempeluhr/stempeluhr.env` dürfen bei Updates nicht gelöscht oder überschrieben werden.
