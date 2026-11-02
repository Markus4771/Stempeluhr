# Optimierungsanalyse – Stempeluhr Professional 5.6.33

Analyse des Repositories `Markus4771/Stempeluhr` (Branch `main`, Commit `f93a660`).
Alle Zahlen wurden durch Messungen gegen die echte Codebasis ermittelt
(SQLite-Testdatenbank, SQLAlchemy-Query-Counter, `EXPLAIN QUERY PLAN`, Ruff).

**Kennzahlen:** 17.343 Zeilen Python, 283 Routen, 26 Route-Dateien, 1 Testdatei (9 Tests).

---

## Prio 1 – Datenbank-Performance (größter Hebel)

### 1.1 `calculate_period`: N+1-Abfragen – 4.507 Queries statt ~5

`app/services/worktime.py:242-265`

Die Schleife über die Mitarbeiter lädt pro Mitarbeiter die Zeiteinträge,
und `holiday_adjusted_target_hours()` fragt **pro Mitarbeiter × pro Tag**
nochmals zwei Einstellungen und einen Feiertag ab.

Messung (100 Mitarbeiter, 31 Tage, 8.800 Buchungen):

| Variante | Queries | Dauer |
|---|---|---|
| Ist-Zustand | **4.507** | 1.177 ms |
| Optimiert (Bulk, Prototyp verifiziert) | **4** | 130 ms |

Die 1.106 Settings- und 1.100 Holiday-Queries sind reines N+1.
Der Prototyp wurde gegen den Ist-Zustand verglichen: **Zeilenanzahl,
`net_hours`, `target_hours`, `incomplete` und alle Totals sind identisch**
(9,0× schneller, 1.127× weniger Queries).

**Status: umgesetzt in 5.6.35.**

**Umsetzung:**
- `app/services/worktime.py`:
  - `settings_dict(db)` lädt alle Einstellungen in einer Abfrage
  - `_holiday_context(db, settings)` lädt die Feiertage in einer Abfrage
  - `_iter_entries_by_employee(...)` liefert die Buchungen blockweise
    (`yield_per(500)`) statt sie alle auf einmal zu laden
  - `_day_rows(...)` berechnet die Tageszeilen eines Mitarbeiters
  - `get_break_settings()` und `holiday_adjusted_target_hours()` bleiben als
    öffentliche Schnittstellen erhalten und verhalten sich unverändert
- `tests/test_worktime_calculation.py`: 13 Tests (Abfrageanzahl, Feiertage,
  Pausen, gelöschte Buchungen, unvollständige Tage, gleichnamige Mitarbeiter)

**Nachgemessen** (100 Mitarbeiter, 31 Tage, 7.599 Buchungen, 5 Feiertage):

| | Queries | Dauer |
|---|---|---|
| Ist-Zustand | 5.940 | 1.429 ms |
| Umgesetzt | **4** | **106 ms** |

**13,5× schneller, 1.485× weniger Abfragen.** Alle 2.919 Zeilen und alle
Totals sind identisch.

**Dashboard** (`/api/dashboard/metrics`, ruft `calculate_period` je Mitarbeiter):

| | Queries | Dauer |
|---|---|---|
| Ist-Zustand | 45.300 | 6.710 ms |
| Umgesetzt | **400** | **419 ms** |

**16× schneller**, Überstundensaldo identisch.

**Speicherbedarf** bleibt begrenzt, weil die Buchungen blockweise gelesen
werden. Bei 200 Mitarbeitern und 48.000 Buchungen liegt der Peak-Speicher
bei 9,4 MB – er wächst mit der Zahl der Ergebniszeilen, nicht mit der Zahl
der Buchungen.

**Abfrageplan** der neuen Buchungsabfrage:

```
SEARCH time_entries USING INDEX ix_time_entries_employee_id_timestamp
  (employee_id=? AND timestamp>? AND timestamp<?)
```

Keine zusätzliche Sortierung der Datenbank nötig, weil die Abfrage nach
`employee_id` und `timestamp` sortiert – genau der Reihenfolge des Index.
Die Ausgabe erfolgt nach Nachname; die Zuordnung der Buchungen zum
Mitarbeiter erfolgt über die Mitarbeiter-Id, damit die Reihenfolge nicht vom
Datenbank-Plan abhängt.

