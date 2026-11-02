"""Tests fuer das Arbeitszeitkonto (calculate_worktime_account).

Die Funktion bucht je Mitarbeiter Saldo, Plus- und Minusstunden, Pausen und
unvollstaendige Tage und gruppiert das Ergebnis zusaetzlich nach Monaten.
Sie ist der zweite Weg, ueber den Arbeitszeit ausgewiesen wird, und war
bisher nicht getestet.
"""
from __future__ import annotations

import os
import sys
from datetime import date, datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("DATABASE_TYPE", "sqlite")

from app.models import Base, Employee, Role, TimeEntry  # noqa: E402
from app.services.worktime import calculate_worktime_account  # noqa: E402

# Mittwoch und Donnerstag, damit ein Monatswechsel im Test abgebildet ist.
DAY_ONE = date(2026, 10, 7)
DAY_TWO = date(2026, 10, 8)
NEXT_MONTH_DAY = date(2026, 11, 2)


@pytest.fixture()
def db(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'worktime_account.db'}",
        connect_args={"check_same_thread": False},
        poolclass=NullPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
    session.add(Role(id=1, name="Administrator"))
    session.commit()
    yield session
    session.close()
    engine.dispose()


def _add_employee(session, employee_id=1, hours=8.0, name="Mustermann", first="Max",
                  active=True, auto_break=True):
    session.add(Employee(
        id=employee_id, employee_number=f"E{employee_id:03d}", first_name=first,
        last_name=name, role_id=1, active=active, auto_break_enabled=auto_break,
        monday_hours=hours, tuesday_hours=hours, wednesday_hours=hours,
        thursday_hours=hours, friday_hours=hours, saturday_hours=0, sunday_hours=0,
    ))
    session.commit()


def _workday(session, employee_id, day, start=8, end=16, entry_type="kommen"):
    session.add(TimeEntry(
        employee_id=employee_id,
        timestamp=datetime(day.year, day.month, day.day, start),
        entry_type=entry_type, method="web", deleted=False,
    ))
    session.add(TimeEntry(
        employee_id=employee_id,
        timestamp=datetime(day.year, day.month, day.day, end),
        entry_type="gehen", method="web", deleted=False,
    ))
    session.commit()


def _employee_row(result, employee_id=1):
    for row in result["employees"]:
        if row["employee_id"] == employee_id:
            return row
    raise AssertionError(f"Mitarbeiter {employee_id} fehlt in {result['employees']}")


# --- Grundlagen ------------------------------------------------------------

def test_an_employee_without_bookings_gets_the_full_target_as_minus(db):
    """Ohne Buchung bleibt das Soll offen und zaehlt als Minusstunde."""
    _add_employee(db)
    result = calculate_worktime_account(db, DAY_ONE, DAY_ONE)
    row = _employee_row(result)
    assert row["actual_hours"] == 0.0
    assert row["target_hours"] == 8.0
    assert row["saldo_hours"] == -8.0
    assert row["plus_hours"] == 0.0
    assert row["minus_hours"] == 8.0
    assert row["incomplete_days"] == 0


def test_the_result_contains_the_day_rows(db):
    _add_employee(db)
    _workday(db, 1, DAY_ONE)
    result = calculate_worktime_account(db, DAY_ONE, DAY_ONE)
    assert len(result["days"]) == 1
    assert result["days"][0].date == DAY_ONE


def test_the_employee_row_carries_the_name_and_number(db):
    _add_employee(db, employee_id=7, name="Schmidt", first="Anna")
    result = calculate_worktime_account(db, DAY_ONE, DAY_ONE)
    row = _employee_row(result, 7)
    assert row["employee_name"] == "Schmidt, Anna"
    assert row["employee_number"] == "E007"


# --- Saldo -----------------------------------------------------------------

def test_a_full_workday_produces_no_balance(db):
    _add_employee(db, hours=8.0)
    _workday(db, 1, DAY_ONE, start=8, end=16)
    result = calculate_worktime_account(db, DAY_ONE, DAY_ONE)
    row = _employee_row(result)
    assert row["actual_hours"] == 8.0
    assert row["target_hours"] == 8.0
    assert row["saldo_hours"] == 0.0


def test_extra_hours_land_in_plus_hours(db):
    _add_employee(db, hours=8.0)
    _workday(db, 1, DAY_ONE, start=8, end=17)
    result = calculate_worktime_account(db, DAY_ONE, DAY_ONE)
    row = _employee_row(result)
    assert row["plus_hours"] == 1.0
    assert row["minus_hours"] == 0.0
    assert row["saldo_hours"] == 1.0


def test_missing_hours_land_in_minus_hours(db):
    _add_employee(db, hours=8.0)
    _workday(db, 1, DAY_ONE, start=8, end=14)
    result = calculate_worktime_account(db, DAY_ONE, DAY_ONE)
    row = _employee_row(result)
    assert row["minus_hours"] == 2.0
    assert row["plus_hours"] == 0.0
    assert row["saldo_hours"] == -2.0


