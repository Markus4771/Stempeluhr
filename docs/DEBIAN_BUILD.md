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

## Paket bauen

```bash
cd /home/pi/Stempeluhr
chmod +x scripts/build_release.sh debian/postinst debian/prerm
./scripts/build_release.sh
```

Das Skript prüft vor dem Build:

- sauberen Git-Stand
- übereinstimmende Version in `version.txt`, `app/version.py` und `debian/control`
- Versionsangaben in README, Changelog und Projektkontext
- Python-Syntax
- Ausschluss von `.env`- und Datenbankdateien
- Paketinhalt und Paketmetadaten

## Ergebnis

Für Version 5.5.04 entstehen:

```text
releases/stempeluhr_5.5.04_all.deb
releases/stempeluhr_5.5.04_all.deb.sha256
releases/stempeluhr_5.5.04_build.log
```

## Paket prüfen

```bash
dpkg-deb --info releases/stempeluhr_5.5.04_all.deb
dpkg-deb --contents releases/stempeluhr_5.5.04_all.deb
sha256sum -c releases/stempeluhr_5.5.04_all.deb.sha256
```

## Upgrade installieren

Vor einem produktiven Upgrade zuerst PostgreSQL sichern:

```bash
sudo -u postgres pg_dump stempeluhr > /root/stempeluhr-vor-update.sql
sudo apt install ./releases/stempeluhr_5.5.04_all.deb
sudo systemctl status stempeluhr --no-pager
curl http://127.0.0.1:8000/health
```

Das Paket löscht keine Datenbank und entfernt bei Updates weder `/etc/stempeluhr/stempeluhr.env` noch `/var/lib/stempeluhr`.

## GitHub Actions

Der Workflow `.github/workflows/debian-package.yml` baut dasselbe Paket auf GitHub. Das Ergebnis wird für 14 Tage als Workflow-Artefakt gespeichert. Ein Workflow-Artefakt ist noch kein veröffentlichter GitHub-Release.
