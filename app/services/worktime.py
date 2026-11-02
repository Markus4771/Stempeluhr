from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Iterable

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models import Employee, TimeEntry, Holiday
from app.services.settings_service import get_setting, settings_dict


@dataclass
class WorkDayResult:
    date: date
    employee_id: int
    employee_name: str
    target_hours: float
    gross_hours: float
    manual_break_hours: float
    auto_break_hours: float
    break_hours: float
    net_hours: float
    overtime_hours: float
    incomplete: bool = False


def _as_bool(value: str, default: bool = False) -> bool:
    if value is None or value == "":
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "ja", "on", "aktiv", "enabled"}


def _as_float(value: str, default: float) -> float:
    try:
        return float(str(value).replace(",", "."))
    except Exception:
        return default


def _setting_value(settings: dict, key: str, default: str) -> str:
    """Liest einen Wert aus einem bereits geladenen Settings-Dict.

    Verhält sich identisch zu get_setting: fehlender Schlüssel und leerer
    Wert werden unterschieden, ein gespeicherter None-Wert ergibt den Default.
    """
    value = settings.get(key)
    return default if value is None else value


def _break_settings_from(settings: dict) -> dict:
    """Baut die Pausenregelung aus einem bereits geladenen Settings-Dict."""
    return {
        "enabled": _as_bool(_setting_value(settings, "auto_break_enabled", "0"), False),
        "threshold_1_hours": _as_float(_setting_value(settings, "auto_break_threshold_1_hours", "6"), 6.0),
        "deduct_1_minutes": _as_float(_setting_value(settings, "auto_break_deduct_1_minutes", "30"), 30.0),
        "threshold_2_hours": _as_float(_setting_value(settings, "auto_break_threshold_2_hours", "9"), 9.0),
        "deduct_2_minutes": _as_float(_setting_value(settings, "auto_break_deduct_2_minutes", "45"), 45.0),
        "only_missing_break": _as_bool(_setting_value(settings, "auto_break_only_missing_break", "1"), True),
    }


def get_break_settings(db: Session) -> dict:
    """Liest die Pausenregelung aus den Systemeinstellungen."""
    return _break_settings_from(settings_dict(db))


def ensure_break_settings(db: Session) -> None:
    from app.services.settings_service import set_setting

    defaults = {
        "auto_break_enabled": "0",
        "auto_break_threshold_1_hours": "6",
        "auto_break_deduct_1_minutes": "30",
        "auto_break_threshold_2_hours": "9",
        "auto_break_deduct_2_minutes": "45",
        "auto_break_only_missing_break": "1",
    }
    for key, value in defaults.items():
        if get_setting(db, key, "") == "":
            set_setting(db, key, value)
    db.commit()



def _exclude_fixed_admin(query):
    """Festen Notfall-/Systemadmin aus Arbeitszeitberechnungen ausschließen."""
    if hasattr(Employee, "employee_number"):
        query = query.filter(Employee.employee_number != "admin")
    if hasattr(Employee, "username"):
        query = query.filter(Employee.username != "admin")
    if hasattr(Employee, "first_name"):
        query = query.filter(Employee.first_name != "Fester")
        query = query.filter(Employee.first_name != "admin")
    if hasattr(Employee, "last_name"):
        query = query.filter(Employee.last_name != "Admin")
        query = query.filter(Employee.last_name != "admin")
    return query

def target_hours_for_date(employee: Employee, day: date) -> float:
    values = [
        employee.monday_hours,
        employee.tuesday_hours,
        employee.wednesday_hours,
        employee.thursday_hours,
        employee.friday_hours,
        employee.saturday_hours,
        employee.sunday_hours,
    ]
    try:
        return float(values[day.weekday()] or 0.0)
    except Exception:
        return 0.0


