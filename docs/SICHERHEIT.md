# Sicherheitskonzept – Stempeluhr Professional

## Grundsätze

- PostgreSQL bleibt Standarddatenbank.
- Der Webprozess läuft als Benutzer `stempeluhr` ohne allgemeine Root-Rechte.
- Geheimnisse werden nicht im Repository, in Logs, Auditdetails oder Diagnoseberichten gespeichert.
- Kritische Änderungen benötigen erneute Administrator-Authentifizierung.

## Konfigurationsdateien

| Pfad | Inhalt | Eigentümer | Modus |
|---|---|---|---|
| `/etc/stempeluhr/stempeluhr.env` | allgemeine Konfiguration | `root:stempeluhr` | `0640` |
| `/etc/stempeluhr/secrets/` | Secret-Verzeichnis | `root:stempeluhr` | `0750` |
| `/etc/stempeluhr/secrets/database.conf` | ausschließlich `DATABASE_PASSWORD` | `root:stempeluhr` | `0640` |
| `/etc/stempeluhr/backup-secrets/` | lokale Rückfallsicherung | `root:root` | `0700` |

## Passwortänderung

1. Administrator öffnet **Systemeinstellungen → Sicherheit → Datenbankzugang**.
2. Das persönliche Administratorpasswort wird erneut geprüft.
3. Ein geschützter JSON-Auftrag wird unter `/var/lib/stempeluhr/tmp` erzeugt.
4. Nur `/usr/local/sbin/stempeluhr-database-secret-helper` darf diesen Auftrag über sudo verarbeiten.
5. Der Helfer sichert bisherige Konfigurationsdateien.
6. PostgreSQL erhält das neue Rollenpasswort mit `password_encryption=scram-sha-256`.
7. Eine echte Anmeldung mit dem neuen Passwort wird getestet.
8. Erst danach wird `database.conf` atomar ersetzt und `DATABASE_PASSWORD` aus `stempeluhr.env` entfernt.
9. Der Dienst wird zeitversetzt neu gestartet.
10. Bei Fehlern wird versucht, Rollenpasswort und Konfigurationsdateien zurückzusetzen.

Passwörter werden nicht als Kommandozeilenargument an PostgreSQL übergeben. Das temporäre SQL-Skript ist nur für den Benutzer `postgres` lesbar und wird unmittelbar gelöscht.

## Update-Migration

Beim Upgrade auf 5.6.12 wird ein vorhandenes `DATABASE_PASSWORD` aus `stempeluhr.env` nach `database.conf` verschoben. Die bestehende PostgreSQL-Rolle wird bei dieser Migration nicht verändert. Dadurch bleiben bestehende Installationen kompatibel.

## Grenzen von 5.6.12

- Passwortänderungen werden nur für eine lokale PostgreSQL-Instanz auf `127.0.0.1` oder `localhost` angeboten.
- SMTP-, API- und Lizenz-Secrets sind noch nicht in eigene Dateien migriert.
- Neuinstallation erzeugt zunächst ein zufälliges Übergangspasswort; der Administrator ersetzt es im Einrichtungsassistenten über die Datenbankzugangsseite.
- Ein vollständiger Test auf Debian 13 ist vor Freigabe zwingend.
