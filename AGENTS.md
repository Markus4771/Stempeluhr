# Stempeluhr – Projektwissen

## Projekt

Webbasierte Zeiterfassung für Debian-Server und Raspberry-Pi-Terminals.
Python, FastAPI, SQLAlchemy, SQLite (Standard) und PostgreSQL (optional).

## Wichtige Pfade

- `app/main.py` – FastAPI-App, Middleware, Routen-Registrierung
- `app/routes/` – API-Routen; `common.py` enthält die Session-/Auth-Helfer
- `app/services/worktime.py` – Arbeitszeitberechnung, Monatsreport
- `app/services/booking_state.py` – Zustandsautomat für Buchungen
- `app/services/network_security.py` – Sicherheitsprüfung je Anfrage
- `app/services/startup_checks.py` – Prüfungen beim Start
- `app/core/config.py` – Konfiguration inkl. `SECRET_KEY`
- `app/db_migrations.py` – nummerierte Migrationen (`_m013_…` etc.)
- `app/models.py` – SQLAlchemy-Modelle
- `version.txt`, `app/version.py`, `debian/control`, `projekt.yaml` – Versionsstände

## Versionsstände

Die Version steht **parallel** in `version.txt`, `app/version.py`,
`debian/control`, `projekt.yaml` und in den CI-Workflows. Beim Ändern
müssen alle Stellen gleichzeitig angepasst werden, sonst schlägt der
Versionscheck in CI fehl.

## Build und Test

```
pip install -r requirements.txt
PYTHONPATH=. python3 -m pytest tests/ -q
python3 -m ruff check <geänderte Dateien> --select F,E9,B
bash -n debian/postinst && bash -n scripts/build_release.sh
```

Der Aufruf mit `PYTHONPATH=.` ist nötig, weil die Tests `app.` importieren.

## Bekanntes aus dem Audit (2026-11)

- Die 12 doppelt registrierten Routen sind dokumentiert, aber **nicht**
  entfernt: Welcher Handler gelten soll, ist eine fachliche Entscheidung.
- `ruff check app/` meldet ~3200 vorbestehende Befunde (fast alle F401
  ungenutzte Importe). Nur die geänderten Dateien prüfen, sonst entsteht
  ein irreführender Eindruck.
- Der Session-Schlüssel wird aus `STEMPELUHR_SECRET_KEY` oder aus
  `/var/lib/stempeluhr/secret_key` gelesen, sonst zufällig erzeugt (0600).
  Vorhersagbare Platzhalter werden abgewiesen. Beim Update können bestehende
  Sessions ungültig werden, solange noch kein Schlüssel hinterlegt ist.

## Git-Historie

Das Audit ist in drei versionstrenne Commits aufgeteilt, jeder Commit ist
für sich lauffähig und getestet (47 / 57 / 131 Tests):

- `f8a3e53` – 5.6.36 Performance, Indizes, CI-Routencheck
- `e2b1fed` – 5.6.37 sicherer Session-Schlüssel
- `f49af20` – 5.6.38 Tests für den Buchungs-Zustandsautomaten

Branch `feature/optimierung-5-6-36-bis-5-6-38`, PR #5 gegen `main`.

## Umgang mit Commits

Versionen dürfen nicht in fremden Commits "mitgezogen" werden. Wer eine
Version anhebt, setzt alle Versionsdateien in **demselben** Commit.
