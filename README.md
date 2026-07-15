# Stempeluhr Professional 5.6.26

Webbasierte Zeiterfassung für Debian-Server und Raspberry-Pi-Terminals mit PostgreSQL, FastAPI, Rollen und Rechten, Reporting, Sicherheitsrichtlinien, Zusatz-Programmen und integriertem Hilfesystem.

## Aktueller Stand

- Version: **5.6.26**
- Standarddatenbank: PostgreSQL
- Zielplattform: Debian 13 / Raspberry Pi OS
- Standardbranch: `main`

## Änderungen in 5.6.26

- frühere Raspberry-Kiosk-Oberfläche wiederhergestellt
- RFID-Feld und die vier großen Tasten `Kommen`, `Gehen`, `Pause Start` und `Pause Ende` sind wieder sichtbar
- automatische Buchung nach der konfigurierten Wartezeit bleibt erhalten
- Links zu Admin, Auswertung und Korrektur bleiben wie im früheren Kiosk
- optionale Stempelgründe sind kompakt in das alte Design integriert
- reine Personenstatus und Statusrücksetzung bleiben unterstützt

## Bereits enthalten

- Zusatz-Programme werden ohne sichtbaren Eintrag vollständig aus dem Hauptmenü entfernt
- Kommen- und Gehen-Uhrzeiten direkt in **Auswertung & Reporting**
- Plausibilitätsmeldungen zurücksetzen
- Überstundenverwaltung mit Mitarbeiterfreigabe per E-Mail
- Abwesenheitskalender je Abteilung

## Installation und Update

```bash
cd ~/Stempeluhr
git pull --ff-only origin main
bash scripts/build_release.sh
sudo apt install ./releases/stempeluhr_5.6.26_all.deb
```

Erwartete Ergebnisse:

```text
releases/stempeluhr_5.6.26_all.deb
releases/stempeluhr_5.6.26_all.deb.sha256
releases/stempeluhr_5.6.26_build.log
releases/stempeluhr_5.6.26_BUILD_REPORT.md
```

## Tests

Zu prüfen sind Paketbau, Dienststart, altes Raspberry-Kiosk-Layout, manuelle Kommen-/Gehen-/Pausenbuchung, automatische Buchung, optionale Stempelgründe, RFID-Lernmodus und Personenstatus.
