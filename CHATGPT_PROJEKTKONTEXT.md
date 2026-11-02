# Stempeluhr Professional – Projektkontext

- Repository: `Markus4771/Stempeluhr`
- Branch: `main`
- Aktuelle Version: **5.6.36**
- Plattform: Debian / Raspberry Pi OS
- Backend: FastAPI, SQLAlchemy, PostgreSQL

## Version 5.6.36




- Admin-Mitarbeiterliste ermittelt den letzten Buchungsstatus aller Mitarbeiter in einer Abfrage statt in einer je Mitarbeiter (50 statt 1 Abfragen)
- Bei gleicher Zeitmarke entscheidet die höhere Buchungs-Id, wie es bisher die Einzelabfrage getan hat
- Sicherheitsprüfung liest ihre Einstellungen nur noch einmal je Anfrage statt bis zu sechsmal (1 statt 6 Abfragen)
- Verhalten unverändert, geprüft mit 180 Kombinationen aus Pfad, Protokoll und Filterkonfiguration
- CI-Check erkennt doppelt registrierte Routen; neue Duplikate lassen den Build scheitern
- Ursache der doppelten Routen ermittelt: verschiedene Module bedienen denselben Pfad (12 Konflikte)
- CI-Check erkennt zusätzlich Duplikate, die FastAPI wegen abweichender Funktionsnamen nicht meldet

## Version 5.6.33




- Urlaubsberechnung basiert verbindlich auf einer 5-Tage-Woche.
- Samstage, Sonntage und volle Feiertage werden nicht als Urlaubstage abgezogen.
- Halbe Feiertage und halbe Urlaubstage werden mit 0,5 Tagen berücksichtigt.
- Berechnungsmodelle: 5-Tage-Woche, feste Teilzeit, unregelmäßiges Jahresmodell und manueller Anspruch.
- Eintritt, Austritt und Arbeitszeitwechsel können anteilig berechnet werden.
- Getrennte Konten für Jahresurlaub, Resturlaub, Zusatzurlaub und Sonderurlaub sind vorhanden.
- Betriebsferien, Buchungsjournal und Rückbuchung bei Krankheit während Urlaub sind ergänzt.
- Verwaltung: `/vacation/management`

## Wichtige Pfade




- Anwendung: `/opt/stempeluhr`
- Dienst: `stempeluhr.service`
- Kiosk: `/raspberry`
- Reporting: `/reports`
- Urlaubsverwaltung: `/vacation/management`
- Dashboard-Buchung: `/dashboard/self-book`
- Mitarbeiterfreigabe: `/admin/employees/{employee_id}/self-booking`
- Stempelgründe: `/system/settings/stamp-reasons`

## Build




```bash
bash scripts/build_release.sh
sha256sum -c releases/stempeluhr_5.6.33_all.deb.sha256
```

