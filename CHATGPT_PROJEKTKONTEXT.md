# Stempeluhr Professional – Projektkontext

- Repository: `Markus4771/Stempeluhr`
- Entwicklungsbranch: `feature/client-server-packages-6.0.0`
- Aktuelle Version: **6.0.0**
- Plattform: Debian / Raspberry Pi OS
- Backend: FastAPI, SQLAlchemy, PostgreSQL

## Version 6.0.0

- drei Debian-Pakete: `stempeluhr-server`, `stempeluhr-terminal`, `stempeluhr-all-in-one`
- All-in-One bildet die bisherige Raspberry-Installation ab
- Server kann separat auf Debian installiert werden
- Terminal kann separat auf Raspberry Pi OS oder Debian installiert werden
- Terminaldienst: `stempeluhr-terminal.service`
- Terminalkonfiguration: `/etc/stempeluhr/terminal.env`
- gemeinsamer Paketbau: `scripts/build_packages.sh`
- bestehende PostgreSQL-Datenbank und Serverkonfiguration bleiben beim Upgrade erhalten
- Phase 1 trennt Installation und Dienste; die interne Modultrennung folgt schrittweise

## Installationspfade

- Server: `/opt/stempeluhr`
- Terminal: `/opt/stempeluhr-terminal`
- Serverdienst: `stempeluhr.service`
- Terminaldienst: `stempeluhr-terminal.service`
- Serverkonfiguration: `/etc/stempeluhr/stempeluhr.env`
- Terminalkonfiguration: `/etc/stempeluhr/terminal.env`

## Build

```bash
bash scripts/build_packages.sh
```

Ergebnis:

```text
releases/stempeluhr-server_6.0.0_all.deb
releases/stempeluhr-terminal_6.0.0_all.deb
releases/stempeluhr-all-in-one_6.0.0_all.deb
```
