# Stempeluhr Professional 5.6.19

Webbasierte Zeiterfassung für Debian-Server und Raspberry-Pi-Terminals mit PostgreSQL, FastAPI, Rollen und Rechten, Reporting, Sicherheitsrichtlinien, Zusatz-Programmen und integriertem Hilfesystem.

## Aktueller Stand

- Version: **5.6.19**
- Standarddatenbank: PostgreSQL
- Zielplattform: Debian 13 / Raspberry Pi OS
- Standardbranch: `main`

## Änderungen in 5.6.19

- Stempelzeiten in **Mein Report** werden serverseitig exakt nach Mitarbeiter und gewähltem Zeitraum geladen
- Begrenzung auf die letzten 300 allgemeinen Buchungen entfernt
- Buchungsarten werden verständlich als **Kommen** und **Gehen** dargestellt
- Mitarbeiter bleiben auf den eigenen Report beschränkt
- Teamleiter sehen ausschließlich die ihnen zugeordneten Mitarbeiter
- GitHub-Updater unterstützt private Repositorys über einen geschützten Zugriffstoken
- Token kann aus `/etc/stempeluhr/secrets/github_token` oder `STEMPELUHR_GITHUB_TOKEN` gelesen werden
- HTTP-404-Meldung des GitHub-Updaters wurde präzisiert

## Bereits enthalten aus 5.6.18

- Filter der Plausibilitätsprüfung bleiben nach dem Speichern erhalten
- öffentlicher Datenschutzlink bei der Kontoeinrichtung
- öffentliche Datenschutzerklärung unter `/datenschutz`

## Automatische Installation und Wartung

Auf einem bestehenden Produktivsystem:

```bash
cd ~/Stempeluhr
git restore install.sh
git pull --ff-only origin main
sudo bash install.sh update
```

Bei einer Erstinstallation:

```bash
sudo bash install.sh install
```

Standardmäßig werden Backups unter `/var/backups/stempeluhr` gespeichert.

## Debian-Paket manuell bauen

```bash
bash scripts/build_release.sh
```

Erwartete Ergebnisse:

```text
releases/stempeluhr_5.6.19_all.deb
releases/stempeluhr_5.6.19_all.deb.sha256
releases/stempeluhr_5.6.19_build.log
releases/stempeluhr_5.6.19_BUILD_REPORT.md
```

## Test und Installation

Version 5.6.19 zuerst auf dem Testsystem installieren. Zu testen sind Stempelzeiten mit Kommen/Gehen im persönlichen Report, Mitarbeiter- und Teamleiterrechte, Plausibilitätsfilter, GitHub-Update mit privatem Repository, `/datenschutz`, `/health` und `/version`.
