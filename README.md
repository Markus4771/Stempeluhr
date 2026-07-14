# Stempeluhr Professional 5.6.24

Webbasierte Zeiterfassung für Debian-Server und Raspberry-Pi-Terminals mit PostgreSQL, FastAPI, Rollen und Rechten, Reporting, Sicherheitsrichtlinien, Zusatz-Programmen und integriertem Hilfesystem.

## Aktueller Stand

- Version: **5.6.24**
- Standarddatenbank: PostgreSQL
- Zielplattform: Debian 13 / Raspberry Pi OS
- Standardbranch: `main`

## Änderungen in 5.6.24

- der Hauptmenüpunkt `Zusatz-Programme` bleibt ausgeblendet, wenn keine Programme hinterlegt sind
- Zusatz-Programme bleiben zusätzlich nach Aktivstatus und Rollenfreigabe gefiltert
- Stempelgründe unterstützen reine Personenstatus ohne Kommen-/Gehen-Buchung
- Beispiele für reine Statusgründe: `Außer Haus`, `Bitte nicht stören`, `Besprechung`, `Homeoffice`
- ein eigener Stempelgrund kann den Personenstatus wieder zurücksetzen
- Personenstatus werden getrennt von Arbeitszeitbuchungen gespeichert

## Bereits enthalten

- Kommen- und Gehen-Uhrzeiten direkt in **Auswertung & Reporting**
- Plausibilitätsmeldungen zurücksetzen
- Überstundenverwaltung mit Mitarbeiterfreigabe per E-Mail
- administrierbare Stempelgründe am Raspberry-Kiosk
- Abwesenheitskalender je Abteilung
- rollenabhängige Zusatz-Programme

## Installation und Update

```bash
cd ~/Stempeluhr
git pull --ff-only origin main
bash scripts/build_release.sh
sudo apt install ./releases/stempeluhr_5.6.24_all.deb
```

Erwartete Ergebnisse:

```text
releases/stempeluhr_5.6.24_all.deb
releases/stempeluhr_5.6.24_all.deb.sha256
releases/stempeluhr_5.6.24_build.log
releases/stempeluhr_5.6.24_BUILD_REPORT.md
```

## Web-Update aus GitHub-main

Nach Installation von 5.6.24 unter **Systemeinstellungen → Updates**:

1. GitHub-Lesetoken hinterlegen.
2. Auf GitHub nach Updates suchen.
3. Wenn kein veröffentlichtes Release vorhanden ist, den aktuellen `main`-Stand bauen und installieren.

Der Token liegt ausschließlich lokal unter `/etc/stempeluhr/secrets/github_token`.

## Tests

Zu prüfen sind Paketbau, Dienststart, ausgeblendetes Zusatz-Programme-Menü ohne Einträge, Rollenfreigaben, reine Personenstatus am Kiosk, Statusrücksetzung und unveränderte automatische Kommen-/Gehen-Buchung ohne Auswahl.
