# Stempeluhr Professional 5.6.18

Webbasierte Zeiterfassung für Debian-Server und Raspberry-Pi-Terminals mit PostgreSQL, FastAPI, Rollen und Rechten, Reporting, Sicherheitsrichtlinien, Zusatz-Programmen und integriertem Hilfesystem.

## Aktueller Stand

- Version: **5.6.18**
- Standarddatenbank: PostgreSQL
- Zielplattform: Debian 13 / Raspberry Pi OS
- Standardbranch: `main`

## Änderungen in 5.6.18

- Filter der Plausibilitätsprüfung bleiben nach dem Speichern erhalten
- gespeicherter Status und Kommentar werden wieder angezeigt
- Stempelzeiten werden in **Mein Report** für den gewählten Zeitraum aufgeführt
- Mitarbeiter sehen ausschließlich den eigenen Report
- Teamleiter sehen nur die ihnen zugeordneten Mitarbeiter
- Personal und Administratoren behalten den vorgesehenen erweiterten Zugriff
- öffentliche Datenschutzerklärung unter `/datenschutz`
- Link zur Datenschutzerklärung bei der Kontoeinrichtung ergänzt

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
releases/stempeluhr_5.6.18_all.deb
releases/stempeluhr_5.6.18_all.deb.sha256
releases/stempeluhr_5.6.18_build.log
releases/stempeluhr_5.6.18_BUILD_REPORT.md
```

## Test und Installation

Version 5.6.18 zuerst auf der Debian-13-Test-VM installieren. Zu testen sind Plausibilitätsfilter, persönliche und Vorgesetzten-Reports, Stempelzeiten, Kontoeinrichtung, `/datenschutz`, `/health` und `/version`.
