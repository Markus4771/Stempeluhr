# Stempeluhr Professional 5.5.06

Webbasierte Zeiterfassung für Debian-Server und Raspberry-Pi-Terminals mit PostgreSQL, FastAPI, Rollen und Rechten, Reporting, Onboarding und Raspberry-Kioskfunktionen.

## Aktueller Stand

- Version: **5.5.06**
- Standarddatenbank: PostgreSQL
- Zielplattform: Debian 13 / Raspberry Pi OS
- Standardbranch: `main`

Änderungen dieser Version:

- Hotfix für PostgreSQL-Verbindungen mit Sonderzeichen im Passwort
- lokale PostgreSQL-Verbindungen verwenden kein geerbtes Root-Zertifikatsverzeichnis
- Updateinstallation ändert vorhandene PostgreSQL-Rollenpasswörter nicht mehr
- Migrationen laufen mit sauberer Benutzerumgebung des Dienstkontos `stempeluhr`
- bestehende Datenbank und `/etc/stempeluhr/stempeluhr.env` bleiben erhalten

## Debian-Paket bauen

Der Build ist ausschließlich für dieses Projekt im Repository enthalten:

```bash
bash scripts/build_release.sh
```

Ergebnis:

```text
releases/stempeluhr_5.5.06_all.deb
releases/stempeluhr_5.5.06_all.deb.sha256
releases/stempeluhr_5.5.06_build.log
releases/stempeluhr_5.5.06_BUILD_REPORT.md
```

Das Buildskript prüft Versionsgleichheit, Git-Status, Python-Syntax, Paketmetadaten und den Ausschluss lokaler Konfigurationen und Datenbanken.

Die vollständige Anleitung steht in `docs/DEBIAN_BUILD.md`.

## Sicherheit

Produktive Zugangsdaten, `.env`-Dateien, Datenbanken, Uploads und Sicherungen gehören nicht in Git. Bestehende PostgreSQL-Daten und `/etc/stempeluhr/stempeluhr.env` dürfen bei Updates nicht gelöscht oder überschrieben werden.
