# Stempeluhr Professional – zentraler Projektkontext

> Diese Datei ist die maßgebliche Wissensbasis für neue ChatGPT-Unterhaltungen und für die weitere Entwicklung. Vor jeder Änderung müssen zusätzlich der aktuelle Quellcode, `version.txt`, `README.md` und `changelog.md` geprüft werden. Aussagen in dieser Datei, die vom Quellcode abweichen, sind an den tatsächlichen Quellcode anzupassen.

## Projektname

**Stempeluhr Professional**

Repository: `Markus4771/Stempeluhr`

## Projektbeschreibung

Stempeluhr Professional ist eine unter Debian betriebene webbasierte Zeiterfassungssoftware für Raspberry-Pi-Terminals und Linux-Server. Die Anwendung kombiniert Mitarbeiterverwaltung, Arbeitszeiterfassung, RFID-Buchungen, Rollen und Rechte, Plausibilitätsprüfungen, Reporting, Kalenderintegration, E-Mail-Funktionen, API-Zugriff, Updates, Backups sowie Raspberry-Kiosk- und Monitoring-Funktionen.

## Ziel des Projekts

Ziel ist eine professionell installierbare, updatefähige und datenschutzorientierte Zeiterfassung für kleine und mittlere Unternehmen. Die Software soll vollständig unter Debian laufen, per `.deb` installiert und aktualisiert werden können und bestehende Daten bei Updates zuverlässig erhalten.

Wichtige Leitziele:

- stabile Zeiterfassung auf Debian und Raspberry Pi
- PostgreSQL als produktive Standarddatenbank
- automatische, reproduzierbare Installation per Debian-Paket
- sichere Updates mit Backup, Selbsttest und Rollback
- zentrale Verwaltung mehrerer Raspberry-Terminals
- dokumentierte REST-API für externe Systeme
- DSGVO-konforme Nachvollziehbarkeit
- keine Rekonstruktion des Projekts: immer auf dem echten aktuellen Quellcode arbeiten

## Aktuelle Version

**5.5.04**

Die Versionsnummer ist verbindlich aus `version.txt` zu lesen. Bei jedem Release müssen mindestens folgende Dateien synchron aktualisiert werden:

- `version.txt`
- `README.md`
- `changelog.md`
- `CHATGPT_PROJEKTKONTEXT.md`

## Aktueller Funktionsstand

Nach bisherigem Projektstand gehören unter anderem folgende Bereiche zum System:

- Mitarbeiterverwaltung
- Arbeitszeiterfassung
- RFID-Buchung
- Dashboard
- Rollen- und Rechteverwaltung
- Plausibilitätsprüfung
- Korrekturworkflow
- individuelle Aktivierung der Pausenregel pro Mitarbeiter
- DSGVO-Funktionen
- REST-API mit Passwort- beziehungsweise Token-Schutz
- HTTPS und Zertifikatsverwaltung
- CalDAV- und iCal-Feiertage
- Monatsreporting
- PDF- und CSV-Export
- Teamstatistik und Fehlzeitenanalyse
- automatische E-Mails
- Update- und Backupfunktionen
- Raspberry-Kioskmodus mit Chromium
- Raspberry-Agent mit Heartbeat-Grundlage
- zentrales Monitoring
- Onboarding mit Einladungslink, Passwort-Erstsetzung und Datenschutzbestätigung

## Roadmap

### Kurzfristig – 5.5.x

- Onboarding im echten Quellcode vollständig prüfen und stabilisieren
- Einladungsstatus, Token-Ablauf und erneutes Senden zuverlässig abbilden
- Datenschutzversion und Zustimmungsprotokoll vervollständigen
- Raspberry-Heartbeat und Screenshot-Erstellung produktionsreif machen
- Monitoring und Fehlerdiagnose verbessern
- API für Mitarbeiterverwaltung vervollständigen und dokumentieren
- Installations- und Updatepfad auf Debian 13 erneut testen

### Mittelfristig – 5.6.x

