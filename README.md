# Stempeluhr Professional 5.6.31

Webbasierte Zeiterfassung für Debian-Server und Raspberry-Pi-Terminals.

## Aktueller Stand

- Version: **5.6.31**
- Standarddatenbank: PostgreSQL
- Zielplattform: Debian / Raspberry Pi OS
- Standardbranch: `main`

## Änderungen in 5.6.31

- Dashboard-Buchung bleibt für bestehende Mitarbeiter standardmäßig verfügbar.
- Die Freigabe kann je Mitarbeiter verwaltet werden.
- Dashboard-Überstunden werden aus den Arbeitszeitdaten berechnet.
- Eine genehmigte Überstundenanpassung dient als neuer Ausgangswert.
- CSV und PDF verwenden die erweiterten Routen mit Kommen- und Gehen-Zeiten.

## Installation

```bash
cd ~/Stempeluhr
git pull --ff-only origin main
bash scripts/build_release.sh
sudo apt install ./releases/stempeluhr_5.6.31_all.deb
```
