# Stempeluhr Professional 5.6.22

Webbasierte Zeiterfassung für Debian-Server und Raspberry-Pi-Terminals mit PostgreSQL, FastAPI, Rollen und Rechten, Reporting, Sicherheitsrichtlinien, Zusatz-Programmen und integriertem Hilfesystem.

## Aktueller Stand

- Version: **5.6.22**
- Standarddatenbank: PostgreSQL
- Zielplattform: Debian 13 / Raspberry Pi OS
- Standardbranch: `main`

## Änderungen in 5.6.22

- integrierter Updater verwendet weiterhin bevorzugt veröffentlichte GitHub-Releases
- wenn kein Release vorhanden ist, kann ein Administrator den aktuellen Stand des Branches `main` installieren
- der private Quellcode wird mit dem lokal hinterlegten GitHub-Lesetoken geladen
- der Quellcode wird in einem temporären Verzeichnis entpackt und mit `scripts/build_release.sh` zu einem Debian-Paket gebaut
- das fertige Paket wird an den bestehenden Update-Assistenten mit Backup, Installation und Healthcheck übergeben
- main-Update ist ausschließlich für Administratoren verfügbar
- geschützter privilegierter Runner und eng begrenzte sudoers-Regel ergänzt
- Token-Eingabe verwendet ein Passwortfeld im Popup und wird nicht im Klartext angezeigt

## Bereits enthalten

- Kommen- und Gehen-Uhrzeiten direkt in **Mein Report**
- Plausibilitätsmeldungen zurücksetzen
- Überstundenverwaltung mit Mitarbeiterfreigabe per E-Mail

## Installation und Update

```bash
cd ~/Stempeluhr
git pull --ff-only origin main
bash scripts/build_release.sh
sudo apt install ./releases/stempeluhr_5.6.22_all.deb
```

Erwartete Ergebnisse:

```text
releases/stempeluhr_5.6.22_all.deb
releases/stempeluhr_5.6.22_all.deb.sha256
releases/stempeluhr_5.6.22_build.log
releases/stempeluhr_5.6.22_BUILD_REPORT.md
```

## Web-Update aus GitHub-main

Nach Installation von 5.6.22 unter **Systemeinstellungen → Updates**:

1. GitHub-Lesetoken hinterlegen.
2. Auf GitHub nach Updates suchen.
3. Wenn kein veröffentlichtes Release vorhanden ist, **Aktuellen main-Stand bauen und installieren** wählen.

Der Token liegt ausschließlich lokal unter `/etc/stempeluhr/secrets/github_token`.

## Tests

Zu prüfen sind GitHub-main-Download mit privatem Repository, Paketbau, Backup, Installation, Dienstneustart, Healthcheck, Token-Popup, Kommen-/Gehen-Zeiten, Rollenrechte, Plausibilitäts-Reset und Überstundenfreigabe.
