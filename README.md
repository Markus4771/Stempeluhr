# Stempeluhr Professional 5.6.14

Webbasierte Zeiterfassung für Debian-Server und Raspberry-Pi-Terminals mit PostgreSQL, FastAPI, konfigurierbaren Rollen und Rechten, Reporting, Onboarding, Raspberry-Kioskfunktionen und Verknüpfungen zu externen Webprogrammen.

## Aktueller Stand

- Version: **5.6.14**
- Standarddatenbank: PostgreSQL
- Zielplattform: Debian 13 / Raspberry Pi OS
- Standardbranch: `main`

Änderungen dieser Version:

- neue Rollenverwaltung unter **Systemeinstellungen → Personal & Arbeitszeit → Rollen & Rechte**
- neue Rollen können mit Beschreibung und auswählbaren Berechtigungen angelegt werden
- vorhandene Rollen können bearbeitet und nicht verwendete eigene Rollen gelöscht werden
- Standardrollen bleiben gegen Löschen geschützt
- die Rolle `Administrator` behält immer Vollzugriff und kann nicht umbenannt werden
- vorhandenes Feld `roles.permissions` wird als JSON genutzt; keine neue Datenbanktabelle erforderlich
- Navigation wird anhand der Rollenberechtigungen aufgebaut
- eigene Berechtigung zum Anzeigen der Zusatz-Programme
- Systemeinstellungs-Untermenüs in den Allgemeinen Einstellungen übersichtlich nach Bereichen gruppiert
- optionale Untermenüs können gesammelt aktiviert oder deaktiviert werden
- externe Webprogramme können mit Name, Beschreibung, HTTP/HTTPS, IP-Adresse oder Hostname, Port und optionalem Pfad hinterlegt werden
- Zusatz-Programme können aktiviert, deaktiviert, bearbeitet, geöffnet und gelöscht werden
- freigeschaltete Programme erscheinen unter **Zusatz-Programme** in der Hauptnavigation
- die Stempeluhr speichert keine Zugangsdaten der verknüpften Programme
- bestehende Standardrollen erhalten rückwärtskompatible Standardrechte, solange keine individuellen Rechte gespeichert wurden
- Rollen werden weiterhin in der vorhandenen Mitarbeiterverwaltung zugeordnet
- keine produktiven Mitarbeiter-, Buchungs- oder PostgreSQL-Daten werden gelöscht

## Debian-Paket lokal bauen

```bash
bash scripts/build_release.sh
```

Ergebnis:

```text
releases/stempeluhr_5.6.14_all.deb
releases/stempeluhr_5.6.14_all.deb.sha256
releases/stempeluhr_5.6.14_build.log
releases/stempeluhr_5.6.14_BUILD_REPORT.md
```

## Test und Installation

Version 5.6.14 zuerst auf der Debian-13-Test-VM installieren. Zu testen sind Rollen anlegen, Berechtigungen speichern, Rolle einem Testbenutzer zuweisen, Navigation prüfen, Zusatz-Programme anlegen/bearbeiten/deaktivieren/öffnen, Standardrollen schützen sowie `/health` und `/version` kontrollieren.
