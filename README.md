# Stempeluhr Professional 5.6.25

Webbasierte Zeiterfassung für Debian-Server und Raspberry-Pi-Terminals mit PostgreSQL, FastAPI, Rollen und Rechten, Reporting, Sicherheitsrichtlinien, Zusatz-Programmen und integriertem Hilfesystem.

## Aktueller Stand

- Version: **5.6.25**
- Standarddatenbank: PostgreSQL
- Zielplattform: Debian 13 / Raspberry Pi OS
- Standardbranch: `main`

## Änderungen in 5.6.25

- der Hauptmenüpunkt `Zusatz-Programme` wird bei leerer oder nicht freigegebener Programmliste vollständig aus der Seite entfernt
- die bisherige reine `hidden`-Darstellung wurde durch eine robuste DOM-Entfernung ergänzt
- Fehler beim Laden der Sichtbarkeitsprüfung führen ebenfalls zum sicheren Ausblenden
- Rollen- und Aktivitätsfilter der Zusatz-Programme bleiben erhalten

## Bereits enthalten

- reine Personenstatus als Stempelgrund ohne Arbeitszeitbuchung
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
sudo apt install ./releases/stempeluhr_5.6.25_all.deb
```

Erwartete Ergebnisse:

```text
releases/stempeluhr_5.6.25_all.deb
releases/stempeluhr_5.6.25_all.deb.sha256
releases/stempeluhr_5.6.25_build.log
releases/stempeluhr_5.6.25_BUILD_REPORT.md
```

## Web-Update aus GitHub-main

Nach Installation von 5.6.25 unter **Systemeinstellungen → Updates**:

1. GitHub-Lesetoken hinterlegen.
2. Auf GitHub nach Updates suchen.
3. Wenn kein veröffentlichtes Release vorhanden ist, den aktuellen `main`-Stand bauen und installieren.

Der Token liegt ausschließlich lokal unter `/etc/stempeluhr/secrets/github_token`.

## Tests

Zu prüfen sind Paketbau, Dienststart, vollständig ausgeblendetes Zusatz-Programme-Menü ohne Einträge, Rollenfreigaben, reine Personenstatus am Kiosk, Statusrücksetzung und unveränderte automatische Kommen-/Gehen-Buchung ohne Auswahl.
