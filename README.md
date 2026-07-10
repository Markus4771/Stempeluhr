# Stempeluhr Professional 5.5.08

Webbasierte Zeiterfassung für Debian-Server und Raspberry-Pi-Terminals mit PostgreSQL, FastAPI, Rollen und Rechten, Reporting, Onboarding und Raspberry-Kioskfunktionen.

## Aktueller Stand

- Version: **5.5.08**
- Standarddatenbank: PostgreSQL
- Zielplattform: Debian 13 / Raspberry Pi OS
- Standardbranch: `main`

Änderungen dieser Version:

- Systemdiagnose aus der Hauptnavigation entfernt
- Systemdiagnose in **Systemeinstellungen → Wartung** integriert
- direkter Diagnosezugang zusätzlich im Systemstatus der Systemeinstellungen
- Rücknavigation von der Diagnose zu den Systemeinstellungen ergänzt
- bestehende Diagnose-API und ZIP-Berichte unverändert erhalten
- keine Änderungen an Datenbankmodellen oder produktiven Daten

## Debian-Paket bauen

```bash
bash scripts/build_release.sh
```

Ergebnis:

```text
releases/stempeluhr_5.5.08_all.deb
releases/stempeluhr_5.5.08_all.deb.sha256
releases/stempeluhr_5.5.08_build.log
releases/stempeluhr_5.5.08_BUILD_REPORT.md
```

Die vollständige Anleitung steht in `docs/DEBIAN_BUILD.md`.

## Sicherheit

Produktive Zugangsdaten, `.env`-Dateien, Datenbanken, Uploads und Sicherungen gehören nicht in Git. Diagnoseberichte enthalten keine Passwörter oder Tokens. Bestehende PostgreSQL-Daten und `/etc/stempeluhr/stempeluhr.env` dürfen bei Updates nicht gelöscht oder überschrieben werden.
