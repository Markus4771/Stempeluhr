# Stempeluhr Professional 5.5.06

Schwerpunkt: robuste Neuinstallation auf Debian.

## Änderungen

- PostgreSQL-Benutzer `stempeluhr` wird bei Installation automatisch vorbereitet.
- Das Datenbankpasswort wird bei Neuinstallation sicher erzeugt.
- Bestehende `/etc/stempeluhr/stempeluhr.env` wird respektiert; das PostgreSQL-Passwort wird passend dazu gesetzt.
- Datenbank `stempeluhr` wird automatisch angelegt, falls sie fehlt.
- Rechte auf Datenbank und Schema `public` werden automatisch gesetzt.
- `.env` wird automatisch angelegt oder repariert.
- Datenbankverbindung wird vor dem Start geprüft.
- `init_db()` und Migrationen laufen erst nach erfolgreicher Datenbankvorbereitung.

## Installation

```bash
sudo apt install ./stempeluhr_5.5.06_all.deb
sudo systemctl status stempeluhr --no-pager
```

## Diagnose

```bash
cat /etc/stempeluhr/stempeluhr.env
journalctl -u stempeluhr -n 100 --no-pager
cat /opt/stempeluhr/logs/package-postinst.log
```