def holiday_adjusted_target_hours(db: Session, employee: Employee, day: date) -> float:
    """Sollstunden unter Berücksichtigung importierter CalDAV-Feiertage.

    Ganztägige aktive Feiertage setzen das Soll auf 0. Halbe Feiertage reduzieren
    das Soll mit dem konfigurierten Faktor, Standard 0,5.
    """
    settings = settings_dict(db)
    context = _holiday_context(db, settings)
    return _holiday_adjusted_target(employee, day, context)


def _holiday_context(db: Session, settings: dict) -> dict:
    """Lädt Feiertage und Faktoren für die Sollberechnung in einem Durchgang.

    Die Daten werden einmal geladen statt pro Mitarbeiter und Tag. Bei
    mehreren Feiertagen am selben Tag zaehlt derselbe wie bei einer
    Einzelabfrage (der mit der kleinsten Id), damit das Ergebnis identisch
    bleibt.
    """
    affects = _as_bool(_setting_value(settings, "caldav_holidays_affect_target_hours", "true"), True)
    factor = max(0.0, min(1.0, _as_float(_setting_value(settings, "caldav_half_day_factor", "0.5"), 0.5)))
    holidays: dict[date, Holiday] = {}
    if affects:
        for holiday in db.query(Holiday).filter(Holiday.active == True).order_by(Holiday.id.asc()).all():
            holidays.setdefault(holiday.date, holiday)
    return {"affects": affects, "factor": factor, "holidays": holidays}


def _holiday_adjusted_target(employee: Employee, day: date, context: dict) -> float:
    """Sollstunden mit bereits geladenen Feiertagen (ohne Datenbankzugriff)."""
    target = target_hours_for_date(employee, day)
    if target <= 0:
        return 0.0
    if not context["affects"]:
        return target
    holiday = context["holidays"].get(day)
    if not holiday:
        return target
    if getattr(holiday, "half_day", False):
        return round(target * context["factor"], 2)
    return 0.0


def _seconds_between(start: datetime | None, end: datetime | None) -> float:
    if not start or not end or end <= start:
        return 0.0
    return (end - start).total_seconds()


def calculate_day(employee: Employee, entries: Iterable[TimeEntry], day: date, settings: dict) -> WorkDayResult:
    sorted_entries = sorted(entries, key=lambda e: e.timestamp)
    gross_seconds = 0.0
    manual_break_seconds = 0.0
    incomplete = False
    work_start = None
    pause_start = None

    for entry in sorted_entries:
        typ = entry.entry_type
        ts = entry.timestamp
        if typ == "kommen":
            if work_start is None:
                work_start = ts
            else:
                incomplete = True
                work_start = ts
        elif typ == "pause_start":
            if work_start is not None and pause_start is None:
                pause_start = ts
        elif typ == "pause_ende":
            if pause_start is not None:
                manual_break_seconds += _seconds_between(pause_start, ts)
                pause_start = None
            else:
                incomplete = True
        elif typ == "gehen":
            if work_start is not None:
                gross_seconds += _seconds_between(work_start, ts)
                work_start = None
            else:
                incomplete = True
            if pause_start is not None:
                # offene Pause bis Gehen zählen, damit die Nettozeit nicht zu hoch wird
                manual_break_seconds += _seconds_between(pause_start, ts)
                pause_start = None

    if work_start is not None or pause_start is not None:
        incomplete = True

    gross_hours = gross_seconds / 3600.0
    manual_break_hours = manual_break_seconds / 3600.0
    auto_break_hours = 0.0

    employee_auto_break_enabled = getattr(employee, "auto_break_enabled", True)
    if employee_auto_break_enabled is None:
        employee_auto_break_enabled = True

    if settings.get("enabled") and bool(employee_auto_break_enabled):
        required_minutes = 0.0
        if gross_hours > float(settings.get("threshold_2_hours", 9.0)):
            required_minutes = float(settings.get("deduct_2_minutes", 45.0))
        elif gross_hours > float(settings.get("threshold_1_hours", 6.0)):
            required_minutes = float(settings.get("deduct_1_minutes", 30.0))

        required_hours = required_minutes / 60.0
        if settings.get("only_missing_break", True):
            auto_break_hours = max(0.0, required_hours - manual_break_hours)
        else:
            auto_break_hours = required_hours

    break_hours = manual_break_hours + auto_break_hours
    net_hours = max(0.0, gross_hours - break_hours)
    target = target_hours_for_date(employee, day)

    return WorkDayResult(
        date=day,
        employee_id=employee.id,
        employee_name=f"{employee.first_name} {employee.last_name}",
        target_hours=round(target, 2),
        gross_hours=round(gross_hours, 2),
        manual_break_hours=round(manual_break_hours, 2),
        auto_break_hours=round(auto_break_hours, 2),
        break_hours=round(break_hours, 2),
        net_hours=round(net_hours, 2),
        overtime_hours=round(net_hours - target, 2),
        incomplete=incomplete,
    )


