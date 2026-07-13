# Stempeluhr Professional 5.6.17

Webbasierte Zeiterfassung für Debian-Server und Raspberry-Pi-Terminals mit PostgreSQL, FastAPI, Rollen und Rechten, Reporting, Sicherheitsrichtlinien, Zusatz-Programmen und integriertem Hilfesystem.

## Aktueller Stand

- Version: **5.6.17**
- Standarddatenbank: PostgreSQL
- Zielplattform: Debian 13 / Raspberry Pi OS
- Standardbranch: `main`

## Änderungen in 5.6.17

- Menüpunkt **Zeiterfassung** aus der normalen Hauptnavigation entfernt
- Kiosk-Seite `/raspberry` bleibt unverändert erreichbar
- Raspberry-Kiosk kann die Zeiterfassung weiterhin direkt und automatisch öffnen
- keine Änderung an Buchungslogik, RFID-Funktion oder produktiven Daten

## Bereits enthalten aus 5.6.16

- Hauptnavigation im Bereich **Abwesenheiten** zusammengefasst
- doppelten Menüpunkt **Meine Abwesenheiten** aus der Hauptnavigation entfernt
- Abwesenheitsübersicht um rollenabhängige Kacheln ergänzt
- **Abwesenheitsarten** für Administratoren direkt aus der Übersicht erreichbar
- Einstellung **Genehmigung nötig** bei Abwesenheitsarten wird beim Anlegen berücksichtigt
- genehmigungsfreie Arten wie **Krank** werden direkt mit Status `genehmigt` gespeichert
- genehmigungsfreie Anträge erscheinen nicht mehr in der offenen Genehmigungsliste
- fehlerhafte Formularzuordnung bei der Bearbeitung von Abwesenheitsarten korrigiert
- `install.sh` für Installation, Update, Backup, Status, Logs und Diagnose ergänzt

## Automatische Installation und Wartung

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
releases/stempeluhr_5.6.17_all.deb
releases/stempeluhr_5.6.17_all.deb.sha256
releases/stempeluhr_5.6.17_build.log
releases/stempeluhr_5.6.17_BUILD_REPORT.md
```

## Test und Installation

Version 5.6.17 zuerst auf der Debian-13-Test-VM installieren. Zu testen sind die normale Hauptnavigation ohne Zeiterfassung, der direkte Kiosk-Aufruf `/raspberry`, Abwesenheitsarten mit und ohne Genehmigung, `/health` und `/version`.
