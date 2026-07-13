# Stempeluhr Professional – zentraler Projektkontext

> Verbindliche Wissensbasis für neue ChatGPT-Unterhaltungen. Zusätzlich immer aktuellen Quellcode, `version.txt`, `README.md` und `changelog.md` prüfen. Bei Abweichungen gilt der tatsächliche Quellcode.

## Projekt

- Repository: `Markus4771/Stempeluhr`
- Standardbranch: `main`
- Aktuelle Entwicklungs- und Testversion: **5.6.22**
- Zielplattform: Debian 13 und Raspberry Pi OS
- Backend: Python, FastAPI, Uvicorn, SQLAlchemy
- Standarddatenbank: PostgreSQL
- Installation und Update: Debian-Paket über `install.sh` oder Web-Updater

## Verbindliche Regeln

Bestehende Daten und Konfigurationen dürfen bei Updates nicht gelöscht werden. PostgreSQL bleibt Standarddatenbank. Secrets gehören niemals in Repository, Logs, URLs oder Diagnoseberichte. `.deb`, Prüfsumme und Release dürfen erst nach tatsächlichem Build und Test als fertig bezeichnet werden.

Bei jeder neuen Version synchron aktualisieren: `version.txt`, `app/version.py`, `debian/control`, `README.md`, `changelog.md`, `CHATGPT_PROJEKTKONTEXT.md` und bei Bedarf `NEUER_CHAT.md`.

## Wichtige Pfade und Funktionen

- Anwendung: `/opt/stempeluhr`
- Konfiguration: `/etc/stempeluhr/stempeluhr.env`
- Datenbank-Secret: `/etc/stempeluhr/secrets/database.conf`
- GitHub-Token: `/etc/stempeluhr/secrets/github_token`
- GitHub-main-Runner: `/usr/local/sbin/stempeluhr-github-main-update`
- variable Daten: `/var/lib/stempeluhr`
- Backups: `/var/backups/stempeluhr`
- Dienst: `stempeluhr.service`
- Healthcheck: `/health`
- Versionsauskunft: `/version`
- Kiosk-Zeiterfassung: `/raspberry`
- Persönlicher Report: `/reports`
- Plausibilitätsprüfung: `/plausibility`
- Überstundenverwaltung: `/overtime-adjustments`
- Updateverwaltung: `/system/settings/updates`
- öffentliche Datenschutzerklärung: `/datenschutz`

## Version 5.6.22

Umgesetzt:

- Updateverwaltung prüft weiterhin bevorzugt veröffentlichte GitHub-Releases
- wenn kein Release vorhanden ist, kann ein Administrator den Branch `main` als Updatequelle verwenden
- privater GitHub-Quellcode wird mit dem lokal gespeicherten Lesetoken geladen
- Quellcode wird in einem temporären Verzeichnis entpackt
- `scripts/build_release.sh` baut daraus lokal das Debian-Paket
- das Paket wird an den bestehenden Web-Update-Runner übergeben
- Backup, Paketinstallation, Dienstneustart und Healthcheck erfolgen über den bestehenden Updateablauf
- main-Update ist nur für Administratoren freigeschaltet
- sudoers erlaubt ausschließlich den dedizierten main-Update-Runner
- Token-Popup verwendet ein Passwortfeld und speichert den Token nicht im Repository

## Bereits enthalten

- Kommen-/Gehen-Uhrzeiten direkt in der Tagesübersicht von `Mein Report`
- normale Mitarbeiter sehen ausschließlich eigene Zeiten
- Teamleiter sehen nur zugeordnete Mitarbeiter
- Plausibilitätsmeldungen zurücksetzen
- Überstundenänderungen mit Mitarbeitergenehmigung per E-Mail

## Offene Prüfungen vor Freigabe 5.6.22

- Python-Syntax und Imports prüfen
- Shell-Syntax des main-Update-Runners prüfen
- Debian-Paket bauen und SHA256 validieren
- Upgrade auf Testsystem installieren
- Token-Popup und Dateirechte prüfen
- main-Download aus privatem Repository prüfen
- Paketbau im temporären Verzeichnis prüfen
- Übergabe an bestehenden Update-Runner prüfen
- Backup, Installation, Dienstneustart und Healthcheck prüfen
- Kommen-/Gehen-Zeiten und Rollenrechte prüfen
- `/health` und `/version` prüfen

## Build

```bash
bash scripts/build_release.sh
sha256sum -c releases/stempeluhr_5.6.22_all.deb.sha256
```

## Startanweisung für neue Chats

> Arbeite am GitHub-Projekt `Markus4771/Stempeluhr`. Lies zuerst `NEUER_CHAT.md`, danach `CHATGPT_PROJEKTKONTEXT.md`, `version.txt`, `README.md` und `changelog.md`. Prüfe anschließend den tatsächlichen Quellcode. Bestätige zuerst Version und Ist-Stand. Keine Rekonstruktion, keine erfundenen Dateien und keine behaupteten Builds oder Releases.
