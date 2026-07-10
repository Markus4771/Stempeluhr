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