def calculate_period(db: Session, start_day: date, end_day: date, employee_id: int | None = None, employee_ids: list[int] | None = None) -> dict:
    """Berechnet Wochen-/Monatsarbeitszeit für einen Zeitraum inklusive Pausenabzug.

    employee_id filtert einen einzelnen Mitarbeiter.
    employee_ids begrenzt die sichtbare Menge nach Benutzerrechten.

    Einstellungen, Feiertage und Buchungen werden jeweils einmal geladen und
    danach im Speicher ausgewertet. Vorher wurde pro Mitarbeiter und Tag
    erneut abgefragt, was bei einem Monatsreport über alle Mitarbeiter
    mehrere tausend Einzelabfragen erzeugt hat.
    """
    settings = settings_dict(db)
    break_settings = _break_settings_from(settings)
    holiday_ctx = _holiday_context(db, settings)

    employees_query = _exclude_fixed_admin(db.query(Employee).filter(Employee.active == True))
    if employee_ids is not None:
        if not employee_ids:
            employees_query = employees_query.filter(Employee.id == -1)
        else:
            employees_query = employees_query.filter(Employee.id.in_(employee_ids))
    if employee_id:
        employees_query = employees_query.filter(Employee.id == employee_id)
    # Die Mitarbeiter-Id ist letzter Sortierschluessel, damit die Reihenfolge
    # bei gleichen Namen eindeutig ist.
    employees = employees_query.order_by(
        Employee.last_name, Employee.first_name, Employee.id
    ).all()

    start_dt = datetime.combine(start_day, time.min)
    end_dt = datetime.combine(end_day + timedelta(days=1), time.min)

    totals = {
        "target_hours": 0.0,
        "gross_hours": 0.0,
        "manual_break_hours": 0.0,
        "auto_break_hours": 0.0,
        "break_hours": 0.0,
        "net_hours": 0.0,
        "overtime_hours": 0.0,
    }

    # Die Buchungen kommen nach Mitarbeiter-Id sortiert aus der Datenbank.
    # Die Ausgabe erfolgt nach Name. Deshalb werden die Zeilen je Mitarbeiter
    # an der Position der Ausgabe abgelegt und am Ende der Reihe nach
    # ausgegeben.
    rows_by_position: dict[int, list[WorkDayResult]] = {}
    position_by_employee = {employee.id: index for index, employee in enumerate(employees)}

    entries_stream = _iter_entries_by_employee(
        db, [e.id for e in employees], start_dt, end_dt
    )
    for employee_id, by_day in entries_stream:
        employee = employees[position_by_employee[employee_id]]
        rows_by_position[position_by_employee[employee_id]] = _day_rows(
            employee, by_day, start_day, end_day, break_settings, holiday_ctx
        )

    # Mitarbeiter ohne Buchungen brauchen ihre Zeilen ebenfalls.
    for position, employee in enumerate(employees):
        if position not in rows_by_position:
            rows_by_position[position] = _day_rows(
                employee, {}, start_day, end_day, break_settings, holiday_ctx
            )

    rows: list[WorkDayResult] = []
    for position in range(len(employees)):
        rows.extend(rows_by_position.get(position, []))

    # Die Summen werden in Ausgabereihenfolge gebildet. Die Reihenfolge ist
    # relevant, weil Gleitkommaaddition nicht assoziativ ist.
    for row in rows:
        for key in totals:
            totals[key] += getattr(row, key)

    totals = {key: round(value, 2) for key, value in totals.items()}
    return {"rows": rows, "totals": totals, "break_settings": break_settings}


