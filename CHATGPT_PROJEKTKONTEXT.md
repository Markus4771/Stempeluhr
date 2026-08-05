# Stempeluhr Professional – Projektkontext

- Repository: `Markus4771/Stempeluhr`
- Branch: `main`
- Aktuelle Version: **5.6.34**
- Plattform: Debian / Raspberry Pi OS
- Backend: FastAPI, SQLAlchemy, PostgreSQL

## Version 5.6.34

- mehrere RFID-/NFC-Medien pro Mitarbeiter über `employee_rfid_media`
- automatische Übernahme bestehender RFID-Zuordnungen
- einheitliche Normalisierung von UID-Formaten für Karten, Handy und Smartwatch
- neue Medienverwaltung unter `/admin/employees/{employee_id}/rfid-media`
- Backupformat mit Manifest, SHA256-Prüfsumme und Integritätsprüfung
- atomare Backup-Erstellung und Prüfsummen für lokale sowie SMB-/NAS-Ziele

## Wichtige Pfade

- Anwendung: `/opt/stempeluhr`
- Dienst: `stempeluhr.service`
- Kiosk: `/raspberry`
- Reporting: `/reports`
- Urlaubsverwaltung: `/vacation/management`
- Dashboard-Buchung: `/dashboard/self-book`
- Mitarbeiterfreigabe: `/admin/employees/{employee_id}/self-booking`
- RFID-/NFC-Medien: `/admin/employees/{employee_id}/rfid-media`
- Stempelgründe: `/system/settings/stamp-reasons`

## Build

```bash
bash scripts/build_release.sh
sha256sum -c releases/stempeluhr_5.6.34_all.deb.sha256
```
