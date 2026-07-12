# Neuer Chat – Stempeluhr Professional

Diese Datei ist der verbindliche Einstiegspunkt für jede neue ChatGPT-Unterhaltung zum Projekt **Stempeluhr Professional**.

## Aktueller Projektstand

- Repository: `Markus4771/Stempeluhr`
- Standardbranch: `main`
- aktuelle Entwicklungs- und Testversion: **5.6.14**
- letzte freigegebene Version: **5.6.13**
- 5.6.14 ist umgesetzt, aber erst nach Build und Test auf der Proxmox-Test-VM freigabefähig
- Standarddatenbank: PostgreSQL
- Zielsysteme: Debian 13 und Raspberry Pi OS
- Installationsformat: Debian-Paket

## Text für einen neuen Chat

Kopiere den folgenden Text vollständig in einen neuen Chat:

> Arbeite am GitHub-Projekt `Markus4771/Stempeluhr`. Lies zuerst `NEUER_CHAT.md`, anschließend `CHATGPT_PROJEKTKONTEXT.md`, `version.txt`, `app/version.py`, `debian/control`, `README.md` und `changelog.md`. Prüfe danach den tatsächlichen aktuellen Quellcode und bestätige mir zuerst die gefundene Version, den Freigabestatus und den für meine Aufgabe relevanten Ist-Stand. Arbeite ausschließlich auf Basis dieses Repository-Stands weiter. Bestehende Mitarbeiter, Buchungen, PostgreSQL-Daten und Konfigurationen dürfen nicht verloren gehen. Keine Rekonstruktion, keine erfundenen Dateien und keine behaupteten Builds, Pakete, Tags oder Releases ohne tatsächlich vorhandene Artefakte.

## Verbindliche Arbeitsreihenfolge

1. Repository `Markus4771/Stempeluhr` und Branch `main` prüfen.
2. `NEUER_CHAT.md` und `CHATGPT_PROJEKTKONTEXT.md` vollständig lesen.
3. Versionen aus `version.txt`, `app/version.py` und `debian/control` vergleichen.
4. `README.md` und `changelog.md` mit dem tatsächlichen Code abgleichen.
5. Betroffene Quellcodedateien, Templates, Dienste und Datenbankmodelle suchen.
6. Vorhandene Funktionen erweitern statt parallele Ersatzlösungen zu erfinden.
7. PostgreSQL-, API-, UI-, systemd- und Debian-Kompatibilität erhalten.
8. Änderungen direkt im echten GitHub-Repository umsetzen.
9. Syntax-, Import-, Start-, Health- und Versionsprüfungen vorbereiten oder durchführen.
10. Bei Versionsänderungen alle Versions- und Dokumentationsdateien synchron aktualisieren.
11. `.deb` auf der Proxmox-Test-VM installieren und testen.
12. Erst nach erfolgreichem Test eine Version freigeben oder ein GitHub Release erstellen.

## Wichtige Projektregeln

- Es gibt nur eine gemeinsame **Stempeluhr Professional**, keine unterschiedlichen Editionen.
- PostgreSQL bleibt die Standarddatenbank.
- Keine Umstellung auf SQLite ohne ausdrücklichen Auftrag.
- Bestehende Mitarbeiter, Buchungen, Einstellungen und Konfigurationen dürfen durch Updates nicht gelöscht werden.
- Keine vorhandenen Funktionen entfernen, außer der Benutzer verlangt es ausdrücklich.
- Raspberry Pi OS, Debian 13, Wayland und labwc berücksichtigen.
- Secrets, echte Passwörter, Tokens und Zugangsdaten niemals ins Repository, in Logs oder Auditdetails schreiben.
- Externe Zusatz-Programme nur als geprüfte HTTP-/HTTPS-Verknüpfung einbinden; keine fremden Zugangsdaten speichern.
- Administrator-Vollzugriff und Notfallzugang dürfen nicht versehentlich entfernt werden.
- Nicht geprüfte Annahmen deutlich kennzeichnen.
- Ein `.deb`, ZIP, Tag oder Release darf erst als fertig bezeichnet werden, wenn es tatsächlich gebaut und vorhanden ist.

## Aktuelle Funktionen von Version 5.6.14

### Rollen und Rechte

- Rollenverwaltung unter **Systemeinstellungen → Personal & Arbeitszeit → Rollen & Rechte**
- eigene Rollen mit Name, Beschreibung und Berechtigungen
- geschützte Standardrollen
- Administrator besitzt immer Vollzugriff
- Berechtigungen im vorhandenen Feld `roles.permissions`
- Navigation wird über Rollenrechte gesteuert

### Systemeinstellungs-Untermenüs

Unter **Allgemeine Einstellungen** gruppiert nach:

- Allgemein
- Personal & Arbeitszeit
- Integrationen
- Sicherheit
- Wartung

Zusätzlich:

- Alle aktivieren
- Alle deaktivieren
- wichtige Kernmenüs bleiben erreichbar

### Zusatz-Programme

- Konfiguration unter **Systemeinstellungen → Allgemeine Einstellungen → Zusatz-Programme**
- Name, Beschreibung, HTTP/HTTPS, IP/Hostname, Port, optionaler Pfad und Aktivstatus
- Programme anlegen, bearbeiten, aktivieren, deaktivieren, öffnen und löschen
- Übersicht unter **Zusatz-Programme**
- Rollenrecht steuert die Sichtbarkeit
- keine fremden Zugangsdaten in der Stempeluhr speichern

## Bei jeder neuen Version aktualisieren

- `version.txt`
- `app/version.py`
- `debian/control`
- `README.md`
- `changelog.md`
- `CHATGPT_PROJEKTKONTEXT.md`
- bei wesentlichen Änderungen `NEUER_CHAT.md`

## Aktuelles Hauptziel

Version **5.6.14** vollständig auf der Proxmox-Test-VM prüfen:

- Rollen und Berechtigungen
- Schutz der Standardrollen
- gruppierte Systemeinstellungs-Untermenüs
- Alle-aktivieren/Alle-deaktivieren
- Zusatz-Programme inklusive Bearbeitung und Aktivstatus
- rollenabhängige Navigation
- Erhalt aller Mitarbeiter und Buchungen
- `/health` und `/version`
- anschließend erst Freigabe und GitHub Release