# Stempeluhr Professional – zentraler Projektkontext

> Diese Datei ist die verbindliche Wissensbasis für neue ChatGPT-Unterhaltungen. Vor jeder Änderung müssen zusätzlich der aktuelle Quellcode, `version.txt`, `README.md` und `changelog.md` geprüft werden. Bei Abweichungen gilt der tatsächliche Quellcode.

## Projekt

- Name: **Stempeluhr Professional**
- Repository: `Markus4771/Stempeluhr`
- Standardbranch: `main`
- Aktuelle Version: **5.6.12**
- Zielplattform: Debian 13 und Raspberry Pi OS
- Backend: Python, FastAPI, Uvicorn, SQLAlchemy
- Standarddatenbank: PostgreSQL
- Installation: Debian-Paket

## Verbindliche Regeln

PostgreSQL bleibt Standarddatenbank. Bestehende Daten und Konfigurationen dürfen bei Updates nicht gelöscht werden. Secrets gehören niemals ins Repository, in Logs oder Diagnoseberichte. Paketartefakte gelten erst nach tatsächlichem Build und Prüfung als fertig.

Bei jeder neuen Version synchron aktualisieren: `version.txt`, `app/version.py`, `debian/control`, `README.md`, `changelog.md` und `CHATGPT_PROJEKTKONTEXT.md`. Die Dateien `VERSION` und `CHANGELOG.md` dürfen nicht existieren.

## Architektur und Betrieb

- Anwendung: `/opt/stempeluhr`
- allgemeine Konfiguration: `/etc/stempeluhr/stempeluhr.env`
- Datenbank-Secret: `/etc/stempeluhr/secrets/database.conf`
- variable Daten: `/var/lib/stempeluhr`
- geschützte temporäre Übergaben: `/var/lib/stempeluhr/tmp`
- Logs: systemd-Journal und `/var/log/stempeluhr`
- Dienst: `stempeluhr.service`
- Datenbankzugang: **Systemeinstellungen → Sicherheit → Datenbankzugang**
- Updates: **Systemeinstellungen → Wartung → Updates**
- Healthcheck: `/health`
- Versionsauskunft: `/version`

## Version 5.6.12

Schwerpunkt: Datenbankpasswort und Secret-Verwaltung.

Umgesetzt:

- `DATABASE_PASSWORD` wird getrennt in `/etc/stempeluhr/secrets/database.conf` gespeichert
- Paketupdate migriert ein vorhandenes Passwort aus `stempeluhr.env`, ohne die bestehende PostgreSQL-Rolle zu verändern
- SQLAlchemy und systemd laden die Secret-Datei zusätzlich zur allgemeinen Konfiguration
- neue Administratorseite `/system/settings/database-security`
- aktuelles Administratorpasswort ist vor einer Änderung erneut erforderlich
- neues Datenbankpasswort muss mindestens 16 Zeichen sowie Groß-/Kleinbuchstaben und Zahlen enthalten
- Passwortwechsel ist nur für die lokale Standard-PostgreSQL-Instanz zulässig
- privilegierter Helfer liegt unter `/usr/local/sbin/stempeluhr-database-secret-helper`
- Webdienst erhält nur einen eng begrenzten sudoers-Aufruf für geschützte JSON-Dateien unter `/var/lib/stempeluhr/tmp`
- PostgreSQL-Rollenpasswort wird mit `password_encryption=scram-sha-256` gesetzt
- Verbindung mit dem neuen Passwort wird vor Speicherung geprüft
- bisherige Konfiguration und Secret-Datei werden unter `/etc/stempeluhr/backup-secrets` gesichert
- bei einem Fehler wird versucht, das vorherige Rollenpasswort und die vorherige Konfiguration wiederherzustellen
- erfolgreicher Wechsel wird ohne Passwortwerte im Audit-Protokoll vermerkt
- keine Datenbankmodelle oder produktiven Mitarbeiter-/Buchungsdaten geändert

## Sicherheitsregeln

- `stempeluhr.env`: `root:stempeluhr`, Modus `0640`
- Secret-Verzeichnis: `root:stempeluhr`, Modus `0750`
- `database.conf`: `root:stempeluhr`, Modus `0640`
- keine Passwörter in URLs, Logs, Auditdetails, Shell-Historie oder Prozessargumenten
- Rollenpasswörter bei normalen Updates nicht verändern
- Secret-Änderungen müssen Verbindungstest und Rollbackpfad besitzen
- Webprozess darf keine allgemeinen Root-Rechte erhalten

## Debian-Buildsystem

```bash
bash scripts/build_release.sh
```

Erwartete Artefakte:

```text
releases/stempeluhr_5.6.12_all.deb
releases/stempeluhr_5.6.12_all.deb.sha256
releases/stempeluhr_5.6.12_build.log
releases/stempeluhr_5.6.12_BUILD_REPORT.md
```

## Offene Prüfungen vor Freigabe

- Python-Syntax und Imports aller neuen Module prüfen
- Debian-Paket auf einer frischen Debian-13-Test-VM installieren
- Upgrade von 5.6.11 auf 5.6.12 testen
- automatische Secret-Migration kontrollieren
- Dateieigentümer und Modi prüfen
- Datenbankpasswort erfolgreich ändern
- absichtlich fehlerhaften Wechsel und Rollback prüfen
- Dienstneustart und `/health` prüfen
- Mitarbeiter und Buchungen kontrollieren
- erst danach Tag `v5.6.12` und GitHub Release veröffentlichen

## Releasefreigabe

5.6.12 ist erst freigegeben, wenn `.deb`, SHA256, Buildlog und Buildbericht tatsächlich vorhanden sind, Neuinstallation und Upgrade getestet wurden, der Passwortwechsel samt Rollback erfolgreich geprüft wurde und produktive Daten erhalten bleiben.

## Startanweisung für neue Chats

> Arbeite am GitHub-Projekt `Markus4771/Stempeluhr`. Lies zuerst `NEUER_CHAT.md`, anschließend `CHATGPT_PROJEKTKONTEXT.md`, `version.txt`, `README.md` und `changelog.md`. Prüfe danach den tatsächlichen aktuellen Quellcode und bestätige zuerst Version und Ist-Stand. Arbeite ausschließlich auf Basis dieses Repository-Stands weiter. Keine Rekonstruktion, keine erfundenen Dateien und keine behaupteten Releases ohne echten Build.
