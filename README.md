# Stempeluhr Professional 5.6.12

Webbasierte Zeiterfassung für Debian-Server und Raspberry-Pi-Terminals mit PostgreSQL, FastAPI, Rollen und Rechten, Reporting, Onboarding und Raspberry-Kioskfunktionen.

## Aktueller Stand

- Version: **5.6.12**
- Standarddatenbank: PostgreSQL
- Zielplattform: Debian 13 / Raspberry Pi OS
- Standardbranch: `main`

Änderungen dieser Version:

- Datenbankpasswort aus der allgemeinen Konfiguration nach `/etc/stempeluhr/secrets/database.conf` ausgelagert
- bestehende Installationen werden beim Paketupdate automatisch und ohne Passwortänderung migriert
- neue Seite **Systemeinstellungen → Sicherheit → Datenbankzugang**
- Administrator kann das lokale PostgreSQL-Passwort nach erneuter Bestätigung seines Admin-Passworts ändern
- Passwortwechsel verwendet SCRAM-SHA-256, Verbindungstest, Konfigurationssicherung und Rollback
- Datenbankpasswort erscheint weder im Audit-Protokoll noch in Ausgaben
- systemd lädt allgemeine Konfiguration und Datenbank-Secret getrennt
- manueller und GitHub-basierter Updateweg bleiben erhalten
- keine Datenbankmodelle oder produktiven Mitarbeiter-/Buchungsdaten geändert

## Debian-Paket lokal bauen

```bash
bash scripts/build_release.sh
```

Ergebnis:

```text
releases/stempeluhr_5.6.12_all.deb
releases/stempeluhr_5.6.12_all.deb.sha256
releases/stempeluhr_5.6.12_build.log
releases/stempeluhr_5.6.12_BUILD_REPORT.md
```

## Test und Installation

Version 5.6.12 soll zuerst auf einer Debian-13-Test-VM installiert werden. Nach erfolgreichem Test kann der Tag `v5.6.12` das GitHub Release erzeugen.

## Sicherheit

`stempeluhr.env` enthält keine Datenbankpasswörter mehr. `database.conf` gehört `root:stempeluhr` und hat Modus `0640`. Der Webdienst erhält keine allgemeinen Root-Rechte; nur der fest definierte Datenbank-Secret-Helfer darf über einen eng begrenzten sudoers-Eintrag aufgerufen werden.