def _day_rows(
    employee: Employee,
    by_day: dict[date, list[TimeEntry]],
    start_day: date,
    end_day: date,
    break_settings: dict,
    holiday_ctx: dict,
) -> list[WorkDayResult]:
    """Erzeugt die Tageszeilen eines Mitarbeiters fuer den Zeitraum.

    Ein Tag erscheint, wenn er Buchungen hat oder wenn an diesem Tag Soll
    vorgegeben ist.
    """
    employee_rows: list[WorkDayResult] = []
    current = start_day
    while current <= end_day:
        day_entries = by_day.get(current, [])
        if day_entries or target_hours_for_date(employee, current) > 0:
            row = calculate_day(employee, day_entries, current, break_settings)
            adjusted_target = _holiday_adjusted_target(employee, current, holiday_ctx)
            row.target_hours = round(adjusted_target, 2)
            row.overtime_hours = round(row.net_hours - row.target_hours, 2)
            employee_rows.append(row)
        current += timedelta(days=1)
    return employee_rows


def _iter_entries_by_employee(db: Session, employee_ids: list[int], start_dt: datetime, end_dt: datetime):
    """Liefert die Buchungen des Zeitraums gruppiert nach Mitarbeiter-Id.

    Die Abfrage sortiert nach employee_id und timestamp. Damit nutzt sie den
    Index ix_time_entries_employee_id_timestamp ohne zusaetzliche Sortierung
    der Datenbank.

    Die Abfrage wird in Bloecken gelesen. Dadurch bleibt der Speicherbedarf
    niedrig, auch wenn viele Buchungen im Zeitraum liegen.
    """
    if not employee_ids:
        return

    query = (
        db.query(TimeEntry)
        .filter(
            TimeEntry.employee_id.in_(employee_ids),
            TimeEntry.timestamp >= start_dt,
            TimeEntry.timestamp < end_dt,
            or_(TimeEntry.deleted == False, TimeEntry.deleted.is_(None)),
        )
        .order_by(TimeEntry.employee_id.asc(), TimeEntry.timestamp.asc())
    )

    current_employee = None
    by_day: dict[date, list[TimeEntry]] = {}
    for entry in query.yield_per(500):
        if current_employee is not None and entry.employee_id != current_employee:
            yield current_employee, by_day
            by_day = {}
        current_employee = entry.employee_id
        by_day.setdefault(entry.timestamp.date(), []).append(entry)
    if current_employee is not None:
        yield current_employee, by_day


def _month_bounds(year: int, month: int) -> tuple[date, date]:
    start = date(year, month, 1)
    if month == 12:
        end = date(year, 12, 31)
    else:
        end = date(year, month + 1, 1) - timedelta(days=1)
    return start, end