**Geprüfte Randfälle** (alt gegen neu, jeweils identisch): leere
Mitarbeiterliste, Mitarbeiter ohne Buchungen, zwei Feiertage am selben Tag,
inaktiver Feiertag, Feiertagabschaltung per Einstellung, halber Feiertag mit
Faktor 0,25, ungültiger Faktor, leerer Einstellungswert, automatische Pause
ohne `only_missing_break`, nur gelöschte Buchungen, Filter auf einen
Mitarbeiter, leere Sichtbarkeitsliste.

### 1.2 `time_entries` ohne Index – Full Table Scan bestätigt

`app/models.py:103-120`

`TimeEntry` hat nur `id` mit Index. `employee_id` und `timestamp` – genau die
beiden Spalten, nach denen **jede** Buchungsabfrage filtert – sind unindiziert.

`EXPLAIN QUERY PLAN` (SQLite, als Proxy für PostgreSQL):

```
vorher:  SCAN time_entries
nachher: SEARCH time_entries USING INDEX ix_time_entries_employee_id_timestamp
          (employee_id=? AND timestamp>? AND timestamp<?)
```

**Status: umgesetzt in 5.6.34.** Index `ix_time_entries_employee_id_timestamp`
auf `(employee_id, timestamp)` in `app/models.py` und Migration 013.
Zusätzlich `ix_audit_logs_created_at` (Audit-Protokoll wächst unbegrenzt).

Gemessen bei 100 Mitarbeitern über 2 Monate (22.400 Buchungen):

| | 100 Buchungsabfragen |
|---|---|
| ohne Index | 153,2 ms |
| mit Index | 46,5 ms |

**3,30× schneller.** Die Wirkung wächst mit der Datenmenge, weil der
Tabellenscan linear mit allen Buchungen wächst.

Bewusst **kein** Index auf `holidays`: die Tabelle enthält nur nationale
Feiertage (einige Hundert Zeilen) und wächst nicht unbegrenzt.

**Umsetzung:**
- `app/models.py`: `Index("ix_time_entries_employee_id_timestamp", "employee_id", "timestamp")`
  und `Index("ix_audit_logs_created_at", "created_at")`
- `app/db_migrations.py`: Migration 013 `performance_indexes` – idempotent,
  legt die Indizes auch in bestehenden Installationen nachträglich an
- `tests/test_performance_indexes.py`: 8 Tests (Index-Anlage, Ausführungsplan,
  Migration, Idempotenz)

Die Modelle werden per `Base.metadata.create_all()` erzeugt – ein Index im
Model erzeugt ihn aber **nicht** in bestehenden Installationen. Deshalb steht
er zusätzlich in der Migrationslogik (`app/db_migrations.py`).

**Verifiziert:** Upgrade einer bestehenden Installation (altes Schema ohne
Index) → Migration legt Index an, Ausführungsplan wechselt von `SCAN` auf
`SEARCH`, alle 1.400 Testbuchungen unverändert, zweiter Migrationslauf ohne
Fehler. Index-Anlage dauert bei 22.400 Buchungen 25 ms, bei 1 Mio. Buchungen
762 ms – die Sperre beim Start ist damit unkritisch.

### 1.3 `latest_employee_statuses`: N+1 – 50 Queries für 50 Mitarbeiter

`app/routes/common.py:460`

```python
for employee_id in employee_ids:
    last = db.query(TimeEntry).filter(...).first()   # 1 Query pro Mitarbeiter
```

**Status: umgesetzt in 5.6.36.**

Die letzte Buchung je Mitarbeiter wird jetzt in einer Abfrage geladen und
danach in Python gruppiert:

```python
last_entries = (
    db.query(TimeEntry)
    .filter(TimeEntry.employee_id.in_(ids))
    .order_by(TimeEntry.employee_id.asc(), TimeEntry.timestamp.desc(), TimeEntry.id.desc())
    .all()
)
```

**Wichtiger Korrekturhinweis:** Der ursprüngliche Vorschlag dieses Berichts
(`max(TimeEntry.id)`) ist **nicht korrekt**. Die Id folgt der Anlage der
Buchung, nicht ihrer Zeitmarke. Eine später angelegte Buchung kann eine
frühere Zeitmarke haben. Bei einem Mitarbeiter mit `id=100` um 09:00 und
`id=101` um 08:00 wählt `max(id)` die falsche Buchung.

