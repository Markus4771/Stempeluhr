# Stempeluhr Professional 5.6.27

Webbasierte Zeiterfassung für Debian-Server und Raspberry-Pi-Terminals mit PostgreSQL, FastAPI, Rollen und Rechten, Reporting, Sicherheitsrichtlinien, Zusatz-Programmen und integriertem Hilfesystem.

## Aktueller Stand

- Version: **5.6.27**
- Standarddatenbank: PostgreSQL
- Zielplattform: Debian 13 / Raspberry Pi OS
- Standardbranch: `main`

## Änderungen in 5.6.27

- Dashboard zeigt Anwesenheit als Verhältnis `anwesend / aktiv`
- heutige Buchungen werden nach Kommen, Gehen und Pause aufgeschlüsselt
- Plausibilitätsmeldungen erhalten Warnstufen
- Überstunden werden rollenbezogen als eigener Stand, Team- oder Gesamtsumme angezeigt
- Backup-Alter wird bewertet: bis 24 Stunden grün, bis 72 Stunden gelb, danach rot
- Systemstatus berücksichtigt Datenbank, Backup, Speicherplatz, E-Mail-Konfiguration und GitHub-Token
- System-Schnellstatus wurde entsprechend erweitert

## Bereits enthalten

- frühere Raspberry-Kiosk-Oberfläche mit RFID-Feld und vier großen Buchungstasten
- optionale Stempelgründe und reine Personenstatus
- Zusatz-Programme werden ohne sichtbaren Eintrag vollständig aus dem Hauptmenü entfernt
- Kommen- und Gehen-Uhrzeiten in **Auswertung & Reporting**
- Plausibilitätsmeldungen zurücksetzen
- Überstundenverwaltung mit Mitarbeiterfreigabe per E-Mail
- Abwesenheitskalender je Abteilung

## Installation und Update

```bash
cd ~/Stempeluhr
git pull --ff-only origin main
bash scripts/build_release.sh
sudo apt install ./releases/stempeluhr_5.6.27_all.deb
```

## Tests

Zu prüfen sind Paketbau, Dienststart, Dashboard-Kennzahlen für Mitarbeiter/Teamleiter/Admin, Backup-Warnstufen, Speicherstatus, E-Mail-/GitHub-Anzeige, `/health` und `/version`.
