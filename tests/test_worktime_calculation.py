"""Regressionstests fuer die Bulk-Berechnung in calculate_period.

Die Tests sichern ab, dass die Optimierung (Punkt 2 aus docs/OPTIMIERUNG.md)
das Ergebnis nicht veraendert und die Zahl der Datenbankabfragen begrenzt
bleibt.
"""
from __future__ import annotations

import os
import sys
from datetime import date, datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.pool import NullPool

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Muss vor dem Import von app.models gesetzt sein, sonst versucht app.database
# eine PostgreSQL-Verbindung aufzubauen.
os.environ.setdefault("DATABASE_TYPE", "sqlite")

from app.models import Base, Employee, Holiday, Role, Setting, TimeEntry  # noqa: E402
from app.services.worktime import calculate_period  # noqa: E402

OCTOBER = (date(2026, 10, 1), date(2026, 10, 31))


@pytest.fixture()
def db(tmp_path):
    """Eigene SQLite-Datenbank je Test, damit die Tests unabhaengig sind."""
    engine = create_engine(
        f"sqlite:///{tmp_path / 'worktime.db'}",
        connect_args={"check_same_thread": False},
        poolclass=NullPool,
    )
    Base.metadata.create_all(engine)

    from sqlalchemy.orm import sessionmaker

    session = sessionmaker(autocommit=False, autoflush=False, bind=engine)()

    queries: list[str] = []

    @event.listens_for(engine, "before_cursor_execute")
    def _count(conn, cursor, statement, params, context, executemany):
        queries.append(statement)

    yield session, queries

    session.close()
    engine.dispose()


def _setup(session, employees=1, hours=8.0):
    session.add(Role(id=1, name="Administrator"))
    for i in range(1, employees + 1):
        session.add(Employee(
            id=i, employee_number=f"E{i:03d}", first_name=f"Max{i}", last_name=f"Mustermann{i}",
            role_id=1, active=True,
            monday_hours=hours, tuesday_hours=hours, wednesday_hours=hours,
            thursday_hours=hours, friday_hours=hours, saturday_hours=0, sunday_hours=0,
        ))
    session.commit()


def _workday(session, employee_id, day, start=8, end=16, minutes=30, deleted=False):
    session.add(TimeEntry(employee_id=employee_id, timestamp=datetime(day.year, day.month, day.day, start),
                          entry_type="kommen", method="web", deleted=deleted))
    session.add(TimeEntry(employee_id=employee_id, timestamp=datetime(day.year, day.month, day.day, 12),
                          entry_type="pause_start", method="web", deleted=deleted))
    session.add(TimeEntry(employee_id=employee_id, timestamp=datetime(day.year, day.month, day.day, 12, minutes),
                          entry_type="pause_ende", method="web", deleted=deleted))
    session.add(TimeEntry(employee_id=employee_id, timestamp=datetime(day.year, day.month, day.day, end),
                          entry_type="gehen", method="web", deleted=deleted))


def test_query_count_stays_constant_with_many_employees(db):
    """Die Abfrageanzahl darf nicht mit der Mitarbeiterzahl wachsen."""
    session, queries = db
    _setup(session, employees=40)
    for employee_id in range(1, 41):
        _workday(session, employee_id, date(2026, 10, 5))
    session.commit()

    queries.clear()
    calculate_period(session, *OCTOBER)

    # Einstellungen, Feiertage, Mitarbeiter, Buchungen - und sonst nichts.
    assert len(queries) <= 6, f"Zu viele Abfragen: {len(queries)}"


def test_query_count_does_not_depend_on_period_length(db):
    """Auch ein langer Zeitraum darf keine Abfrage pro Tag ausloesen."""
    session, queries = db
    _setup(session, employees=5)
    session.commit()

    queries.clear()
    calculate_period(session, date(2026, 1, 1), date(2026, 12, 31))

    assert len(queries) <= 6, f"Zu viele Abfragen: {len(queries)}"


def test_totals_are_correct_for_a_single_workday(db):
    """Stunden, Pausen und Soll werden korrekt berechnet."""
    session, queries = db
    _setup(session, employees=1, hours=8.0)
    _workday(session, 1, date(2026, 10, 5), start=8, end=16, minutes=30)
    session.commit()

    result = calculate_period(session, *OCTOBER)

    row = next(r for r in result["rows"] if r.date == date(2026, 10, 5))
    assert row.gross_hours == 8.0
    assert row.manual_break_hours == 0.5
    assert row.net_hours == 7.5
    assert row.target_hours == 8.0
    assert row.overtime_hours == -0.5
    assert result["totals"]["net_hours"] == 7.5