Deshalb wird nach `timestamp DESC` sortiert und bei gleicher Zeitmarke nach
`id DESC` als Tie-Breaker – das entspricht der Reihenfolge, die auch die
bisherige Einzelabfrage mit `.first()` geliefert hat.

**Nachgemessen** (50 Mitarbeiter, 165 Buchungen, davon 20 % gelöscht):

| | Queries | Ergebnis |
|---|---|---|
| Ist-Zustand | 50 | – |
| Umgesetzt | **1** | identisch |

Geprüft: leere Liste, Teilmenge, Mitarbeiter ohne Buchung, gelöschte
Buchungen (werden weiterhin berücksichtigt, wie bisher), vertauschte
Id- und Zeitmarkenfolge, gleiche Zeitmarke.

### 1.4 Middleware: 2 zusätzliche Queries pro **jedem** Request

`app/main.py:134-146` + `app/services/network_security.py`

`https_should_redirect()` und `access_allowed()` lesen dieselben
Einstellungen mehrfach aus der Datenbank – bei aktivem Admin-Filter bis zu
**6 Queries pro Request**, auch für statische Dateien und `/health`.

**Status: umgesetzt in 5.6.36.**

Beide Funktionen nehmen die Einstellungen nun als Dict entgegen. Ohne
Übergabe lesen sie selbst aus der Datenbank, damit bestehende Aufrufer
unverändert funktionieren. Die Middleware lädt die Einstellungen einmal und
gibt sie an beide Prüfungen weiter.

```python
settings = settings_dict(db)
if https_should_redirect(request, db, settings):
    ...
allowed, reason = access_allowed(request, db, settings)
```

**Nachgemessen** im laufenden System mit allen drei Netzfiltern aktiv:

| | Queries je Request |
|---|---|
| Ist-Zustand | bis zu 6 |
| Umgesetzt | **1** |

**Verhalten unverändert**, geprüft mit 180 Kombinationen aus Pfad, Protokoll
(`http`/`https`) und neun Filterkonfigurationen – keine Abweichung.

---

## Prio 2 – Korrektheit und tote Code-Pfade

### 2.1 12 doppelt registrierte Routen – der zweite Handler ist toter Code

FastAPI/Starlette registriert den **ersten** Handler; alle weiteren werden
stillschweigend ignoriert. FastAPI warnt nur, wenn zusätzlich der
**Funktionsname** übereinstimmt:

```
UserWarning: Duplicate Operation ID delete_role_system_settings_roles__role_id__delete_post
  for function delete_role at app/routes/roles_rights.py
```

**Wichtiger:** FastAPI warnt *nicht*, wenn zwei verschiedene Funktionen
denselben Pfad bedienen. Diese Fälle sind gravierender, weil beim Lesen
des Codes nicht erkennbar ist, welcher Handler wirklich läuft.

**Ursache (empirisch ermittelt, 288 Routen geprüft):** FastAPI erzeugt die
Operation-ID aus Pfad und Methode, nicht aus dem Funktionsnamen. Die
Duplikate entstehen, weil **verschiedene Module denselben Pfad bedienen**.
Der Router in `app/routes/__init__.py` ist daran **nicht** beteiligt – er
wird in `app/main.py` gar nicht eingebunden. Ein Test mit entferntem
Router ergab unverändert 12 Konflikte.

Alle 12 Konflikte, jeweils mit dem tatsächlich erreichbaren Handler:

| Pfad | Methode | Erreichbar | Toter Code |
|---|---|---|---|
| `/` | GET | `dashboard.py:index` | `dashboard_privacy.py:privacy_dashboard_home` |
| `/dashboard` | GET | `dashboard.py:dashboard` | `dashboard_privacy.py:privacy_dashboard_alias` |
| `/api/dashboard/metrics` | GET | `dashboard_metrics.py:dashboard_metrics` | `dashboard_metrics_corrected.py:corrected_dashboard_metrics` |
| `/dashboard/self-book` | POST | `dashboard_self_booking.py:dashboard_self_book` | `dashboard_self_booking_extended.py:dashboard_self_book_extended` |
| `/login` | GET | `security_login.py:secure_login_form` | `dashboard.py:login_form` |
| `/login` | POST | `security_login.py:secure_login_submit` | `dashboard.py:login_submit` |
| `/onboarding/{token}` | POST | `security_login.py:secure_onboarding_submit` | `onboarding.py:onboarding_accept_submit` |
| `/password-reset/{token}` | GET | `security_login.py:secure_password_reset_form` | `dashboard.py:password_reset_form` |
| `/password-reset/{token}` | POST | `security_login.py:secure_password_reset_submit` | `dashboard.py:password_reset_submit` |
| `/system/settings/caldav` | GET | `vacation.py:system_caldav_settings` | `caldav_accounts.py:caldav_accounts_page` |
| `/system/settings/roles` | GET | `roles.py:roles_settings` | `roles_rights.py:roles_rights_page` |
| `/system/settings/roles/{role_id}/delete` | POST | `roles.py:delete_role` | `roles_rights.py:delete_role` |

