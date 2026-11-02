# Stempeluhr Professional 5.6.36

Webbasierte Zeiterfassung für Debian-Server und Raspberry-Pi-Terminals.

## Änderungen in 5.6.36



- Admin-Mitarbeiterliste ermittelt den letzten Buchungsstatus aller Mitarbeiter in einer Abfrage statt in einer je Mitarbeiter (50 statt 1 Abfragen)
- Bei gleicher Zeitmarke entscheidet die höhere Buchungs-Id, wie es bisher die Einzelabfrage getan hat
- Sicherheitsprüfung liest ihre Einstellungen nur noch einmal je Anfrage statt bis zu sechsmal (1 statt 6 Abfragen)
- Verhalten unverändert, geprüft mit 180 Kombinationen aus Pfad, Protokoll und Filterkonfiguration
- CI-Check erkennt doppelt registrierte Routen; neue Duplikate lassen den Build scheitern
- Ursache der doppelten Routen ermittelt: verschiedene Module bedienen denselben Pfad (12 Konflikte)
- CI-Check erkennt zusätzlich Duplikate, die FastAPI wegen abweichender Funktionsnamen nicht meldet

## Aktueller Stand



- Version: **5.6.36**
- Standarddatenbank: PostgreSQL
- Zielplattform: Debian / Raspberry Pi OS
- Standardbranch: `main`

## Änderungen in 5.6.33



- Urlaubswochen werden verbindlich mit fünf Arbeitstagen berechnet.
- Samstage, Sonntage und volle Feiertage werden nicht vom Urlaubskonto abgezogen.
- Halbe Feiertage und halbe Urlaubstage werden mit 0,5 Tagen berücksichtigt.
- Unterstützte Modelle: feste 5-Tage-Woche, feste Teilzeit, unregelmäßiges Jahresmodell und manueller Anspruch.
- Eintritt, Austritt und Arbeitszeitwechsel können zeitanteilig berechnet werden.
- Getrennte Konten für Jahres-, Rest-, Zusatz- und Sonderurlaub sowie ein Buchungsjournal sind enthalten.
- Betriebsferien und die Rückbuchung bei Krankheit während des Urlaubs sind administrierbar.
- Verwaltung: `/vacation/management`

## Installation



```bash
cd ~/Stempeluhr
git pull --ff-only origin main
bash scripts/build_release.sh
sudo apt install ./releases/stempeluhr_5.6.33_all.deb
```

