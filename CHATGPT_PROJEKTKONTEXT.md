# Stempeluhr Professional – Projektkontext

- Repository: `Markus4771/Stempeluhr`
- Branch: `main`
- Aktuelle Version: **5.6.32**
- Plattform: Debian / Raspberry Pi OS
- Backend: FastAPI, SQLAlchemy, PostgreSQL

## Version 5.6.32

- `Meine Zeiterfassung` enthält Kommen, Gehen, Pause Start und Pause Ende.
- Aktive Stempelgründe werden im Dashboard angeboten.
- Stempelgründe können Arbeitszeitbuchungen oder reine Personenstatus auslösen.
- Die Freigabe wird weiterhin je Mitarbeiter verwaltet.

## Wichtige Pfade

- Anwendung: `/opt/stempeluhr`
- Dienst: `stempeluhr.service`
- Kiosk: `/raspberry`
- Reporting: `/reports`
- Dashboard-Buchung: `/dashboard/self-book`
- Mitarbeiterfreigabe: `/admin/employees/{employee_id}/self-booking`
- Stempelgründe: `/system/settings/stamp-reasons`

## Build

```bash
bash scripts/build_release.sh
sha256sum -c releases/stempeluhr_5.6.32_all.deb.sha256
```