**Beachtenswert:** Die Datei `dashboard_metrics_corrected.py` enthält die
*korrigierte* Kennzahlenberechnung und wird nie ausgeführt. Ob die
korrigierte oder die ursprüngliche Variante gelten soll, ist eine
fachliche Entscheidung.

**Status: CI-Prüfung ergänzt in 5.6.36, Auflösung offen.**

`tests/test_route_duplicates.py` enthält zwei Prüfungen:

1. `test_no_new_duplicate_routes` – nutzt die FastAPI-Warnung und erkennt
   Duplikate mit gleichem Funktionsnamen.
2. `test_no_new_route_conflicts` – geht die registrierten Routen selbst
   durch und erkennt **alle** mehrfach belegten Pfad+Methoden-Kombinationen.
   Das ist die strengere Prüfung; sie fand drei Konflikte, die die
   FastAPI-Warnung nicht meldet (`/`, `/api/dashboard/metrics`,
   `/dashboard/self-book`).

Beide Prüfungen sind **gegengeprüft**: Eine temporär eingebaute doppelte
Route ließ die Suite wie erwartet fehlschlagen.

**Noch offen:** Welche Variante gewollt ist, ist eine fachliche
Entscheidung und wurde **nicht** automatisch getroffen:

| Variante | Verhalten |
|---|---|
| `roles.py:delete_role` | `require_system_admin_response`, Redirect mit Meldung in die Query-Parameter |
| `roles_rights.py:delete_role` | `require_admin_response`, wirft `HTTPException` (404/400) |

**Empfehlung:** Je Pfad genau eine Implementierung behalten. Danach kann
`KNOWN_ROUTE_CONFLICTS` leer werden und der Test verschärft sich auf
„keine Konflikte".

### 2.2 `app/routes/common.py:21` – doppelter Import

```python
from app.models import ..., AbsenceType, AbsenceType
```
(Ruff `F811`/`F601`) – harmlos, aber entfernen.

### 2.3 Doppelte Settings-Helfer in fünf Modulen

`_get_setting` / `_setting` existiert in `network_security.py:14`,
`reports.py:12`, `api_v1.py:40` plus `get_setting` in `settings_service.py:5`.
Alle tun das Gleiche. `common.py` um 380 Zeilen verkürzen und `common.py`
als Fassaden-Modul auflösen.

---

## Prio 3 – Sicherheit

### 3.1 Statischer Fallback für `SECRET_KEY` (kritisch) – behoben in 5.6.36

`app/core/config.py:10` (alt):

```python
SECRET_KEY = os.environ.get("STEMPELUHR_SECRET_KEY", "stempeluhr-change-me-2026-v4-3-0")
```

Wenn die Umgebungsvariable fehlt, signiert die Session mit einem **bekannten
Schlüssel** – jeder kann Session-Cookies fälschen und sich als Administrator
anmelden. `startup_checks.py` prüft die DB-Konfiguration, aber **nicht** den
Session-Schlüssel.

**Umsetzung in 5.6.36:**

| Datei | Änderung |
|---|---|
| `app/core/config.py` | Kein fester Vorgabewert. Der Schlüssel wird aus der Umgebung, sonst aus `/var/lib/stempeluhr/secret_key` gelesen, sonst zufällig erzeugt und mit Modus 0600 abgelegt. |
| `app/core/config.py` | `INSECURE_SECRET_KEYS` sperrt bekannte Platzhalter – auch wenn sie in der Umgebung gesetzt sind. |
| `app/services/startup_checks.py` | Neue Prüfung `secret_key`: meldet leeren, zu kurzen oder vorhersagbaren Schlüssel. |
| `debian/postinst` | Erzeugt bei Neuinstallation einen zufälligen `STEMPELUHR_SECRET_KEY`; trägt ihn bei Bestandsinstallationen nach, falls er fehlt. |
| `scripts/build_release.sh` | `STEMPELUHR_SECRET_KEY` in der Beispielkonfiguration ergänzt. |
| `tests/test_secret_key.py` | 10 neue Tests. |

