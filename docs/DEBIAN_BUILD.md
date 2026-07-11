# Debian-Paket bauen – Stempeluhr Professional

Diese Anleitung gilt ausschließlich für das Repository `Markus4771/Stempeluhr`.

## Voraussetzungen

Auf Debian 13 beziehungsweise Raspberry Pi OS:

```bash
sudo apt update
sudo apt install -y git rsync dpkg-dev python3
```

## Repository aktualisieren

Git-Befehle im Repository als Benutzer `pi` ausführen:

```bash
cd /home/pi/Stempeluhr
git fetch origin --prune
git pull --ff-only origin main
```

## Paket lokal bauen

Das Skript wird direkt über Bash gestartet. Dadurch werden keine Dateirechte im Git-Arbeitsverzeichnis verändert:

```bash
cd /home/pi/Stempeluhr
bash scripts/build_release.sh
```

Das Skript prüft vor dem Build:

- sauberen Git-Stand
- übereinstimmende Version in `version.txt`, `app/version.py` und `debian/control`
- Versionsangaben in README, Changelog und Projektkontext
- Python-Syntax
- Ausschluss von `.env`- und Datenbankdateien
- Paketinhalt und Paketmetadaten

## Ergebnis

Für Version 5.6.10 entstehen:

```text
releases/stempeluhr_5.6.10_all.deb
releases/stempeluhr_5.6.10_all.deb.sha256
releases/stempeluhr_5.6.10_build.log
releases/stempeluhr_5.6.10_BUILD_REPORT.md
```

## Paket prüfen

```bash
dpkg-deb --info releases/stempeluhr_5.6.10_all.deb
dpkg-deb --contents releases/stempeluhr_5.6.10_all.deb
sha256sum -c releases/stempeluhr_5.6.10_all.deb.sha256
```

## Upgrade installieren

Vor einem produktiven Upgrade zuerst PostgreSQL sichern:

```bash
sudo -u postgres pg_dump stempeluhr > /root/stempeluhr-vor-update.sql
sudo apt install ./releases/stempeluhr_5.6.10_all.deb
sudo systemctl status stempeluhr --no-pager
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/version
```

Das Paket löscht keine Datenbank und entfernt bei Updates weder `/etc/stempeluhr/stempeluhr.env` noch `/var/lib/stempeluhr`.

## GitHub Actions bei normalen Pushes

Der Workflow `.github/workflows/debian-package.yml` baut bei relevanten Änderungen dasselbe Paket auf GitHub. Das Ergebnis wird 14 Tage als Workflow-Artefakt gespeichert. Ein normaler Push auf `main` veröffentlicht kein dauerhaftes Release.

## GitHub Release veröffentlichen

Ein Release wird ausschließlich durch einen Versions-Tag ausgelöst. Vorher müssen lokaler Build, Upgrade und Healthcheck erfolgreich gewesen sein.

```bash
cd /home/pi/Stempeluhr
git pull --ff-only origin main
git status
git tag -a v5.6.10 -m "Stempeluhr Professional 5.6.10"
git push origin v5.6.10
```

Der Workflow verweigert die Veröffentlichung, wenn der Tag nicht exakt zu `version.txt` passt.

Bei Erfolg werden unter **GitHub → Releases** dauerhaft veröffentlicht:

```text
stempeluhr_5.6.10_all.deb
stempeluhr_5.6.10_all.deb.sha256
stempeluhr_5.6.10_BUILD_REPORT.md
stempeluhr_5.6.10_changelog.md
```

Die Release Notes enthalten außerdem die Installations- und Prüfbefehle sowie automatisch den Abschnitt `5.6.10` aus `changelog.md`.

## Installation aus GitHub

Nach dem Herunterladen beider Dateien:

```bash
sha256sum -c stempeluhr_5.6.10_all.deb.sha256
sudo dpkg -i stempeluhr_5.6.10_all.deb
```

Ein GitHub Release gilt erst als freigegeben, wenn der Actions-Lauf erfolgreich ist und die veröffentlichten Dateien tatsächlich vorhanden und geprüft sind.