def calculate_worktime_account(
    db: Session,
    start_day: date,
    end_day: date,
    employee_id: int | None = None,
    employee_ids: list[int] | None = None,
) -> dict:
    """Arbeitszeitkonto / Überstundenkonto für einen Zeitraum.

    Nutzt dieselbe Tagesberechnung wie die Auswertung und berücksichtigt damit:
    - manuelle und automatische Pausen
    - gelöschte Buchungen werden ignoriert
    - CalDAV-Feiertage/halbe Feiertage über holiday_adjusted_target_hours
    - individuelle Sollstunden je Wochentag aus der Mitarbeiterverwaltung

    Das Ergebnis enthält pro Mitarbeiter einen Saldo und zusätzlich Monatsgruppen.
    """
    period = calculate_period(db, start_day, end_day, employee_id, employee_ids)
    rows = period.get("rows", [])

    employees_query = _exclude_fixed_admin(db.query(Employee).filter(Employee.active == True))
    if employee_ids is not None:
        employees_query = employees_query.filter(Employee.id.in_(employee_ids) if employee_ids else Employee.id == -1)
    if employee_id:
        employees_query = employees_query.filter(Employee.id == employee_id)
    employees = employees_query.order_by(Employee.last_name, Employee.first_name).all()

    by_employee: dict[int, dict] = {}
    for emp in employees:
        by_employee[emp.id] = {
            "employee_id": emp.id,
            "employee_number": emp.employee_number,
            "employee_name": f"{emp.last_name}, {emp.first_name}",
            "target_hours": 0.0,
            "actual_hours": 0.0,
            "break_hours": 0.0,
            "plus_hours": 0.0,
            "minus_hours": 0.0,
            "saldo_hours": 0.0,
            "incomplete_days": 0,
        }

    monthly: dict[tuple[int, int, int], dict] = {}
    for row in rows:
        emp = by_employee.setdefault(row.employee_id, {
            "employee_id": row.employee_id,
            "employee_number": "",
            "employee_name": row.employee_name,
            "target_hours": 0.0,
            "actual_hours": 0.0,
            "break_hours": 0.0,
            "plus_hours": 0.0,
            "minus_hours": 0.0,
            "saldo_hours": 0.0,
            "incomplete_days": 0,
        })
        saldo = float(row.overtime_hours or 0.0)
        emp["target_hours"] += float(row.target_hours or 0.0)
        emp["actual_hours"] += float(row.net_hours or 0.0)
        emp["break_hours"] += float(row.break_hours or 0.0)
        emp["saldo_hours"] += saldo
        if saldo >= 0:
            emp["plus_hours"] += saldo
        else:
            emp["minus_hours"] += abs(saldo)
        if getattr(row, "incomplete", False):
            emp["incomplete_days"] += 1

        key = (row.employee_id, row.date.year, row.date.month)
        month_row = monthly.setdefault(key, {
            "employee_id": row.employee_id,
            "employee_name": row.employee_name,
            "year": row.date.year,
            "month": row.date.month,
            "target_hours": 0.0,
            "actual_hours": 0.0,
            "break_hours": 0.0,
            "saldo_hours": 0.0,
        })
        month_row["target_hours"] += float(row.target_hours or 0.0)
        month_row["actual_hours"] += float(row.net_hours or 0.0)
        month_row["break_hours"] += float(row.break_hours or 0.0)
        month_row["saldo_hours"] += saldo

    employee_rows = []
    for row in by_employee.values():
        for key in ("target_hours", "actual_hours", "break_hours", "plus_hours", "minus_hours", "saldo_hours"):
            row[key] = round(row[key], 2)
        employee_rows.append(row)

    monthly_rows = []
    for row in monthly.values():
        for key in ("target_hours", "actual_hours", "break_hours", "saldo_hours"):
            row[key] = round(row[key], 2)
        monthly_rows.append(row)
    monthly_rows.sort(key=lambda x: (x["employee_name"], x["year"], x["month"]))

    totals = {
        "target_hours": round(sum(r["target_hours"] for r in employee_rows), 2),
        "actual_hours": round(sum(r["actual_hours"] for r in employee_rows), 2),
        "break_hours": round(sum(r["break_hours"] for r in employee_rows), 2),
        "plus_hours": round(sum(r["plus_hours"] for r in employee_rows), 2),
        "minus_hours": round(sum(r["minus_hours"] for r in employee_rows), 2),
        "saldo_hours": round(sum(r["saldo_hours"] for r in employee_rows), 2),
        "incomplete_days": sum(r["incomplete_days"] for r in employee_rows),
    }
    return {"employees": employee_rows, "monthly": monthly_rows, "totals": totals, "days": rows}
