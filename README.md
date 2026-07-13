# Stempeluhr Professional 5.6.21

Webbasierte Zeiterfassung für Debian-Server und Raspberry-Pi-Terminals mit PostgreSQL, FastAPI, Rollen und Rechten, Reporting, Sicherheitsrichtlinien, Zusatz-Programmen und integriertem Hilfesystem.

## Aktueller Stand

- Version: **5.6.21**
- Standarddatenbank: PostgreSQL
- Zielplattform: Debian 13 / Raspberry Pi OS
- Standardbranch: `main`

## Änderungen in 5.6.21

- Kommen- und Gehen-Uhrzeiten werden direkt in **Mein Report** aus der Datenbank geladen
- Filterung erfolgt serverseitig nach Berechtigung, Mitarbeiter und gewähltem Zeitraum
- iframe-/JavaScript-Zwischenlösung für Stempelzeiten entfernt
- Menüeinträge **Überstunden** und **Plausibilität** für Teamleiter, Personal und Administratoren sichtbar
- GitHub-Token kann in der Updateverwaltung über ein Eingabefenster hinterlegt oder ersetzt werden
- bei fehlendem Token wird das Eingabefenster automatisch nach einer fehlgeschlagenen GitHub-Prüfung geöffnet
- Token wird lokal unter `/etc/stempeluhr/secrets/github_token` mit restriktiven Rechten gespeichert

## Bereits enthalten aus 5.6.20

- Plausibilitätsmeldungen können durch Administrator, Personal und zuständige Teamleiter auf `offen` zurückgesetzt werden
- Überstundenverwaltung mit Zielwert, sofortiger oder geplanter Wirksamkeit
- Mitarbeiterfreigabe per E-Mail vor einer Überstundenänderung

## Installation und Update

```bash
cd ~/Stempeluhr
git pull --ff-only origin main
bash scripts/build_release.sh
sudo apt install ./releases/stempeluhr_5.6.21_all.deb
```

Erwartete Ergebnisse:

```text
releases/stempeluhr_5.6.21_all.deb
releases/stempeluhr_5.6.21_all.deb.sha256
releases/stempeluhr_5.6.21_build.log
releases/stempeluhr_5.6.21_BUILD_REPORT.md
```

## Tests

Zu prüfen sind Kommen-/Gehen-Zeiten im Report, Mitarbeiter- und Teamleiterrechte, Plausibilitäts-Reset, Überstundenfreigabe per E-Mail, Token-Eingabe in der Updateverwaltung, `/health` und `/version`.
