# Stempeluhr Professional 5.6.15

Webbasierte Zeiterfassung für Debian-Server und Raspberry-Pi-Terminals mit PostgreSQL, FastAPI, Rollen und Rechten, Reporting, Sicherheitsrichtlinien, Zusatz-Programmen und integriertem Hilfesystem.

## Aktueller Stand

- Version: **5.6.15**
- Standarddatenbank: PostgreSQL
- Zielplattform: Debian 13 / Raspberry Pi OS
- Standardbranch: `main`

## Änderungen in 5.6.15

- neuer Hauptmenüpunkt **Hilfe & Dokumentation**
- integriertes Administratorhandbuch
- integriertes Benutzerhandbuch
- integriertes Installations- und Einrichterhandbuch
- integriertes API-Handbuch
- gemeinsame Volltextsuche über alle Handbücher
- HTML-Leseansicht und Druckansicht
- PDF-Erzeugung und Download direkt aus der Weboberfläche
- Markdown-Quellen unter `docs/manuals/`
- PDF-Erzeugung mit der bereits vorhandenen ReportLab-Abhängigkeit
- Hilferouten nur für angemeldete Benutzer zugänglich
- keine produktiven Mitarbeiter-, Buchungs- oder Datenbankdaten verändert

## Bereits enthalten aus 5.6.14

- Rollen- und Berechtigungsverwaltung
- gruppierte Systemeinstellungs-Untermenüs
- konfigurierbare Zusatz-Programme über HTTP/HTTPS, IP oder Hostname und Port
- rollenabhängige Navigation

## Debian-Paket lokal bauen

```bash
bash scripts/build_release.sh
```

Erwartete Ergebnisse:

```text
releases/stempeluhr_5.6.15_all.deb
releases/stempeluhr_5.6.15_all.deb.sha256
releases/stempeluhr_5.6.15_build.log
releases/stempeluhr_5.6.15_BUILD_REPORT.md
```

## Test und Installation

Version 5.6.15 zuerst auf der Debian-13-Test-VM installieren. Zu testen sind `/help`, alle vier Handbücher, Suche, Druckansicht, PDF-Downloads, Rollen, Zusatz-Programme sowie `/health` und `/version`.
