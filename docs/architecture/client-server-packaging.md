# Client-Server-Paketarchitektur ab Version 6.0

## Ziel

Eine Codebasis unterstützt kleine All-in-One-Installationen und getrennte produktive Client-Server-Umgebungen.

## Pakete

### `stempeluhr-server`

- FastAPI-Webanwendung
- PostgreSQL-Anbindung und Migrationen
- Mitarbeiter-, Zeit- und Abwesenheitsverwaltung
- Berichte, Backup und Systemverwaltung
- Terminal- und Authentifizierungs-API
- systemd-Dienst `stempeluhr.service`

Installationspfad: `/opt/stempeluhr`

### `stempeluhr-terminal`

- Hardware-Agent
- Terminal-Heartbeat
- Displaysteuerung
- RFID-/NFC-Anlernmodus
- später weitere Hardware-Provider
- systemd-Dienst `stempeluhr-terminal.service`

Installationspfad: `/opt/stempeluhr-terminal`
Konfiguration: `/etc/stempeluhr/terminal.env`

### `stempeluhr-all-in-one`

Metapaket mit exakten Abhängigkeiten auf Server und Terminal derselben Version. Es enthält selbst keine Anwendungsdateien.

## Betriebsmodelle

### All-in-One

Server und Terminal laufen auf demselben Raspberry Pi. Der Terminal-Agent verwendet standardmäßig:

```ini
STEMPELUHR_SERVER=http://127.0.0.1:8000
```

### Getrennter Server

`stempeluhr-server` läuft auf Debian mit PostgreSQL. Es ist kein Leser und kein lokales Display erforderlich.

### Entferntes Terminal

`stempeluhr-terminal` läuft auf Raspberry Pi OS oder Debian. Die Serveradresse wird über `STEMPELUHR_SERVER` konfiguriert.

## Migrationsstrategie

1. Version 6.0 trennt Pakete und Dienste, ohne die bestehende Serveranwendung sofort umzuschreiben.
2. Bestehende Datenbank und Konfiguration unter `/etc/stempeluhr` bleiben erhalten.
3. Der bisherige RFID-Agent wird zum allgemeinen Terminal-Agenten weiterentwickelt.
4. Danach werden Shared-Protokoll, Terminalfähigkeiten und Authentifizierungsprovider schrittweise aus dem Monolithen gelöst.
5. RFID bleibt während der gesamten Migration funktionsfähig.

## Sicherheitsgrundsätze

- Terminals speichern langfristig keine Mitarbeiterstammdaten.
- Hardwareereignisse werden über die Server-API verarbeitet.
- Terminalregistrierung und Zertifikate werden in einer späteren Phase ergänzt.
- Offline-Puffer enthalten nur minimal erforderliche, verschlüsselte Ereignisse.