**Bewusste Entscheidung:** Der Start wird **nicht** verweigert. Ein harter
Abbruch würde jedes Deployment brechen, in dem die Variable nicht gesetzt
ist. Stattdessen wird ein sicherer Schlüssel erzeugt und der Zustand über
den Startup-Check gemeldet.

**Wirkung:** Mit dem bisherigen Vorgabewert konnte jeder die Session
fälschen. Ab 5.6.36 ist der Schlüssel pro Installation zufällig und
unbekannt.

**Hinweis für Bestandsinstallationen:** Beim Update wird ein neuer Schlüssel
erzeugt, sofern noch keiner hinterlegt ist. **Alle bestehenden Sessions
werden dadurch ungültig** – die Benutzer müssen sich einmal neu anmelden.
Das ist der unvermeidbare Preis, wenn der bisher vorhersagbare Schlüssel
abgeschafft wird.

**Hinweis für die Ablage:** Der Schlüssel liegt in `/var/lib/stempeluhr/`
und damit im Verzeichnis der Anwendungsdaten. Wird dieses Verzeichnis
gelöscht, erzeugt der nächste Start einen neuen Schlüssel und die Sessions
verlieren ihre Gültigkeit.

### 3.2 Kein CSRF-Schutz

`grep -rni csrf app/` findet nichts. Alle Formulare (283 Routen, davon ~120
POST) verändern Daten – Buchungen, Urlaubsanträge, Lohndaten-Adjacent,
Admin-Aktionen. `same_site="lax"` schützt gegen die meisten Cross-Site-POSTs,
aber nicht vollständig (Top-Level-GET-Navigation und ältere Browser).

**Fix:** CSRF-Token pro Formular (Middleware + Jinja-Helper) oder
`starlette-csrf`-Middleware.

### 3.3 Kein Rate-Limiting auf der Anmeldung

`app/routes/security_login.py:46` – es gibt eine Sperre nach Fehlversuchen
(`login_block_status`), aber keine Drosselung *vor* dem Passwort-Hash.

### 3.4 User-Enumeration per Timing

`security_login.py:68`:

```python
if not employee or not verify_password(password or "", employee.password_hash):
```

Ist der Benutzer unbekannt, wird gar nicht gehasht → messbare Zeitdifferenz.
**Fix:** immer gegen einen Dummy-Hash prüfen.

### 3.5 `SessionMiddleware` ohne `https_only`

`app/main.py:26-31` – `https_only=False` ist hart gesetzt, auch wenn die
Installation HTTPS erzwingt. Der Session-Cookie geht bei HTTP im Klartext mit.

### 3.6 `except Exception:` – 150 Treffer

Breite Exception-Handler schlucken Fehler. In `main.py:165` führt das zu
einer generischen HTML-Fehlerseite – bei JSON-Endpunkten sollte der
Content-Type zum Fehler passen.

---

## Prio 4 – Struktur und Wartbarkeit

### 4.1 `import *` in 26 Dateien

`from .common import *` in 26 Route-Dateien. Ruff meldet **2.792
F405**-Verletzungen (undefiniertes Name durch Wildcard-Import). Der
`__all__`--Hack in `common.py:381` (`__all__ = [name for name in globals()...]`)
verhindert sogar den Export von `_*`-Namen – genau das hat laut Kommentar
in Zeile 379 schon einmal einen Bug verursacht.

**Fix:** `common.py` in echte Module aufteilen (z. B. `app/routes/_helpers/`)
und explizite Importe verwenden.

### 4.2 Riesige Dateien

| Datei | Zeilen | Funktionen |
|---|---|---|
| `app/routes/vacation.py` | 967 | 46 |
| `app/routes/api_v1.py` | 832 | 44 |
| `app/routes/common.py` | 592 | 41 |
| `app/routes/corrections.py` | 566 | 10 |
| `app/routes/backup.py` | 491 | 17 |

`corrections.py` hat 534 Zeilen in 10 Funktionen – die längste Funktion der
Codebasis.

