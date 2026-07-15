# Stempeluhr Professional 5.6.29

Webbasierte Zeiterfassung für Debian-Server und Raspberry-Pi-Terminals mit PostgreSQL, FastAPI, Rollen und Rechten, Reporting, Sicherheitsrichtlinien, Zusatz-Programmen und integriertem Hilfesystem.

## Aktueller Stand

- Version: **5.6.29**
- Standarddatenbank: PostgreSQL
- Zielplattform: Debian 13 / Raspberry Pi OS
- Standardbranch: `main`

## Änderungen in 5.6.29

- Dashboard wird rollenabhängig reduziert
- Mitarbeiter sehen persönliche Informationen und die eigene Überstundenanzeige
- Teamleiter sehen Anwesenheit und offene Vorgänge des Teams
- Personal und Administratoren sehen übergreifende Vorgänge
- technische Backup- und Systeminformationen erscheinen nur für Administratoren
- Tabellen mit letzten Buchungen, anwesenden Namen und Aktivitäten wurden aus der normalen Mitarbeiteransicht entfernt
- angemeldete Benutzer können optional direkt das eigene Kommen oder Gehen buchen
- die direkte Eigenbuchung ist global unter `Allgemeine Einstellungen → Dashboard-Buchung konfigurieren` aktivierbar
- zentrale Zustandsprüfung, Doppelbuchungsschutz und Audit-Protokoll bleiben aktiv
- der feste Systemadministrator ist von Arbeitszeitbuchungen ausgeschlossen

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
sudo apt install ./releases/stempeluhr_5.6.29_all.deb
```

## Tests

Zu prüfen sind Paketbau, Dienststart, Dashboard mit Mitarbeiter/Teamleiter/Personal/Admin, aktivierte und deaktivierte Eigenbuchung, Buchungsfolgen, Doppelbuchungsschutz, Audit-Protokoll, `/health` und `/version`.