- zentraler Scheduler mit nachvollziehbarem Jobstatus
- professionelles Audit- und Ereignisprotokoll
- verbesserte Backup-/Restore-Oberfläche
- automatische Integritätsprüfung
- stabiler Rollback nach fehlgeschlagenem Update
- erweiterte API-Berechtigungen und Rate-Limits

### Langfristig – 6.x

- Mehrmandantenfähigkeit
- LDAP / Active Directory / OIDC
- Zwei-Faktor-Authentifizierung
- Multi-Standort-Unterstützung
- vollständige API-Abdeckung aller Kernobjekte
- optionale mobile oder externe Terminal-Anbindung

## Offene Aufgaben (TODO)

Priorität hoch:

- tatsächlichen Stand des Onboarding-Moduls gegen Quellcode und UI prüfen
- Raspberry-Screenshot unter Wayland/labwc zuverlässig erstellen und hochladen
- Heartbeat-Status im Monitoring dauerhaft speichern und korrekt als online/offline darstellen
- Debian-Installer auf frischem Debian 13 und als Upgrade testen
- PostgreSQL-Rolle, Datenbank und Passwort idempotent einrichten
- Service-Dateien auf genau eine gültige `ExecStart`-Zeile prüfen
- alle Python-Abhängigkeiten ausschließlich aus der Projekt-Virtualenv starten

Priorität mittel:

- API-Endpunkte und Request-/Response-Schemata dokumentieren
- Monitoring-Seiten konsolidieren
- Testabdeckung für Login, Buchung, Plausibilität, Onboarding und Update erhöhen
- Changelog und README auf den tatsächlichen Stand vereinheitlichen

## Architektur

### Backend

- Python 3
- FastAPI
- Uvicorn
- SQLAlchemy
- PostgreSQL über psycopg2
- Jinja2-Templates für die Weboberfläche

### Frontend

- serverseitig gerenderte HTML-Seiten
- CSS und JavaScript unterhalb des statischen Anwendungsverzeichnisses
- responsive Ansichten für Desktop und Raspberry-Kiosk

### Datenbank

- PostgreSQL ist die produktive Standarddatenbank
- Datenbankname standardmäßig: `stempeluhr`
- Anwendungsrolle standardmäßig: `stempeluhr`
- Zugangsdaten werden über `/etc/stempeluhr/stempeluhr.env` geladen
- Migrationen müssen updatefähig und idempotent sein

### Raspberry-Terminal

- Chromium im Kioskmodus
- Wayland/labwc unter Debian 13 berücksichtigen
- User-Systemdienst `stempeluhr-agent.service`
- Konfiguration über `/etc/stempeluhr/raspberry-agent.env`
- Agent überwacht Chromium und soll Heartbeat sowie Screenshots an den Server senden

### Betrieb

- systemd verwaltet Webanwendung und Raspberry-Agent
- Anwendung wird gewöhnlich unter `/opt/stempeluhr` installiert
- Konfiguration liegt unter `/etc/stempeluhr`
- variable Daten liegen unter `/var/lib/stempeluhr`
- Logs liegen unter `/var/log` beziehungsweise im systemd-Journal

## Verzeichnisstruktur

Die tatsächliche Struktur ist vor Änderungen mit dem Repository abzugleichen. Erwartete Hauptstruktur:

```text
/
├── app/
│   ├── main.py
│   ├── database.py
│   ├── init_db.py
│   ├── models/
│   ├── routes/
│   ├── services/
│   ├── templates/
│   └── static/
├── scripts/
├── packaging/ oder debian/
├── requirements.txt
├── version.txt
├── README.md
├── changelog.md
├── CHATGPT_PROJEKTKONTEXT.md
└── NEUER_CHAT.md
```

Wichtig: Keine Datei oder Struktur aus dieser Übersicht blind annehmen. Vor jeder Änderung den echten Repository-Baum prüfen.

## Datenbankstruktur

Die exakten Modell- und Tabellennamen sind dem aktuellen Quellcode zu entnehmen. Funktional werden mindestens folgende Datenbereiche erwartet:

