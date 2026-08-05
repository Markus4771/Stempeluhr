# Stempeluhr Professional 5.7.0

Webbasierte Zeiterfassung für Debian-Server und Raspberry-Pi-Terminals.

## Aktueller Stand

- Version: **5.7.0**
- Standarddatenbank: PostgreSQL
- Zielplattform: Debian / Raspberry Pi OS
- Standardbranch: `main`

## Änderungen in 5.7.0

- Moderne Verwaltung für mehrere RFID-/NFC-Medien je Mitarbeiter.
- Entferntes Anlernen über einen ausgewählten Raspberry Pi, auch wenn die Weboberfläche an einem anderen PC geöffnet ist.
- Live-Status für Terminal, Scanauftrag, Zeitüberschreitung und erkannte UID.
- Raspberry-Agent für Tastatur-Wedge-RFID-/NFC-Leser über Linux `evdev`.
- Karten, Handys, Smartwatches, NFC-Ringe und weitere Medien werden getrennt verwaltet.
- Anzeige der letzten Verwendung eines Mediums.
- Die Backup-Verbesserungen aus 5.6.34 bleiben enthalten.

## Installation

```bash
cd ~/Stempeluhr
git pull --ff-only
bash scripts/build_release.sh
sudo apt install ./releases/stempeluhr_5.7.0_all.deb
sudo bash /opt/stempeluhr/scripts/install_rfid_agent.sh
```

Danach `/etc/stempeluhr/rfid-agent.env` prüfen und dort das richtige `RFID_INPUT_DEVICE` eintragen.
