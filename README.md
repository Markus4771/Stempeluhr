# Stempeluhr Professional 5.6.30

Webbasierte Zeiterfassung für Debian-Server und Raspberry-Pi-Terminals mit PostgreSQL, FastAPI, Rollen und Rechten, Reporting, Sicherheitsrichtlinien, Zusatz-Programmen und integriertem Hilfesystem.

## Aktueller Stand

- Version: **5.6.30**
- Standarddatenbank: PostgreSQL
- Zielplattform: Debian 13 / Raspberry Pi OS
- Standardbranch: `main`

## Änderungen in 5.6.30

- CSV- und PDF-Report zeigen Kommen- und Gehen-Zeiten direkt je Tageszeile
- beide Exportformate enthalten zusätzlich eine vollständige Liste aller Stempelzeiten
- die Liste `Aktuell anwesend` bleibt für alle angemeldeten Rollen sichtbar
- passwortlose Kommen-/Gehen-Buchung wird pro Mitarbeiter verwaltet
- die Freigabe befindet sich in der Mitarbeiter-Bearbeitung unter `Dashboard-Buchung`
- die bisherige globale Freigabe in den allgemeinen Einstellungen wurde entfernt
- Buchungszustand, Doppelbuchungsschutz und Audit-Protokoll bleiben aktiv

## Installation und Update

```bash
cd ~/Stempeluhr
git pull --ff-only origin main
bash scripts/build_release.sh
sudo apt install ./releases/stempeluhr_5.6.30_all.deb
```

## Tests

Zu prüfen sind Paketbau, Dienststart, CSV-/PDF-Ausgabe mit Stempelzeiten, Anzeige der aktuell Anwesenden für alle Rollen, Mitarbeiterfreigabe der Dashboard-Buchung, Buchungsfolgen, `/health` und `/version`.
