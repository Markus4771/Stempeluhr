# Stempeluhr Professional 5.6.33

Webbasierte Zeiterfassung für Debian-Server und Raspberry-Pi-Terminals.

## Aktueller Stand

- Version: **5.6.33**
- Standarddatenbank: PostgreSQL
- Zielplattform: Debian / Raspberry Pi OS
- Standardbranch: `main`

## Änderungen in 5.6.33

- Urlaubswochen werden verbindlich mit fünf Arbeitstagen berechnet.
- Samstage, Sonntage und volle Feiertage werden nicht vom Urlaubskonto abgezogen.
- Halbe Feiertage und halbe Urlaubstage werden mit 0,5 Tagen berücksichtigt.
- Unterstützte Modelle: feste 5-Tage-Woche, feste Teilzeit, unregelmäßiges Jahresmodell und manueller Anspruch.
- Eintritt, Austritt und Arbeitszeitwechsel können zeitanteilig berechnet werden.
- Getrennte Konten für Jahres-, Rest-, Zusatz- und Sonderurlaub sowie ein Buchungsjournal sind enthalten.
- Betriebsferien und die Rückbuchung bei Krankheit während des Urlaubs sind administrierbar.
- Verwaltung: `/vacation/management`

## Installation

```bash
cd ~/Stempeluhr
git pull --ff-only origin main
bash scripts/build_release.sh
sudo apt install ./releases/stempeluhr_5.6.33_all.deb
```
