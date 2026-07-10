# Stempeluhr Modulebene ab Version 5.2.03

Dieser Ordner ist die neue Zielstruktur für die schrittweise Modularisierung.

Wichtig: In 5.2.03 werden bestehende Routen noch nicht verschoben. Die Version legt die neue Struktur an und dokumentiert die zukünftige Zuordnung, damit der laufende Stand stabil bleibt.

Geplante Modulbereiche:

- `auth` – Login, Sessions, Passwortfunktionen
- `dashboard` – Startseite, Raspberry-Ansicht, Schnellbuchung
- `employees` – Mitarbeiterverwaltung, Abteilungen, Rollen
- `attendance` – Kommen/Gehen, Arbeitszeiten, Korrekturen
- `absences` – Urlaub, Krankheit, Berufsschule, sonstige Abwesenheiten
- `calendar` – CalDAV, Feiertage, Abwesenheitskalender, ICS-Export
- `reports` – Auswertungen, PDF, Export
- `updates` – GUI-Update, Build-Status, Update-Runner
- `api` – REST-API, API-Token, externe Integrationen
- `system` – Systemeinstellungen, Sicherheit, HTTPS, NTP, DSGVO
- `rfid` – RFID-Leser, Anlernen, Terminalkommunikation
- `core` – gemeinsame Hilfsfunktionen, Konfiguration, Version, Datenbankzugriff
