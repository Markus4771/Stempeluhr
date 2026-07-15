# Stempeluhr Professional 5.6.28

Webbasierte Zeiterfassung für Debian-Server und Raspberry-Pi-Terminals mit PostgreSQL, FastAPI, Rollen und Rechten, Reporting, Sicherheitsrichtlinien, Zusatz-Programmen und integriertem Hilfesystem.

## Aktueller Stand

- Version: **5.6.28**
- Standarddatenbank: PostgreSQL
- Zielplattform: Debian 13 / Raspberry Pi OS
- Standardbranch: `main`

## Änderungen in 5.6.28

- Dashboard-Kennzahlen verwenden eine einheitliche Basis aktiver Mitarbeiter
- widersprüchliche Anzeige `anwesend / aktiv` und abweichende Unterzeile entfernt
- Kachel `Heute nicht anwesend` entfernt, da sie dieselbe Information doppelt darstellte
- Anwesenheit wird kompakt als Zahl plus `von X aktiven` angezeigt
- Systemstatus nennt den konkreten Hauptgrund, z. B. `Backup veraltet` oder `Speicher knapp`
- E-Mail- und GitHub-Token-Status lösen keinen roten Gesamtstatus mehr aus
- Backup-Alter wird als Stunden oder Tage verständlich ausgegeben
- Dashboard-Kacheln wurden sprachlich gekürzt und übersichtlicher gestaltet

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
sudo apt install ./releases/stempeluhr_5.6.28_all.deb
```

## Tests

Zu prüfen sind Paketbau, Dienststart, konsistente Anwesenheitswerte, konkrete Systemstatusmeldung, Backup-Alter, Rollenansichten, `/health` und `/version`.