- Mitarbeiter / Benutzer
- Rollen und Rechte
- RFID-Zuordnungen
- Zeitbuchungen
- Korrekturen
- Arbeitszeitmodelle
- individuelle Pausenregel
- Abwesenheiten und Urlaub
- Feiertage
- Einstellungen
- Plausibilitätsverstöße beziehungsweise Versandstatus
- E-Mail- und Versandprotokolle
- Onboarding-Tokens
- Datenschutzversionen und Zustimmungen
- Raspberry-Terminals, Heartbeats, Befehle und Screenshots
- Backup- und Updatehistorie

Datenbankregeln:

- keine produktiven Daten bei Update oder Deinstallation automatisch löschen
- vor Schemaänderungen Backup vorsehen
- Migrationen wiederholbar und rückwärtskompatibel gestalten
- neue Spalten mit sinnvollen Standardwerten einführen
- PostgreSQL-Kompatibilität ist verbindlich

## API

Die API liegt unter `/api/v1` und soll langfristig die Kernfunktionen abdecken.

Bereits geplant beziehungsweise teilweise vorhanden:

```text
GET    /api/v1/health
GET    /api/v1/users
GET    /api/v1/users/{id}
POST   /api/v1/users
PUT    /api/v1/users/{id}
DELETE /api/v1/users/{id}
POST   /api/v1/users/{id}/rfid
POST   /api/v1/users/import
GET    /api/v1/users/changes
POST   /api/v1/raspberry/heartbeat
POST   /api/v1/raspberry/screenshot
GET    /api/v1/raspberry/list
```

Vor Verwendung oder Dokumentation eines Endpunkts immer prüfen, ob er im aktuellen Quellcode tatsächlich registriert und funktionsfähig ist.

API-Anforderungen:

- Authentifizierung zwingend für schreibende Endpunkte
- eindeutige Validierung mit Pydantic-Schemata
- keine sensiblen Daten in Logs oder Antworten ausgeben
- konsistente HTTP-Statuscodes
- abwärtskompatible Änderungen bevorzugen
- OpenAPI-Dokumentation aktuell halten

## Installationsanleitung

### Voraussetzungen

- Debian 13 oder kompatibles Debian-System
- Python 3.13 beziehungsweise die vom Paket unterstützte Python-Version
- PostgreSQL
- systemd
- Netzwerkzugriff auf den vorgesehenen Webport

### Installation per Debian-Paket

```bash
sudo apt install ./stempeluhr_<VERSION>_all.deb
sudo systemctl status stempeluhr --no-pager
curl http://127.0.0.1:8000/health
```

Die Installationsroutine muss:

1. Linux-Benutzer und Gruppe `stempeluhr` anlegen, falls nicht vorhanden.
2. Verzeichnisse und Rechte korrekt setzen.
3. PostgreSQL-Rolle und Datenbank idempotent anlegen.
4. bestehende Konfiguration bei Updates erhalten.
5. eine Virtualenv anlegen oder aktualisieren.
6. `requirements.txt` installieren.
7. Datenbankmigrationen ausführen.
8. systemd neu laden und den Dienst starten.
9. einen Healthcheck durchführen.
10. bei Fehlern einen klaren Installationsstatus hinterlassen.

### Standardzugriff

```text
http://<SERVER-IP>:8000
http://<SERVER-IP>:8000/raspberry
```

Der Port wird über `/etc/stempeluhr/stempeluhr.env` konfiguriert.

## Build-Anleitung

Die tatsächlichen Packaging-Dateien sind vor dem Build zu prüfen.

Typischer Debian-Build:

```bash
cd <repository>
chmod +x debian/rules 2>/dev/null || true
dpkg-buildpackage -us -uc -b
```

Alternativ kann das Projekt einen eigenen Build-Helper unter `scripts/` oder `packaging/` verwenden.

Vor jedem Release:

```bash
python3 -m compileall app
pytest
shellcheck scripts/* 2>/dev/null || true
```

Danach auf zwei Wegen testen:

- Neuinstallation auf frischem Debian 13
- Upgrade von der vorherigen produktiven Version mit vorhandener PostgreSQL-Datenbank

## Verwendete Bibliotheken

Aus `requirements.txt`:

