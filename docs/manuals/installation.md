# Installations- und Einrichterhandbuch

Version 5.6.15 – Stempeluhr Professional

## Voraussetzungen

Empfohlen wird Debian 13 oder Raspberry Pi OS mit Netzwerkzugang, fester IP-Adresse beziehungsweise zuverlässiger DNS-Auflösung, aktueller Systemzeit und ausreichend freiem Speicher. PostgreSQL ist die Standarddatenbank.

## Vorbereitung

```bash
sudo apt update
sudo apt install -y git curl postgresql postgresql-contrib
```

Für produktive Installationen zusätzlich regelmäßige Backups, HTTPS und eine Firewall einplanen.

## Installation über Debian-Paket

```bash
sudo apt install ./stempeluhr_5.6.15_all.deb
sudo systemctl enable --now stempeluhr.service
```

Danach prüfen:

```bash
systemctl status stempeluhr.service --no-pager -l
curl -sS http://127.0.0.1:8000/health
curl -sS http://127.0.0.1:8000/version
```

## Wichtige Pfade

- Anwendung: `/opt/stempeluhr`
- Konfiguration: `/etc/stempeluhr/stempeluhr.env`
- Datenbank-Secret: `/etc/stempeluhr/secrets/database.conf`
- variable Daten: `/var/lib/stempeluhr`
- Logs: systemd-Journal und `/var/log/stempeluhr`

## Ersteinrichtung

1. Weboberfläche öffnen.
2. Einrichtungsassistent starten.
3. Firmendaten und Zeitzone festlegen.
4. PostgreSQL-Verbindung prüfen.
5. Administratorkennwort ändern.
6. Sicherheitsrichtlinien konfigurieren.
7. E-Mail, Backup und Terminals einrichten.
8. Testmitarbeiter und Testbuchung anlegen.
9. Systemdiagnose ausführen.

## PostgreSQL

Die Anwendung verwendet eine eigene Datenbankrolle. Das Datenbankpasswort wird geschützt in der Secret-Datei gespeichert. Rechte der Secret-Dateien nicht lockern und keine Kennwörter in Befehlsprotokolle oder GitHub übernehmen.

## HTTPS und Netzwerk

Für produktiven Zugriff HTTPS verwenden. Reverse Proxy und Zertifikate so konfigurieren, dass die Anwendung intern weiterhin zuverlässig erreichbar bleibt. Nach Änderungen Login, Weiterleitungen, API und Terminals testen.

## Upgrade

```bash
sudo apt install --reinstall ./stempeluhr_NEUE_VERSION_all.deb
sudo systemctl restart stempeluhr.service
```

Vor jedem Upgrade ein Backup und möglichst einen VM-Snapshot erstellen. Nach dem Upgrade Version, Healthcheck, Mitarbeiter und Buchungen prüfen.

## Neuinstallation und Wiederherstellung

Bei einem neuen System zuerst das Debian-Paket installieren und anschließend das geprüfte Backup wiederherstellen. Datenbank, Konfiguration und Secret-Dateien müssen zusammenpassen. Restore zunächst auf einer Test-VM durchführen.

## Fehlerbehebung

```bash
sudo journalctl -u stempeluhr.service -n 150 --no-pager
sudo systemctl daemon-reload
sudo systemctl restart stempeluhr.service
```

Bei einem Paketfehler zusätzlich ausführen:

```bash
sudo dpkg --configure -a
sudo apt -f install
```

## Abnahmecheck

- Dienst ist aktiv.
- `/health` meldet `status: ok`.
- `/version` zeigt die installierte Version.
- Login funktioniert.
- Mitarbeiter und Buchungen sind vorhanden.
- Backup wird erstellt.
- Systemdiagnose zeigt keine kritischen Fehler.
