# Entwurf – Stempeluhr Professional 5.5.06

> Status: Nicht veröffentlicht, nicht als fertiges Debian-Paket bestätigt und nicht zur Installation freigegeben.
>
> Maßgeblicher produktiver und im Repository bestätigter Stand ist Version 5.5.04.

Schwerpunkt dieses Entwurfs: robuste Neuinstallation auf Debian.

## Geplante Änderungen

- PostgreSQL-Benutzer `stempeluhr` bei der Installation automatisch vorbereiten.
- Datenbankpasswort bei einer Neuinstallation sicher erzeugen.
- Bestehende `/etc/stempeluhr/stempeluhr.env` respektieren und PostgreSQL-Zugang passend einrichten.
- Datenbank `stempeluhr` automatisch anlegen, falls sie fehlt.
- Rechte auf Datenbank und Schema `public` automatisch setzen.
- `.env` automatisch anlegen oder reparieren.
- Datenbankverbindung vor dem Start prüfen.
- `init_db()` und Migrationen erst nach erfolgreicher Datenbankvorbereitung ausführen.

## Freigabebedingungen

Vor einer Veröffentlichung müssen mindestens folgende Punkte erfüllt sein:

- Versionsnummern in allen verbindlichen Dateien synchronisieren.
- Syntax-, Import-, Start- und Healthchecks erfolgreich durchführen.
- Neuinstallation auf einem frischen Debian-13-System testen.
- Upgrade von Version 5.5.04 mit bestehender PostgreSQL-Datenbank testen.
- Tatsächliches Debian-Paket bauen und dessen Existenz sowie Installierbarkeit bestätigen.
- Changelog, README und Projektkontext aktualisieren.

## Diagnose für spätere Tests

```bash
cat /etc/stempeluhr/stempeluhr.env
journalctl -u stempeluhr -n 100 --no-pager
cat /opt/stempeluhr/logs/package-postinst.log
```
