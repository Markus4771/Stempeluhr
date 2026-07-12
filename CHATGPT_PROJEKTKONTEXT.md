# Stempeluhr Professional – zentraler Projektkontext

> Diese Datei ist die verbindliche Wissensbasis für neue ChatGPT-Unterhaltungen. Vor jeder Änderung müssen zusätzlich der aktuelle Quellcode, `version.txt`, `README.md` und `changelog.md` geprüft werden. Bei Abweichungen gilt der tatsächliche Quellcode.

## Projekt

- Name: **Stempeluhr Professional**
- Repository: `Markus4771/Stempeluhr`
- Standardbranch: `main`
- Aktuelle Version: **5.6.13**
- Zielplattform: Debian 13 und Raspberry Pi OS
- Backend: Python, FastAPI, Uvicorn, SQLAlchemy
- Standarddatenbank: PostgreSQL
- Installation: Debian-Paket

## Verbindliche Regeln

PostgreSQL bleibt Standarddatenbank. Bestehende Daten und Konfigurationen dürfen bei Updates nicht gelöscht werden. Secrets und Passwörter gehören niemals ins Repository, in Logs oder Diagnoseberichte. Paketartefakte gelten erst nach tatsächlichem Build und Prüfung als fertig.

Bei jeder neuen Version synchron aktualisieren: `version.txt`, `app/version.py`, `debian/control`, `README.md`, `changelog.md` und `CHATGPT_PROJEKTKONTEXT.md`. Die Dateien `VERSION` und `CHANGELOG.md` dürfen nicht existieren.

## Architektur und Betrieb

- Anwendung: `/opt/stempeluhr`
- allgemeine Konfiguration: `/etc/stempeluhr/stempeluhr.env`
- Datenbank-Secret: `/etc/stempeluhr/secrets/database.conf`
- variable Daten: `/var/lib/stempeluhr`
- Logs: systemd-Journal und `/var/log/stempeluhr`
- Dienst: `stempeluhr.service`
- Sicherheitsrichtlinien: **Systemeinstellungen → Allgemeine Einstellungen → Sicherheit**
- Datenbankzugang: **Systemeinstellungen → Sicherheit → Datenbankzugang**
- Updates: **Systemeinstellungen → Wartung → Updates**
- Healthcheck: `/health`
- Versionsauskunft: `/version`

## Version 5.6.13

Schwerpunkt: konfigurierbare Anmelde- und Passwortrichtlinien.

Umgesetzt:

- Brute-Force-Schutz kann aktiviert oder deaktiviert werden
- Fehlversuche bis zur Sperre sind von 1 bis 20 konfigurierbar
- Sperrdauer für Benutzerkonto und IP-Adresse ist von 1 bis 1440 Minuten konfigurierbar
- IP-Sperre kann unabhängig aktiviert oder deaktiviert werden
- Sperrstände werden als interne Settings in PostgreSQL gespeichert und durch vorhandene Backups erfasst
- fehlgeschlagene und blockierte Anmeldungen werden ohne Passwortwerte im Audit protokolliert
- Passwort-Mindestlänge ist von 8 bis 64 Zeichen konfigurierbar
- Großbuchstaben, Kleinbuchstaben, Zahlen, Sonderzeichen, Leerzeichen und Identitätsbestandteile sind einzeln konfigurierbar
- Regeln gelten beim Onboarding, beim Passwort-Reset und beim Ändern des festen Admin-Passworts
- bestehende Passwörter werden nicht rückwirkend ungültig
- der feste Benutzer `admin` wird bei Neuinstallationen weiterhin einmalig mit `admin123` angelegt
- solange der Hash noch `admin123` entspricht, zeigt jede angemeldete Seite eine dauerhafte Warnung
- nach der ersten Änderung gelten sämtliche Richtlinien; `admin123` darf nicht erneut gesetzt werden
- die Erkennung des Standardpassworts erfolgt ausschließlich über Hash-Prüfung, ohne zusätzliches Klartextmerkmal

## Sicherheitsregeln

- niemals Passwörter in Logs, Auditdetails, URLs oder Prozessargumenten speichern
- Login-Fehlermeldungen dürfen keine Benutzerexistenz offenlegen
- erfolgreiche Anmeldung löscht den zugehörigen Fehlversuchsstatus
- bestehende Konten dürfen durch neue Richtlinien nicht ohne Passwortänderung ausgesperrt werden
- das Standardpasswort des festen Admins ist nur eine einmalige Einrichtungsausnahme
- Passwortänderungen müssen die zentralen Richtlinien verwenden
- Webprozess darf keine allgemeinen Root-Rechte erhalten

## Debian-Buildsystem

```bash
bash scripts/build_release.sh
```

Erwartete Artefakte:

```text
releases/stempeluhr_5.6.13_all.deb
releases/stempeluhr_5.6.13_all.deb.sha256
releases/stempeluhr_5.6.13_build.log
releases/stempeluhr_5.6.13_BUILD_REPORT.md
```

## Offene Prüfungen vor Freigabe

- Python-Syntax und Imports der neuen Module prüfen
- Upgrade von 5.6.12 auf 5.6.13 auf der Proxmox-Test-VM durchführen
- korrekten Login mit bestehendem Passwort prüfen
- Sperre nach konfigurierter Anzahl falscher Anmeldungen prüfen
- automatische Entsperrung nach Ablauf prüfen
- IP-Sperre getrennt prüfen
- deaktivierten Brute-Force-Schutz prüfen
- Standardpasswort-Warnung für `admin` prüfen
- Admin-Passwort nach konfigurierter Richtlinie ändern und Verschwinden der Warnung prüfen
- erneutes Setzen von `admin123` muss abgelehnt werden
- Passwort-Reset und Onboarding gegen die Richtlinien testen
- `/health`, `/version`, Mitarbeiter und Buchungen prüfen
- erst danach Tag `v5.6.13` und GitHub Release veröffentlichen

## Releasefreigabe

5.6.13 ist erst freigegeben, wenn `.deb`, SHA256, Buildlog und Buildbericht tatsächlich vorhanden sind und Login-Sperre, Entsperrung, Passwortregeln, Admin-Ausnahme, Warnung, Onboarding und Passwort-Reset auf der Test-VM erfolgreich geprüft wurden.

## Startanweisung für neue Chats

> Arbeite am GitHub-Projekt `Markus4771/Stempeluhr`. Lies zuerst `NEUER_CHAT.md`, anschließend `CHATGPT_PROJEKTKONTEXT.md`, `version.txt`, `README.md` und `changelog.md`. Prüfe danach den tatsächlichen aktuellen Quellcode und bestätige zuerst Version und Ist-Stand. Arbeite ausschließlich auf Basis dieses Repository-Stands weiter. Keine Rekonstruktion, keine erfundenen Dateien und keine behaupteten Releases ohne echten Build.
