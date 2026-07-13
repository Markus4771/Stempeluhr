# Stempeluhr Professional 5.6.16

Webbasierte Zeiterfassung für Debian-Server und Raspberry-Pi-Terminals mit PostgreSQL, FastAPI, Rollen und Rechten, Reporting, Sicherheitsrichtlinien, Zusatz-Programmen und integriertem Hilfesystem.

## Aktueller Stand

- Version: **5.6.16**
- Standarddatenbank: PostgreSQL
- Zielplattform: Debian 13 / Raspberry Pi OS
- Standardbranch: `main`

## Änderungen in 5.6.16

- Hauptnavigation im Bereich **Abwesenheiten** zusammengefasst
- doppelten Menüpunkt **Meine Abwesenheiten** aus der Hauptnavigation entfernt
- Abwesenheitsübersicht um rollenabhängige Kacheln ergänzt
- **Abwesenheitsarten** für Administratoren direkt aus der Übersicht erreichbar
- Einstellung **Genehmigung nötig** bei Abwesenheitsarten wird beim Anlegen berücksichtigt
- genehmigungsfreie Arten wie **Krank** werden direkt mit Status `genehmigt` gespeichert
- genehmigungsfreie Anträge erscheinen nicht mehr in der offenen Genehmigungsliste
- fehlerhafte Formularzuordnung bei der Bearbeitung von Abwesenheitsarten korrigiert
- neues `install.sh` für Installation, Update, Backup, Status, Logs und Diagnose ergänzt

## Bereits enthalten aus 5.6.15

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

## Automatische Installation und Wartung

Das Skript `install.sh` übernimmt Repository-Aktualisierung, Paketbau, Datensicherung, Installation und Systemprüfung.

Auf einem bestehenden Produktivsystem:

```bash
cd ~/Stempeluhr
git restore install.sh
git pull --ff-only origin main
sudo bash install.sh update
```

Bei einer Erstinstallation:

```bash
sudo bash install.sh install
```

Wichtige Befehle:

```text
sudo bash install.sh install              Erstinstallation
sudo bash install.sh update               Backup, Aktualisierung, Paketbau und Installation
sudo bash install.sh build                nur Debian-Paket bauen
sudo bash install.sh backup               PostgreSQL und Konfiguration sichern
sudo bash install.sh restore DATEI        Backup wiederherstellen
sudo bash install.sh status               Dienst, Version und Health anzeigen
sudo bash install.sh logs                 letzte Dienstprotokolle anzeigen
sudo bash install.sh version              installierte und vorhandene Versionen anzeigen
sudo bash install.sh doctor               vollständige Systemdiagnose
sudo bash install.sh restart              Dienst neu starten
sudo bash install.sh uninstall            Paket entfernen, Daten behalten
sudo bash install.sh uninstall --purge    Backup erstellen und vollständig entfernen
```

Standardmäßig werden Backups unter `/var/backups/stempeluhr` gespeichert.

## Debian-Paket manuell bauen

```bash
bash scripts/build_release.sh
```

Erwartete Ergebnisse:

```text
releases/stempeluhr_5.6.16_all.deb
releases/stempeluhr_5.6.16_all.deb.sha256
releases/stempeluhr_5.6.16_build.log
releases/stempeluhr_5.6.16_BUILD_REPORT.md
```

## Test und Installation

Version 5.6.16 zuerst auf der Debian-13-Test-VM installieren. Zu testen sind Abwesenheitsarten mit und ohne Genehmigung, die zusammengefasste Abwesenheitsnavigation, `/help`, alle vier Handbücher, Suche, Druckansicht, PDF-Downloads, Rollen, Zusatz-Programme sowie `/health` und `/version`.
