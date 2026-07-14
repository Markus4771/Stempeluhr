# Stempeluhr Professional 5.6.23

Webbasierte Zeiterfassung für Debian-Server und Raspberry-Pi-Terminals mit PostgreSQL, FastAPI, Rollen und Rechten, Reporting, Sicherheitsrichtlinien, Zusatz-Programmen und integriertem Hilfesystem.

## Aktueller Stand

- Version: **5.6.23**
- Standarddatenbank: PostgreSQL
- Zielplattform: Debian 13 / Raspberry Pi OS
- Standardbranch: `main`

## Änderungen in 5.6.23

- Zusatz-Programme können pro Eintrag für bestimmte Rollen freigegeben werden
- bestehende Einträge ohne Rollenangabe bleiben aus Kompatibilitätsgründen für Administrator, Personal, Teamleiter und Mitarbeiter sichtbar
- die Programmübersicht zeigt nur aktive und für die aktuelle Rolle freigegebene Programme
- der Hauptmenüpunkt `Zusatz-Programme` wird nur eingeblendet, wenn mindestens ein freigegebenes Programm vorhanden ist
- Rollenfreigaben werden in der Administrationsoberfläche gepflegt und im Audit-Protokoll dokumentiert
- Report-Webansicht, CSV, PDF und E-Mail-Anhang verwenden dieselbe Filterung vollständiger, nicht zukünftiger Tage

## Bereits enthalten

- Kommen- und Gehen-Uhrzeiten direkt in **Auswertung & Reporting**
- Plausibilitätsmeldungen zurücksetzen
- Überstundenverwaltung mit Mitarbeiterfreigabe per E-Mail
- administrierbare Stempelgründe am Raspberry-Kiosk
- Abwesenheitskalender je Abteilung

## Installation und Update

```bash
cd ~/Stempeluhr
git pull --ff-only origin main
bash scripts/build_release.sh
sudo apt install ./releases/stempeluhr_5.6.23_all.deb
```

Erwartete Ergebnisse:

```text
releases/stempeluhr_5.6.23_all.deb
releases/stempeluhr_5.6.23_all.deb.sha256
releases/stempeluhr_5.6.23_build.log
releases/stempeluhr_5.6.23_BUILD_REPORT.md
```

## Web-Update aus GitHub-main

Nach Installation von 5.6.23 unter **Systemeinstellungen → Updates**:

1. GitHub-Lesetoken hinterlegen.
2. Auf GitHub nach Updates suchen.
3. Wenn kein veröffentlichtes Release vorhanden ist, den aktuellen `main`-Stand bauen und installieren.

Der Token liegt ausschließlich lokal unter `/etc/stempeluhr/secrets/github_token`.

## Tests

Zu prüfen sind Paketbau, Dienststart, Rollenfreigaben der Zusatz-Programme, dynamische Hauptnavigation, direkter Zugriffsschutz, Report-Summen, CSV-/PDF-Ausgabe, Kiosk-Stempelgründe und Abteilungskalender.