### 4.3 Testabdeckung: 1 Testdatei für 17.343 LOC – teilweise behoben

Stand 5.6.36: Nur `tests/test_vacation_calculation.py` (9 Tests) existierte.
Ungetestet waren u. a. die Buchungs-Zustandsmaschine
(`app/services/booking_state.py`) und die Arbeitszeitberechnung
(`app/services/worktime.py`) – beides Kernlogik mit hohem Fehlerrisiko.

**Umgesetzt in 5.6.36 bis 5.6.36:**

| Testdatei | Tests | Gegenstand |
|---|---|---|
| `tests/test_vacation_calculation.py` | 9 | Urlaubsberechnung |
| `tests/test_worktime_calculation.py` | 15 | `calculate_period` inkl. Abfragezahl |
| `tests/test_performance_indexes.py` | 8 | Datenbankindizes |
| `tests/test_status_and_network.py` | 11 | Statusabfrage und Sicherheitsprüfung |
| `tests/test_route_duplicates.py` | 4 | doppelt registrierte Routen |
| `tests/test_secret_key.py` | 10 | Session-Schlüssel |
| `tests/test_booking_state.py` | 74 | Buchungs-Zustandsautomat |

**Empfehlung 9 in 5.6.36 umgesetzt:** 74 Tests für
`app/services/booking_state.py`.

Abgedeckt sind:

- **Zustandsübergänge** – alle gültigen und ungültigen Kombinationen aus
  `abwesend`, `anwesend`, `pause` und den vier Buchungstypen
- **Buchungsaliase** – `checkin`, `out`, `pause`, `pauseende` und Varianten
  mit Bindestrich oder Leerzeichen
- **Gelöschte Buchungen** – bleiben ohne Wirkung auf den Zustand
- **Tagesgrenzen** – Mitternachtsübergänge gehören zum richtigen Tag
- **Ungültige Buchungen** – werden gezählt und ändern den Zustand nicht
- **Mitarbeiterbezug** – der Zustand eines Mitarbeiters gilt nicht für
  einen anderen
- **Abfragezahl** – die Zustandsermittlung braucht keine Abfrage je Buchung

**Gegenprüfung:** Fünf eingebaute Fehler in der Zustandslogik wurden
geprüft. Alle fünf lassen die Suite wie erwartet fehlschlagen:

| Eingebauter Fehler | Erkannte Tests |
|---|---|
| Gelöschte Buchungen werden nicht mehr gefiltert | 3 |
| Ungültige Buchung setzt den Zustand auf abwesend | 1 |
| `last_valid_entry` wird nicht mehr gesetzt | 1 |
| Id-Auflösung bei gleicher Zeitmarke entfernt | 1 |
| `gehen`-Transition entfernt | 3 |

**Nebenbefund:** SQLite liefert bei gleicher Zeitmarke über den Index
bereits in Id-Reihenfolge. Die Sortierangabe `TimeEntry.id.asc()` sichert
das Verhalten für **PostgreSQL** ab, wo die Reihenfolge bei gleichem
Zeitstempel sonst unspezifiziert wäre. Der Test prüft deshalb das
tatsächlich ausgeführte SQL, nicht nur das Ergebnis.

**Noch offen:** Die Arbeitszeitberechnung (`app/services/worktime.py`) ist
über `calculate_period` hinaus nur teilweise abgedeckt. Die
Berechnung der Monatsreports und der Überstundenlisten ist weiterhin
ohne eigenen Test.

---

## Prio 5 – Betrieb

### 5.1 Scheduler-Threads halten DB-Verbindungen

`app/main.py:47-132` – vier `threading.Thread`s. Jeder erzeugt pro Tick eine
eigene Session (3 × pro Minute + 1 × alle 15 Min). Bei Postgres
`pool_size=10, max_overflow=20` ist das verkraftbar, aber die Threads laufen
mitten im Request-Betrieb.

### 5.2 `require_system_admin_response` gibt bei fehlendem Login `None` zurück

`app/routes/common.py:324-328` – der Fehlerfall ist `None, RedirectResponse`.
Das ist korrekt, aber die 120 Aufrufstellen prüfen `if redirect:` – bei
erfolgreichem Login ist `user` ein Objekt, `redirect` ist `None`. Konsistent,
aber fragil: `user` könnte versehentlich als falsy geprüft werden, wenn ein
`Employee`-Objekt mal `__bool__` definiert.

