# Stempeluhr Professional 5.6.11

Webbasierte Zeiterfassung für Debian-Server und Raspberry-Pi-Terminals mit PostgreSQL, FastAPI, Rollen und Rechten, Reporting, Onboarding und Raspberry-Kioskfunktionen.

## Aktueller Stand

- Version: **5.6.11**
- Standarddatenbank: PostgreSQL
- Zielplattform: Debian 13 / Raspberry Pi OS
- Standardbranch: `main`

Änderungen dieser Version:

- bestehende Updateverwaltung um stabile GitHub Releases erweitert
- manuelles Hochladen von `.deb`-Paketen bleibt unverändert verfügbar
- neue Prüfung auf die neueste GitHub-Version direkt unter **Systemeinstellungen → Wartung → Updates**
- Release Notes werden auf der vorhandenen Update-Seite angezeigt
- GitHub-Paket und veröffentlichte SHA256-Datei werden vor der Installation geprüft
- das geprüfte Paket wird anschließend an denselben bestehenden Update-Runner übergeben
- Backup, Installation, Neustart, Fortschrittsanzeige und Healthcheck bleiben zentral erhalten
- keine Änderungen an Datenbankmodellen oder produktiven Daten

## Debian-Paket lokal bauen

```bash
bash scripts/build_release.sh
```

Ergebnis:

```text
releases/stempeluhr_5.6.11_all.deb
releases/stempeluhr_5.6.11_all.deb.sha256
releases/stempeluhr_5.6.11_build.log
releases/stempeluhr_5.6.11_BUILD_REPORT.md
```

## GitHub Release veröffentlichen

Erst nach lokalem Build, Installation und Prüfung:

```bash
git tag -a v5.6.11 -m "Stempeluhr Professional 5.6.11"
git push origin v5.6.11
```

Das Release enthält `.deb`, SHA256, Buildbericht und Changelog. Ein normaler Push auf `main` erzeugt nur ein zeitlich begrenztes Actions-Artefakt.

## Integriertes Update

Unter **Systemeinstellungen → Wartung → Updates** kann entweder ein Paket manuell hochgeladen oder das neueste stabile GitHub Release geprüft und installiert werden. Beide Wege verwenden denselben bestehenden Update-Runner.

## Sicherheit

Produktive Zugangsdaten, `.env`-Dateien, Datenbanken, Uploads und Sicherungen gehören nicht in Git. GitHub-Pakete werden nur zusammen mit der veröffentlichten SHA256-Datei akzeptiert. Bestehende PostgreSQL-Daten und `/etc/stempeluhr/stempeluhr.env` dürfen bei Updates nicht gelöscht oder überschrieben werden.
