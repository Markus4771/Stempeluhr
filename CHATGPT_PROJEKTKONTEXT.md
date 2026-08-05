# Stempeluhr Professional – Projektkontext

- Repository: `Markus4771/Stempeluhr`
- Branch: `main`
- Aktuelle Version: **5.7.0**
- Plattform: Debian / Raspberry Pi OS
- Backend: FastAPI, SQLAlchemy, PostgreSQL

## Version 5.7.0

- moderne responsive RFID-/NFC-Medienverwaltung
- mehrere RFID-/NFC-Medien pro Mitarbeiter über `employee_rfid_media`
- entferntes Anlernen über ein ausgewähltes Raspberry-Pi-Terminal
- Browser kann auf einem anderen PC geöffnet sein; die UID wird am Raspberry gelesen
- Terminalstatus, Scanauftrag, Polling, Timeout und Fehleranzeige sind integriert
- Raspberry-Agent: `scripts/raspberry_rfid_agent.py`
- Agent-Installation: `scripts/install_rfid_agent.sh`
- systemd-Dienst: `stempeluhr-rfid-agent.service`
- Backupverbesserungen aus 5.6.34 bleiben enthalten

## Wichtige Pfade

- Anwendung: `/opt/stempeluhr`
- Dienst: `stempeluhr.service`
- RFID-Agent: `stempeluhr-rfid-agent.service`
- RFID-Agent-Konfiguration: `/etc/stempeluhr/rfid-agent.env`
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
sha256sum -c releases/stempeluhr_5.7.0_all.deb.sha256
```