def test_full_holiday_sets_target_to_zero(db):
    """Ein ganztaegiger Feiertag setzt das Soll auf 0."""
    session, queries = db
    _setup(session, employees=1, hours=8.0)
    session.add(Holiday(name="Feiertag", date=date(2026, 10, 5), active=True, half_day=False))
    _workday(session, 1, date(2026, 10, 5))
    session.commit()

    result = calculate_period(session, *OCTOBER)

    row = next(r for r in result["rows"] if r.date == date(2026, 10, 5))
    assert row.target_hours == 0.0
    assert row.overtime_hours == row.net_hours


def test_half_holiday_halves_the_target(db):
    """Ein halber Feiertag halbiert das Soll."""
    session, queries = db
    _setup(session, employees=1, hours=8.0)
    session.add(Holiday(name="Halber Feiertag", date=date(2026, 10, 5), active=True, half_day=True))
    session.add(Setting(key="caldav_half_day_factor", value="0.5"))
    _workday(session, 1, date(2026, 10, 5))
    session.commit()

    result = calculate_period(session, *OCTOBER)

    row = next(r for r in result["rows"] if r.date == date(2026, 10, 5))
    assert row.target_hours == 4.0


def test_inactive_holiday_does_not_affect_target(db):
    """Inaktive Feiertage bleiben ohne Wirkung."""
    session, queries = db
    _setup(session, employees=1, hours=8.0)
    session.add(Holiday(name="Inaktiv", date=date(2026, 10, 5), active=False, half_day=False))
    _workday(session, 1, date(2026, 10, 5))
    session.commit()

    result = calculate_period(session, *OCTOBER)

    row = next(r for r in result["rows"] if r.date == date(2026, 10, 5))
    assert row.target_hours == 8.0


def test_holiday_setting_can_disable_the_adjustment(db):
    """Die Einstellung caldav_holidays_affect_target_hours schaltet die Anpassung ab."""
    session, queries = db
    _setup(session, employees=1, hours=8.0)
    session.add(Holiday(name="Feiertag", date=date(2026, 10, 5), active=True, half_day=False))
    session.add(Setting(key="caldav_holidays_affect_target_hours", value="false"))
    _workday(session, 1, date(2026, 10, 5))
    session.commit()

    result = calculate_period(session, *OCTOBER)

    row = next(r for r in result["rows"] if r.date == date(2026, 10, 5))
    assert row.target_hours == 8.0


def test_duplicate_holidays_on_the_same_day_use_the_first_one(db):
    """Bei zwei Feiertagen am selben Tag zaehlt der erste - wie bisher."""
    session, queries = db
    _setup(session, employees=1, hours=8.0)
    session.add(Holiday(id=10, name="Voll", date=date(2026, 10, 5), active=True, half_day=False))
    session.add(Holiday(id=11, name="Halb", date=date(2026, 10, 5), active=True, half_day=True))
    _workday(session, 1, date(2026, 10, 5))
    session.commit()

    result = calculate_period(session, *OCTOBER)

    row = next(r for r in result["rows"] if r.date == date(2026, 10, 5))
    assert row.target_hours == 0.0


def test_deleted_entries_are_ignored(db):
    """Geloeschte Buchungen zaehlen nicht zur Arbeitszeit."""
    session, queries = db
    _setup(session, employees=1, hours=8.0)
    _workday(session, 1, date(2026, 10, 5), deleted=True)
    session.commit()

    result = calculate_period(session, *OCTOBER)

    row = next(r for r in result["rows"] if r.date == date(2026, 10, 5))
    assert row.gross_hours == 0.0


def test_incomplete_day_is_flagged(db):
    """Ein Tag ohne Gehen-Buchung wird als unvollstaendig markiert."""
    session, queries = db
    _setup(session, employees=1, hours=8.0)
    session.add(TimeEntry(employee_id=1, timestamp=datetime(2026, 10, 5, 8), entry_type="kommen",
                          method="web", deleted=False))
    session.commit()

    result = calculate_period(session, *OCTOBER)

    row = next(r for r in result["rows"] if r.date == date(2026, 10, 5))
    assert row.incomplete is True


