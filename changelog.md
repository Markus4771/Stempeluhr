## 5.6.12

- Datenbankpasswort aus `stempeluhr.env` nach `/etc/stempeluhr/secrets/database.conf` ausgelagert
- bestehende Passwörter werden beim Paketupdate automatisch und ohne Rollenänderung migriert
- systemd und SQLAlchemy laden die geschützte Secret-Datei zusätzlich zur allgemeinen Konfiguration
- neue Seite `Systemeinstellungen → Sicherheit → Datenbankzugang`
- Administrator muss sein eigenes Passwort erneut bestätigen
- neues Datenbankpasswort wird auf Mindestlänge und Komplexität geprüft
- lokaler PostgreSQL-Rollenwechsel verwendet SCRAM-SHA-256
- neue Verbindung wird vor Speicherung getestet
- vorherige Konfiguration und Secret-Datei werden vor Änderung gesichert
- automatischer Rollback auf das alte PostgreSQL-Passwort bei Fehlern
- enger Root-Helfer und begrenzter sudoers-Eintrag statt allgemeiner sudo-Rechte
- Audit protokolliert nur das Ereignis, niemals Passwortwerte
- keine Datenbankmodelle oder produktiven Daten geändert

## 5.6.11

- bestehende Updateverwaltung um stabile GitHub Releases erweitert
- manuelles Hochladen von Debian-Paketen unverändert erhalten
- GitHub-Prüfung und Release Notes direkt in die vorhandene Update-Seite integriert
- `.deb` und veröffentlichte SHA256-Datei werden gemeinsam heruntergeladen und geprüft
- nur neuere Versionen mit vollständigem Release-Dateisatz werden angeboten
- geprüftes GitHub-Paket wird an denselben bestehenden Update-Runner übergeben
- Backup, Installation, Dienstneustart, Fortschrittsanzeige und Healthcheck bleiben unverändert zentral
- keine Datenbankmodelle oder produktiven Daten geändert

## 5.6.10

- automatisches GitHub-Release-System für Debian-Pakete ergänzt
- Release wird ausschließlich durch einen passenden Versions-Tag wie `v5.6.10` ausgelöst
- Tag muss exakt mit `version.txt` und den Paketmetadaten übereinstimmen
- `.deb`, SHA256, Buildbericht und Changelog werden dauerhaft am GitHub Release veröffentlicht
- Release Notes werden automatisch aus diesem Versionsabschnitt erzeugt
- normale Pushes auf `main` erzeugen weiterhin nur ein 14 Tage gespeichertes Workflow-Artefakt
- GitHub-Workflow verwendet `contents: write` ausschließlich für tagbasierte Veröffentlichungen
- bestehende Datenbank, Konfiguration und Anwendungsfunktionen bleiben unverändert

## 5.6.00

- Einrichtungsassistent als achtstufigen Wizard neu aufgebaut
- Fortschrittsanzeige, Zurück/Weiter-Navigation und Wiederaufnahme ergänzt
- Unternehmensdaten, Sprache und Zeitzone im Assistenten konfigurierbar
- Administrator- und PostgreSQL-Prüfung ergänzt
- Arbeitszeit, E-Mail, API, HTTPS und Backup im Assistenten zusammengeführt
- Raspberry-Status integriert, bestehende Dashboard-Kachel unverändert gelassen
- Abschlussprüfung mit vorhandener Systemdiagnose und Warnungsübersicht ergänzt
- Einrichtungsassistent aus der Hauptnavigation entfernt und unter `Systemeinstellungen → Wartung` eingeordnet
- bestehende Daten und Konfigurationen werden nicht überschrieben
- keine Schema-Migration erforderlich

## 5.5.09

- Offboarding aus dem Bereich `Wartung` entfernt
- Offboarding direkt neben Onboarding unter `Systemeinstellungen → Personal & Arbeitszeit` eingeordnet
- Beschreibung der Systemeinstellungsübersicht angepasst
- keine Änderungen an Datenbankmodellen oder produktiven Daten

## 5.5.08

- Systemdiagnose aus der Hauptnavigation entfernt
- Systemdiagnose in `Systemeinstellungen` unter `Wartung` integriert
- direkten Diagnosezugang im Systemstatus der Systemeinstellungen ergänzt
- Rücknavigation von der Diagnose zu den Systemeinstellungen ergänzt
- Diagnose-API und ZIP-Bericht unverändert erhalten
- keine Änderungen an Datenbankmodellen oder produktiven Daten

## 5.5.07

- neue Admin-Seite `Systemdiagnose` ergänzt
- geschützte Diagnose-API unter `/diagnostics` und `/api/v1/diagnostics`
- PostgreSQL-Verbindung, Latenz, Serverversion und Datenbestände prüfbar
- Konfigurationsdatei auf fehlende Pflichtvariablen geprüft
- Speicherplatz, wichtige Pfade und Schreibrechte geprüft
- Diagnosebericht als ZIP ohne Passwörter, Tokens oder Secrets ergänzt
- Startup-Checks um Konfiguration, Speicher und Verzeichnisrechte erweitert

## 5.5.06

- PostgreSQL-Verbindungs-URL mit `SQLAlchemy URL.create()` sicher aufgebaut
- Sonderzeichen in Datenbankpasswörtern werden korrekt verarbeitet
- lokale PostgreSQL-Verbindungen greifen nicht mehr auf `/root/.postgresql` zu
- bestehende PostgreSQL-Rollenpasswörter werden bei Updates nicht mehr verändert
- Migrationen laufen mit sauberer Umgebung des Benutzers `stempeluhr`
- bestehende Datenbank und Konfiguration bleiben erhalten

## 5.5.05

- Projektspezifischen Debian-Buildprozess erweitert
- Automatischen Buildbericht mit Version, Git-Commit, Buildzeit, Debian-/Python-Version, Paketgröße und SHA256 ergänzt
- Doppelte Datei `CHANGELOG.md` bereinigt; verbindlicher Änderungsverlauf bleibt `changelog.md`
- Versionsprüfung für Anwendung, Dokumentation und Debian-Paket synchronisiert
- Keine Änderung an produktiven Datenbankmodellen oder Zeiterfassungsfunktionen

## 5.5.04

- Onboarding aus dem Hauptmenü entfernt
- Einladungsbutton in der Mitarbeiterverwaltung dauerhaft verfügbar
- Installierter und maßgeblicher Repository-Stand auf Version 5.5.04 vereinheitlicht
- Versionsdokumentation für neue ChatGPT-Unterhaltungen ergänzt

## 5.5.0

- Onboarding als eigener Einstellungsbereich sichtbar integriert
- Einladungsmail mit Einmal-Token und Passwort-Erstsetzung
- Datenschutzbestätigung beim ersten Login / bei neuer Datenschutz-Version
- Onboarding-Protokoll in den Systemeinstellungen
- Benutzer-REST-API erweitert
- Plugin-/Odoo-Menüs entfernt bzw. deaktiviert
- Raspberry-Monitoring und Screenshot-Funktion stabilisiert