def test_plus_and_minus_hours_are_counted_separately(db):
    _add_employee(db, hours=8.0)
    _workday(db, 1, DAY_ONE, start=8, end=17)
    _workday(db, 1, DAY_TWO, start=8, end=14)
    result = calculate_worktime_account(db, DAY_ONE, DAY_TWO)
    row = _employee_row(result)
    assert row["plus_hours"] == 1.0
    assert row["minus_hours"] == 2.0
    assert row["saldo_hours"] == -1.0


def test_a_holiday_reduces_the_target_and_therefore_the_balance(db):
    from app.models import Holiday

    _add_employee(db, hours=8.0)
    _workday(db, 1, DAY_ONE, start=8, end=16)
    db.add(Holiday(id=1, name="Feiertag", date=DAY_ONE, half_day=False, active=True))
    db.commit()
    result = calculate_worktime_account(db, DAY_ONE, DAY_ONE)
    row = _employee_row(result)
    assert row["target_hours"] == 0.0
    assert row["saldo_hours"] == 8.0


def test_deleted_entries_do_not_count(db):
    """Geloeschte Buchungen zaehlen nicht, das Soll bleibt aber offen."""
    _add_employee(db, hours=8.0)
    _workday(db, 1, DAY_ONE, start=8, end=16)
    for entry in db.query(TimeEntry).all():
        entry.deleted = True
    db.commit()
    result = calculate_worktime_account(db, DAY_ONE, DAY_ONE)
    row = _employee_row(result)
    assert row["actual_hours"] == 0.0
    assert row["target_hours"] == 8.0
    assert row["saldo_hours"] == -8.0


def test_breaks_are_counted_in_the_account(db):
    _add_employee(db, hours=8.0)
    db.add(TimeEntry(employee_id=1, timestamp=datetime(2026, 10, 7, 8),
                     entry_type="kommen", method="web"))
    db.add(TimeEntry(employee_id=1, timestamp=datetime(2026, 10, 7, 12),
                     entry_type="pause_start", method="web"))
    db.add(TimeEntry(employee_id=1, timestamp=datetime(2026, 10, 7, 12, 30),
                     entry_type="pause_ende", method="web"))
    db.add(TimeEntry(employee_id=1, timestamp=datetime(2026, 10, 7, 16),
                     entry_type="gehen", method="web"))
    db.commit()
    result = calculate_worktime_account(db, DAY_ONE, DAY_ONE)
    row = _employee_row(result)
    assert row["break_hours"] == 0.5
    assert row["actual_hours"] == 7.5


# --- Unvollstaendige Tage --------------------------------------------------

def test_a_day_without_an_exit_is_counted_as_incomplete(db):
    _add_employee(db, hours=8.0)
    db.add(TimeEntry(employee_id=1, timestamp=datetime(2026, 10, 7, 8),
                     entry_type="kommen", method="web"))
    db.commit()
    result = calculate_worktime_account(db, DAY_ONE, DAY_ONE)
    row = _employee_row(result)
    assert row["incomplete_days"] == 1


def test_incomplete_days_are_counted_per_day(db):
    _add_employee(db, hours=8.0)
    db.add(TimeEntry(employee_id=1, timestamp=datetime(2026, 10, 7, 8),
                     entry_type="kommen", method="web"))
    db.add(TimeEntry(employee_id=1, timestamp=datetime(2026, 10, 8, 8),
                     entry_type="kommen", method="web"))
    db.commit()
    result = calculate_worktime_account(db, DAY_ONE, DAY_TWO)
    assert _employee_row(result)["incomplete_days"] == 2


def test_the_totals_sum_the_incomplete_days(db):
    _add_employee(db, hours=8.0)
    db.add(TimeEntry(employee_id=1, timestamp=datetime(2026, 10, 7, 8),
                     entry_type="kommen", method="web"))
    db.commit()
    result = calculate_worktime_account(db, DAY_ONE, DAY_ONE)
    assert result["totals"]["incomplete_days"] == 1


# --- Monatsgruppen ---------------------------------------------------------

def test_the_result_is_grouped_by_month(db):
    _add_employee(db, hours=8.0)
    _workday(db, 1, DAY_ONE, start=8, end=17)
    _workday(db, 1, NEXT_MONTH_DAY, start=8, end=17)
    result = calculate_worktime_account(db, DAY_ONE, NEXT_MONTH_DAY)
    months = result["monthly"]
    assert len(months) == 2
    assert months[0]["month"] == 10
    assert months[1]["month"] == 11


def test_the_monthly_group_carries_the_saldo(db):
    _add_employee(db, hours=8.0)
    _workday(db, 1, DAY_ONE, start=8, end=17)
    result = calculate_worktime_account(db, DAY_ONE, DAY_ONE)
    month = result["monthly"][0]
    assert month["target_hours"] == 8.0
    assert month["actual_hours"] == 9.0
    assert month["saldo_hours"] == 1.0