### 5.3 Keine Retention-Policy für `audit_logs`

`app/routes/dsgvo.py:46` löscht alte Audit-Logs nur manuell. Ohne
 automatischen Cleanup wächst die Tabelle unbegrenzt – bei `pool_pre_ping`
und Reports über alle Einträge ein spürbares Problem.

---

## Empfohlene Reihenfolge

| # | Maßnahme | Aufwand | Wirkung |
|---|---|---|---|
| 1 | ~~Index auf `time_entries(employee_id, timestamp)` + Migration~~ | klein | sehr hoch | **erledigt in 5.6.34** |
| 2 | ~~`calculate_period` auf Bulk-Queries umstellen~~ | mittel | sehr hoch | **erledigt in 5.6.35** |
| 3 | ~~`latest_employee_statuses` N+1 beheben~~ | klein | hoch | **erledigt in 5.6.36** |
| 4 | ~~Middleware-Settings cachen~~ | klein | hoch (jeder Request) | **erledigt in 5.6.36** |
| 5 | ~~Doppelte Routen: CI-Check~~ / Auflösung offen | mittel | hoch (Korrektheit) | **CI-Check in 5.6.36** |
| 6 | ~~`SECRET_KEY` erzwingen / Startup-Check~~ | klein | hoch (Sicherheit) | **erledigt in 5.6.36** |
| 7 | CSRF-Schutz | mittel | hoch (Sicherheit) |
| 8 | `import *` auflösen, `common.py` aufteilen | groß | mittel (Wartbarkeit) |
| 9 | ~~Tests für `booking_state`~~ / `worktime` offen | mittel | mittel (Regressionsschutz) | **`booking_state` in 5.6.36** |

### Umsetzungsstand

**5.6.36 – Tests für den Buchungs-Zustandsautomaten (umgesetzt):**

| Datei | Änderung |
|---|---|
| `tests/test_booking_state.py` | 74 Tests für `app/services/booking_state.py` |
| `.github/workflows/performance-index-tests.yml` | Buchungszustand-Tests und Syntaxprüfung ergänzt |
| `version.txt`, `app/version.py`, `debian/control`, `projekt.yaml` | Version 5.6.36 |
| `README.md`, `changelog.md`, `CHATGPT_PROJEKTKONTEXT.md` | Änderungen dokumentiert |

Die Zustandslogik der Buchungen war ungetestet. 74 Tests decken die
Übergänge, Aliase, gelöschte Buchungen, Tagesgrenzen und den
Mitarbeiterbezug ab. Fünf eingebaute Fehler wurden gegengeprüft – alle
fünf lassen die Suite fehlschlagen.

**5.6.36 – Sicherer Session-Schlüssel (umgesetzt):**

| Datei | Änderung |
|---|---|
| `app/core/config.py` | Kein fester Vorgabewert; Schlüssel aus Umgebung, Datei oder zufällig erzeugt |
| `app/services/startup_checks.py` | Neue Prüfung `secret_key` |
| `debian/postinst` | Erzeugt und ergänzt den `STEMPELUHR_SECRET_KEY` |
| `scripts/build_release.sh` | `STEMPELUHR_SECRET_KEY` in der Beispielkonfiguration |
| `tests/test_secret_key.py` | 10 neue Tests |
| `version.txt`, `app/version.py`, `debian/control`, `projekt.yaml` | Version 5.6.36 |
| `README.md`, `changelog.md`, `CHATGPT_PROJEKTKONTEXT.md` | Änderungen dokumentiert |

Mit dem bisherigen Vorgabewert `stempeluhr-change-me-2026-v4-3-0` konnte
jeder die Session fälschen und sich als Administrator anmelden. Der
Schlüssel ist jetzt pro Installation zufällig, wird mit Modus 0600
abgelegt und übersteht Neustarts.

**5.6.36 – Gebündelte Statusabfrage, Settings-Cache und Routen-Check (umgesetzt):**

