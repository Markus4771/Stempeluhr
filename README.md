# Stempeluhr Professional 5.5.04

Webbasierte Zeiterfassung für Debian-Server und Raspberry-Pi-Terminals mit PostgreSQL, FastAPI, Rollen und Rechten, Reporting, Onboarding und Raspberry-Kioskfunktionen.

## Aktueller Stand

- Version: **5.5.04**
- Standarddatenbank: PostgreSQL
- Zielplattform: Debian 13 / Raspberry Pi OS
- Standardbranch: `main`

Änderungen dieser Version:

- Onboarding aus dem Hauptmenü entfernt
- Einladungsbutton in der Mitarbeiterverwaltung dauerhaft verfügbar

## Debian-Paket bauen

Der Build ist ausschließlich für dieses Projekt im Repository enthalten:

```bash
chmod +x scripts/build_release.sh debian/postinst debian/prerm
./scripts/build_release.sh
```

Ergebnis:

```text
releases/stempeluhr_5.5.04_all.deb
releases/stempeluhr_5.5.04_all.deb.sha256
releases/stempeluhr_5.5.04_build.log
```

Das Buildskript prüft Versionsgleichheit, Git-Status, Python-Syntax, Paketmetadaten und den Ausschluss lokaler Konfigurationen und Datenbanken.

Die vollständige Anleitung steht in `docs/DEBIAN_BUILD.md`.

## Sicherheit

Produktive Zugangsdaten, `.env`-Dateien, Datenbanken, Uploads und Sicherungen gehören nicht in Git. Bestehende PostgreSQL-Daten und `/etc/stempeluhr/stempeluhr.env` dürfen bei Updates nicht gelöscht oder überschrieben werden.
