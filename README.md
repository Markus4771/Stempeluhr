# Stempeluhr Professional 5.6.32

Webbasierte Zeiterfassung für Debian-Server und Raspberry-Pi-Terminals.

## Aktueller Stand

- Version: **5.6.32**
- Standarddatenbank: PostgreSQL
- Zielplattform: Debian / Raspberry Pi OS
- Standardbranch: `main`

## Änderungen in 5.6.32

- `Meine Zeiterfassung` enthält jetzt Kommen, Gehen, Pause Start und Pause Ende.
- Aktive Stempelgründe werden zusätzlich im Dashboard angeboten.
- Stempelgründe können Arbeitszeitbuchungen oder reine Personenstatus auslösen.
- Die Freigabe bleibt je Mitarbeiter administrierbar.

## Installation

```bash
cd ~/Stempeluhr
git pull --ff-only origin main
bash scripts/build_release.sh
sudo apt install ./releases/stempeluhr_5.6.32_all.deb
```
