# Stempeluhr Professional – Projektkontext

- Repository: `Markus4771/Stempeluhr`
- Branch: `main`
- Aktuelle Version: **5.6.27**
- Plattform: Debian / Raspberry Pi OS
- Backend: FastAPI, SQLAlchemy, PostgreSQL

## Version 5.6.27

Das Dashboard wurde erweitert:

- Anwesenheit als Verhältnis anwesend/aktiv
- Buchungen nach Kommen, Gehen und Pause
- Warnstufen für Plausibilität und Backup
- rollenbezogene Überstundenanzeige
- Systemstatus für Datenbank, Backup, Speicherplatz, E-Mail und GitHub-Token

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
sha256sum -c releases/stempeluhr_5.6.27_all.deb.sha256
```

Vor Freigabe sind Paketbau, Dienststart, Dashboard-Rollenansichten, Warnstufen, `/health` und `/version` zu testen.