def test_auto_break_is_deducted(db):
    """Die automatische Pause wird abgezogen, wenn keine manuelle Pause vorliegt."""
    session, queries = db
    _setup(session, employees=1, hours=8.0)
    session.add(Setting(key="auto_break_enabled", value="1"))
    session.add(Setting(key="auto_break_threshold_1_hours", value="6"))
    session.add(Setting(key="auto_break_deduct_1_minutes", value="30"))
    session.add(Setting(key="auto_break_only_missing_break", value="1"))
    session.add(TimeEntry(employee_id=1, timestamp=datetime(2026, 10, 5, 8), entry_type="kommen",
                          method="web", deleted=False))
    session.add(TimeEntry(employee_id=1, timestamp=datetime(2026, 10, 5, 16), entry_type="gehen",
                          method="web", deleted=False))
    session.commit()

    result = calculate_period(session, *OCTOBER)

    row = next(r for r in result["rows"] if r.date == date(2026, 10, 5))
    assert row.gross_hours == 8.0
    assert row.auto_break_hours == 0.5
    assert row.net_hours == 7.5


def test_empty_employee_list_returns_no_rows(db):
    """Eine leere Sichtbarkeitsliste liefert keine Zeilen."""
    session, queries = db
    _setup(session, employees=3)
    session.commit()

    result = calculate_period(session, *OCTOBER, employee_ids=[])

    assert result["rows"] == []
    assert result["totals"]["net_hours"] == 0.0


def test_single_employee_filter(db):
    """Der Filter auf einen einzelnen Mitarbeiter greift."""
    session, queries = db
    _setup(session, employees=3)
    for employee_id in range(1, 4):
        _workday(session, employee_id, date(2026, 10, 5))
    session.commit()

    result = calculate_period(session, *OCTOBER, employee_id=2)

    assert {r.employee_id for r in result["rows"]} == {2}


def test_identical_names_are_kept_apart(db):
    """Mitarbeiter mit gleichem Namen bekommen ihre Buchungen korrekt zugeteilt.

    Die Buchungsabfrage laeuft in der Reihenfolge der Mitarbeiterausgabe.
    Ohne eindeutigen letzten Sortierschluessel koennten zwei gleichnamige
    Mitarbeiter vertauscht werden.
    """
    session, queries = db
    session.add(Role(id=1, name="Administrator"))
    for i in (1, 2):
        session.add(Employee(
            id=i, employee_number=f"E{i:03d}", first_name="Max", last_name="Müller",
            role_id=1, active=True,
            monday_hours=8, tuesday_hours=8, wednesday_hours=8,
            thursday_hours=8, friday_hours=8, saturday_hours=0, sunday_hours=0,
        ))
    session.commit()

    # Mitarbeiter 1 arbeitet 8 Stunden, Mitarbeiter 2 nur 4 Stunden.
    session.add(TimeEntry(employee_id=1, timestamp=datetime(2026, 10, 5, 8),
                          entry_type="kommen", method="web", deleted=False))
    session.add(TimeEntry(employee_id=1, timestamp=datetime(2026, 10, 5, 16),
                          entry_type="gehen", method="web", deleted=False))
    session.add(TimeEntry(employee_id=2, timestamp=datetime(2026, 10, 5, 8),
                          entry_type="kommen", method="web", deleted=False))
    session.add(TimeEntry(employee_id=2, timestamp=datetime(2026, 10, 5, 12),
                          entry_type="gehen", method="web", deleted=False))
    session.commit()

    result = calculate_period(session, *OCTOBER)

    by_employee = {}
    for row in result["rows"]:
        if row.date == date(2026, 10, 5):
            by_employee[row.employee_id] = row.gross_hours
    assert by_employee == {1: 8.0, 2: 4.0}


def test_employee_without_entries_gets_no_row_when_target_is_zero(db):
    """Ohne Buchungen und ohne Soll entsteht keine Zeile."""
    session, queries = db
    session.add(Role(id=1, name="Administrator"))
    session.add(Employee(
        id=1, employee_number="E001", first_name="Max", last_name="Müller",
        role_id=1, active=True,
        monday_hours=0, tuesday_hours=0, wednesday_hours=0,
        thursday_hours=0, friday_hours=0, saturday_hours=0, sunday_hours=0,
    ))
    session.commit()

    result = calculate_period(session, *OCTOBER)

    assert result["rows"] == []