- FastAPI
- Uvicorn Standard
- SQLAlchemy
- psycopg2-binary
- python-dotenv
- Jinja2
- python-multipart
- itsdangerous
- passlib mit bcrypt
- ReportLab
- Requests
- caldav
- icalendar
- recurring-ical-events

Die exakten Versionsstände sind derzeit nicht fest gepinnt. Vor produktiven Releases sollte geprüft werden, ob reproduzierbare Version-Pins sinnvoll sind.

## Systemdienste

### `stempeluhr.service`

- startet FastAPI/Uvicorn
- läuft unter dem Systembenutzer `stempeluhr`
- Arbeitsverzeichnis: `/opt/stempeluhr`
- liest `/etc/stempeluhr/stempeluhr.env`
- muss die Projekt-Virtualenv verwenden
- darf nur eine `ExecStart`-Direktive enthalten

### `stempeluhr-agent.service`

- systemd-Userdienst des Raspberry-Kioskbenutzers, typischerweise `pi`
- startet `/opt/stempeluhr/scripts/stempeluhr-raspberry-agent`
- überwacht Chromium
- sendet Heartbeats und verarbeitet Remote-Befehle

## Konfigurationsdateien

### `/etc/stempeluhr/stempeluhr.env`

Typische Werte:

```text
DATABASE_TYPE=postgresql
DATABASE_HOST=127.0.0.1
DATABASE_PORT=5432
DATABASE_NAME=stempeluhr
DATABASE_USER=stempeluhr
DATABASE_PASSWORD=<geheim>
HOST=0.0.0.0
PORT=8000
```

### `/etc/stempeluhr/raspberry-agent.env`

Typische Werte:

```text
STEMPELUHR_AGENT_ENABLED=1
STEMPELUHR_KIOSK_URL=http://127.0.0.1:8000/raspberry
STEMPELUHR_BROWSER=auto
STEMPELUHR_AGENT_INTERVAL=10
STEMPELUHR_START_DELAY=8
STEMPELUHR_LOG_FILE=/var/log/stempeluhr-agent.log
STEMPELUHR_CHROME_PROFILE=~/.config/stempeluhr-chromium-profile
STEMPELUHR_HEARTBEAT_ENABLED=1
STEMPELUHR_SERVER_BASE=http://127.0.0.1:8000
```

Berechtigungen müssen dem tatsächlichen Kioskbenutzer Leserechte geben. Bewährter Stand für einen Benutzer `pi`:

```text
/etc/stempeluhr                    root:pi  0750
/etc/stempeluhr/raspberry-agent.env root:pi 0640
```

Dabei ist zu beachten, dass sensible Server-Konfigurationen nicht unnötig für den Kioskbenutzer lesbar werden dürfen. Langfristig sollte die Agent-Konfiguration in einem getrennten Verzeichnis liegen.

## Wichtige Pfade

```text
/opt/stempeluhr
/opt/stempeluhr/.venv
/opt/stempeluhr/app
/opt/stempeluhr/scripts
/etc/stempeluhr/stempeluhr.env
/etc/stempeluhr/raspberry-agent.env
/var/lib/stempeluhr
/var/lib/stempeluhr/uploads
/var/lib/stempeluhr/raspberry_screenshots
/var/log/stempeluhr
/var/log/stempeluhr-agent.log
/etc/systemd/system/stempeluhr.service
/etc/systemd/user/stempeluhr-agent.service
```

## Bekannte Probleme

- Raspberry-Screenshots unter Wayland/labwc waren zuletzt noch nicht vollständig zuverlässig.
- Heartbeat funktionierte erst nach Korrektur der Leserechte auf `/etc/stempeluhr` und `raspberry-agent.env`.
- Frühere Pakete enthielten zeitweise ungültige systemd-Startzeilen mit nicht expandiertem `${PORT:-8000}`.
- Mehrere `ExecStart`-Zeilen in einer Service-Datei führten zu Startproblemen.
- PostgreSQL-Rolle und Datenbank wurden in früheren Installern nicht immer automatisch angelegt.
- Python-Abhängigkeiten wurden teilweise nicht vollständig in der Virtualenv installiert.
- Onboarding-Funktionen und Menüeinträge müssen gegen den tatsächlichen aktuellen Quellcode geprüft werden.
- README und Changelog können unterschiedliche Versionsstände anzeigen und müssen bei Releases synchronisiert werden.

