# Stempeluhr Professional – zentraler Projektkontext

> Diese Datei ist die verbindliche Wissensbasis für neue ChatGPT-Unterhaltungen. Vor jeder Änderung müssen zusätzlich der aktuelle Quellcode, `version.txt`, `README.md` und `changelog.md` geprüft werden. Bei Abweichungen gilt der tatsächliche Quellcode.

## Projekt

- Name: **Stempeluhr Professional**
- Repository: `Markus4771/Stempeluhr`
- Standardbranch: `main`
- Aktuelle Version: **5.6.10**
- Zielplattform: Debian 13 und Raspberry Pi OS
- Backend: Python, FastAPI, Uvicorn, SQLAlchemy
- Standarddatenbank: PostgreSQL
- Installation: Debian-Paket

## Verbindliche Regeln

PostgreSQL bleibt Standarddatenbank. Bestehende Daten und Konfigurationen dürfen bei Updates nicht gelöscht werden. Secrets gehören niemals ins Repository, in Logs oder Diagnoseberichte. Debian 13, Raspberry Pi OS, Wayland und labwc sind zu berücksichtigen. Paketartefakte gelten erst nach tatsächlichem Build und Prüfung als fertig.

Bei jeder neuen Version synchron aktualisieren:

- `version.txt`
- `app/version.py`
- `debian/control`
- `README.md`
- `changelog.md`
- `CHATGPT_PROJEKTKONTEXT.md`

Die Dateien `VERSION` und `CHANGELOG.md` dürfen nicht existieren.

## Aktueller Funktionsstand

Zum System gehören Mitarbeiterverwaltung, Arbeitszeiterfassung, RFID, Dashboard, Rollen und Rechte, Plausibilitätsprüfung, Korrekturworkflow, DSGVO, REST-API, HTTPS, CalDAV/iCal, Reporting, PDF/CSV-Export, E-Mail-Funktionen, Update/Backup, Raspberry-Kiosk, Agent, Heartbeat, Monitoring, Onboarding, Offboarding, Systemdiagnose, ein mehrstufiger Einrichtungsassistent und ein automatisches GitHub-Release-System.

## Architektur und Betrieb

- Anwendung: `/opt/stempeluhr`
- Konfiguration: `/etc/stempeluhr/stempeluhr.env`
- variable Daten: `/var/lib/stempeluhr`
- Logs: systemd-Journal und `/var/log/stempeluhr`
- Dienst: `stempeluhr.service`
- Standardport: 8000
- Healthcheck: `/health`
- Versionsauskunft: `/version`
- Onboarding und Offboarding: **Systemeinstellungen → Personal & Arbeitszeit**
- Einrichtungsassistent: **Systemeinstellungen → Wartung → Einrichtungsassistent** beziehungsweise `/setup`
- Systemdiagnose: **Systemeinstellungen → Wartung → Systemdiagnose** beziehungsweise `/system/diagnostics`

## Version 5.6.10

Schwerpunkt: fertige Debian-Pakete automatisch über GitHub Releases bereitstellen.

Umgesetzt:

- GitHub Actions baut weiterhin bei relevanten Pushes auf `main`
- ein Tag im Format `vX.Y.Z` löst zusätzlich die Veröffentlichung eines GitHub Releases aus
- Tagname muss exakt `v` plus Inhalt von `version.txt` sein
- Paketname und Paketversion werden vor Veröffentlichung mit `dpkg-deb` geprüft
- Paketinhalt und SHA256 werden kontrolliert
- Release Notes werden aus dem passenden Abschnitt in `changelog.md` erstellt
- veröffentlicht werden `.deb`, `.sha256`, Buildbericht und Changelog
- ein vorhandenes Release desselben Tags wird kontrolliert aktualisiert; Assets werden mit `--clobber` ersetzt
- normale Pushes erzeugen kein dauerhaftes Release
- keine Datenbankmodelle oder produktiven Funktionen geändert

## Release-Ablauf

1. Versionsdateien und Dokumentation synchronisieren.
2. Lokal bauen und testen.
3. Produktives Upgrade und `/health` prüfen.
4. Erst danach den passenden annotierten Tag erstellen und pushen:

```bash
git tag -a v5.6.10 -m "Stempeluhr Professional 5.6.10"
git push origin v5.6.10
```

5. GitHub Actions baut erneut und veröffentlicht die Dateien unter **GitHub → Releases**.

Erwartete Release-Dateien:

```text
stempeluhr_5.6.10_all.deb
stempeluhr_5.6.10_all.deb.sha256
stempeluhr_5.6.10_BUILD_REPORT.md
stempeluhr_5.6.10_changelog.md
```

## Datenbankregeln

- Standarddatenbank und Rolle: `stempeluhr`
- Zugangsdaten ausschließlich aus geschützter Konfiguration
- SQLAlchemy-Verbindungen müssen Sonderzeichen sicher verarbeiten
- lokale Verbindungen dürfen keine Root-Zertifikatsumgebung erben
- Rollenpasswörter bei normalen Updates nicht verändern
- Migrationen wiederholbar und PostgreSQL-kompatibel ausführen
- keine produktiven Daten in Pakete oder Repository aufnehmen

## Debian-Buildsystem

```bash
bash scripts/build_release.sh
```

Erwartete lokale Artefakte:

```text
releases/stempeluhr_5.6.10_all.deb
releases/stempeluhr_5.6.10_all.deb.sha256
releases/stempeluhr_5.6.10_build.log
releases/stempeluhr_5.6.10_BUILD_REPORT.md
```

## Offene Prüfungen

- GitHub-Actions-Build für 5.6.10 erfolgreich abschließen
- 5.6.10 lokal bauen und Paketmetadaten kontrollieren
- Upgrade von produktiver 5.6.00 auf 5.6.10 testen
- `/health`, `/version`, Mitarbeiter und Buchungen prüfen
- erst nach erfolgreicher Prüfung den Tag `v5.6.10` pushen
- GitHub Release und alle vier veröffentlichten Dateien kontrollieren

## Releasefreigabe

Eine Version gilt erst als freigegeben, wenn Versionsdateien und Dokumentation übereinstimmen, `.deb`/SHA256/Buildlog/Buildbericht vorhanden sind, das Upgrade getestet wurde, der Dienst läuft, `/health` die erwartete Version meldet und bestehende Daten erhalten sind. Ein GitHub Release darf erst danach durch den Versions-Tag ausgelöst werden.

## Startanweisung für neue Chats

> Arbeite am GitHub-Projekt `Markus4771/Stempeluhr`. Lies zuerst `NEUER_CHAT.md`, anschließend `CHATGPT_PROJEKTKONTEXT.md`, `version.txt`, `README.md` und `changelog.md`. Prüfe danach den tatsächlichen aktuellen Quellcode und bestätige zuerst Version und Ist-Stand. Arbeite ausschließlich auf Basis dieses Repository-Stands weiter. Keine Rekonstruktion, keine erfundenen Dateien und keine behaupteten Releases ohne echten Build.
