# Stempeluhr Professional 5.6.10

Webbasierte Zeiterfassung für Debian-Server und Raspberry-Pi-Terminals mit PostgreSQL, FastAPI, Rollen und Rechten, Reporting, Onboarding und Raspberry-Kioskfunktionen.

## Aktueller Stand

- Version: **5.6.10**
- Standarddatenbank: PostgreSQL
- Zielplattform: Debian 13 / Raspberry Pi OS
- Standardbranch: `main`

Änderungen dieser Version:

- automatisches GitHub-Release-System für fertige Debian-Pakete
- normale Pushes bauen weiterhin ein zeitlich begrenztes Actions-Artefakt
- ein Versions-Tag wie `v5.6.10` erzeugt ein dauerhaftes GitHub Release
- Tag und `version.txt` müssen exakt übereinstimmen
- Release enthält `.deb`, SHA256-Prüfsumme, Buildbericht und Changelog
- Release Notes werden automatisch aus dem aktuellen Changelog-Abschnitt erzeugt
- bestehende Daten, Benutzer und PostgreSQL-Konfiguration werden nicht verändert

## Debian-Paket lokal bauen

```bash
bash scripts/build_release.sh
```

Ergebnis:

```text
releases/stempeluhr_5.6.10_all.deb
releases/stempeluhr_5.6.10_all.deb.sha256
releases/stempeluhr_5.6.10_build.log
releases/stempeluhr_5.6.10_BUILD_REPORT.md
```

## GitHub Release veröffentlichen

Erst wenn der Stand gebaut und geprüft wurde, wird der passende Tag gesetzt:

```bash
git tag -a v5.6.10 -m "Stempeluhr Professional 5.6.10"
git push origin v5.6.10
```

GitHub Actions baut das Paket erneut, prüft Paketname, Version, Inhalt und SHA256 und veröffentlicht anschließend unter **GitHub → Releases**:

```text
stempeluhr_5.6.10_all.deb
stempeluhr_5.6.10_all.deb.sha256
stempeluhr_5.6.10_BUILD_REPORT.md
stempeluhr_5.6.10_changelog.md
```

Ein normaler Push auf `main` veröffentlicht ausdrücklich kein Release.

## Installation aus einem GitHub Release

Nach dem Download:

```bash
sha256sum -c stempeluhr_5.6.10_all.deb.sha256
sudo dpkg -i stempeluhr_5.6.10_all.deb
```

Die vollständige lokale Build-Anleitung steht in `docs/DEBIAN_BUILD.md`.

## Sicherheit

Produktive Zugangsdaten, `.env`-Dateien, Datenbanken, Uploads und Sicherungen gehören nicht in Git. GitHub Releases dürfen erst nach erfolgreichem Build und Prüfung erzeugt werden. Bestehende PostgreSQL-Daten und `/etc/stempeluhr/stempeluhr.env` dürfen bei Updates nicht gelöscht oder überschrieben werden.
