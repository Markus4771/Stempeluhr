# Stempeluhr Professional – Projektkontext

- Repository: `Markus4771/Stempeluhr`
- Branch: `main`
- Aktuelle Version: **5.6.31**
- Plattform: Debian / Raspberry Pi OS
- Backend: FastAPI, SQLAlchemy, PostgreSQL

## Version 5.6.31

- Dashboard-Buchung bleibt für bestehende Mitarbeiter standardmäßig verfügbar.
- Die Berechtigung kann je Mitarbeiter verwaltet werden.
- Dashboard-Überstunden werden aus den tatsächlichen Arbeitszeitdaten berechnet.
- Eine genehmigte Überstundenanpassung dient als neuer Ausgangswert.
- CSV und PDF verwenden die erweiterten Routen mit Kommen- und Gehen-Zeiten.
- `Aktuell anwesend` bleibt für alle angemeldeten Benutzer sichtbar.

## Wichtige Pfade

- Anwendung: `/opt/stempeluhr`
- Dienst: `stempeluhr.service`
- Kiosk: `/raspberry`
- Reporting: `/reports`
- CSV-Export: `/reports/export.csv`
- PDF-Ansicht: `/reports/print`
- Dashboard-Metriken: `/api/dashboard/metrics`
- Dashboard-Buchung: `/dashboard/self-book`
- Mitarbeiterfreigabe: `/admin/employees/{employee_id}/self-booking`

## Build

```bash
bash scripts/build_release.sh
sha256sum -c releases/stempeluhr_5.6.31_all.deb.sha256
```
