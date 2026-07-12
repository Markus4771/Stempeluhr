# Stempeluhr Professional 5.6.13

Webbasierte Zeiterfassung für Debian-Server und Raspberry-Pi-Terminals mit PostgreSQL, FastAPI, Rollen und Rechten, Reporting, Onboarding und Raspberry-Kioskfunktionen.

## Aktueller Stand

- Version: **5.6.13**
- Standarddatenbank: PostgreSQL
- Zielplattform: Debian 13 / Raspberry Pi OS
- Standardbranch: `main`

Änderungen dieser Version:

- konfigurierbarer Schutz gegen wiederholte Fehlanmeldungen
- Fehlversuche bis Sperre sowie Benutzer- und IP-Sperrdauer unter **Allgemeine Einstellungen → Sicherheit** einstellbar
- konfigurierbare Passwortregeln für Mindestlänge, Groß-/Kleinbuchstaben, Zahlen, Sonderzeichen, Leerzeichen und Identitätsbestandteile
- Richtlinien gelten für Onboarding, Passwort-Reset und die Änderung des festen Admin-Passworts
- der feste Benutzer `admin` darf das initiale Standardpasswort `admin123` zunächst weiter verwenden
- solange das Standardpasswort aktiv ist, erscheint nach jeder Anmeldung eine dauerhafte Sicherheitswarnung
- nach der ersten Änderung gelten alle konfigurierten Regeln; `admin123` kann nicht erneut gesetzt werden
- fehlgeschlagene und gesperrte Anmeldungen werden ohne Passwortdaten im Audit protokolliert
- bestehende Passwörter bleiben gültig, bis sie geändert werden

## Debian-Paket lokal bauen

```bash
bash scripts/build_release.sh
```

Ergebnis:

```text
releases/stempeluhr_5.6.13_all.deb
releases/stempeluhr_5.6.13_all.deb.sha256
releases/stempeluhr_5.6.13_build.log
releases/stempeluhr_5.6.13_BUILD_REPORT.md
```

## Test und Installation

Version 5.6.13 zuerst auf der Debian-13-Test-VM installieren. Besonders zu testen sind Login-Sperre, Entsperrung nach Ablauf, IP-Sperre, Passwortregeln, Onboarding, Passwort-Reset und die dauerhafte Admin-Warnung.