| Datei | Änderung |
|---|---|
| `app/routes/common.py` | `latest_employee_statuses` ermittelt die letzte Buchung je Mitarbeiter in einer Abfrage |
| `app/services/network_security.py` | `https_should_redirect` und `access_allowed` nehmen die Einstellungen als Dict entgegen |
| `app/main.py` | Middleware lädt die Einstellungen einmal je Request |
| `tests/test_status_and_network.py` | 11 neue Tests |
| `tests/test_route_duplicates.py` | 4 neue Tests, erkennen doppelt registrierte Routen |
| `.github/workflows/performance-index-tests.yml` | CI um die neuen Tests und den Routen-Check erweitert |
| `version.txt`, `app/version.py`, `debian/control`, `projekt.yaml` | Version 5.6.36 |
| `README.md`, `changelog.md`, `CHATGPT_PROJEKTKONTEXT.md` | Änderungen dokumentiert |

Admin-Mitarbeiterliste: 50 → 1 Abfrage.
Sicherheitsprüfung: bis zu 6 → 1 Abfrage je Request.
Ergebnisse unverändert (Differenztest mit 180 Konfigurationskombinationen
für die Sicherheitsprüfung, Zufallsdaten mit gelöschten Buchungen für die
Statusabfrage).

Offen bleibt die fachliche Entscheidung, welche der beiden `delete_role`
Varianten gelten soll (siehe Abschnitt 2.1).

**5.6.35 – Bulk-Berechnung der Arbeitszeit (umgesetzt):**

| Datei | Änderung |
|---|---|
| `app/services/worktime.py` | `calculate_period` lädt Einstellungen, Feiertage und Buchungen gesammelt; Buchungen blockweise; `_day_rows`, `_holiday_context`, `_iter_entries_by_employee` neu |
| `tests/test_worktime_calculation.py` | 13 neue Tests |
| `.github/workflows/performance-index-tests.yml` | CI-Job um die neuen Tests erweitert |
| `version.txt`, `app/version.py`, `debian/control`, `projekt.yaml` | Version 5.6.35 |
| `README.md`, `changelog.md`, `CHATGPT_PROJEKTKONTEXT.md` | Änderungen dokumentiert |

Monatsreport: 5.940 → 4 Abfragen, 13,5× schneller.
Dashboard: 45.300 → 400 Abfragen, 16× schneller.
Ergebnisse unverändert (Differenztest gegen die alte Implementierung,
2.919 Zeilen ohne Abweichung, 13 Randfälle identisch).

**5.6.34 – Performance-Indizes (umgesetzt):**

| Datei | Änderung |
|---|---|
| `app/models.py` | `Index` importiert; `ix_time_entries_employee_id_timestamp`, `ix_audit_logs_created_at` |
| `app/db_migrations.py` | Migration 013 `performance_indexes` (idempotent) |
| `tests/test_performance_indexes.py` | 8 neue Tests |
| `.github/workflows/performance-index-tests.yml` | CI-Job für die Index-Tests |
| `version.txt`, `app/version.py`, `debian/control`, `projekt.yaml` | Version 5.6.34 |
| `README.md`, `changelog.md`, `CHATGPT_PROJEKTKONTEXT.md` | Änderungen dokumentiert |

Nachgewiesen: `pytest tests/` → **131 Tests grün** (9 Urlaub + 8 Index +
15 Arbeitszeit + 11 Status/Netzwerk + 4 Routen-Check + 10 Session-Schlüssel +
74 Buchungszustand).

Die beiden Maßnahmen greifen ineinander: Die Buchungsabfrage aus 5.6.35
sortiert nach `employee_id` und `timestamp` und nutzt damit direkt den Index
aus 5.6.34, ohne zusätzliche Sortierung der Datenbank.

**Bekannte Fehler in der Empfehlung 1.3:** Der ursprünglich vorgeschlagene
Ansatz `max(TimeEntry.id)` liefert die falsche Buchung, wenn eine später
angelegte Buchung eine frühere Zeitmarke hat. Umgesetzt wurde deshalb
`ORDER BY timestamp DESC, id DESC`.

## Messprotokoll

```bash
# Query-Counter
from sqlalchemy import event
@event.listens_for(engine, "before_cursor_execute")
def before(conn, cursor, statement, params, context, executemany):
    counter["n"] += 1

# Index-Wirkung
EXPLAIN QUERY PLAN SELECT * FROM time_entries
  WHERE employee_id=5 AND timestamp>='2026-10-01' AND timestamp<'2026-11-01';

# Statische Analyse
ruff check app/ --select F,E9,B,SIM,RET,ARG --statistics
```

Reproduzierbar mit den Skripten aus der Analyse-Sitzung; `pytest tests/` läuft
mit 9 grünen Tests durch.
