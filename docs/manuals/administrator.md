# Administratorhandbuch

Version 5.6.15 – Stempeluhr Professional

## Aufgabe des Administrators

Administratoren verwalten Benutzer, Rollen, Sicherheit, Backups, Updates, Schnittstellen und Systembetrieb. Der feste Benutzer `admin` dient als Notfall- und Einrichtungszugang. Das initiale Kennwort muss nach der Einrichtung geändert werden.

## Erste Schritte

- Administratorkennwort ändern.
- Unter **Systemeinstellungen → Allgemeine Einstellungen → Sicherheit** die Anmelde- und Passwortregeln prüfen.
- Systemdiagnose öffnen.
- Backup-Ziel einrichten und ein erstes Backup erstellen.
- E-Mail, Uhrzeit, Abteilungen und Terminals konfigurieren.

## Mitarbeiterverwaltung

Unter **Mitarbeiterverwaltung** können Mitarbeiter angelegt, bearbeitet, deaktiviert und Rollen zugeordnet werden. Wichtige Angaben sind Mitarbeiternummer, Name, E-Mail, Eintrittsdatum, Rolle, Abteilung, RFID-Code, Arbeitszeitmodell und Urlaubsanspruch.

Vor dem Deaktivieren eines Kontos offene Buchungen, Abwesenheiten und Korrekturen prüfen.

## Rollen und Rechte

Pfad: **Systemeinstellungen → Personal & Arbeitszeit → Rollen & Rechte**

- `Administrator` besitzt immer Vollzugriff.
- Standardrollen sind gegen Löschen geschützt.
- Eigene Rollen können mit Menü- und Funktionsrechten angelegt werden.
- Rollen mit zugeordneten Benutzern können nicht gelöscht werden.
- Das Recht **Zusatz-Programme anzeigen** steuert den Zugriff auf externe Webprogramme.

Nach Rechteänderungen sollte sich der betroffene Benutzer neu anmelden.

## Sicherheitsrichtlinien

Pfad: **Systemeinstellungen → Allgemeine Einstellungen → Sicherheit**

Konfigurierbar sind Fehlversuche bis zur Sperre, Sperrdauer, optionale IP-Sperre, Passwort-Mindestlänge sowie Anforderungen an Großbuchstaben, Kleinbuchstaben, Zahlen und Sonderzeichen. Bestehende Passwörter bleiben bis zur nächsten Änderung gültig.

## Backup und Wiederherstellung

Vor Updates und größeren Änderungen ein manuelles Backup erstellen. Ein vollständiges Backup muss PostgreSQL-Daten, allgemeine Konfiguration, Secret-Dateien und variable Anwendungsdaten enthalten.

Wiederherstellungen zuerst auf einer Test-VM prüfen. Vor einem Restore einen Snapshot erstellen.

## Updates

Empfohlener Ablauf:

1. Backup erstellen.
2. Update zuerst auf der Proxmox-Test-VM installieren.
3. `/health` und `/version` prüfen.
4. Mitarbeiter, Buchungen und Kernfunktionen testen.
5. Erst danach das Produktivsystem aktualisieren.

## Zusatz-Programme

Pfad: **Systemeinstellungen → Allgemeine Einstellungen → Zusatz-Programme**

Konfigurierbar sind Name, Beschreibung, HTTP oder HTTPS, IP beziehungsweise Hostname, Port, optionaler Pfad und Sichtbarkeit. Zugangsdaten externer Programme werden nicht gespeichert.

Beispiel:

```text
Name: Odoo
Protokoll: HTTP
Host: 10.0.0.20
Port: 8069
Pfad: web
```

## Diagnose und Fehlerbehebung

```bash
sudo systemctl status stempeluhr.service --no-pager -l
sudo journalctl -u stempeluhr.service -n 100 --no-pager
curl -sS http://127.0.0.1:8000/health
```

Bei einer nicht gefundenen Seite zuerst installierte Version, Dienststatus, Browsercache und Router-Registrierung prüfen.

## Sichere Betriebsregeln

- Nicht direkt auf dem Produktivsystem entwickeln.
- Keine Secrets in GitHub, Logs oder Diagnoseberichte schreiben.
- Regelmäßige Restore-Tests durchführen.
- Nur geprüfte und freigegebene Debian-Pakete produktiv installieren.
- Rollen nach dem Prinzip der geringsten Rechte vergeben.
