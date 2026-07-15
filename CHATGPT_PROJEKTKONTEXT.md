# Stempeluhr Professional – Projektkontext

- Repository: `Markus4771/Stempeluhr`
- Branch: `main`
- Aktuelle Version: **5.6.29**
- Plattform: Debian / Raspberry Pi OS
- Backend: FastAPI, SQLAlchemy, PostgreSQL

## Version 5.6.29

- Dashboard wird abhängig von der Rolle reduziert dargestellt
- Mitarbeiter sehen persönliche Kennzahlen
- Teamleiter sehen Kennzahlen ihres Bereichs
- Personal und Administratoren sehen übergreifende Kennzahlen
- technische Informationen sind nur für Administratoren sichtbar
- eigene Kommen- und Gehen-Buchung für angemeldete Benutzer ist optional verfügbar
- Konfiguration: `/system/settings/general/self-booking`
- Statusabfrage: `/api/dashboard/self-booking`
- Buchungsroute: `/dashboard/self-book`
- Buchungen werden dem angemeldeten Mitarbeiter zugeordnet und protokolliert

## Wichtige Pfade

- Anwendung: `/opt/stempeluhr`
- Dienst: `stempeluhr.service`
- Kiosk: `/raspberry`
- Reporting: `/reports`
- Dashboard-Metriken: `/api/dashboard/metrics`
- GitHub-Token: `/etc/stempeluhr/secrets/github_token`

## Build

```bash
bash scripts/build_release.sh
sha256sum -c releases/stempeluhr_5.6.29_all.deb.sha256
```

Vor Freigabe sind Paketbau, Dienststart, Dashboard-Rollen, die optionale Eigenbuchung sowie `/health` und `/version` zu testen.
