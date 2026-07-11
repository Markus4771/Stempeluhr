# Stempeluhr Professional – zentraler Projektkontext

> Diese Datei ist die verbindliche Wissensbasis für neue ChatGPT-Unterhaltungen. Vor jeder Änderung müssen zusätzlich der aktuelle Quellcode, `version.txt`, `README.md` und `changelog.md` geprüft werden. Bei Abweichungen gilt der tatsächliche Quellcode.

## Projekt

- Name: **Stempeluhr Professional**
- Repository: `Markus4771/Stempeluhr`
- Standardbranch: `main`
- Aktuelle Version: **5.6.11**
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

Zum System gehören Mitarbeiterverwaltung, Arbeitszeiterfassung, RFID, Dashboard, Rollen und Rechte, Plausibilitätsprüfung, Korrekturworkflow, DSGVO, REST-API, HTTPS, CalDAV/iCal, Reporting, PDF/CSV-Export, E-Mail-Funktionen, Backup, Raspberry-Kiosk, Agent, Heartbeat, Monitoring, Onboarding, Offboarding, Systemdiagnose, mehrstufiger Einrichtungsassistent, automatisches GitHub-Release-System und eine integrierte Updateverwaltung mit manueller sowie GitHub-basierter Paketquelle.

## Architektur und Betrieb

- Anwendung: `/opt/stempeluhr`
- Konfiguration: `/etc/stempeluhr/stempeluhr.env`
- variable Daten: `/var/lib/stempeluhr`
- Logs: systemd-Journal und `/var/log/stempeluhr`
- Dienst: `stempeluhr.service`
- Standardport: 8000
- Healthcheck: `/health`
- Versionsauskunft: `/version`
- Updates: **Systemeinstellungen → Wartung → Updates**
- Einrichtungsassistent: **Systemeinstellungen → Wartung → Einrichtungsassistent** beziehungsweise `/setup`
- Systemdiagnose: **Systemeinstellungen → Wartung → Systemdiagnose** beziehungsweise `/system/diagnostics`

## Version 5.6.11

Schwerpunkt: GitHub Releases mit der bestehenden Updatefunktion verbinden.

Umgesetzt:

- vorhandene Update-Seite um GitHub-Release-Prüfung erweitert
- neueste stabile Version und Release Notes werden auf derselben Seite angezeigt
- GitHub-Release muss ein passendes `.deb` und die zugehörige `.sha256` enthalten
- beide Dateien werden heruntergeladen und die SHA256 wird vor Übergabe geprüft
- nur eine tatsächlich neuere Version wird zur Installation angeboten
- das GitHub-Paket wird anschließend an die vorhandene Upload-/Paketprüfung und denselben privilegierten Update-Runner übergeben
- manueller DEB-Upload bleibt vollständig erhalten
- Backup, Installation, Neustart, Statusdatei, Fortschrittsanzeige, Protokoll und Healthcheck bleiben zentral im bestehenden Ablauf
- Repository kann über `STEMPELUHR_GITHUB_REPOSITORY` abweichend konfiguriert werden; Standard ist `Markus4771/Stempeluhr`
- keine Datenbankmodelle geändert; keine Schema-Migration erforderlich

## Release- und Updateablauf

1. Versionsdateien und Dokumentation synchronisieren.
2. Lokal bauen und testen.
3. Produktives Upgrade und `/health` prüfen.
4. Passenden Tag erstellen und pushen, zum Beispiel:

```bash
git tag -a v5.6.11 -m "Stempeluhr Professional 5.6.11"
git push origin v5.6.11
```

5. GitHub Actions veröffentlicht `.deb`, SHA256, Buildbericht und Changelog.
6. Eine ältere installierte Stempeluhr kann danach unter **Updates** das Release prüfen und über denselben vorhandenen Update-Runner installieren.

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
releases/stempeluhr_5.6.11_all.deb
releases/stempeluhr_5.6.11_all.deb.sha256
releases/stempeluhr_5.6.11_build.log
releases/stempeluhr_5.6.11_BUILD_REPORT.md
```

## Offene Prüfungen

- Python-Syntax und Import der neuen GitHub-Update-Module prüfen
- GitHub-Actions-Build für 5.6.11 erfolgreich abschließen
- Upgrade von produktiver 5.6.10 auf 5.6.11 testen
- manuelle Updatequelle weiterhin testen
- GitHub-Prüfung gegen ein echtes Release testen
- `.deb`-/SHA256-Download und Übergabe an den bestehenden Runner testen
- `/health`, `/version`, Mitarbeiter und Buchungen prüfen
- erst danach den Tag `v5.6.11` veröffentlichen

## Releasefreigabe

Eine Version gilt erst als freigegeben, wenn Versionsdateien und Dokumentation übereinstimmen, `.deb`/SHA256/Buildlog/Buildbericht vorhanden sind, das Upgrade getestet wurde, der Dienst läuft, `/health` die erwartete Version meldet und bestehende Daten erhalten sind. Das integrierte GitHub-Update gilt erst nach einem erfolgreichen Test mit einem echten veröffentlichten Release als produktiv bestätigt.

## Startanweisung für neue Chats

> Arbeite am GitHub-Projekt `Markus4771/Stempeluhr`. Lies zuerst `NEUER_CHAT.md`, anschließend `CHATGPT_PROJEKTKONTEXT.md`, `version.txt`, `README.md` und `changelog.md`. Prüfe danach den tatsächlichen aktuellen Quellcode und bestätige zuerst Version und Ist-Stand. Arbeite ausschließlich auf Basis dieses Repository-Stands weiter. Keine Rekonstruktion, keine erfundenen Dateien und keine behaupteten Releases ohne echten Build.
