# Stempeluhr Professional 5.6.20

Webbasierte Zeiterfassung für Debian-Server und Raspberry-Pi-Terminals mit PostgreSQL, FastAPI, Rollen und Rechten, Reporting, Sicherheitsrichtlinien, Zusatz-Programmen und integriertem Hilfesystem.

## Aktueller Stand

- Version: **5.6.20**
- Standarddatenbank: PostgreSQL
- Zielplattform: Debian 13 / Raspberry Pi OS
- Standardbranch: `main`

## Änderungen in 5.6.20

- Plausibilitätsmeldungen können durch Administrator, Personal und zuständige Teamleiter auf `offen` zurückgesetzt werden
- Kommentar, Erledigungszeit und Bearbeiter werden beim Zurücksetzen entfernt
- neue Überstundenverwaltung für Administrator, Personal und Teamleiter
- Überstundenstand kann auf `0`, einen positiven oder negativen Zielwert gesetzt werden
- sofortige oder zeitlich geplante Wirksamkeit
- Änderung wird erst nach Genehmigung des Mitarbeiters per E-Mail wirksam
- vollständiger Änderungsverlauf mit Altwert, Zielwert, Zeitpunkt und Status
- Kommen-/Gehen-Anzeige in `Mein Report` robuster eingebunden

## GitHub-Update

Der integrierte Web-Updater installiert ausschließlich **veröffentlichte GitHub-Releases** mit einem passenden DEB/SHA256-Paar. Ein Git-Commit oder lokal gebautes Paket ist noch kein GitHub-Release. Bei einem privaten Repository ist zusätzlich ein Lesetoken unter `/etc/stempeluhr/secrets/github_token` erforderlich.

## Installation und Update

```bash
cd ~/Stempeluhr
git pull --ff-only origin main
bash scripts/build_release.sh
sudo apt install ./releases/stempeluhr_5.6.20_all.deb
```

Erwartete Ergebnisse:

```text
releases/stempeluhr_5.6.20_all.deb
releases/stempeluhr_5.6.20_all.deb.sha256
releases/stempeluhr_5.6.20_build.log
releases/stempeluhr_5.6.20_BUILD_REPORT.md
```

## Tests

Zu prüfen sind Plausibilitäts-Reset, Überstundenfreigabe per E-Mail, geplante Wirksamkeit, Rollen- und Abteilungsrechte, Kommen-/Gehen-Zeiten im Report, `/health` und `/version`.