## Changelog – Zusammenfassung

### 5.5.04

- Onboarding aus dem Hauptmenü entfernt
- Einladungsbutton in der Mitarbeiterverwaltung dauerhaft verfügbar

### 5.5.0

- Onboarding als Einstellungsbereich
- Einladungsmail mit Einmal-Token und Passwort-Erstsetzung
- Datenschutzbestätigung beim ersten Login beziehungsweise bei neuer Datenschutzversion
- Onboarding-Protokoll
- Benutzer-REST-API erweitert
- Plugin- und Odoo-Menüs entfernt beziehungsweise deaktiviert
- Raspberry-Monitoring und Screenshot-Funktion stabilisiert

Ältere Detailstände sind aus `changelog.md`, Git-Historie und Releases zu entnehmen.

## Entwicklungsregeln

1. **Immer den echten aktuellen Quellcode verwenden.** Keine Rekonstruktion und kein vereinfachtes Ersatzprojekt.
2. Vor Änderungen `version.txt`, `README.md`, `changelog.md` und diese Datei lesen.
3. Bestehende Funktionen nur entfernen, wenn dies ausdrücklich beauftragt wurde.
4. PostgreSQL ist die Standarddatenbank und darf nicht stillschweigend durch SQLite ersetzt werden.
5. Daten und Konfiguration müssen Updates überstehen.
6. Jede Schemaänderung benötigt eine sichere Migration.
7. systemd-Dateien müssen vor dem Release validiert werden.
8. Alle Python-Prozesse müssen die Projekt-Virtualenv verwenden.
9. Neue API-Endpunkte benötigen Authentifizierung, Validierung und Dokumentation.
10. Secrets niemals in Git committen.
11. Nach jeder Änderung mindestens Syntax-, Import-, Start- und Healthcheck durchführen.
12. Für UI-Änderungen Desktop- und Raspberry-Kiosk-Ansicht testen.
13. Releaseversionen müssen in allen Dokumentations- und Paketdateien identisch sein.
14. `CHATGPT_PROJEKTKONTEXT.md` ist bei jedem Release mitzuaktualisieren.
15. Unsichere oder nicht überprüfte Informationen als solche kennzeichnen, nicht raten.

## Automatische Aktualisierung des Projektkontexts

Eine vollständig automatische inhaltliche Dokumentation ist ohne Prüfung nicht zuverlässig. Deshalb gilt folgender verbindlicher Prozess:

- Der Release-Build oder die CI muss prüfen, dass die Version aus `version.txt` in `README.md`, `changelog.md` und `CHATGPT_PROJEKTKONTEXT.md` enthalten ist.
- Ein Release darf bei abweichenden Versionsangaben fehlschlagen.
- Bei jedem Versions-Commit muss der Entwickler die Abschnitte **Aktuelle Version**, **Roadmap**, **TODO**, **Bekannte Probleme** und **Changelog** aktualisieren.
- Änderungen an Architektur, API, Datenbank oder Systemdiensten müssen sofort in dieser Datei dokumentiert werden.

## Hinweise für neue ChatGPT-Chats

In einem neuen Chat soll der Benutzer schreiben:

> Arbeite am GitHub-Projekt `Markus4771/Stempeluhr`. Lies zuerst `NEUER_CHAT.md`, anschließend `CHATGPT_PROJEKTKONTEXT.md`, `version.txt`, `README.md` und `changelog.md`. Prüfe danach den aktuellen Quellcode und arbeite ausschließlich auf diesem Stand weiter.

Der neue Chat muss anschließend:

1. den aktuellen Repository-Stand lesen,
2. die Versionsnummer bestätigen,
3. bestehende Implementierung der betroffenen Funktion analysieren,
4. Änderungen direkt auf Basis des echten Codes vornehmen,
5. Tests und Migrationsauswirkungen beschreiben,
6. Version und Dokumentation aktualisieren,
7. keine fertigen Releases behaupten, solange Build und Dateien nicht tatsächlich erstellt wurden.
