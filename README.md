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

## Automatische Installation und Wartung

Das Skript `install.sh` übernimmt Repository-Aktualisierung, Paketbau, Datensicherung, Installation und Systemprüfung.

Auf einem bestehenden Produktivsystem:

```bash
cd ~/Stempeluhr
git pull origin main
chmod +x install.sh
sudo ./install.sh update
```

Bei einer Erstinstallation:

```bash
sudo ./install.sh install
```

Wichtige Befehle:

```text
sudo ./install.sh install              Erstinstallation
sudo ./install.sh update               Backup, Aktualisierung, Paketbau und Installation
sudo ./install.sh build                nur Debian-Paket bauen
sudo ./install.sh backup               PostgreSQL und Konfiguration sichern
sudo ./install.sh restore DATEI        Backup wiederherstellen
sudo ./install.sh status               Dienst, Version und Health anzeigen
sudo ./install.sh logs                 letzte Dienstprotokolle anzeigen
sudo ./install.sh version              installierte und vorhandene Versionen anzeigen
sudo ./install.sh doctor               vollständige Systemdiagnose
sudo ./install.sh restart              Dienst neu starten
sudo ./install.sh uninstall            Paket entfernen, Daten behalten
sudo ./install.sh uninstall --purge    Backup erstellen und vollständig entfernen
```

Standardmäßig werden Backups unter `/var/backups/stempeluhr` gespeichert.

## Debian-Paket manuell bauen

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
