# Stempeluhr Professional – Projektkontext

- Repository: `Markus4771/Stempeluhr`
- Branch: `main`
- Aktuelle Version: **5.6.28**
- Plattform: Debian / Raspberry Pi OS
- Backend: FastAPI, SQLAlchemy, PostgreSQL

## Version 5.6.28

Das Dashboard wurde korrigiert und vereinfacht:

- Anwesenheit und aktive Mitarbeiter verwenden dieselbe Datenbasis
- Anzeige kompakt als Anzahl anwesend plus `von X aktiven`
- doppelte Kachel für nicht anwesende Mitarbeiter entfernt
- Backup-Alter wird in Stunden oder Tagen angezeigt
- Systemstatus nennt den konkreten Hauptgrund wie `Backup veraltet` oder `Speicher knapp`
- E-Mail- und GitHub-Token-Hinweise werden nur in den Systemdetails angezeigt und lösen keinen roten Gesamtstatus aus
- Plausibilitäts- und Überstundenwerte bleiben rollenbezogen beziehungsweise aktionsorientiert

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
sha256sum -c releases/stempeluhr_5.6.28_all.deb.sha256
```

Vor Freigabe sind Paketbau, Dienststart, konsistente Dashboard-Werte, Warnstufen, `/health` und `/version` zu testen.
