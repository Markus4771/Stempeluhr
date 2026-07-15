# Stempeluhr Professional – Projektkontext

- Repository: `Markus4771/Stempeluhr`
- Branch: `main`
- Aktuelle Version: **5.6.30**
- Plattform: Debian / Raspberry Pi OS
- Backend: FastAPI, SQLAlchemy, PostgreSQL

## Version 5.6.30

- CSV- und PDF-Report zeigen Kommen- und Gehen-Zeiten pro Tageszeile
- beide Exporte enthalten eine vollständige Liste aller Stempelzeiten
- `Aktuell anwesend` bleibt für alle angemeldeten Benutzer sichtbar
- Dashboard-Selbstbuchung ohne erneute Passworteingabe wird pro Mitarbeiter freigegeben
- Freigabe erfolgt in der Mitarbeiter-Bearbeitung
- Statusabfrage für angemeldeten Benutzer: `/api/dashboard/self-booking`
- Admin-Statusabfrage: `/api/admin/employees/{employee_id}/self-booking`
- Buchungsroute: `/dashboard/self-book`
- Einstellungsroute: `/admin/employees/{employee_id}/self-booking`
- globale Einstellung aus den allgemeinen Einstellungen ist nicht mehr maßgeblich

## Wichtige Pfade

- Anwendung: `/opt/stempeluhr`
- Dienst: `stempeluhr.service`
- Kiosk: `/raspberry`
- Reporting: `/reports`
- CSV-Export: `/reports/export.csv`
- PDF-Ansicht: `/reports/print`
- Dashboard-Metriken: `/api/dashboard/metrics`
- GitHub-Token: `/etc/stempeluhr/secrets/github_token`

## Build

```bash
bash scripts/build_release.sh
sha256sum -c releases/stempeluhr_5.6.30_all.deb.sha256
```

Vor Freigabe sind Paketbau, Dienststart, CSV/PDF mit Stempelzeiten, Rollenansichten, Mitarbeiterfreigabe der Dashboard-Buchung sowie `/health` und `/version` zu testen.
