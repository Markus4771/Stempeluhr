# Stempeluhr Professional 5.5.05

Webbasierte Zeiterfassung für Debian-Server und Raspberry-Pi-Terminals mit PostgreSQL, FastAPI, Rollen und Rechten, Reporting, Onboarding und Raspberry-Kioskfunktionen.

## Aktueller Stand

- Version: **5.5.05**
- Standarddatenbank: PostgreSQL
- Zielplattform: Debian 13 / Raspberry Pi OS
- Standardbranch: `main`

Änderungen dieser Version:

- projektspezifischer Debian-Buildprozess erweitert
- automatischer Buildbericht mit Version, Commit, Systemdaten, Paketgröße und Prüfsumme
- doppelte Changelog-Datei bereinigt; verbindlich ist `changelog.md`
- keine Änderung an produktiven Datenbankmodellen oder Zeiterfassungsfunktionen

## Debian-Paket bauen

Der Build ist ausschließlich für dieses Projekt im Repository enthalten:

```bash
bash scripts/build_release.sh
```

Ergebnis:

```text
releases/stempeluhr_5.5.05_all.deb
releases/stempeluhr_5.5.05_all.deb.sha256
releases/stempeluhr_5.5.05_build.log
releases/stempeluhr_5.5.05_BUILD_REPORT.md
```

Das Buildskript prüft Versionsgleichheit, Git-Status, Python-Syntax, Paketmetadaten und den Ausschluss lokaler Konfigurationen und Datenbanken.

Die vollständige Anleitung steht in `docs/DEBIAN_BUILD.md`.

## Sicherheit

Produktive Zugangsdaten, `.env`-Dateien, Datenbanken, Uploads und Sicherungen gehören nicht in Git. Bestehende PostgreSQL-Daten und `/etc/stempeluhr/stempeluhr.env` dürfen bei Updates nicht gelöscht oder überschrieben werden.