def test_the_monthly_group_sums_up_several_days(db):
    _add_employee(db, hours=8.0)
    _workday(db, 1, DAY_ONE, start=8, end=17)
    _workday(db, 1, DAY_TWO, start=8, end=17)
    result = calculate_worktime_account(db, DAY_ONE, DAY_TWO)
    month = result["monthly"][0]
    assert month["actual_hours"] == 18.0
    assert month["saldo_hours"] == 2.0


def test_the_monthly_groups_are_sorted_by_name_and_time(db):
    _add_employee(db, employee_id=1, name="Zeta", first="Zoe", hours=8.0)
    _add_employee(db, employee_id=2, name="Alpha", first="Adam", hours=8.0)
    _workday(db, 1, DAY_ONE, start=8, end=17)
    _workday(db, 2, DAY_ONE, start=8, end=17)
    result = calculate_worktime_account(db, DAY_ONE, DAY_ONE)
    names = [m["employee_name"] for m in result["monthly"]]
    assert names == ["Adam Alpha", "Zoe Zeta"]


def test_the_monthly_name_differs_from_the_employee_name(db):
    """Die Monatszeile nutzt "Vorname Nachname", die Mitarbeiterzeile "Nachname, Vorname".

    Das ist im Produktivcode so gewollt: Die Monatsgruppen stammen aus
    calculate_period, die Mitarbeiterzeilen aus der eigenen Abfrage.
    """
    _add_employee(db, employee_id=1, name="Mustermann", first="Max")
    _workday(db, 1, DAY_ONE, start=8, end=17)
    result = calculate_worktime_account(db, DAY_ONE, DAY_ONE)
    assert result["employees"][0]["employee_name"] == "Mustermann, Max"
    assert result["monthly"][0]["employee_name"] == "Max Mustermann"


# --- Filter ----------------------------------------------------------------

def test_a_single_employee_can_be_selected(db):
    _add_employee(db, employee_id=1, name="Alpha")
    _add_employee(db, employee_id=2, name="Beta")
    result = calculate_worktime_account(db, DAY_ONE, DAY_ONE, employee_id=2)
    assert len(result["employees"]) == 1
    assert result["employees"][0]["employee_id"] == 2


def test_the_visible_set_can_be_limited(db):
    _add_employee(db, employee_id=1, name="Alpha")
    _add_employee(db, employee_id=2, name="Beta")
    _add_employee(db, employee_id=3, name="Gamma")
    result = calculate_worktime_account(db, DAY_ONE, DAY_ONE, employee_ids=[1, 3])
    ids = sorted(r["employee_id"] for r in result["employees"])
    assert ids == [1, 3]


def test_an_empty_visible_set_returns_no_employees(db):
    _add_employee(db, employee_id=1)
    result = calculate_worktime_account(db, DAY_ONE, DAY_ONE, employee_ids=[])
    assert result["employees"] == []
    assert result["totals"]["saldo_hours"] == 0.0


def test_an_inactive_employee_is_not_counted(db):
    _add_employee(db, employee_id=1, active=False)
    result = calculate_worktime_account(db, DAY_ONE, DAY_ONE)
    assert result["employees"] == []


def test_several_employees_are_kept_apart(db):
    _add_employee(db, employee_id=1, name="Mustermann", first="Max")
    _add_employee(db, employee_id=2, name="Mustermann", first="Max")
    _workday(db, 1, DAY_ONE, start=8, end=17)
    _workday(db, 2, DAY_ONE, start=8, end=14)
    result = calculate_worktime_account(db, DAY_ONE, DAY_ONE)
    assert len(result["employees"]) == 2
    assert sorted(r["saldo_hours"] for r in result["employees"]) == [-2.0, 1.0]


# --- Summen ----------------------------------------------------------------

def test_the_totals_add_up_the_employees(db):
    _add_employee(db, employee_id=1, name="Alpha")
    _add_employee(db, employee_id=2, name="Beta")
    _workday(db, 1, DAY_ONE, start=8, end=17)
    _workday(db, 2, DAY_ONE, start=8, end=14)
    result = calculate_worktime_account(db, DAY_ONE, DAY_ONE)
    totals = result["totals"]
    assert totals["actual_hours"] == 15.0
    assert totals["plus_hours"] == 1.0
    assert totals["minus_hours"] == 2.0
    assert totals["saldo_hours"] == -1.0


def test_the_totals_are_zero_without_employees(db):
    result = calculate_worktime_account(db, DAY_ONE, DAY_ONE)
    assert result["totals"]["target_hours"] == 0.0
    assert result["totals"]["saldo_hours"] == 0.0


def test_the_totals_match_the_sum_of_the_employee_rows(db):
    _add_employee(db, employee_id=1, name="Alpha")
    _add_employee(db, employee_id=2, name="Beta")
    _workday(db, 1, DAY_ONE, start=8, end=17)
    _workday(db, 2, DAY_ONE, start=8, end=14)
    result = calculate_worktime_account(db, DAY_ONE, DAY_ONE)
    assert result["totals"]["saldo_hours"] == round(
        sum(r["saldo_hours"] for r in result["employees"]), 2
    )
